"""学习计划 API 路由。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.plan import LearningPlanRequest
from app.services.learning_plan_service import LearningPlanService


router = APIRouter(prefix="/api/plan", tags=["plan"])


class GeneratePlanHttpRequest(BaseModel):
    student_id: str = Field(..., description="学生 ID")
    course_name: str = Field(..., description="课程名称")
    learning_goal: str = Field(..., description="学习目标")
    focus_topics: List[str] = Field(default_factory=list, description="重点知识点")
    available_days: int = Field(default=14, ge=1, le=365, description="可用学习天数")
    daily_minutes: int = Field(default=40, ge=1, le=600, description="每日学习分钟数")
    extra_requirement: Optional[str] = Field(default=None, description="额外要求")


@router.post("/generate")
def generate_plan(payload: GeneratePlanHttpRequest) -> Dict[str, Any]:
    """生成个性化学习计划。"""

    request = LearningPlanRequest(
        student_id=payload.student_id,
        course_name=payload.course_name,
        learning_goal=payload.learning_goal,
        focus_topics=payload.focus_topics,
        available_days=payload.available_days,
        daily_minutes=payload.daily_minutes,
        extra_requirement=payload.extra_requirement,
    )

    try:
        plan = LearningPlanService().generate(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成学习计划失败：{exc}") from exc

    return plan.to_dict()


@router.get("/{plan_id}")
def get_plan(plan_id: str) -> Dict[str, Any]:
    """读取学习计划。"""

    try:
        plan = LearningPlanService().load_plan(plan_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取学习计划失败：{exc}") from exc

    return plan.to_dict()
