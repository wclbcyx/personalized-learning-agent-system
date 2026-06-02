"""学习问答 API 路由。

这个文件是 V0.1 最小闭环的 HTTP 入口。

请求链路：

    前端 / curl / Postman
    -> POST /api/learning/ask
    -> LearningQuestionRequest
    -> LearningService.ask()
    -> RagService.search()
    -> TutorAgent.answer()
    -> LearningAnswerResponse
    -> JSON 响应

路由层只负责：
    - 接收 HTTP 请求
    - 做基础参数校验
    - 调用 service
    - 把结果返回给前端

不要把 RAG、Agent、大模型调用逻辑写在路由层里。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import LearningQuestionRequest
from app.services.learning_service import LearningService


router = APIRouter(prefix="/api/learning", tags=["learning"])


class AskLearningRequest(BaseModel):
    """HTTP 层的提问请求模型。

    注意：
        这里使用 Pydantic BaseModel，是因为 FastAPI 需要它来解析和校验
        HTTP JSON。

        app.models.schemas 里的 dataclass 是业务层数据结构。
        路由层收到请求后，会把 Pydantic 模型转换成 dataclass。
    """

    student_id: str = Field(..., description="学生 ID，例如 stu_001")
    question: str = Field(..., description="学生提出的问题")
    course_name: Optional[str] = Field(default=None, description="课程名称")
    learning_goal: Optional[str] = Field(default=None, description="学习目标")
    current_level: Optional[str] = Field(default=None, description="当前基础水平")
    preferred_style: Optional[str] = Field(default=None, description="偏好的讲解风格")


@router.post("/ask")
def ask_learning_question(payload: AskLearningRequest) -> Dict[str, Any]:
    """处理一次学习问答请求。

    示例请求：

    ```json
    {
      "student_id": "stu_001",
      "question": "为什么解不等式时除以负数要改变方向？",
      "course_name": "初中数学"
    }
    ```

    示例响应结构：

    ```json
    {
      "answer": "...",
      "sources": [...],
      "next_steps": [...],
      "summary": "...",
      "debug": {...}
    }
    ```
    """

    request = LearningQuestionRequest(
        student_id=payload.student_id,
        question=payload.question,
        course_name=payload.course_name,
        learning_goal=payload.learning_goal,
        current_level=payload.current_level,
        preferred_style=payload.preferred_style,
    )

    try:
        # V0.1 这里每次请求创建一个 LearningService。
        # 好处是简单、无跨用户历史污染。
        # 后续如果要优化性能，可以缓存 RagService，但要注意 Agent 对话历史隔离。
        service = LearningService()
        response = service.ask(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"学习问答处理失败：{exc}",
        ) from exc

    return response.to_dict()
