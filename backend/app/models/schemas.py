"""V0.1 最小闭环会用到的数据结构。

这个文件只负责定义“数据长什么样”，不写具体业务逻辑。

当前 V0.1 的目标链路是：

用户问题 -> 课程资料检索 -> TutorAgent 回答 -> 返回答案和引用来源

为了让你前期更容易理解和运行，这里先使用 Python 标准库里的
``dataclass``。等后面接 FastAPI 接口时，可以再把这些结构改成或
包装成 Pydantic 的 BaseModel。
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LearningQuestionRequest:
    """用户的一次学习提问。

    这是最小闭环的输入对象。

    例子：
        学生问：“工具调用和 RAG 有什么关系？”

    后续流程：
        LearningQuestionRequest
        -> RAG 检索相关课程片段
        -> TutorAgent 生成回答
        -> LearningAnswerResponse
    """

    # 学生 ID。
    # V0.1 里只是透传；V0.2 做记忆系统时，会用它读取学生画像、
    # 历史问题、薄弱点和错题记录。
    student_id: str

    # 学生当前提出的问题。
    question: str

    # 课程名称，可选。
    # 例如："HelloAgents"、"机器学习"、"数据结构"。
    # 如果以后支持多个课程，可以用这个字段决定检索哪个资料库。
    course_name: Optional[str] = None

    # 学习目标，可选。
    # 例如："4 周内掌握 HelloAgents 并完成一个多智能体项目"。
    # V0.1 可以先不用，后续 PlannerAgent 会用到。
    learning_goal: Optional[str] = None

    # 当前水平，可选。
    # 例如："会 Python，但不了解 RAG 和多智能体"。
    # 后续 TutorAgent 可以根据这个字段调整讲解深度。
    current_level: Optional[str] = None

    # 偏好的讲解风格，可选。
    # 例如："先讲原理，再给例子，最后给练习"。
    preferred_style: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """把请求对象转成普通字典。

        用途：
        - 打印调试日志
        - 返回 API 响应
        - 保存到本地 JSON 文件
        """

        return asdict(self)


@dataclass
class CourseDocument:
    """一份完整的课程资料文档。

    它通常对应一个 Markdown 文件，比如 HelloAgents 的某一章。

    注意：
        RAG 检索时不会直接把整篇文档都丢给模型，而是会先把
        CourseDocument 切成多个 SourceChunk。
    """

    # 文档标题。
    # 可以来自 Markdown 的一级标题，也可以直接使用文件名。
    title: str

    # 文档来源路径。
    # 例如：backend/data/course_materials/chapter01.md
    source_path: str

    # 文档完整文本内容。
    content: str

    # 扩展元数据。
    # 先留着，后续可以放 chapter_id、url、author、tags 等信息。
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """把课程文档对象转成普通字典。"""

        return asdict(self)


@dataclass
class SourceChunk:
    """RAG 检索出来的一小段资料。

    RAG 的基本思想是：
        1. 把课程资料切成很多小片段。
        2. 根据用户问题找到最相关的几个片段。
        3. 把这些片段作为上下文交给 Agent。
        4. Agent 基于上下文回答，而不是凭空编造。
    """

    # 片段唯一 ID。
    # 例如："chapter01_0001"。
    chunk_id: str

    # 所属文档标题。
    # 例如："第一章 Agent 基础"。
    title: str

    # 片段正文内容。
    # 这部分会进入 TutorAgent 的提示词上下文。
    content: str

    # 检索相关度分数。
    # 分数越高，说明这个片段和用户问题越相关。
    score: float

    # 原始文档路径。
    # 用来做引用来源，也方便调试“答案来自哪里”。
    source_path: str

    # 片段在原文中的起始位置，可选。
    # 关键词检索阶段可以先不填，后续做更精细的切分时再用。
    start_index: Optional[int] = None

    # 片段在原文中的结束位置，可选。
    end_index: Optional[int] = None

    # 扩展元数据。
    # 例如：所属章节、标题层级、关键词、token 数等。
    metadata: Dict[str, Any] = field(default_factory=dict)

    def citation_label(self) -> str:
        """生成一个简短的引用标签。

        例子：
            第一章 Agent 基础 (chapter01_0001)
        """

        return f"{self.title} ({self.chunk_id})"

    def to_dict(self) -> Dict[str, Any]:
        """把资料片段对象转成普通字典。"""

        return asdict(self)


@dataclass
class LearningAnswerResponse:
    """学习助手返回给用户的最终结果。

    这是最小闭环的输出对象。

    它不仅包含回答文本，还包含：
    - sources：回答依据来自哪些课程资料片段。
    - next_steps：建议用户接下来怎么学。
    - summary：一句话摘要，方便前端展示。
    - debug：调试信息，开发阶段很有用。
    """

    # TutorAgent 生成的自然语言回答。
    answer: str

    # 本次回答使用到的资料片段。
    # 前端可以把它展示成“引用来源”。
    sources: List[SourceChunk] = field(default_factory=list)

    # 下一步学习建议。
    # 例如：["阅读工具调用章节", "实现一个 SearchTool 示例"]。
    next_steps: List[str] = field(default_factory=list)

    # 回答摘要，可选。
    # 比如前端卡片标题可以显示这句话。
    summary: Optional[str] = None

    # 调试信息。
    # 比如检索耗时、命中的关键词、原始模型输出等。
    # 注意：正式展示给用户时可以隐藏这个字段。
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转成适合 JSON 序列化的普通字典。

        这里手动处理 sources，是因为 sources 里面装的是 SourceChunk 对象，
        不能直接作为 JSON 返回。
        """

        return {
            "answer": self.answer,
            "sources": [source.to_dict() for source in self.sources],
            "next_steps": self.next_steps,
            "summary": self.summary,
            "debug": self.debug,
        }
