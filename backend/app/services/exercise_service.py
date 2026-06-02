"""V0.3 练习生成业务服务。

ExerciseService 负责把下面几个模块串起来：

    MemoryService        -> 读取学生画像和历史记忆
    RagService           -> 检索课程资料
    ExerciseAgent        -> 调用大模型生成练习题
    ExerciseStoreService -> 保存完整题目，供后续批改使用

完整链路：

    ExerciseGenerationRequest
    -> 读取 StudentProfile
    -> 构建 memory_context
    -> 根据 topic/question 检索课程资料
    -> ExerciseAgent.generate()
    -> ExerciseGenerationResponse

注意：
    当前版本会把完整题目保存到本地 JSON。
    前端展示时应使用 response.to_dict(include_answer=False)，避免泄露答案。
"""

from __future__ import annotations

import time
from typing import Optional

from app.agents.exercise_agent import ExerciseAgent
from app.core.config import get_settings
from app.models.exercise import ExerciseGenerationRequest, ExerciseGenerationResponse
from app.services.exercise_store_service import ExerciseStoreService
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService


class ExerciseService:
    """练习生成业务服务。"""

    def __init__(
        self,
        rag_service: Optional[RagService] = None,
        memory_service: Optional[MemoryService] = None,
        exercise_agent: Optional[ExerciseAgent] = None,
        exercise_store_service: Optional[ExerciseStoreService] = None,
    ) -> None:
        """初始化练习生成服务。

        Args:
            rag_service:
                课程资料检索服务。
            memory_service:
                学生记忆服务。
            exercise_agent:
                出题 Agent。
            exercise_store_service:
                练习题存储服务，用来保存完整题目。
        """

        self.settings = get_settings()
        self.rag_service = rag_service or RagService()
        self.memory_service = memory_service or MemoryService()
        self.exercise_agent = exercise_agent or ExerciseAgent()
        self.exercise_store_service = exercise_store_service or ExerciseStoreService()

    def generate(self, request: ExerciseGenerationRequest) -> ExerciseGenerationResponse:
        """生成练习题。

        Args:
            request:
                包含 student_id、course_name、topic、question、count、difficulty、
                exercise_type 等信息。

        Returns:
            ExerciseGenerationResponse：结构化题目列表。
        """

        started_at = time.perf_counter()

        self._validate_request(request)

        # 1. 读取学生画像，并用请求里的显式信息更新它。
        #    出题时只更新 course_name；目标、水平、偏好已经在问答流程中维护。
        profile = self.memory_service.load_profile(request.student_id)
        if request.course_name:
            profile.course_name = request.course_name

        memory_context = self.memory_service.build_memory_context(profile)

        # 2. 构建检索 query。
        #    优先用 topic，其次用 question，最后用 course_name。
        query = self._build_search_query(request)
        sources = self.rag_service.search(question=query, top_k=self.settings.rag_top_k)

        if not sources:
            raise ValueError("没有检索到相关课程资料，无法生成练习题。")

        # 3. 调用出题 Agent。
        response = self.exercise_agent.generate(
            request=request,
            sources=sources,
            memory_context=memory_context,
        )

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.debug.update(
            {
                "student_id": request.student_id,
                "course_name": request.course_name,
                "topic": request.topic,
                "question": request.question,
                "search_query": query,
                "retrieved_source_count": len(sources),
                "memory_count": len(profile.memories),
                "elapsed_ms": elapsed_ms,
            }
        )

        # 4. 保存学生画像中的课程名更新。
        self.memory_service.save_profile(profile)

        # 5. 保存完整题目，供后续批改时读取 reference_answer 和 rubric。
        saved_path = self.exercise_store_service.save_exercise_set(response)
        response.debug["exercise_set_saved"] = True
        response.debug["exercise_set_path"] = str(saved_path)

        return response

    @staticmethod
    def _validate_request(request: ExerciseGenerationRequest) -> None:
        """校验生成练习请求。"""

        if not request.student_id.strip():
            raise ValueError("student_id 不能为空。")

        if not (request.topic and request.topic.strip()) and not (
            request.question and request.question.strip()
        ):
            raise ValueError("topic 和 question 至少需要提供一个。")

        if request.count <= 0:
            raise ValueError("count 必须大于 0。")

        if request.count > 10:
            raise ValueError("一次最多生成 10 道题。")

    @staticmethod
    def _build_search_query(request: ExerciseGenerationRequest) -> str:
        """构建 RAG 检索 query。"""

        parts = []
        if request.course_name:
            parts.append(request.course_name)
        if request.topic:
            parts.append(request.topic)
        if request.question:
            parts.append(request.question)

        return " ".join(part.strip() for part in parts if part and part.strip())


def generate_exercises(request: ExerciseGenerationRequest) -> ExerciseGenerationResponse:
    """便捷函数：生成练习题。"""

    service = ExerciseService()
    return service.generate(request)
