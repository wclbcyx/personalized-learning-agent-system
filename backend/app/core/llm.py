"""本地轻量 LLM 与 Agent 封装。

项目不再依赖 hello-agents 包。这里保留 ``HelloAgentsLLM`` 和
``SimpleAgent`` 两个类名，是为了让现有 Agent 代码保持清晰，同时把实际实现
控制在本项目内部。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class HelloAgentsLLM:
    """OpenAI 兼容 Chat Completions 客户端。"""

    model: str
    api_key: str
    base_url: str = ""
    timeout: int = 60
    temperature: float = 0.2

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """调用大模型并返回文本内容。"""

        if not self.api_key:
            raise RuntimeError("LLM_API_KEY 不能为空，请在 backend/.env 中配置。")

        try:
            from openai import OpenAI
        except Exception as exc:
            raise RuntimeError("缺少 openai 依赖，请先安装 requirements.txt。") from exc

        client_kwargs = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        message = response.choices[0].message
        content: Optional[str] = message.content
        if not content:
            raise RuntimeError("模型返回为空。")
        return content


class SimpleAgent:
    """最小 Agent 封装：保存角色提示词，并执行一次 LLM 调用。"""

    def __init__(self, name: str, llm: HelloAgentsLLM, system_prompt: str) -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt

    def run(self, prompt: str) -> str:
        """执行一次 Agent 推理。"""

        return self.llm.complete(
            system_prompt=self.system_prompt,
            user_prompt=prompt,
        )
