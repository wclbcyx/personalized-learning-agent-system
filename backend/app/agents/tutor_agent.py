"""V0.1 个性化学习导师 Agent。

TutorAgent 的职责：
    根据用户问题和 RAG 检索到的课程资料片段，调用大模型生成学习回答。

当前版本特点：
    - 使用本项目自己实现的 ``SimpleAgent``。
    - 使用本项目自己实现的 ``HelloAgentsLLM`` 读取 backend/.env 里的模型配置。
    - 不再使用模板兜底；如果模型或配置有问题，会明确报错。

最小闭环中的位置：
    question -> RagService.search -> TutorAgent.answer -> LearningAnswerResponse
"""

from __future__ import annotations

from typing import List

from app.core.config import get_settings
from app.core.llm import HelloAgentsLLM, SimpleAgent
from app.models.schemas import LearningAnswerResponse, SourceChunk
from app.tools.search_tool import SearchTool


TUTOR_SYSTEM_PROMPT = """你是一个耐心、严谨、擅长项目制学习的 AI 课程导师。

你的任务是基于给定的课程资料片段回答学生问题。

行为要求：
1. 必须优先依据课程资料回答，不要脱离资料自由发挥。
2. 如果课程资料不足，要明确说明“当前资料不足”。
3. 回答要适合初学者理解，先讲结论，再讲原因。
4. 如果问题涉及学习路径，要给出清晰的学习顺序。
5. 回答末尾要列出引用来源，引用片段 ID 或标题。
6. 不要编造不存在的章节、资料或实验结果。
"""


class TutorAgent:
    """学习导师 Agent。

    输入：
        - 用户问题 question
        - RAG 检索到的 sources

    输出：
        - answer：大模型生成的回答正文
        - sources：本次回答使用的资料来源
        - next_steps：系统侧补充的下一步学习建议
    """

    def __init__(self) -> None:
        """初始化导师 Agent。

        这里会创建本地 HelloAgentsLLM 和 SimpleAgent。
        """

        self.settings = get_settings()
        self._agent = self._create_agent()

    def answer(
        self,
        question: str,
        sources: List[SourceChunk],
        memory_context: str = "",
    ) -> LearningAnswerResponse:
        """根据用户问题和检索资料生成回答。

        Args:
            question:
                学生提出的问题。
            sources:
                RagService 检索出来的资料片段。
            memory_context:
                学生长期记忆上下文。由 MemoryService 根据学生画像和最近学习记录生成。

        Returns:
            LearningAnswerResponse：包含回答、引用来源和下一步建议。
        """

        if not sources:
            return self._answer_with_search(question, memory_context)

        prompt = self._build_prompt(question, sources, memory_context=memory_context)

        try:
            raw_answer = self._agent.run(prompt)
        except Exception as exc:
            raise RuntimeError(f"TutorAgent 调用大模型失败：{exc}") from exc

        return LearningAnswerResponse(
            answer=raw_answer.strip(),
            sources=sources,
            next_steps=self._build_next_steps(question, sources),
            summary=self._build_summary(question),
            debug={
                "mode": "llm",
                "model": self.settings.llm_model_id,
                "source_count": len(sources),
                "has_memory_context": bool(memory_context.strip()),
            },
        )

    def _create_agent(self):
        """创建本地 SimpleAgent。

        这里把 backend/.env 中读到的 LLM 配置显式传给本地 HelloAgentsLLM。
        这样配置来源更清晰，也避免依赖外部 shell 环境变量。
        """

        llm_kwargs = {
            "model": self.settings.llm_model_id,
            "api_key": self.settings.llm_api_key,
            "base_url": self.settings.llm_base_url,
            "timeout": self.settings.llm_timeout,
            "temperature": 0.2,
        }

        try:
            llm = HelloAgentsLLM(**llm_kwargs)
            return SimpleAgent(
                name="个性化学习导师",
                llm=llm,
                system_prompt=TUTOR_SYSTEM_PROMPT,
            )
        except Exception as exc:
            raise RuntimeError(
                "创建 TutorAgent 失败。请检查 backend/.env 中的 "
                "LLM_API_KEY、LLM_BASE_URL、LLM_MODEL_ID、LLM_TIMEOUT。"
            ) from exc

    def _answer_with_search(self, question: str, memory_context: str) -> LearningAnswerResponse:
        """课程资料无命中时，调用搜索工具兜底回答。"""

        search_results = SearchTool().search(question, max_results=5)
        if not search_results:
            return LearningAnswerResponse(
                answer="当前课程资料中没有检索到足够相关的内容，搜索工具也没有返回可用结果。建议先补充课程资料，或换一个更具体的问题。",
                sources=[],
                next_steps=[
                    "检查 backend/data/course_materials 是否已有课程资料",
                    "尝试使用更具体的关键词提问",
                    "配置 TAVILY_API_KEY 或 SERPAPI_API_KEY 以启用更稳定的搜索兜底",
                ],
                summary="未找到相关资料",
                debug={"mode": "no_sources_no_search_results"},
            )

        prompt = self._build_search_prompt(question, search_results, memory_context)
        try:
            raw_answer = self._agent.run(prompt)
        except Exception as exc:
            raise RuntimeError(f"TutorAgent 调用搜索兜底回答失败：{exc}") from exc

        return LearningAnswerResponse(
            answer=raw_answer.strip(),
            sources=[],
            next_steps=[
                "优先补充或上传与该问题相关的课程资料",
                "对搜索结果中的结论进行课堂资料核对",
                "把本次问题整理为新的课程资料片段，便于后续 RAG 命中",
            ],
            summary=self._build_summary(question),
            debug={
                "mode": "web_search_fallback",
                "model": self.settings.llm_model_id,
                "search_result_count": len(search_results),
                "search_results": [item.to_dict() for item in search_results],
                "has_memory_context": bool(memory_context.strip()),
            },
        )

    @staticmethod
    def _build_search_prompt(question: str, search_results, memory_context: str = "") -> str:
        """构建搜索兜底提示词。"""

        search_context = "\n\n".join(
            f"[搜索结果 {index}]\n"
            f"标题：{item.title}\n"
            f"链接：{item.url}\n"
            f"摘要：{item.snippet}"
            for index, item in enumerate(search_results, start=1)
        )
        memory_block = memory_context.strip() or "暂无学生历史记忆。"

        return f"""课程资料没有检索到相关内容。请基于“学生记忆”和“搜索结果”回答学生问题。

学生记忆：
{memory_block}

学生问题：
{question}

搜索结果：
{search_context}

请严格按照下面结构回答：

## 简短结论
用 2-3 句话直接回答学生问题，并说明本次使用的是搜索兜底。

## 原理解释
基于搜索摘要解释原因，不要编造搜索结果中没有的细节。若资料仍不足，要明确说明不确定。

## 学习建议
给出 2-4 条具体可执行的下一步学习建议。

## 搜索来源
列出使用到的搜索结果标题和链接。
"""

    def _build_prompt(
        self,
        question: str,
        sources: List[SourceChunk],
        memory_context: str = "",
    ) -> str:
        """构建发给大模型的用户提示词。

        这里就是最小版“上下文工程”：
            用户问题 + RAG 资料片段 + 输出格式要求

        这里已经接入 V0.2 记忆系统：
            - memory_context：学生画像、历史薄弱点、最近学习记录
            - source_context：RAG 检索到的课程资料
        """

        source_context = "\n\n".join(
            f"[资料 {index}]\n"
            f"标题：{source.title}\n"
            f"片段ID：{source.chunk_id}\n"
            f"相关度：{source.score}\n"
            f"来源路径：{source.source_path}\n"
            f"内容：\n{source.content}"
            for index, source in enumerate(sources, start=1)
        )

        memory_block = memory_context.strip() or "暂无学生历史记忆。"

        return f"""请基于“学生记忆”和“课程资料”回答学生问题。

学生记忆：
{memory_block}

学生问题：
{question}

课程资料：
{source_context}

请严格按照下面结构回答：

## 简短结论
用 2-3 句话直接回答学生问题。

## 原理解释
结合课程资料解释原因，不要泛泛而谈。若学生记忆中包含当前水平、薄弱点或偏好，请体现个性化讲解。

## 学习建议
给出 2-4 条具体可执行的下一步学习建议。建议要结合学生当前水平和历史薄弱点。

## 引用来源
列出你使用到的资料片段 ID，例如 doc001_chunk0003。
"""

    @staticmethod
    def _build_summary(question: str) -> str:
        """生成一句话摘要，方便前端或日志展示。"""

        clean_question = question.strip().replace("\n", " ")
        if len(clean_question) <= 32:
            return f"关于“{clean_question}”的学习回答"
        return f"关于“{clean_question[:32]}...”的学习回答"

    @staticmethod
    def _build_next_steps(question: str, sources: List[SourceChunk]) -> List[str]:
        """生成系统侧下一步建议。

        大模型回答里也会包含学习建议；这里再保留结构化 next_steps，
        是为了方便前端后续做按钮、任务卡片或学习计划。
        """

        steps = [
            "回到引用资料，通读相关小节并标记关键词",
            "用自己的话复述本次回答中的核心概念",
        ]

        lowered_question = question.lower()
        if "rag" in lowered_question or "检索" in question:
            steps.append("画出 RAG 的四步流程：资料加载、文本切分、相关检索、回答生成")
        if "工具" in question or "tool" in lowered_question:
            steps.append("设计一个 KnowledgeRetrievalTool，写出输入参数和输出结果")
        if "agent" in lowered_question or "智能体" in question:
            steps.append("判断这个任务适合单 Agent 完成，还是拆给多个 Agent 协作")

        if sources:
            steps.append(f"优先阅读资料来源：{sources[0].citation_label()}")

        return steps
