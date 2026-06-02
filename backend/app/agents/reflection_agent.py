"""V0.4 学习反思 Agent。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from app.core.config import get_settings


REFLECTION_SYSTEM_PROMPT = """你是一个学习反思与诊断专家。

你需要根据学生画像、最近学习记录、问答和练习批改表现，总结薄弱点、掌握情况和下一步建议。

输出必须是严格 JSON，不要 Markdown，不要解释性废话。
"""


class ReflectionAgent:
    """根据学习历史总结薄弱点和下一步建议。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._agent = self._create_agent()

    def reflect(self, memory_context: str) -> Dict[str, Any]:
        """生成反思结果。"""

        prompt = f"""请根据以下学生记忆生成学习反思。

学生记忆：
{memory_context or "暂无学生记忆。"}

请只输出 JSON，格式如下：
{{
  "summary": "一句话总结学生近期状态",
  "mastered_points": ["已掌握知识点"],
  "weak_points": ["薄弱点"],
  "next_recommendations": ["下一步建议"],
  "level_update": "对 current_level 的更新建议"
}}
"""
        try:
            raw_output = self._agent.run(prompt)
        except Exception as exc:
            raise RuntimeError(f"ReflectionAgent 调用大模型失败：{exc}") from exc

        return self._parse_json_payload(raw_output)

    def _create_agent(self):
        from app.core.llm import HelloAgentsLLM, SimpleAgent

        llm = HelloAgentsLLM(
            model=self.settings.llm_model_id,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout,
            temperature=0.2,
        )
        return SimpleAgent(name="学习反思专家", llm=llm, system_prompt=REFLECTION_SYSTEM_PROMPT)

    @staticmethod
    def _parse_json_payload(raw_output: str) -> Dict[str, Any]:
        text = raw_output.strip()
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"ReflectionAgent 输出不是合法 JSON：{raw_output}")
        payload = json.loads(text[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("ReflectionAgent 输出 JSON 顶层必须是对象。")
        return payload
