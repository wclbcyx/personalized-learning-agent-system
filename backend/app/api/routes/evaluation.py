"""评估与实验数据 API。"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Response

from app.services.evaluation_service import EvaluationService


router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/summary")
def get_evaluation_summary() -> Dict[str, Any]:
    """返回学习数据看板汇总指标。"""

    return EvaluationService().build_summary().to_dict()


@router.get("/events")
def get_events() -> Dict[str, Any]:
    """返回统一协调器调用日志。"""

    events = EvaluationService().load_events()
    return {"events": events, "count": len(events)}


@router.get("/export.json")
def export_json() -> Dict[str, Any]:
    """导出 JSON 实验数据。"""

    return EvaluationService().export_json()


@router.get("/export.csv")
def export_csv() -> Response:
    """导出 CSV 实验数据。"""

    return Response(
        content=EvaluationService().export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=learning-agent-events.csv"},
    )
