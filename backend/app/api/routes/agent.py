"""统一 Agent 协调 API 路由。"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.coordinator_agent import CoordinatorAgent
from app.services.reflection_service import ReflectionService


router = APIRouter(prefix="/api/agent", tags=["agent"])


class CoordinateHttpRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict, description="任意任务载荷")


class ReflectionHttpRequest(BaseModel):
    student_id: str = Field(..., description="学生 ID")


@router.post("/coordinate")
def coordinate(payload: CoordinateHttpRequest) -> Dict[str, Any]:
    """判断请求应该交给哪个 Agent 或 service。"""

    return CoordinatorAgent().route(payload.payload).to_dict()


@router.post("/reflect")
def reflect(payload: ReflectionHttpRequest) -> Dict[str, Any]:
    """生成学习反思并更新学生画像。"""

    try:
        return ReflectionService().reflect(payload.student_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成学习反思失败：{exc}") from exc
