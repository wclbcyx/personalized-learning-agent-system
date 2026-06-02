"""V0.3 练习批改业务服务。

GradingService 负责把下面几个模块串起来：

    ExerciseStoreService -> 根据 exercise_set_id + exercise_id 读取完整题目
    MemoryService        -> 读取学生画像和历史记忆
    GradingAgent         -> 调用大模型批改学生答案
    MemoryService        -> 把批改结果写入学生记忆

完整链路：

    GradeExerciseRequest
    -> 读取完整 ExerciseItem
    -> 构建 ExerciseSubmission
    -> 构建 memory_context
    -> GradingAgent.grade()
    -> 保存批改记忆
    -> GradingResult
"""

from __future__ import annotations

import time
from typing import Optional

from app.agents.grading_agent import GradingAgent
from app.models.exercise import ExerciseSubmission, GradeExerciseRequest, GradingResult
from app.models.memory import LearningMemoryItem
from app.services.exercise_store_service import ExerciseStoreService
from app.services.memory_service import MemoryService


class GradingService:
    """练习批改业务服务。"""

    def __init__(
        self,
        exercise_store_service: Optional[ExerciseStoreService] = None,
        memory_service: Optional[MemoryService] = None,
        grading_agent: Optional[GradingAgent] = None,
    ) -> None:
        """初始化批改服务。

        Args:
            exercise_store_service:
                用于读取完整题目，包括 reference_answer 和 rubric。
            memory_service:
                用于读取和保存学生记忆。
            grading_agent:
                调用大模型完成批改的 Agent。
        """

        self.exercise_store_service = exercise_store_service or ExerciseStoreService()
        self.memory_service = memory_service or MemoryService()
        self.grading_agent = grading_agent or GradingAgent()

    def grade(self, request: GradeExerciseRequest) -> GradingResult:
        """批改一道学生提交的练习题。

        Args:
            request:
                包含 student_id、exercise_set_id、exercise_id 和 student_answer。

        Returns:
            GradingResult：结构化批改结果。
        """

        started_at = time.perf_counter()
        self._validate_request(request)

        # 1. 从本地题库存储中读取完整题目。
        #    这里能拿到前端没有看到的 reference_answer 和 rubric。
        exercise = self.exercise_store_service.get_exercise(
            exercise_set_id=request.exercise_set_id,
            exercise_id=request.exercise_id,
        )

        # 2. 构建学生提交对象。
        submission = ExerciseSubmission(
            student_id=request.student_id,
            exercise=exercise,
            student_answer=request.student_answer.strip(),
        )

        # 3. 读取学生记忆，给批改 Agent 个性化上下文。
        profile = self.memory_service.load_profile(request.student_id)
        memory_context = self.memory_service.build_memory_context(profile)

        # 4. 调用批改 Agent。
        result = self.grading_agent.grade(
            submission=submission,
            memory_context=memory_context,
        )

        # 5. 把批改表现写入学生记忆。
        self._append_grading_memory(profile, request, submission, result)
        self.memory_service.save_profile(profile)

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        result.debug.update(
            {
                "student_id": request.student_id,
                "exercise_set_id": request.exercise_set_id,
                "exercise_id": request.exercise_id,
                "memory_file_updated": True,
                "memory_count": len(profile.memories),
                "elapsed_ms": elapsed_ms,
            }
        )

        return result

    @staticmethod
    def _validate_request(request: GradeExerciseRequest) -> None:
        """校验批改请求。"""

        if not request.student_id.strip():
            raise ValueError("student_id 不能为空。")
        if not request.exercise_set_id.strip():
            raise ValueError("exercise_set_id 不能为空。")
        if not request.exercise_id.strip():
            raise ValueError("exercise_id 不能为空。")
        if not request.student_answer.strip():
            raise ValueError("student_answer 不能为空。")

    def _append_grading_memory(
        self,
        profile,
        request: GradeExerciseRequest,
        submission: ExerciseSubmission,
        result: GradingResult,
    ) -> None:
        """把一次批改结果追加到学生长期记忆。

        这里复用 LearningMemoryItem，让“问答记忆”和“练习批改记忆”
        都保存在 StudentProfile.memories 里。
        """

        exercise = submission.exercise
        answer_summary = (
            f"练习 {exercise.exercise_id} 批改：得分 {result.score}/100；"
            f"{result.feedback}"
        )

        next_steps = result.improvement_suggestions or [
            "回顾本题相关知识点，并重新独立完成一遍。"
        ]

        knowledge_points = self.memory_service._merge_unique(
            exercise.knowledge_points,
            result.mistake_points,
        )

        memory = LearningMemoryItem(
            question=f"练习批改：{exercise.question}",
            answer_summary=self.memory_service.summarize_answer(answer_summary),
            source_ids=exercise.source_ids,
            knowledge_points=knowledge_points,
            next_steps=next_steps,
            metadata={
                "type": "grading",
                "exercise_set_id": request.exercise_set_id,
                "exercise_id": request.exercise_id,
                "student_answer": request.student_answer,
                "score": result.score,
                "is_correct": result.is_correct,
            },
        )

        profile.memories.append(memory)
        profile.weak_points = self.memory_service._merge_unique(
            profile.weak_points,
            result.mistake_points or exercise.knowledge_points,
        )
        profile.recent_recommendations = next_steps[:5]


def grade_exercise(request: GradeExerciseRequest) -> GradingResult:
    """便捷函数：批改一道练习题。"""

    service = GradingService()
    return service.grade(request)
