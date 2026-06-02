"""V0.4 学习计划业务服务。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

from app.agents.planner_agent import PlannerAgent
from app.core.config import BACKEND_DIR, get_settings
from app.models.plan import LearningPlan, LearningPlanRequest
from app.models.schemas import LearningQuestionRequest
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService


DEFAULT_PLAN_DIR = BACKEND_DIR / "data" / "student_profiles" / "plans"


class LearningPlanService:
    """读取学生画像、调用 PlannerAgent、保存学习计划。"""

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        rag_service: Optional[RagService] = None,
        planner_agent: Optional[PlannerAgent] = None,
        plan_dir: Optional[str | Path] = None,
    ) -> None:
        self.settings = get_settings()
        self.memory_service = memory_service or MemoryService()
        self.rag_service = rag_service or RagService()
        self.planner_agent = planner_agent or PlannerAgent()
        self.plan_dir = Path(plan_dir) if plan_dir else DEFAULT_PLAN_DIR
        self.plan_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: LearningPlanRequest) -> LearningPlan:
        """生成并保存学习计划。"""

        started_at = time.perf_counter()
        self._validate_request(request)

        profile = self.memory_service.load_profile(request.student_id)
        profile.course_name = request.course_name
        profile.learning_goal = request.learning_goal
        self.memory_service.save_profile(profile)

        memory_context = self.memory_service.build_memory_context(profile)
        query = self._build_search_query(request)
        sources = self.rag_service.search(query, top_k=self.settings.rag_top_k)
        if not sources:
            raise ValueError("没有检索到课程资料，无法生成学习计划。")

        plan = self.planner_agent.generate_plan(request, memory_context, sources)
        plan.debug.update(
            {
                "search_query": query,
                "retrieved_source_count": len(sources),
                "memory_count": len(profile.memories),
                "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        self.save_plan(plan)
        return plan

    def save_plan(self, plan: LearningPlan) -> Path:
        """保存计划到本地 JSON。"""

        path = self._plan_path(plan.plan_id)
        path.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_plan(self, plan_id: str) -> LearningPlan:
        """读取学习计划。"""

        path = self._plan_path(plan_id)
        if not path.exists():
            raise FileNotFoundError(f"学习计划不存在：{plan_id}")
        return LearningPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _validate_request(request: LearningPlanRequest) -> None:
        if not request.student_id.strip():
            raise ValueError("student_id 不能为空。")
        if not request.course_name.strip():
            raise ValueError("course_name 不能为空。")
        if not request.learning_goal.strip():
            raise ValueError("learning_goal 不能为空。")
        if request.available_days <= 0:
            raise ValueError("available_days 必须大于 0。")
        if request.daily_minutes <= 0:
            raise ValueError("daily_minutes 必须大于 0。")

    @staticmethod
    def _build_search_query(request: LearningPlanRequest) -> str:
        parts = [request.course_name, request.learning_goal, *request.focus_topics]
        return " ".join(part.strip() for part in parts if part and part.strip())

    def _plan_path(self, plan_id: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", plan_id.strip()) or "unknown_plan"
        return self.plan_dir / f"{safe_id}.json"


def generate_learning_plan(request: LearningPlanRequest) -> LearningPlan:
    """便捷函数：生成学习计划。"""

    return LearningPlanService().generate(request)
