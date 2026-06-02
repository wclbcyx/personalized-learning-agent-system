"""学生记忆读写服务。

V0.2 先使用本地 JSON 文件实现长期记忆：

    backend/data/student_profiles/{student_id}.json

这个实现足够支撑毕业设计早期演示：
    - 同一个学生多次提问，系统能保留历史记录。
    - 下一次回答时，可以把最近学习历史放入 TutorAgent 上下文。
    - 前端可以展示“这个学生之前学过什么、薄弱点是什么”。

后续升级方向：
    - SQLite/PostgreSQL：更稳定的结构化存储。
    - 向量数据库：做语义记忆检索。
    - Neo4j：构建知识点图谱和学生掌握路径。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List, Optional

from app.core.config import BACKEND_DIR
from app.models.memory import LearningMemoryItem, StudentProfile, now_iso
from app.models.schemas import LearningAnswerResponse, LearningQuestionRequest


DEFAULT_PROFILE_DIR = BACKEND_DIR / "data" / "student_profiles"


class MemoryService:
    """学生长期记忆服务。"""

    def __init__(self, profile_dir: Optional[str | Path] = None) -> None:
        """初始化记忆服务。

        Args:
            profile_dir:
                学生画像保存目录。不传时使用 backend/data/student_profiles。
        """

        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def load_profile(self, student_id: str) -> StudentProfile:
        """读取学生画像。

        如果文件不存在，就创建一个新的空画像。
        """

        path = self._profile_path(student_id)
        if not path.exists():
            return StudentProfile(student_id=student_id)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            profile = StudentProfile.from_dict(data)
            if not profile.student_id:
                profile.student_id = student_id
            return profile
        except json.JSONDecodeError:
            # 文件损坏时，不直接让系统崩溃，而是重新创建空画像。
            return StudentProfile(student_id=student_id)

    def save_profile(self, profile: StudentProfile) -> None:
        """保存学生画像到 JSON 文件。"""

        profile.updated_at = now_iso()
        path = self._profile_path(profile.student_id)
        path.write_text(
            json.dumps(profile.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_profile_from_request(
        self,
        profile: StudentProfile,
        request: LearningQuestionRequest,
    ) -> StudentProfile:
        """用本次请求里的显式信息更新学生画像。

        例如用户在前端填写了 course_name、learning_goal、current_level，
        就可以同步到长期画像中。
        """

        if request.course_name:
            profile.course_name = request.course_name
        if request.learning_goal:
            profile.learning_goal = request.learning_goal
        if request.current_level:
            profile.current_level = request.current_level
        if request.preferred_style:
            profile.preferred_style = request.preferred_style

        return profile

    def append_learning_memory(
        self,
        profile: StudentProfile,
        request: LearningQuestionRequest,
        response: LearningAnswerResponse,
    ) -> StudentProfile:
        """把一次学习问答追加到学生长期记忆中。"""

        source_ids = [source.chunk_id for source in response.sources]
        knowledge_points = self.extract_knowledge_points(
            request.question,
            [source.title for source in response.sources],
            response.answer,
        )

        memory = LearningMemoryItem(
            question=request.question,
            answer_summary=self.summarize_answer(response.answer),
            source_ids=source_ids,
            knowledge_points=knowledge_points,
            next_steps=response.next_steps,
            metadata={
                "summary": response.summary,
                "mode": response.debug.get("mode"),
                "model": response.debug.get("model"),
                "source_count": len(response.sources),
            },
        )

        profile.memories.append(memory)
        profile.weak_points = self._merge_unique(profile.weak_points, knowledge_points)
        profile.recent_recommendations = response.next_steps[:5]

        return profile

    def build_memory_context(self, profile: StudentProfile, limit: int = 5) -> str:
        """构建给 TutorAgent 使用的记忆上下文。

        这个字符串后续会拼进大模型 Prompt，让回答更个性化。
        """

        lines: List[str] = []

        lines.append(f"学生ID：{profile.student_id}")
        if profile.course_name:
            lines.append(f"学习课程：{profile.course_name}")
        if profile.learning_goal:
            lines.append(f"学习目标：{profile.learning_goal}")
        if profile.current_level:
            lines.append(f"当前水平：{profile.current_level}")
        if profile.preferred_style:
            lines.append(f"讲解偏好：{profile.preferred_style}")
        if profile.weak_points:
            lines.append(f"历史薄弱点：{', '.join(profile.weak_points[:8])}")

        recent_memories = profile.memories[-limit:]
        if recent_memories:
            lines.append("最近学习记录：")
            for item in recent_memories:
                points = "、".join(item.knowledge_points[:4]) or "未提取"
                lines.append(
                    f"- {item.created_at} 提问：{item.question}；"
                    f"摘要：{item.answer_summary}；知识点：{points}"
                )

        return "\n".join(lines)

    def _profile_path(self, student_id: str) -> Path:
        """返回某个学生画像文件路径。"""

        safe_id = self._safe_student_id(student_id)
        return self.profile_dir / f"{safe_id}.json"

    @staticmethod
    def _safe_student_id(student_id: str) -> str:
        """把 student_id 转成安全文件名。"""

        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", student_id.strip())
        return cleaned or "unknown_student"

    @staticmethod
    def summarize_answer(answer: str, max_length: int = 120) -> str:
        """从回答正文中截取一个简短摘要。"""

        compact = " ".join(answer.split())
        if len(compact) <= max_length:
            return compact
        return compact[:max_length].rstrip() + "..."

    @staticmethod
    def extract_knowledge_points(*texts: str | Iterable[str]) -> List[str]:
        """从问题、标题、回答中粗略提取知识点。

        V0.2 先用规则提取，后续可以换成 LLM 总结或知识图谱。
        """

        joined_parts: List[str] = []
        for item in texts:
            if isinstance(item, str):
                joined_parts.append(item)
            else:
                joined_parts.extend(str(value) for value in item)

        text = "\n".join(joined_parts)

        candidates = [
            "有理数",
            "数轴",
            "绝对值",
            "整式",
            "同类项",
            "一元一次方程",
            "二元一次方程组",
            "不等式",
            "不等式组",
            "一次函数",
            "反比例函数",
            "三角形",
            "全等三角形",
            "相似三角形",
            "勾股定理",
            "平行四边形",
            "圆",
            "统计",
            "概率",
        ]

        return [point for point in candidates if point in text]

    @staticmethod
    def _merge_unique(existing: List[str], new_items: List[str]) -> List[str]:
        """合并列表并保持顺序去重。"""

        merged: List[str] = []
        for item in [*existing, *new_items]:
            if item and item not in merged:
                merged.append(item)
        return merged
