"""系统评估与实验数据服务。

V1.0 的评估模块用于支撑毕设论文展示：它不替代严肃实验平台，但能从现有
学生画像、练习批次、课程资料和调用日志中汇总可解释指标。
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from app.core.config import BACKEND_DIR
from app.models.memory import StudentProfile
from app.services.exercise_store_service import DEFAULT_EXERCISE_SET_DIR
from app.services.material_service import MaterialService
from app.services.memory_service import DEFAULT_PROFILE_DIR, MemoryService


DEFAULT_LOG_DIR = BACKEND_DIR / "data" / "logs"
DEFAULT_EVENT_LOG = DEFAULT_LOG_DIR / "agent_events.jsonl"


@dataclass
class EvaluationSummary:
    """评估看板指标。"""

    student_count: int
    material_count: int
    indexed_material_count: int
    exercise_set_count: int
    plan_count: int
    memory_count: int
    grading_count: int
    average_score: Optional[float]
    weak_point_count: int
    event_count: int
    average_response_ms: Optional[float]
    intent_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class EvaluationService:
    """读取与记录评估数据。"""

    def __init__(
        self,
        profile_dir: Path = DEFAULT_PROFILE_DIR,
        log_path: Path = DEFAULT_EVENT_LOG,
    ) -> None:
        self.profile_dir = profile_dir
        self.plan_dir = profile_dir / "plans"
        self.exercise_dir = DEFAULT_EXERCISE_SET_DIR
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: dict[str, Any]) -> None:
        """写入一次系统调用事件。"""

        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **event,
        }
        self.log_path.write_text("", encoding="utf-8") if not self.log_path.exists() else None
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def build_summary(self) -> EvaluationSummary:
        """聚合当前系统指标。"""

        profiles = self._load_profiles()
        materials = MaterialService().list_materials()
        scores = self._collect_scores(profiles)
        events = self.load_events()
        elapsed_values = [
            float(event["elapsed_ms"])
            for event in events
            if isinstance(event.get("elapsed_ms"), (int, float))
        ]

        intent_distribution: dict[str, int] = {}
        for event in events:
            intent = str(event.get("intent") or "unknown")
            intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

        return EvaluationSummary(
            student_count=len(profiles),
            material_count=len(materials),
            indexed_material_count=sum(1 for item in materials if item.indexed),
            exercise_set_count=len(list(self.exercise_dir.glob("*.json"))) if self.exercise_dir.exists() else 0,
            plan_count=len(list(self.plan_dir.glob("*.json"))) if self.plan_dir.exists() else 0,
            memory_count=sum(len(profile.memories) for profile in profiles),
            grading_count=sum(
                1
                for profile in profiles
                for memory in profile.memories
                if memory.metadata.get("type") == "grading"
            ),
            average_score=round(sum(scores) / len(scores), 2) if scores else None,
            weak_point_count=len({point for profile in profiles for point in profile.weak_points}),
            event_count=len(events),
            average_response_ms=round(sum(elapsed_values) / len(elapsed_values), 2) if elapsed_values else None,
            intent_distribution=intent_distribution,
        )

    def load_events(self) -> list[dict[str, Any]]:
        """读取调用日志。"""

        if not self.log_path.exists():
            return []

        events = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events

    def export_json(self) -> dict[str, Any]:
        """导出论文实验可用 JSON。"""

        return {
            "summary": self.build_summary().to_dict(),
            "events": self.load_events(),
        }

    def export_csv(self) -> str:
        """导出调用日志 CSV 文本。"""

        output = StringIO()
        fieldnames = ["created_at", "student_id", "intent", "success", "elapsed_ms", "next_actions"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for event in self.load_events():
            writer.writerow(
                {
                    "created_at": event.get("created_at", ""),
                    "student_id": event.get("student_id", ""),
                    "intent": event.get("intent", ""),
                    "success": event.get("success", ""),
                    "elapsed_ms": event.get("elapsed_ms", ""),
                    "next_actions": " | ".join(event.get("next_actions", []))
                    if isinstance(event.get("next_actions"), list)
                    else "",
                }
            )
        return output.getvalue()

    def _load_profiles(self) -> list[StudentProfile]:
        service = MemoryService(profile_dir=self.profile_dir)
        profiles = []
        if not self.profile_dir.exists():
            return profiles
        for path in sorted(self.profile_dir.glob("*.json")):
            profiles.append(service.load_profile(path.stem))
        return profiles

    @staticmethod
    def _collect_scores(profiles: list[StudentProfile]) -> list[float]:
        scores = []
        for profile in profiles:
            for memory in profile.memories:
                score = memory.metadata.get("score")
                if isinstance(score, (int, float)):
                    scores.append(float(score))
        return scores
