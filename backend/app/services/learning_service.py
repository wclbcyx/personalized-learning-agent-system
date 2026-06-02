"""V0.1 学习问答业务编排服务。

这个文件负责把前面已经写好的两个核心模块串起来：

    RagService      -> 负责从课程资料中检索相关片段
    TutorAgent      -> 负责基于相关片段调用大模型生成回答

也就是说，LearningService 是 V0.1 最小闭环的入口：

    用户问题
    -> LearningService.ask()
    -> RagService.search()
    -> TutorAgent.answer()
    -> LearningAnswerResponse

为什么需要这个 service：
    不建议在 API 路由里直接写 RAG 和 Agent 调用逻辑。
    路由层应该只负责 HTTP 请求和响应；真正的业务流程放在 service 里，
    后面加入记忆系统、多智能体调度、日志和评估时会更清晰。
"""

from __future__ import annotations

import time
from typing import Optional

from app.agents.tutor_agent import TutorAgent
from app.core.config import get_settings
from app.models.schemas import LearningAnswerResponse, LearningQuestionRequest
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService


class LearningService:
    """学习问答业务服务。

    当前 V0.1 只做一件事：
        基于课程资料回答学生问题。

    后续版本可以在这里继续扩展：
        - 读取学生长期记忆
        - 写入本轮学习摘要
        - 调用 PlannerAgent 生成学习计划
        - 调用 ExerciseAgent 生成练习
        - 调用 ReflectionAgent 更新薄弱点
    """

    def __init__(
        self,
        rag_service: Optional[RagService] = None,
        tutor_agent: Optional[TutorAgent] = None,
        memory_service: Optional[MemoryService] = None,
    ) -> None:
        """初始化学习服务。

        Args:
            rag_service:
                可选的 RAG 服务实例。
                不传时会自动创建默认 RagService。

            tutor_agent:
                可选的导师 Agent 实例。
                不传时会自动创建默认 TutorAgent。

            memory_service:
                可选的记忆服务实例。
                不传时会自动使用本地 JSON 记忆。

        这些参数主要是为了方便测试。
        比如单元测试时可以传一个假的 tutor_agent，避免真的调用大模型。
        """

        self.settings = get_settings()
        self.rag_service = rag_service or RagService()
        self.tutor_agent = tutor_agent or TutorAgent()
        self.memory_service = memory_service or MemoryService()

    def ask(self, request: LearningQuestionRequest) -> LearningAnswerResponse:
        """处理一次学习提问。

        Args:
            request:
                用户学习问题，包含 student_id、question、course_name 等字段。

        Returns:
            LearningAnswerResponse：
                包含大模型回答、引用来源、下一步建议和调试信息。
        """

        started_at = time.perf_counter()

        # 1. 基础校验：问题不能为空。
        question = request.question.strip()
        if not question:
            return LearningAnswerResponse(
                answer="问题不能为空。请先输入你想学习或想解决的问题。",
                sources=[],
                next_steps=["输入一个更具体的问题，例如：工具调用和 RAG 有什么关系？"],
                summary="空问题",
                debug={
                    "mode": "validation_error",
                    "student_id": request.student_id,
                },
            )

        # 2. 读取并更新学生画像。
        #    这里先把前端传来的课程、目标、水平和偏好写入 profile。
        profile = self.memory_service.load_profile(request.student_id)
        profile = self.memory_service.update_profile_from_request(profile, request)
        memory_context = self.memory_service.build_memory_context(profile)

        # 3. RAG 检索：从课程资料中找出和问题最相关的片段。
        sources = self.rag_service.search(
            question=question,
            top_k=self.settings.rag_top_k,
            course_name=request.course_name,
        )

        # 4. TutorAgent 回答：把问题、资料片段、学生记忆交给大模型。
        response = self.tutor_agent.answer(
            question=question,
            sources=sources,
            memory_context=memory_context,
        )

        # 5. 保存本轮学习记忆。
        #    即使本次没有检索到资料，也保存画像信息；有回答时追加学习记录。
        profile = self.memory_service.append_learning_memory(profile, request, response)
        self.memory_service.save_profile(profile)

        # 6. 补充结构化调试信息。
        #    这些信息对开发非常有帮助，前端正式展示时可以隐藏 debug。
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.debug.update(
            {
                "student_id": request.student_id,
                "course_name": request.course_name,
                "learning_goal": request.learning_goal,
                "current_level": request.current_level,
                "preferred_style": request.preferred_style,
                "retrieved_source_count": len(sources),
                "memory_file_updated": True,
                "memory_count": len(profile.memories),
                "weak_points": profile.weak_points,
                "elapsed_ms": elapsed_ms,
            }
        )

        return response


def ask_learning_question(request: LearningQuestionRequest) -> LearningAnswerResponse:
    """便捷函数：处理一次学习问题。

    如果你只是想快速测试，不想手动创建 LearningService，可以这样用：

        request = LearningQuestionRequest(
            student_id="stu_001",
            question="工具调用和 RAG 有什么关系？",
        )
        response = ask_learning_question(request)
    """

    service = LearningService()
    return service.ask(request)
