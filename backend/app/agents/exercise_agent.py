"""V0.3 练习生成 Agent。

ExerciseAgent 的职责：
    根据学生画像、当前主题、RAG 检索资料，调用大模型生成结构化练习题。

它在系统中的位置：

    ExerciseGenerationRequest
    -> RagService 检索课程资料
    -> MemoryService 构建学生记忆上下文
    -> ExerciseAgent.generate()
    -> ExerciseGenerationResponse

注意：
    这个 Agent 必须输出可解析的 JSON。
    因为后续前端展示题目、GradingAgent 批改答案，都依赖稳定的数据结构。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.core.config import get_settings
from app.models.exercise import (
    ExerciseGenerationRequest,
    ExerciseGenerationResponse,
    ExerciseItem,
)
from app.models.schemas import SourceChunk


EXERCISE_SYSTEM_PROMPT = """你是一个严谨的通用课程练习题生成专家。

你的任务是基于课程资料、课程名称、学生情况和练习要求，生成适合学生当前水平的练习题。

行为要求：
1. 必须依据给定课程资料生成题目，不要生成超出资料范围太远的内容。
2. 题目难度要符合学生当前水平和请求中的 difficulty。
3. 每道题必须包含参考答案 reference_answer。
4. 每道题必须包含评分标准 rubric。
5. 如果是选择题，必须提供 options。
6. 输出必须是严格 JSON，不要输出 Markdown，不要输出解释性废话。
7. 不要假设课程一定是数学；应根据 course_name、topic 和课程资料判断学科。
"""


class ExerciseAgent:
    """练习生成 Agent。"""

    def __init__(self) -> None:
        """初始化 ExerciseAgent。

        会创建本项目自己的 HelloAgentsLLM 和 SimpleAgent。
        如果模型配置不正确，会抛出 RuntimeError，方便排查。
        """

        self.settings = get_settings()
        self._agent = self._create_agent()

    def generate(
        self,
        request: ExerciseGenerationRequest,
        sources: List[SourceChunk],
        memory_context: str = "",
    ) -> ExerciseGenerationResponse:
        """生成练习题。

        Args:
            request:
                练习生成请求，包含学生 ID、主题、题型、数量、难度等。
            sources:
                RAG 检索到的课程资料片段。
            memory_context:
                学生画像和最近学习记录。

        Returns:
            ExerciseGenerationResponse：结构化练习题结果。
        """

        if not sources:
            raise ValueError("没有检索到课程资料，无法生成练习题。")

        prompt = self._build_prompt(request, sources, memory_context)

        try:
            raw_output = self._agent.run(prompt)
        except Exception as exc:
            raise RuntimeError(f"ExerciseAgent 调用大模型失败：{exc}") from exc

        payload = self._parse_json_payload(raw_output)
        exercises = self._build_exercises(payload, request, sources)

        return ExerciseGenerationResponse(
            exercise_set_id=str(payload.get("exercise_set_id") or self._default_set_id(request)),
            student_id=request.student_id,
            exercises=exercises,
            summary=str(payload.get("summary") or f"已生成 {len(exercises)} 道练习题。"),
            debug={
                "mode": "llm",
                "model": self.settings.llm_model_id,
                "source_count": len(sources),
                "has_memory_context": bool(memory_context.strip()),
                "raw_exercise_count": len(payload.get("exercises", [])),
            },
        )

    def _create_agent(self):
        """创建本地 SimpleAgent。"""

        from app.core.llm import HelloAgentsLLM, SimpleAgent

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
                name="练习生成专家",
                llm=llm,
                system_prompt=EXERCISE_SYSTEM_PROMPT,
            )
        except Exception as exc:
            raise RuntimeError(
                "创建 ExerciseAgent 失败。请检查 backend/.env 中的 LLM 配置。"
            ) from exc

    def _build_prompt(
        self,
        request: ExerciseGenerationRequest,
        sources: List[SourceChunk],
        memory_context: str,
    ) -> str:
        """构建练习生成提示词。

        这里把“学生情况 + 出题要求 + 课程资料 + JSON 格式”都放进去。
        """

        source_context = "\n\n".join(
            f"[资料 {index}]\n"
            f"标题：{source.title}\n"
            f"片段ID：{source.chunk_id}\n"
            f"相关度：{source.score}\n"
            f"内容：\n{source.content}"
            for index, source in enumerate(sources, start=1)
        )

        memory_block = memory_context.strip() or "暂无学生历史记忆。"
        source_ids = [source.chunk_id for source in sources]

        return f"""请为学生生成课程练习题。

学生记忆：
{memory_block}

出题请求：
- student_id: {request.student_id}
- course_name: {request.course_name or "未指定，请根据课程资料判断"}
- topic: {request.topic or "未指定，请根据问题和资料判断"}
- question: {request.question or "未指定"}
- count: {request.count}
- difficulty: {request.difficulty}
- exercise_type: {request.exercise_type}
- extra_requirement: {request.extra_requirement or "无"}

课程资料：
{source_context}

可引用的资料片段 ID：
{source_ids}

请只输出 JSON，格式必须严格如下：
{{
  "exercise_set_id": "set_stu_001_001",
  "summary": "本组练习围绕本次学习主题，共 3 题。",
  "exercises": [
    {{
      "exercise_id": "exercise_001",
      "exercise_type": "{request.exercise_type}",
      "difficulty": "{request.difficulty}",
      "knowledge_points": ["不等式"],
      "question": "题干内容",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "reference_answer": "参考答案",
      "hint": "解题提示",
      "rubric": ["评分标准1", "评分标准2"],
      "source_ids": ["doc001_chunk0001"]
    }}
  ]
}}

重要约束：
1. exercises 数量必须等于 {request.count}。
2. exercise_type 必须是 "{request.exercise_type}"。
3. difficulty 必须是 "{request.difficulty}"。
4. source_ids 只能从上方“可引用的资料片段 ID”里选择。
5. 如果不是选择题，options 输出空数组 []。
6. 不要把 JSON 包在 ```json 代码块里。
7. 题目内容必须匹配 course_name 和课程资料，不要固定为数学题。
"""

    def _parse_json_payload(self, raw_output: str) -> Dict[str, Any]:
        """解析模型输出中的 JSON。

        大模型偶尔会在 JSON 外面加说明文字，所以这里会先尝试直接解析，
        失败后再提取第一个 JSON 对象。
        """

        text = raw_output.strip()

        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        json_text = self._extract_json_object(text)
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ExerciseAgent 输出不是合法 JSON：{raw_output}") from exc

        if not isinstance(payload, dict):
            raise ValueError("ExerciseAgent 输出 JSON 顶层必须是对象。")

        return payload

    @staticmethod
    def _extract_json_object(text: str) -> str:
        """从文本中提取第一个 JSON 对象。"""

        # 去掉常见代码块包裹。
        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text.strip()).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("未找到 JSON 对象。")
        return text[start : end + 1]

    def _build_exercises(
        self,
        payload: Dict[str, Any],
        request: ExerciseGenerationRequest,
        sources: List[SourceChunk],
    ) -> List[ExerciseItem]:
        """把模型 JSON 转成 ExerciseItem 列表。"""

        raw_items = payload.get("exercises")
        if not isinstance(raw_items, list) or not raw_items:
            raise ValueError("ExerciseAgent 输出中缺少 exercises 列表。")

        valid_source_ids = {source.chunk_id for source in sources}
        exercises: List[ExerciseItem] = []

        for index, item in enumerate(raw_items[: request.count], start=1):
            if not isinstance(item, dict):
                continue

            source_ids = [
                source_id
                for source_id in item.get("source_ids", [])
                if source_id in valid_source_ids
            ]
            if not source_ids and sources:
                source_ids = [sources[0].chunk_id]

            exercise = ExerciseItem(
                exercise_id=str(item.get("exercise_id") or f"exercise_{index:03d}"),
                exercise_type=request.exercise_type,
                difficulty=request.difficulty,
                knowledge_points=list(item.get("knowledge_points", [])),
                question=str(item.get("question", "")).strip(),
                options=list(item.get("options", [])),
                reference_answer=str(item.get("reference_answer", "")).strip(),
                hint=item.get("hint"),
                rubric=list(item.get("rubric", [])),
                source_ids=source_ids,
                metadata={
                    "generated_by": "ExerciseAgent",
                    "model": self.settings.llm_model_id,
                },
            )

            self._validate_exercise(exercise)
            exercises.append(exercise)

        if not exercises:
            raise ValueError("ExerciseAgent 没有生成有效题目。")

        return exercises

    @staticmethod
    def _validate_exercise(exercise: ExerciseItem) -> None:
        """校验题目是否满足后续展示和批改的最低要求。"""

        if not exercise.question:
            raise ValueError(f"题目 {exercise.exercise_id} 缺少 question。")
        if not exercise.reference_answer:
            raise ValueError(f"题目 {exercise.exercise_id} 缺少 reference_answer。")
        if not exercise.rubric:
            raise ValueError(f"题目 {exercise.exercise_id} 缺少 rubric。")
        if exercise.exercise_type == "choice" and not exercise.options:
            raise ValueError(f"选择题 {exercise.exercise_id} 缺少 options。")

    @staticmethod
    def _default_set_id(request: ExerciseGenerationRequest) -> str:
        """生成默认练习批次 ID。"""

        safe_student_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.student_id)
        return f"set_{safe_student_id or 'student'}"
