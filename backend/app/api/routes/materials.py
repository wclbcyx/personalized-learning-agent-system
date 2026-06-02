"""课程资料管理 API。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.material_service import MaterialService


router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("")
def list_materials() -> Dict[str, Any]:
    """列出课程资料。"""

    service = MaterialService()
    return {
        "materials": [item.to_dict() for item in service.list_materials()],
        "index_status": service.get_index_status(),
    }


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    course_name: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    """上传课程资料并保存到本地知识库目录。"""

    try:
        content = await file.read()
        item = MaterialService().save_upload(
            file_name=file.filename or "material.md",
            content=content,
            course_name=course_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"上传资料失败：{exc}") from exc

    return {
        "material": item.to_dict(),
        "message": "资料已保存；Markdown 资料会在下一次 RAG 检索时自动进入本地索引。",
    }


@router.get("/index-status")
def index_status(course_name: Optional[str] = None) -> Dict[str, Any]:
    """查看本地 RAG 索引状态。"""

    return MaterialService().get_index_status(course_name=course_name)
