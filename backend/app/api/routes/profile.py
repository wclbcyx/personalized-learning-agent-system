"""学生画像 API。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.memory import StudentProfile
from app.services.memory_service import DEFAULT_PROFILE_DIR, MemoryService


router = APIRouter(prefix="/api/profile", tags=["profile"])


class UpdateProfileHttpRequest(BaseModel):
    course_name: Optional[str] = Field(default=None)
    learning_goal: Optional[str] = Field(default=None)
    current_level: Optional[str] = Field(default=None)
    preferred_style: Optional[str] = Field(default=None)
    weak_points: Optional[List[str]] = Field(default=None)
    recent_recommendations: Optional[List[str]] = Field(default=None)


@router.get("")
def list_profiles() -> Dict[str, Any]:
    """列出所有学生画像摘要。"""

    service = MemoryService()
    profiles = []
    for path in sorted(DEFAULT_PROFILE_DIR.glob("*.json")):
        profile = service.load_profile(path.stem)
        profiles.append(
            {
                "student_id": profile.student_id,
                "course_name": profile.course_name,
                "learning_goal": profile.learning_goal,
                "current_level": profile.current_level,
                "weak_point_count": len(profile.weak_points),
                "memory_count": len(profile.memories),
                "updated_at": profile.updated_at,
            }
        )
    return {"profiles": profiles}


@router.get("/{student_id}")
def get_profile(student_id: str) -> Dict[str, Any]:
    """读取某个学生完整画像。"""

    return MemoryService().load_profile(student_id).to_dict()


@router.put("/{student_id}")
def update_profile(student_id: str, payload: UpdateProfileHttpRequest) -> Dict[str, Any]:
    """更新学生画像基础字段。"""

    service = MemoryService()
    profile = service.load_profile(student_id)

    for field_name in [
        "course_name",
        "learning_goal",
        "current_level",
        "preferred_style",
        "weak_points",
        "recent_recommendations",
    ]:
        value = getattr(payload, field_name)
        if value is not None:
            setattr(profile, field_name, value)

    service.save_profile(profile)
    return profile.to_dict()


@router.delete("/{student_id}/memory")
def clear_profile_memory(student_id: str) -> Dict[str, Any]:
    """清空某个学生的长期记忆，但保留基础画像字段。"""

    service = MemoryService()
    profile = service.load_profile(student_id)
    if not isinstance(profile, StudentProfile):
        raise HTTPException(status_code=404, detail=f"学生画像不存在：{student_id}")

    profile.memories = []
    profile.weak_points = []
    profile.recent_recommendations = []
    service.save_profile(profile)
    return {
        "student_id": profile.student_id,
        "message": "已清空学习记忆、薄弱点和近期建议。",
        "profile": profile.to_dict(),
    }
