"""课程资料管理服务。

V1.0 资料管理仍然落在本地文件系统：

    backend/data/course_materials

上传后的 Markdown/TXT/PDF 会保存到该目录。当前 RAG 服务会在创建时重新读取
Markdown 资料；PDF 先作为可管理资料保存，后续可以接入 file_parser_tool 做解析。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from app.core.config import get_settings
from app.services.rag_service import RagService


SUPPORTED_MATERIAL_SUFFIXES = {".md", ".markdown", ".txt", ".pdf"}


@dataclass
class MaterialInfo:
    """前端资料列表展示所需信息。"""

    file_name: str
    relative_path: str
    suffix: str
    size_bytes: int
    course_name: Optional[str] = None
    indexed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class MaterialService:
    """管理课程资料文件和本地 RAG 索引状态。"""

    def __init__(self, materials_dir: Optional[str | Path] = None) -> None:
        settings = get_settings()
        self.materials_dir = Path(materials_dir) if materials_dir else settings.course_materials_path
        self.materials_dir.mkdir(parents=True, exist_ok=True)

    def list_materials(self) -> list[MaterialInfo]:
        """列出已上传/内置课程资料。"""

        items = []
        for path in self._iter_material_paths():
            items.append(
                MaterialInfo(
                    file_name=path.name,
                    relative_path=self._relative_path(path),
                    suffix=path.suffix.lower(),
                    size_bytes=path.stat().st_size,
                    course_name=self._infer_course_name(path),
                    indexed=path.suffix.lower() in {".md", ".markdown", ".txt", ".pdf"},
                )
            )
        return items

    def save_upload(self, file_name: str, content: bytes, course_name: str | None = None) -> MaterialInfo:
        """保存前端上传的资料文件。"""

        suffix = Path(file_name).suffix.lower()
        if suffix not in SUPPORTED_MATERIAL_SUFFIXES:
            raise ValueError("仅支持 .md、.markdown、.txt、.pdf 课程资料。")

        safe_name = self._safe_file_name(file_name)
        if course_name and course_name.strip():
            course_dir = self.materials_dir / self._safe_file_name(course_name.strip())
            course_dir.mkdir(parents=True, exist_ok=True)
            path = course_dir / safe_name
        else:
            path = self.materials_dir / safe_name

        path.write_bytes(content)
        return MaterialInfo(
            file_name=path.name,
            relative_path=self._relative_path(path),
            suffix=path.suffix.lower(),
            size_bytes=path.stat().st_size,
            course_name=course_name.strip() if course_name and course_name.strip() else self._infer_course_name(path),
            indexed=path.suffix.lower() in {".md", ".markdown", ".txt", ".pdf"},
        )

    def get_index_status(self, course_name: str | None = None) -> dict:
        """返回当前本地 RAG 可检索资料状态。"""

        rag = RagService()
        chunks = rag._filter_chunks_by_course(course_name)
        return {
            "course_name": course_name,
            "document_count": len(rag.documents),
            "chunk_count": len(chunks),
            "retrieval_mode": "local_keyword_rag",
            "indexed_suffixes": [".md", ".markdown", ".txt", ".pdf"],
        }

    def _iter_material_paths(self) -> Iterable[Path]:
        return sorted(
            path
            for path in self.materials_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_MATERIAL_SUFFIXES
        )

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.materials_dir))
        except ValueError:
            return str(path)

    def _infer_course_name(self, path: Path) -> Optional[str]:
        try:
            relative = path.relative_to(self.materials_dir)
        except ValueError:
            return None
        if len(relative.parts) > 1:
            return relative.parts[0]
        return None

    @staticmethod
    def _safe_file_name(value: str) -> str:
        name = Path(value).name.strip()
        stem = Path(name).stem
        suffix = Path(name).suffix
        safe_stem = re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]+", "_", stem).strip("._")
        return f"{safe_stem or 'material'}{suffix.lower()}"
