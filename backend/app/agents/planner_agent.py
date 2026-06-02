"""V0.4 学习规划 Agent。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.core.config import get_settings
from app.models.plan import LearningPlan, LearningPlanRequest, LearningStage, LearningTask, PlanCheckpoint
from app.models.schemas import SourceChunk


PLANNER_SYSTEM_PROMPT = """你是一个严谨的个性化学习规划专家。

你需要基于学生画像、历史薄弱点、学习目标和课程资料，生成阶段化学习计划。

要求：
1. 计划必须可执行，任务要具体。
2. 每个阶段要有明确 objective、任务列表和检查点。
3. 每个任务要包含 task_type、estimated_minutes、knowledge_points。
4. 总体安排要匹配 available_days 和 daily_minutes。
5. 输出必须是严格 JSON，不要 Markdown，不要解释性废话。
"""


class PlannerAgent:
    """根据学生目标、水平、薄弱点和资料生成学习计划。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._agent = self._create_agent()

    def generate_plan(
        self,
        request: LearningPlanRequest,
        memory_context: str,
        sources: List[SourceChunk],
    ) -> LearningPlan:
        """生成完整学习计划。"""

        prompt = self._build_prompt(request, memory_context, sources)
        try:
            raw_output = self._agent.run(prompt)
        except Exception as exc:
            raise RuntimeError(f"PlannerAgent 调用大模型失败：{exc}") from exc

        payload = self._parse_json_payload(raw_output)
        return self._build_plan(payload, request, sources)

    def _create_agent(self):
        from app.core.llm import HelloAgentsLLM, SimpleAgent

        try:
            llm = HelloAgentsLLM(
                model=self.settings.llm_model_id,
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.llm_timeout,
                temperature=0.2,
            )
            return SimpleAgent(name="学习规划专家", llm=llm, system_prompt=PLANNER_SYSTEM_PROMPT)
        except Exception as exc:
            raise RuntimeError("创建 PlannerAgent 失败，请检查 LLM 配置。") from exc

    def _build_prompt(
        self,
        request: LearningPlanRequest,
        memory_context: str,
        sources: List[SourceChunk],
    ) -> str:
        source_context = "\n\n".join(
            f"[资料 {index}] 标题：{source.title}\n片段ID：{source.chunk_id}\n内容：{source.content}"
            for index, source in enumerate(sources, start=1)
        )
        source_ids = [source.chunk_id for source in sources]
        focus_topics = request.focus_topics or []

        return f"""请生成个性化学习计划。

学生画像与历史记忆：
{memory_context or "暂无学生记忆。"}

计划请求：
- student_id: {request.student_id}
- course_name: {request.course_name}
- learning_goal: {request.learning_goal}
- focus_topics: {focus_topics}
- available_days: {request.available_days}
- daily_minutes: {request.daily_minutes}
- extra_requirement: {request.extra_requirement or "无"}

课程资料：
{source_context}

可引用资料片段 ID：
{source_ids}

请只输出 JSON，格式如下：
{{
  "plan_id": "plan_stu_001_001",
  "overall_suggestions": ["建议1", "建议2"],
  "stages": [
    {{
      "stage_id": "stage_001",
      "title": "阶段标题",
      "objective": "阶段目标",
      "start_day": 1,
      "end_day": 3,
      "knowledge_points": ["知识点"],
      "tasks": [
        {{
          "task_id": "task_001",
          "task_type": "reading",
          "title": "任务标题",
          "description": "具体任务描述",
          "estimated_minutes": 20,
          "knowledge_points": ["知识点"],
          "completion_criteria": "完成标准",
          "source_ids": ["doc001_chunk0001"]
        }}
      ],
      "checkpoint": {{
        "checkpoint_id": "checkpoint_001",
        "title": "检查点标题",
        "description": "检查方式",
        "pass_criteria": "达标标准"
      }}
    }}
  ]
}}

约束：
1. task_type 只能是 reading/explanation/exercise/review/quiz/project。
2. source_ids 只能从可引用资料片段 ID 中选择。
3. 所有任务 estimated_minutes 总体要适配每日 {request.daily_minutes} 分钟。
4. 不要把 JSON 包在代码块里。
"""

    def _parse_json_payload(self, raw_output: str) -> Dict[str, Any]:
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
            raise ValueError(f"PlannerAgent 输出不是合法 JSON：{raw_output}")
        return json.loads(text[start : end + 1])

    def _build_plan(
        self,
        payload: Dict[str, Any],
        request: LearningPlanRequest,
        sources: List[SourceChunk],
    ) -> LearningPlan:
        valid_source_ids = {source.chunk_id for source in sources}
        stages: List[LearningStage] = []

        for stage_index, raw_stage in enumerate(payload.get("stages", []), start=1):
            if not isinstance(raw_stage, dict):
                continue

            tasks: List[LearningTask] = []
            for task_index, raw_task in enumerate(raw_stage.get("tasks", []), start=1):
                if not isinstance(raw_task, dict):
                    continue
                source_ids = [
                    source_id for source_id in raw_task.get("source_ids", []) if source_id in valid_source_ids
                ]
                tasks.append(
                    LearningTask(
                        task_id=str(raw_task.get("task_id") or f"task_{stage_index:03d}_{task_index:03d}"),
                        task_type=raw_task.get("task_type", "reading"),
                        title=str(raw_task.get("title", "")),
                        description=str(raw_task.get("description", "")),
                        estimated_minutes=int(raw_task.get("estimated_minutes", request.daily_minutes)),
                        knowledge_points=list(raw_task.get("knowledge_points", [])),
                        completion_criteria=raw_task.get("completion_criteria"),
                        source_ids=source_ids,
                    )
                )

            checkpoint_data = raw_stage.get("checkpoint") or {}
            checkpoint = None
            if isinstance(checkpoint_data, dict) and checkpoint_data:
                checkpoint = PlanCheckpoint(
                    checkpoint_id=str(checkpoint_data.get("checkpoint_id") or f"checkpoint_{stage_index:03d}"),
                    title=str(checkpoint_data.get("title", "")),
                    description=str(checkpoint_data.get("description", "")),
                    pass_criteria=str(checkpoint_data.get("pass_criteria", "")),
                )

            stages.append(
                LearningStage(
                    stage_id=str(raw_stage.get("stage_id") or f"stage_{stage_index:03d}"),
                    title=str(raw_stage.get("title", "")),
                    objective=str(raw_stage.get("objective", "")),
                    start_day=int(raw_stage.get("start_day", stage_index)),
                    end_day=int(raw_stage.get("end_day", stage_index)),
                    knowledge_points=list(raw_stage.get("knowledge_points", [])),
                    tasks=tasks,
                    checkpoint=checkpoint,
                )
            )

        if not stages:
            raise ValueError("PlannerAgent 没有生成有效 stages。")

        return LearningPlan(
            plan_id=str(payload.get("plan_id") or f"plan_{request.student_id}"),
            student_id=request.student_id,
            course_name=request.course_name,
            learning_goal=request.learning_goal,
            available_days=request.available_days,
            daily_minutes=request.daily_minutes,
            stages=stages,
            overall_suggestions=list(payload.get("overall_suggestions", [])),
            status="draft",
            debug={
                "mode": "llm",
                "model": self.settings.llm_model_id,
                "source_count": len(sources),
            },
        )
