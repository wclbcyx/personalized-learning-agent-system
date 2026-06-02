"""练习题存储服务。

这个服务负责保存和读取 ExerciseAgent 生成的完整题目。

为什么需要它：
    前端展示题目时不应该看到 reference_answer 和 rubric。
    但后端批改时必须能拿到 reference_answer 和 rubric。

所以流程是：

    生成练习题
    -> 后端保存完整题目到 JSON
    -> 前端只拿隐藏答案后的题目
    -> 学生提交答案
    -> 后端根据 exercise_set_id + exercise_id 读取完整题目
    -> GradingAgent 批改

保存位置：
    backend/data/submissions/exercise_sets/{exercise_set_id}.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from app.core.config import BACKEND_DIR
from app.models.exercise import ExerciseGenerationResponse, ExerciseItem


DEFAULT_EXERCISE_SET_DIR = BACKEND_DIR / "data" / "submissions" / "exercise_sets"


class ExerciseStoreService:
    """练习题本地 JSON 存储服务。"""

    def __init__(self, store_dir: Optional[str | Path] = None) -> None:
        """初始化练习题存储目录。"""

        self.store_dir = Path(store_dir) if store_dir else DEFAULT_EXERCISE_SET_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save_exercise_set(self, response: ExerciseGenerationResponse) -> Path:
        """保存完整练习题批次。

        注意：
            这里会保存 reference_answer 和 rubric。
            因此这个 JSON 文件只给后端使用，不应该直接暴露给前端。
        """

        path = self._exercise_set_path(response.exercise_set_id)
        path.write_text(
            json.dumps(response.to_dict(include_answer=True), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load_exercise_set(self, exercise_set_id: str) -> ExerciseGenerationResponse:
        """读取一个完整练习题批次。"""

        path = self._exercise_set_path(exercise_set_id)
        if not path.exists():
            raise FileNotFoundError(f"练习批次不存在：{exercise_set_id}")

        data = json.loads(path.read_text(encoding="utf-8"))
        exercises = [
            ExerciseItem.from_dict(item)
            for item in data.get("exercises", [])
            if isinstance(item, dict)
        ]

        return ExerciseGenerationResponse(
            exercise_set_id=str(data.get("exercise_set_id") or exercise_set_id),
            student_id=str(data.get("student_id", "")),
            exercises=exercises,
            summary=data.get("summary"),
            debug=dict(data.get("debug", {})),
        )

    def get_exercise(self, exercise_set_id: str, exercise_id: str) -> ExerciseItem:
        """读取某一批次中的某一道题。"""

        exercise_set = self.load_exercise_set(exercise_set_id)
        for exercise in exercise_set.exercises:
            if exercise.exercise_id == exercise_id:
                return exercise

        raise KeyError(f"题目不存在：exercise_set_id={exercise_set_id}, exercise_id={exercise_id}")

    def _exercise_set_path(self, exercise_set_id: str) -> Path:
        """返回练习批次文件路径。"""

        safe_id = self._safe_id(exercise_set_id)
        return self.store_dir / f"{safe_id}.json"

    @staticmethod
    def _safe_id(value: str) -> str:
        """把 ID 转成安全文件名。"""

        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
        return cleaned or "unknown_exercise_set"
