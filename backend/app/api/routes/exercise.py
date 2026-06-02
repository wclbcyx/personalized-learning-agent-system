"""练习生成与批改 API 路由。

V0.3 暴露两个接口：

    POST /api/exercise/generate
        生成练习题。返回给前端时隐藏 reference_answer 和 rubric。

    POST /api/exercise/grade
        批改学生答案。前端只需要传 exercise_set_id、exercise_id 和 student_answer。

路由层只负责 HTTP 输入输出，不直接写出题、批改或存储逻辑。
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.exercise import ExerciseGenerationRequest, GradeExerciseRequest
from app.services.exercise_service import ExerciseService
from app.services.grading_service import GradingService


router = APIRouter(prefix="/api/exercise", tags=["exercise"])


class GenerateExerciseHttpRequest(BaseModel):
    """HTTP 层的练习生成请求。"""

    student_id: str = Field(..., description="学生 ID，例如 stu_001")
    course_name: Optional[str] = Field(default=None, description="课程名称")
    topic: Optional[str] = Field(default=None, description="练习主题或知识点")
    question: Optional[str] = Field(default=None, description="可选：本次讲解问题")
    count: int = Field(default=3, ge=1, le=10, description="生成题目数量")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium",
        description="题目难度",
    )
    exercise_type: Literal["short_answer", "choice", "calculation"] = Field(
        default="short_answer",
        description="题型",
    )
    extra_requirement: Optional[str] = Field(default=None, description="额外出题要求")


class GradeExerciseHttpRequest(BaseModel):
    """HTTP 层的练习批改请求。"""

    student_id: str = Field(..., description="学生 ID，例如 stu_001")
    exercise_set_id: str = Field(..., description="练习批次 ID")
    exercise_id: str = Field(..., description="题目 ID")
    student_answer: str = Field(..., description="学生答案")


@router.post("/generate")
def generate_exercises(payload: GenerateExerciseHttpRequest) -> Dict[str, Any]:
    """生成练习题。

    返回给前端时会隐藏 reference_answer 和 rubric，避免提前泄露答案。
    完整题目会由 ExerciseStoreService 保存到后端本地 JSON。
    """

    request = ExerciseGenerationRequest(
        student_id=payload.student_id,
        course_name=payload.course_name,
        topic=payload.topic,
        question=payload.question,
        count=payload.count,
        difficulty=payload.difficulty,
        exercise_type=payload.exercise_type,
        extra_requirement=payload.extra_requirement,
    )

    try:
        service = ExerciseService()
        response = service.generate(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"生成练习失败：{exc}",
        ) from exc

    return response.to_dict(include_answer=False)


@router.post("/grade")
def grade_exercise(payload: GradeExerciseHttpRequest) -> Dict[str, Any]:
    """批改学生答案。"""

    request = GradeExerciseRequest(
        student_id=payload.student_id,
        exercise_set_id=payload.exercise_set_id,
        exercise_id=payload.exercise_id,
        student_answer=payload.student_answer,
    )

    try:
        service = GradingService()
        result = service.grade(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"批改练习失败：{exc}",
        ) from exc

    return result.to_dict()
