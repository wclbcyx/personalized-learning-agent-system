"""V0.4 检索 Agent。

它把已有 RagService 包装成正式 Agent 角色，方便 CoordinatorAgent 统一调度。
"""

from __future__ import annotations

from typing import List

from app.models.schemas import SourceChunk
from app.services.rag_service import RagService


class RetrieverAgent:
    """课程资料检索 Agent。"""

    def __init__(self, rag_service: RagService | None = None) -> None:
        self.rag_service = rag_service or RagService()

    def retrieve(self, query: str, top_k: int | None = None) -> List[SourceChunk]:
        """检索课程资料。"""

        return self.rag_service.search(question=query, top_k=top_k)
