"""V0.3 答案批改 Agent。

GradingAgent 的职责：
    根据题目、参考答案、评分标准和学生答案，调用大模型完成批改。

它在系统中的位置：

    ExerciseSubmission
    -> GradingAgent.grade()
    -> GradingResult

注意：
    这个 Agent 是通用课程批改器，不固定为数学。
    批改依据来自 ExerciseItem 中的 reference_answer 和 rubric。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from app.core.config import get_settings
from app.models.exercise import ExerciseSubmission, GradingResult


GRADING_SYSTEM_PROMPT = """你是一个严谨、公正、擅长解释错误原因的课程练习批改专家。

你的任务是根据题目、参考答案、评分标准和学生答案进行批改。

行为要求：
1. 必须依据题目、参考答案和评分标准批改，不要随意改变标准。
2. 分数范围必须是 0 到 100 的整数。
3. feedback 要说明学生哪里做对、哪里做错。
4. mistake_points 要提取学生主要错误点。
5. improvement_suggestions 要给出具体可执行的改进建议。
6. 如果学生答案和参考答案表达不同但含义正确，可以判为正确。
7. 输出必须是严格 JSON，不要输出 Markdown，不要输出解释性废话。
"""


class GradingAgent:
    """答案批改 Agent。"""

    def __init__(self) -> None:
        """初始化 GradingAgent。"""

        self.settings = get_settings()
        self._agent = self._create_agent()

    def grade(self, submission: ExerciseSubmission, memory_context: str = "") -> GradingResult:
        """批改一道题。

        Args:
            submission:
                学生提交，包含题目、参考答案、评分标准和学生答案。
            memory_context:
                学生画像和历史学习记录，可用于让反馈更个性化。

        Returns:
            GradingResult：结构化批改结果。
        """

        prompt = self._build_prompt(submission, memory_context)

        try:
            raw_output = self._agent.run(prompt)
        except Exception as exc:
            raise RuntimeError(f"GradingAgent 调用大模型失败：{exc}") from exc

        payload = self._parse_json_payload(raw_output)
        return self._build_result(payload, submission)

    def _create_agent(self):
        """创建本地 SimpleAgent。"""

        from app.core.llm import HelloAgentsLLM, SimpleAgent

        llm_kwargs = {
            "model": self.settings.llm_model_id,
            "api_key": self.settings.llm_api_key,
            "base_url": self.settings.llm_base_url,
            "timeout": self.settings.llm_timeout,
            "temperature": 0.1,
        }

        try:
            llm = HelloAgentsLLM(**llm_kwargs)
            return SimpleAgent(
                name="答案批改专家",
                llm=llm,
                system_prompt=GRADING_SYSTEM_PROMPT,
            )
        except Exception as exc:
            raise RuntimeError(
                "创建 GradingAgent 失败。请检查 backend/.env 中的 LLM 配置。"
            ) from exc

    def _build_prompt(self, submission: ExerciseSubmission, memory_context: str) -> str:
        """构建批改提示词。"""

        exercise = submission.exercise
        options_text = "\n".join(exercise.options) if exercise.options else "无"
        rubric_text = "\n".join(f"- {item}" for item in exercise.rubric) or "无"
        memory_block = memory_context.strip() or "暂无学生历史记忆。"

        return f"""请批改学生答案。

学生记忆：
{memory_block}

题目信息：
- exercise_id: {exercise.exercise_id}
- exercise_type: {exercise.exercise_type}
- difficulty: {exercise.difficulty}
- knowledge_points: {exercise.knowledge_points}

题干：
{exercise.question}

选项：
{options_text}

参考答案：
{exercise.reference_answer}

评分标准：
{rubric_text}

学生答案：
{submission.student_answer}

请只输出 JSON，格式必须严格如下：
{{
  "exercise_id": "{exercise.exercise_id}",
  "is_correct": false,
  "score": 60,
  "feedback": "学生答案的具体反馈。",
  "reference_answer": "参考答案或参考解法。",
  "mistake_points": ["错误点1", "错误点2"],
  "improvement_suggestions": ["建议1", "建议2"]
}}

重要约束：
1. score 必须是 0 到 100 的整数。
2. is_correct 必须是布尔值。
3. feedback 要具体，不要只写“错了”或“很好”。
4. mistake_points 和 improvement_suggestions 必须是数组。
5. 不要把 JSON 包在 ```json 代码块里。
"""

    def _parse_json_payload(self, raw_output: str) -> Dict[str, Any]:
        """解析模型输出中的 JSON。"""

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
            raise ValueError(f"GradingAgent 输出不是合法 JSON：{raw_output}") from exc

        if not isinstance(payload, dict):
            raise ValueError("GradingAgent 输出 JSON 顶层必须是对象。")

        return payload

    @staticmethod
    def _extract_json_object(text: str) -> str:
        """从文本中提取第一个 JSON 对象。"""

        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text.strip()).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("未找到 JSON 对象。")
        return text[start : end + 1]

    def _build_result(
        self,
        payload: Dict[str, Any],
        submission: ExerciseSubmission,
    ) -> GradingResult:
        """把模型 JSON 转成 GradingResult。"""

        exercise = submission.exercise
        score = self._normalize_score(payload.get("score", 0))
        is_correct = self._normalize_bool(payload.get("is_correct"), score)

        feedback = str(payload.get("feedback", "")).strip()
        if not feedback:
            feedback = "模型未提供具体反馈，请检查批改输出。"

        reference_answer = str(
            payload.get("reference_answer") or exercise.reference_answer
        ).strip()

        return GradingResult(
            exercise_id=str(payload.get("exercise_id") or exercise.exercise_id),
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            reference_answer=reference_answer,
            mistake_points=self._normalize_str_list(payload.get("mistake_points")),
            improvement_suggestions=self._normalize_str_list(
                payload.get("improvement_suggestions")
            ),
            debug={
                "mode": "llm",
                "model": self.settings.llm_model_id,
                "student_id": submission.student_id,
                "has_memory_context": True,
            },
        )

    @staticmethod
    def _normalize_score(value: Any) -> int:
        """把模型输出的 score 规范成 0-100 整数。"""

        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            score = 0
        return max(0, min(100, score))

    @staticmethod
    def _normalize_bool(value: Any, score: int) -> bool:
        """把模型输出的 is_correct 规范成布尔值。"""

        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "correct", "对", "正确"}:
                return True
            if lowered in {"false", "no", "incorrect", "错", "错误"}:
                return False
        return score >= 80

    @staticmethod
    def _normalize_str_list(value: Any) -> list[str]:
        """把模型输出规范成字符串列表。"""

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
