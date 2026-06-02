"""V0.3 练习生成与批改的数据结构。

这个文件只定义“数据长什么样”，不负责调用大模型，也不负责业务编排。

V0.3 的目标链路是：

    用户选择知识点/问题
    -> ExerciseAgent 生成练习题
    -> 用户提交答案
    -> GradingAgent 批改答案
    -> 保存批改结果到学生记忆

因此这里需要定义：
    - 练习生成请求
    - 题目对象
    - 学生答案提交
    - 批改结果
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


ExerciseType = Literal["short_answer", "choice", "calculation"]
DifficultyLevel = Literal["easy", "medium", "hard"]


def now_iso() -> str:
    """返回当前时间字符串，方便记录题目生成和批改时间。"""

    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ExerciseGenerationRequest:
    """生成练习题的请求。

    它描述“要给谁、围绕什么内容、生成什么难度的题”。

    例子：
        给 stu_001 生成 3 道关于“不等式变号”的初中数学练习题。
    """

    # 学生 ID。后续用于读取学生画像和薄弱点。
    student_id: str

    # 课程名称，例如“初中数学”。
    course_name: Optional[str] = None

    # 用户想练习的主题或知识点，例如“不等式”“勾股定理”。
    topic: Optional[str] = None

    # 可选：用户刚刚问过的问题。
    # 如果用户从一次讲解后点击“生成练习”，可以把原问题传进来。
    question: Optional[str] = None

    # 题目数量。
    count: int = 3

    # 难度：easy / medium / hard。
    difficulty: DifficultyLevel = "medium"

    # 题型：short_answer / choice / calculation。
    exercise_type: ExerciseType = "short_answer"

    # 可选：额外要求，例如“每题都要给出解题提示”。
    extra_requirement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典，方便 API 返回或调试。"""

        return asdict(self)


@dataclass
class ExerciseItem:
    """一道练习题。

    注意：
        题目对象里可以包含参考答案和评分标准。
        前端展示时可以选择暂时隐藏 reference_answer 和 rubric，
        等学生提交后再展示。
    """

    # 题目唯一 ID，例如 exercise_001。
    exercise_id: str

    # 题型。
    exercise_type: ExerciseType

    # 难度。
    difficulty: DifficultyLevel

    # 知识点，例如“不等式”“数轴”。
    knowledge_points: List[str]

    # 题干。
    question: str

    # 选择题选项。非选择题可以为空。
    options: List[str] = field(default_factory=list)

    # 参考答案。
    reference_answer: str = ""

    # 解题提示。前端可以作为“提示”按钮展示。
    hint: Optional[str] = None

    # 评分标准。
    rubric: List[str] = field(default_factory=list)

    # 引用来源片段 ID。
    source_ids: List[str] = field(default_factory=list)

    # 创建时间。
    created_at: str = field(default_factory=now_iso)

    # 扩展元数据，例如模型名、原始输出等。
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_answer: bool = True) -> Dict[str, Any]:
        """转成普通字典。

        Args:
            include_answer:
                是否包含 reference_answer 和 rubric。
                - 后端调试或批改时需要 True。
                - 前端出题展示时可以用 False，避免直接泄露答案。
        """

        data = asdict(self)
        if not include_answer:
            data.pop("reference_answer", None)
            data.pop("rubric", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExerciseItem":
        """从字典恢复题目对象。"""

        return cls(
            exercise_id=str(data.get("exercise_id", "")),
            exercise_type=data.get("exercise_type", "short_answer"),
            difficulty=data.get("difficulty", "medium"),
            knowledge_points=list(data.get("knowledge_points", [])),
            question=str(data.get("question", "")),
            options=list(data.get("options", [])),
            reference_answer=str(data.get("reference_answer", "")),
            hint=data.get("hint"),
            rubric=list(data.get("rubric", [])),
            source_ids=list(data.get("source_ids", [])),
            created_at=str(data.get("created_at") or now_iso()),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ExerciseGenerationResponse:
    """练习生成结果。"""

    # 本次练习批次 ID。
    exercise_set_id: str

    # 学生 ID。
    student_id: str

    # 题目列表。
    exercises: List[ExerciseItem]

    # 本次练习的整体说明。
    summary: Optional[str] = None

    # 调试信息。
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_answer: bool = True) -> Dict[str, Any]:
        """转成适合 JSON 返回的字典。"""

        return {
            "exercise_set_id": self.exercise_set_id,
            "student_id": self.student_id,
            "exercises": [
                exercise.to_dict(include_answer=include_answer)
                for exercise in self.exercises
            ],
            "summary": self.summary,
            "debug": self.debug,
        }


@dataclass
class ExerciseSubmission:
    """学生提交的一道题答案。"""

    # 学生 ID。
    student_id: str

    # 题目对象。
    exercise: ExerciseItem

    # 学生答案。
    student_answer: str

    # 提交时间。
    submitted_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典。"""

        return {
            "student_id": self.student_id,
            "exercise": self.exercise.to_dict(include_answer=True),
            "student_answer": self.student_answer,
            "submitted_at": self.submitted_at,
        }


@dataclass
class GradeExerciseRequest:
    """批改练习题的请求。

    前端不需要把完整题目和参考答案传回来，只需要提交：
        - 哪个学生
        - 哪一组练习
        - 哪一道题
        - 学生答案

    后端会根据 exercise_set_id + exercise_id 从 ExerciseStoreService 中
    找到完整题目，再交给 GradingAgent 批改。
    """

    # 学生 ID。
    student_id: str

    # 练习批次 ID，例如 set_stu_001。
    exercise_set_id: str

    # 题目 ID，例如 exercise_001。
    exercise_id: str

    # 学生提交的答案。
    student_answer: str

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典。"""

        return asdict(self)


@dataclass
class GradingResult:
    """一道题的批改结果。"""

    # 题目 ID。
    exercise_id: str

    # 是否答对。
    is_correct: bool

    # 分数，建议范围 0-100。
    score: int

    # 批改反馈，说明哪里对、哪里错。
    feedback: str

    # 标准答案或参考解法。
    reference_answer: str

    # 学生的错误点。
    mistake_points: List[str] = field(default_factory=list)

    # 针对错误点的改进建议。
    improvement_suggestions: List[str] = field(default_factory=list)

    # 批改时间。
    graded_at: str = field(default_factory=now_iso)

    # 调试信息。
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转成适合 JSON 返回的字典。"""

        return asdict(self)
