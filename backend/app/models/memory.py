"""学生记忆系统的数据结构。

V0.2 的目标不是做复杂数据库，而是先让系统具备“记住学生”的能力。

当前记忆会保存到本地 JSON 文件：

    backend/data/student_profiles/{student_id}.json

记忆内容包括：
    - 学生画像
    - 历史学习记录
    - 薄弱点
    - 最近学习建议

后续可以把这里的结构迁移到 SQLite、PostgreSQL、Neo4j 或向量数据库。
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    """返回当前时间的 ISO 字符串，方便 JSON 保存。"""

    return datetime.now().isoformat(timespec="seconds")


@dataclass
class LearningMemoryItem:
    """一次学习会话记忆。

    每当学生完成一次提问，系统就可以保存一个 LearningMemoryItem。

    例子：
        学生问了“不等式为什么除以负数要变号”，系统回答后，
        就把问题、回答摘要、引用来源、下一步建议保存下来。
    """

    # 本次学习问题。
    question: str

    # AI 回答的一句话摘要。
    answer_summary: str

    # 本次命中的资料片段 ID，例如 ["doc001_chunk0005"]。
    source_ids: List[str] = field(default_factory=list)

    # 本次涉及的知识点，例如 ["不等式", "负数", "数轴"]。
    knowledge_points: List[str] = field(default_factory=list)

    # 系统给出的下一步学习建议。
    next_steps: List[str] = field(default_factory=list)

    # 本次学习发生时间。
    created_at: str = field(default_factory=now_iso)

    # 扩展字段，例如耗时、模型名、检索数量等。
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转成适合 JSON 保存的字典。"""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningMemoryItem":
        """从 JSON 字典恢复成 LearningMemoryItem。"""

        return cls(
            question=str(data.get("question", "")),
            answer_summary=str(data.get("answer_summary", "")),
            source_ids=list(data.get("source_ids", [])),
            knowledge_points=list(data.get("knowledge_points", [])),
            next_steps=list(data.get("next_steps", [])),
            created_at=str(data.get("created_at") or now_iso()),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class StudentProfile:
    """学生长期画像。

    这是个性化学习系统的核心。

    当前 V0.2 先保存最基础的信息：
        - 学生 ID
        - 课程名称
        - 学习目标
        - 当前水平
        - 讲解偏好
        - 薄弱点
        - 最近学习记录
    """

    # 学生唯一标识。
    student_id: str

    # 当前主要学习课程。
    course_name: Optional[str] = None

    # 学习目标，例如“提高初中数学基础”。
    learning_goal: Optional[str] = None

    # 当前水平，例如“初二，刚学不等式”。
    current_level: Optional[str] = None

    # 偏好的讲解风格。
    preferred_style: Optional[str] = None

    # 系统归纳出的薄弱点。
    weak_points: List[str] = field(default_factory=list)

    # 最近的学习建议，可以用于前端展示。
    recent_recommendations: List[str] = field(default_factory=list)

    # 历史学习记录。
    memories: List[LearningMemoryItem] = field(default_factory=list)

    # 创建和更新时间。
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        """转成适合 JSON 保存的字典。"""

        return {
            "student_id": self.student_id,
            "course_name": self.course_name,
            "learning_goal": self.learning_goal,
            "current_level": self.current_level,
            "preferred_style": self.preferred_style,
            "weak_points": self.weak_points,
            "recent_recommendations": self.recent_recommendations,
            "memories": [item.to_dict() for item in self.memories],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentProfile":
        """从 JSON 字典恢复成 StudentProfile。"""

        memories = [
            LearningMemoryItem.from_dict(item)
            for item in data.get("memories", [])
            if isinstance(item, dict)
        ]

        return cls(
            student_id=str(data.get("student_id", "")),
            course_name=data.get("course_name"),
            learning_goal=data.get("learning_goal"),
            current_level=data.get("current_level"),
            preferred_style=data.get("preferred_style"),
            weak_points=list(data.get("weak_points", [])),
            recent_recommendations=list(data.get("recent_recommendations", [])),
            memories=memories,
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )
