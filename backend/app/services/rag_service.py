"""V0.1 最小版 RAG 检索服务。

RAG = Retrieval-Augmented Generation，检索增强生成。

这个文件先实现“检索”部分：

课程 Markdown -> 切分成 chunk -> 根据问题打分 -> 返回最相关的片段

注意：
    V0.1 这里故意不使用向量数据库和 embedding 模型。
    原因是我们现在的目标是先跑通完整链路，而不是一开始就把系统做复杂。

后续升级方向：
    - 把关键词检索换成 embedding 相似度检索。
    - 把内存索引换成 Qdrant / Chroma / FAISS。
    - 加入重排 rerank。
    - 加入更精细的 Markdown 标题层级切分。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Sequence

from app.core.config import get_settings
from app.models.schemas import CourseDocument, SourceChunk
from app.services.material_ingestion_service import MaterialIngestionService


# 中文和英文混合文本里，先用一个简单正则抽取“词”。
# - 英文/数字：agent、rag、tool、v0.1
# - 中文：先抽取连续中文，再额外拆成 2 字/3 字片段，提高召回效果。
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.+-]+|[\u4e00-\u9fff]+")


class RagService:
    """最小版 RAG 检索服务。

    这个类负责三件事：
        1. 读取课程资料。
        2. 把长文档切成较小片段。
        3. 根据用户问题返回最相关的片段。
    """

    def __init__(
        self,
        documents: Sequence[CourseDocument] | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        """初始化 RAG 服务。

        Args:
            documents:
                可选的课程文档列表。如果不传，就自动从资料目录读取。
                这个参数方便你后面写单元测试。
            chunk_size:
                每个 chunk 的最大字符数。
            chunk_overlap:
                相邻 chunk 的重叠字符数，避免切分时丢失上下文。
        """

        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.documents = list(documents) if documents is not None else self._load_documents()
        self.chunks = self.chunk_documents(self.documents)

    def search(
        self,
        question: str,
        top_k: int | None = None,
        course_name: str | None = None,
    ) -> List[SourceChunk]:
        """根据用户问题检索最相关的资料片段。

        Args:
            question:
                用户问题。
            top_k:
                返回几个最相关片段。如果不传，使用 config.py 里的 rag_top_k。
            course_name:
                可选课程名。传入后会优先限制在标题、路径或正文中包含该课程名的资料片段。

        Returns:
            按 score 从高到低排序的 SourceChunk 列表。
        """

        settings = get_settings()
        limit = top_k or settings.rag_top_k

        query_tokens = self._tokenize(question)
        if not query_tokens:
            return []

        candidate_chunks = self._filter_chunks_by_course(course_name)
        scored_chunks: List[SourceChunk] = []
        for chunk in candidate_chunks:
            score = self._score_chunk(query_tokens, chunk)
            if score <= 0:
                continue

            scored_chunks.append(
                SourceChunk(
                    chunk_id=chunk.chunk_id,
                    title=chunk.title,
                    content=chunk.content,
                    score=round(score, 4),
                    source_path=chunk.source_path,
                    start_index=chunk.start_index,
                    end_index=chunk.end_index,
                    metadata=chunk.metadata,
                )
            )

        scored_chunks.sort(key=lambda item: item.score, reverse=True)
        return scored_chunks[:limit]

    def _filter_chunks_by_course(self, course_name: str | None) -> List[SourceChunk]:
        """按课程名过滤 chunk。

        V1.0 仍然使用本地 Markdown 检索，因此课程筛选先采用轻量规则：
        标题、路径、元数据或正文中出现课程名即可。若过滤后为空，则回退到全部资料，
        避免用户课程名写得略有差异时完全检索不到内容。
        """

        course = (course_name or "").strip().lower()
        if not course:
            return list(self.chunks)

        matched = []
        for chunk in self.chunks:
            haystack = " ".join(
                [
                    chunk.title,
                    chunk.source_path,
                    chunk.content[:500],
                    str(chunk.metadata.get("course_name", "")),
                    str(chunk.metadata.get("relative_path", "")),
                ]
            ).lower()
            if course in haystack:
                matched.append(chunk)

        return matched or list(self.chunks)

    def chunk_documents(self, documents: Sequence[CourseDocument]) -> List[SourceChunk]:
        """把课程文档切分成 SourceChunk。

        为什么要切分：
            大模型上下文有限，不能每次都塞入整本教材。
            RAG 通常会先把文档切成小块，再检索最相关的小块。

        当前策略：
            先按 Markdown 标题和空行切成段落，再把段落合并到固定长度。
        """

        chunks: List[SourceChunk] = []

        for document_index, document in enumerate(documents, start=1):
            sections = self._split_markdown_sections(document.content)
            merged_chunks = self._merge_sections_to_chunks(sections)

            cursor = 0
            for chunk_index, chunk_text in enumerate(merged_chunks, start=1):
                start_index = document.content.find(chunk_text, cursor)
                if start_index == -1:
                    start_index = None
                    end_index = None
                else:
                    end_index = start_index + len(chunk_text)
                    cursor = end_index

                chunk_id = f"doc{document_index:03d}_chunk{chunk_index:04d}"
                chunks.append(
                    SourceChunk(
                        chunk_id=chunk_id,
                        title=document.title,
                        content=chunk_text,
                        score=0.0,
                        source_path=document.source_path,
                        start_index=start_index,
                        end_index=end_index,
                        metadata={
                            **document.metadata,
                            "document_index": document_index,
                            "chunk_index": chunk_index,
                        },
                    )
                )

        return chunks

    def _load_documents(self) -> List[CourseDocument]:
        """从资料目录读取课程文档。"""

        ingestion_service = MaterialIngestionService()
        return ingestion_service.load_markdown_files()

    @staticmethod
    def _split_markdown_sections(content: str) -> List[str]:
        """把 Markdown 文本拆成较小的语义段落。

        这里保留标题行，因为标题本身经常包含重要关键词，比如
        “工具调用”“RAG”“记忆系统”。
        """

        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        raw_sections = re.split(r"\n\s*\n", normalized)
        return [section.strip() for section in raw_sections if section.strip()]

    def _merge_sections_to_chunks(self, sections: Sequence[str]) -> List[str]:
        """把短段落合并成大小合适的 chunk。

        如果每个段落都作为一个 chunk，可能太碎。
        如果整篇文档作为一个 chunk，又太长。
        所以这里把多个小段落合并到 chunk_size 附近。
        """

        chunks: List[str] = []
        current_parts: List[str] = []
        current_length = 0

        for section in sections:
            section_length = len(section)

            # 如果单个 section 已经很长，就单独切它。
            if section_length > self.chunk_size:
                if current_parts:
                    chunks.append("\n\n".join(current_parts))
                    current_parts = []
                    current_length = 0
                chunks.extend(self._split_long_text(section))
                continue

            next_length = current_length + section_length + (2 if current_parts else 0)
            if current_parts and next_length > self.chunk_size:
                chunks.append("\n\n".join(current_parts))

                # 简单保留上一块尾部一点内容，作为 overlap。
                overlap_text = self._tail_overlap(chunks[-1])
                current_parts = [overlap_text, section] if overlap_text else [section]
                current_length = sum(len(part) for part in current_parts) + 2 * (len(current_parts) - 1)
            else:
                current_parts.append(section)
                current_length = next_length

        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _split_long_text(self, text: str) -> List[str]:
        """切分超过 chunk_size 的长文本。"""

        chunks: List[str] = []
        step = max(1, self.chunk_size - self.chunk_overlap)

        for start in range(0, len(text), step):
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break

        return chunks

    def _tail_overlap(self, text: str) -> str:
        """取上一块末尾的一小段，作为下一块开头的上下文。"""

        if self.chunk_overlap <= 0:
            return ""
        return text[-self.chunk_overlap :].strip()

    def _score_chunk(self, query_tokens: Sequence[str], chunk: SourceChunk) -> float:
        """计算问题和 chunk 的相关度分数。

        这是一个非常朴素的关键词分数，适合教学和 V0.1 验证：
            - 命中的关键词越多，分数越高。
            - 标题命中会额外加分。
            - chunk 太长会轻微惩罚，避免长文本天然占便宜。
        """

        chunk_tokens = self._tokenize(chunk.content)
        if not chunk_tokens:
            return 0.0

        query_counter = Counter(query_tokens)
        chunk_counter = Counter(chunk_tokens)
        title_tokens = set(self._tokenize(chunk.title))

        overlap_score = 0.0
        for token, query_count in query_counter.items():
            chunk_count = chunk_counter.get(token, 0)
            if chunk_count <= 0:
                continue

            # log 可以避免某个词重复很多次时分数过度膨胀。
            overlap_score += query_count * (1.0 + math.log(chunk_count))

            if token in title_tokens:
                overlap_score += 1.5

        length_penalty = 1.0 + len(chunk_tokens) / 220.0
        return overlap_score / length_penalty

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """把文本转换成检索用 token。

        注意：
            这不是严肃的中文分词，只是 V0.1 的轻量实现。
            对中文连续片段会生成 2-gram 和 3-gram，例如：
                工具调用 -> 工具、具调、调用、工具调、具调用
            这样可以让“工具调用”和“调用工具”这类问题更容易命中。
            后续可以替换成 jieba、embedding 或向量数据库检索。
        """

        raw_tokens = TOKEN_PATTERN.findall(text.lower())
        tokens: List[str] = []

        for token in raw_tokens:
            if not token.strip():
                continue

            tokens.append(token)

            if re.fullmatch(r"[\u4e00-\u9fff]+", token):
                for ngram_size in (2, 3):
                    if len(token) < ngram_size:
                        continue
                    tokens.extend(
                        token[index : index + ngram_size]
                        for index in range(0, len(token) - ngram_size + 1)
                    )

        return tokens


def search_course_materials(question: str, top_k: int | None = None) -> List[SourceChunk]:
    """便捷函数：直接检索课程资料。"""

    service = RagService()
    return service.search(question=question, top_k=top_k)
