"""V0.4 学习反思业务服务。"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.agents.reflection_agent import ReflectionAgent
from app.models.memory import LearningMemoryItem
from app.services.memory_service import MemoryService


class ReflectionService:
    """读取最近记忆，调用 ReflectionAgent，并更新 StudentProfile。"""

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        reflection_agent: Optional[ReflectionAgent] = None,
    ) -> None:
        self.memory_service = memory_service or MemoryService()
        self.reflection_agent = reflection_agent or ReflectionAgent()

    def reflect(self, student_id: str) -> Dict[str, Any]:
        """生成学习反思并写回学生画像。"""

        started_at = time.perf_counter()
        if not student_id.strip():
            raise ValueError("student_id 不能为空。")

        profile = self.memory_service.load_profile(student_id)
        memory_context = self.memory_service.build_memory_context(profile, limit=8)
        result = self.reflection_agent.reflect(memory_context)

        weak_points = self._as_str_list(result.get("weak_points"))
        recommendations = self._as_str_list(result.get("next_recommendations"))
        mastered_points = self._as_str_list(result.get("mastered_points"))
        level_update = str(result.get("level_update") or "").strip()

        profile.weak_points = self.memory_service._merge_unique(profile.weak_points, weak_points)
        if recommendations:
            profile.recent_recommendations = recommendations[:5]
        if level_update:
            profile.current_level = level_update

        summary = str(result.get("summary") or "已完成一次学习反思。")
        profile.memories.append(
            LearningMemoryItem(
                question="学习反思",
                answer_summary=summary,
                knowledge_points=self.memory_service._merge_unique(mastered_points, weak_points),
                next_steps=recommendations,
                metadata={"type": "reflection"},
            )
        )
        self.memory_service.save_profile(profile)

        result["debug"] = {
            "student_id": student_id,
            "memory_file_updated": True,
            "memory_count": len(profile.memories),
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
        }
        return result

    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []


def reflect_student(student_id: str) -> Dict[str, Any]:
    """便捷函数：生成学习反思。"""

    return ReflectionService().reflect(student_id)
