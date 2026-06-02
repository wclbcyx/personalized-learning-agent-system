"""V0.4 协调 Agent。

CoordinatorAgent 负责判断用户意图，并给出应该调用的能力。
当前版本先做轻量规则编排，不调用大模型，保证稳定。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal


IntentType = Literal["ask", "generate_exercise", "grade_exercise", "generate_plan", "reflect"]


@dataclass
class CoordinationResult:
    """协调器输出。"""

    intent: IntentType
    reason: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "reason": self.reason,
            "payload": self.payload,
        }


class CoordinatorAgent:
    """根据请求内容判断应该调用哪个 Agent 或 service。"""

    def route(self, payload: Dict[str, Any]) -> CoordinationResult:
        """轻量规则路由。"""

        text = self._collect_text(payload)

        if payload.get("student_answer") and payload.get("exercise_set_id") and payload.get("exercise_id"):
            return CoordinationResult("grade_exercise", "检测到练习批次、题目 ID 和学生答案。", payload)

        if self._contains(text, ["批改", "评分", "提交答案"]) and payload.get("student_answer"):
            return CoordinationResult("grade_exercise", "检测到批改意图和学生答案。", payload)

        if payload.get("available_days") or payload.get("daily_minutes") or payload.get("learning_goal"):
            if payload.get("course_name") and payload.get("learning_goal"):
                return CoordinationResult("generate_plan", "检测到课程和学习目标，适合生成学习计划。", payload)

        if self._contains(text, ["安排学习", "学习计划", "规划", "怎么学", "计划"]):
            return CoordinationResult("generate_plan", "检测到学习规划意图。", payload)

        if payload.get("topic") or payload.get("count") or payload.get("exercise_type"):
            return CoordinationResult("generate_exercise", "检测到练习主题、数量或题型。", payload)

        if self._contains(text, ["出题", "练习", "三道题", "题目", "检测题"]):
            return CoordinationResult("generate_exercise", "检测到生成练习意图。", payload)

        if payload.get("reflect") or payload.get("reflection"):
            return CoordinationResult("reflect", "检测到反思请求。", payload)

        if self._contains(text, ["反思", "薄弱", "总结", "哪里错", "哪里弱", "掌握情况"]):
            return CoordinationResult("reflect", "检测到学习反思或薄弱点诊断意图。", payload)

        return CoordinationResult("ask", "默认作为学习问答处理。", payload)

    @staticmethod
    def _collect_text(payload: Dict[str, Any]) -> str:
        keys = ["message", "question", "command", "learning_goal", "topic", "student_answer"]
        return " ".join(str(payload.get(key) or "") for key in keys).lower()

    @staticmethod
    def _contains(text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)
