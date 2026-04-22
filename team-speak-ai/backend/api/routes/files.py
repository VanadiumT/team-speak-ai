from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from models.upload import UploadResponse
from services.file_storage import file_storage

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    function_id: str = Form(...),
    batch_id: Optional[str] = Form(None),
    metadata: str = Form("{}"),
):
    """
    上传文件

    请求参数:
    - file: 文件内容
    - function_id: 功能标识 (必填)
    - batch_id: 批次ID (可选，不填则自动生成)
    - metadata: 额外元数据 JSON
    """
    import json

    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}

    content = await file.read()
    result = await file_storage.save(
        content=content,
        function_id=function_id,
        filename=file.filename,
        batch_id=batch_id,
        content_type=file.content_type,
        metadata=meta,
    )

    return UploadResponse(
        success=True,
        file_id=result["file_id"],
        batch_id=result["batch_id"],
        filename=result["filename"],
        url=result["url"],
    )


@router.post("/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    function_id: str = Form(...),
    metadata: str = Form("{}"),
):
    """
    批量上传

    同一批次的文件会共享:
    - batch_id: 相同
    - uploaded_at: 相同
    - function_id: 相同
    """
    import json

    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}

    results = []
    batch_id = str(uuid4())

    for file in files:
        content = await file.read()
        result = await file_storage.save(
            content=content,
            function_id=function_id,
            filename=file.filename,
            batch_id=batch_id,
            content_type=file.content_type,
            metadata=meta,
        )
        results.append(result)

    return {"success": True, "batch_id": batch_id, "files": results}


@router.get("/batch/{batch_id}")
async def get_batch(batch_id: str):
    """获取批次信息及所有文件"""
    result = await file_storage.list(function_id=None, batch_id=batch_id)
    return result


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    """获取文件信息"""
    result = await file_storage.get(file_id)
    if not result:
        raise HTTPException(status_code=404, detail="File not found")
    return result


@router.get("/files/{file_id}/content")
async def get_file_content(file_id: str):
    """获取文件内容"""
    result = await file_storage.get(file_id)
    if not result:
        raise HTTPException(status_code=404, detail="File not found")
    return result


@router.delete("/batch/{batch_id}")
async def delete_batch(batch_id: str):
    """删除整个批次"""
    success = await file_storage.delete_batch(batch_id)
    return {"success": success}


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """删除单个文件"""
    success = await file_storage.delete(file_id)
    return {"success": success}


@router.delete("/all")
async def delete_all_files():
    """删除所有上传文件"""
    result = await file_storage.delete_all()
    return {"success": True, **result}
