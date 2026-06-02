"""课程资料读取服务。

这个文件负责把磁盘上的课程资料读取成统一的 ``CourseDocument`` 对象。

V1.0 支持 Markdown、TXT 和 PDF。Markdown/TXT 会直接读取文本，PDF 会在安装
pypdf 后抽取页面文字。

当前职责：
    backend/data/course_materials/*.md
    -> CourseDocument 列表

暂时不做：
    - PDF 解析
    - Word 解析
    - 网页抓取
    - 向量化

这些能力后续可以继续扩展到 file_parser_tool 或 RAG 服务里。
"""

from pathlib import Path
from typing import Iterable, List, Optional

from app.core.config import get_settings
from app.models.schemas import CourseDocument


SUPPORTED_MATERIAL_SUFFIXES = {".md", ".markdown", ".txt", ".pdf"}


class MaterialIngestionService:
    """课程资料读取服务。

    你可以把它理解成 RAG 的第一步：先把资料从文件系统读进来。
    读取进来以后，后续的 ``rag_service.py`` 才能做切分和检索。
    """

    def __init__(self, materials_dir: Optional[str | Path] = None) -> None:
        """初始化资料读取服务。

        Args:
            materials_dir:
                课程资料目录。如果不传，就从 config.py 读取
                settings.course_materials_path。
        """

        settings = get_settings()
        self.materials_dir = Path(materials_dir) if materials_dir else settings.course_materials_path

    def load_markdown_files(self) -> List[CourseDocument]:
        """读取资料目录下所有可检索文本资料。

        Returns:
            CourseDocument 列表。

        说明：
            - 会递归读取子目录。
            - 会忽略空文件。
            - 会按照路径排序，保证每次读取顺序稳定。
        """

        if not self.materials_dir.exists():
            return []

        documents: List[CourseDocument] = []

        for file_path in self._iter_material_paths(self.materials_dir):
            content = self._read_document_file(file_path)
            if not content.strip():
                continue

            document = CourseDocument(
                title=self._extract_title(content, file_path),
                source_path=str(file_path),
                content=content,
                metadata={
                    "file_name": file_path.name,
                    "file_suffix": file_path.suffix,
                    "relative_path": self._relative_path(file_path),
                },
            )
            documents.append(document)

        return documents

    def _iter_material_paths(self, root_dir: Path) -> Iterable[Path]:
        """递归遍历可检索资料文件路径。

        单独抽成方法，是为了让“哪些文件算课程资料”这个规则更清晰。
        """

        return sorted(
            path
            for path in root_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_MATERIAL_SUFFIXES
        )

    @staticmethod
    def _read_document_file(file_path: Path) -> str:
        """读取资料文本内容。

        文本文件默认使用 utf-8。PDF 依赖 pypdf；如果未安装，会返回空字符串，
        避免资料列表可上传但 RAG 构建直接崩溃。
        """

        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except Exception:
                return ""

            reader = PdfReader(str(file_path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

        return file_path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_title(content: str, file_path: Path) -> str:
        """从 Markdown 内容中提取标题。

        优先使用第一个一级标题：
            # 第一章 Agent 基础

        如果没有一级标题，就退回使用文件名。
        """

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.lstrip("#").strip()
                if title:
                    return title

        return file_path.stem

    def _relative_path(self, file_path: Path) -> str:
        """返回相对资料目录的路径，方便前端展示和日志调试。"""

        try:
            return str(file_path.relative_to(self.materials_dir))
        except ValueError:
            return str(file_path)


def load_markdown_files(materials_dir: Optional[str | Path] = None) -> List[CourseDocument]:
    """便捷函数：读取 Markdown 课程资料。

    如果只是想快速使用，不想手动创建 service，可以直接调用：

        documents = load_markdown_files()
    """

    service = MaterialIngestionService(materials_dir=materials_dir)
    return service.load_markdown_files()
