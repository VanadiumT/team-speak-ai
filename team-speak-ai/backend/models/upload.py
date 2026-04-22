from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4


class UploadBatch(BaseModel):
    """上传批次 - 同一批次的文件共享 batch_id"""
    batch_id: UUID = uuid4()
    function_id: str  # 功能标识 (如 "arena_championship")
    created_at: datetime = datetime.now()
    files: List["UploadFile"] = []


class UploadFile(BaseModel):
    """单个上传文件"""
    file_id: UUID = uuid4()
    batch_id: UUID  # 关联批次
    function_id: str  # 所属功能
    filename: str  # 原始文件名
    content_type: str  # MIME 类型
    size: int  # 文件大小
    path: str  # 存储路径
    uploaded_at: datetime = datetime.now()
    metadata: dict = {}  # 额外元数据


class UploadRequest(BaseModel):
    """上传请求"""
    function_id: str  # 必须指定功能
    batch_id: Optional[UUID] = None  # 可指定批次，不指定则创建新批次
    metadata: dict = {}  # 可选元数据


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    file_id: str
    batch_id: str
    filename: str
    url: str  # 访问 URL
