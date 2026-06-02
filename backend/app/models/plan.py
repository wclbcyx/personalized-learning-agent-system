"""V0.4 个性化学习计划的数据结构。

这个文件只定义“学习计划长什么样”，不负责调用大模型。

V0.4 的目标链路是：

    用户设置学习目标
    -> PlannerAgent 读取学生画像、历史薄弱点和课程资料
    -> 生成阶段化学习计划
    -> 前端展示阶段、每日任务和检查点

一个完整计划包含：
    - 基本信息：学生、课程、目标、周期
    - 多个学习阶段：每个阶段解决一类问题
    - 多个学习任务：阅读、讲解、练习、复习、测试、项目
    - 检查点：用于判断是否掌握并决定是否调整计划
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


TaskType = Literal[
    "reading",
    "explanation",
    "exercise",
    "review",
    "quiz",
    "project",
]

TaskStatus = Literal["pending", "in_progress", "completed", "skipped"]
PlanStatus = Literal["draft", "active", "completed", "adjusted"]


def now_iso() -> str:
    """返回当前时间字符串，方便 JSON 保存。"""

    return datetime.now().isoformat(timespec="seconds")


@dataclass
class LearningPlanRequest:
    """生成学习计划的请求。

    这个请求通常来自前端“创建学习计划”表单。

    例子：
        学生希望在 14 天内掌握初中数学中的不等式和一次函数，
        每天可以投入 40 分钟。
    """

    # 学生 ID，用于读取 StudentProfile。
    student_id: str

    # 课程名称，例如“初中数学”“Python 编程”“机器学习”。
    course_name: str

    # 学习目标，例如“两周内掌握一次函数和不等式”。
    learning_goal: str

    # 可选：希望重点学习的知识点。
    focus_topics: List[str] = field(default_factory=list)

    # 可用学习天数。
    available_days: int = 14

    # 每天计划投入多少分钟。
    daily_minutes: int = 40

    # 可选：额外要求，例如“周末安排综合测试”。
    extra_requirement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典。"""

        return asdict(self)


@dataclass
class LearningTask:
    """计划中的一个具体学习任务。

    一个任务应该足够具体，学生可以直接执行。

    例子：
        - 阅读不等式基础规则，整理 3 条变号条件。
        - 完成 5 道一元一次不等式计算题。
        - 用自己的话解释一次函数中 k 和 b 的含义。
    """

    # 任务唯一 ID，例如 task_001。
    task_id: str

    # 任务类型。
    task_type: TaskType

    # 简短标题。
    title: str

    # 具体任务描述。
    description: str

    # 建议耗时，单位：分钟。
    estimated_minutes: int

    # 本任务涉及的知识点。
    knowledge_points: List[str] = field(default_factory=list)

    # 可选：任务完成标准，例如“正确率达到 80%”。
    completion_criteria: Optional[str] = None

    # 可选：关联课程资料片段 ID。
    source_ids: List[str] = field(default_factory=list)

    # 任务状态。
    status: TaskStatus = "pending"

    # 扩展元数据。
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典。"""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningTask":
        """从字典恢复任务对象。"""

        return cls(
            task_id=str(data.get("task_id", "")),
            task_type=data.get("task_type", "reading"),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            estimated_minutes=int(data.get("estimated_minutes", 0)),
            knowledge_points=list(data.get("knowledge_points", [])),
            completion_criteria=data.get("completion_criteria"),
            source_ids=list(data.get("source_ids", [])),
            status=data.get("status", "pending"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class PlanCheckpoint:
    """学习阶段中的检查点。

    检查点用于回答：
        学生是否已经掌握当前阶段？
        是否可以进入下一阶段？
        是否需要 ReflectionAgent 调整计划？
    """

    # 检查点唯一 ID。
    checkpoint_id: str

    # 检查点标题。
    title: str

    # 检查方式，例如“完成 5 道测试题，正确率达到 80%”。
    description: str

    # 达标标准。
    pass_criteria: str

    # 可选：实际结果，后续执行计划时填写。
    result_summary: Optional[str] = None

    # 可选：是否达标。
    passed: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典。"""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanCheckpoint":
        """从字典恢复检查点对象。"""

        return cls(
            checkpoint_id=str(data.get("checkpoint_id", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            pass_criteria=str(data.get("pass_criteria", "")),
            result_summary=data.get("result_summary"),
            passed=data.get("passed"),
        )


@dataclass
class LearningStage:
    """学习计划中的一个阶段。

    一个阶段通常聚焦一个主题，包含若干任务和一个阶段检查点。
    """

    # 阶段唯一 ID，例如 stage_001。
    stage_id: str

    # 阶段标题，例如“阶段一：不等式基础巩固”。
    title: str

    # 阶段学习目标。
    objective: str

    # 建议安排在第几天到第几天。
    start_day: int
    end_day: int

    # 本阶段重点知识点。
    knowledge_points: List[str] = field(default_factory=list)

    # 具体学习任务。
    tasks: List[LearningTask] = field(default_factory=list)

    # 阶段检查点。
    checkpoint: Optional[PlanCheckpoint] = None

    def to_dict(self) -> Dict[str, Any]:
        """转成普通字典。"""

        return {
            "stage_id": self.stage_id,
            "title": self.title,
            "objective": self.objective,
            "start_day": self.start_day,
            "end_day": self.end_day,
            "knowledge_points": self.knowledge_points,
            "tasks": [task.to_dict() for task in self.tasks],
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningStage":
        """从字典恢复阶段对象。"""

        tasks = [
            LearningTask.from_dict(item)
            for item in data.get("tasks", [])
            if isinstance(item, dict)
        ]

        checkpoint_data = data.get("checkpoint")
        checkpoint = (
            PlanCheckpoint.from_dict(checkpoint_data)
            if isinstance(checkpoint_data, dict)
            else None
        )

        return cls(
            stage_id=str(data.get("stage_id", "")),
            title=str(data.get("title", "")),
            objective=str(data.get("objective", "")),
            start_day=int(data.get("start_day", 1)),
            end_day=int(data.get("end_day", 1)),
            knowledge_points=list(data.get("knowledge_points", [])),
            tasks=tasks,
            checkpoint=checkpoint,
        )


@dataclass
class LearningPlan:
    """完整个性化学习计划。

    它是 PlannerAgent 的最终输出，也是后续前端学习计划面板的数据源。
    """

    # 计划唯一 ID，例如 plan_stu_001_001。
    plan_id: str

    # 学生 ID。
    student_id: str

    # 课程名称。
    course_name: str

    # 总体学习目标。
    learning_goal: str

    # 总学习周期。
    available_days: int

    # 每日学习时长。
    daily_minutes: int

    # 阶段列表。
    stages: List[LearningStage]

    # 可选：总体建议。
    overall_suggestions: List[str] = field(default_factory=list)

    # 计划状态。
    status: PlanStatus = "draft"

    # 创建和更新时间。
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    # 调试信息。
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转成适合 JSON 保存和 API 返回的字典。"""

        return {
            "plan_id": self.plan_id,
            "student_id": self.student_id,
            "course_name": self.course_name,
            "learning_goal": self.learning_goal,
            "available_days": self.available_days,
            "daily_minutes": self.daily_minutes,
            "stages": [stage.to_dict() for stage in self.stages],
            "overall_suggestions": self.overall_suggestions,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "debug": self.debug,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningPlan":
        """从字典恢复完整学习计划。"""

        stages = [
            LearningStage.from_dict(item)
            for item in data.get("stages", [])
            if isinstance(item, dict)
        ]

        return cls(
            plan_id=str(data.get("plan_id", "")),
            student_id=str(data.get("student_id", "")),
            course_name=str(data.get("course_name", "")),
            learning_goal=str(data.get("learning_goal", "")),
            available_days=int(data.get("available_days", 14)),
            daily_minutes=int(data.get("daily_minutes", 40)),
            stages=stages,
            overall_suggestions=list(data.get("overall_suggestions", [])),
            status=data.get("status", "draft"),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
            debug=dict(data.get("debug", {})),
        )
