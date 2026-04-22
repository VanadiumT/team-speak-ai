from pathlib import Path
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
import json
import aiofiles

from config import settings


class FileStorage:
    """文件存储服务"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self.base_dir / "metadata.json"
        self._init_metadata()

    def _init_metadata(self):
        if not self._metadata_file.exists():
            with open(self._metadata_file, "w") as f:
                json.dump({}, f)

    def _load_metadata(self) -> dict:
        with open(self._metadata_file, "r") as f:
            return json.load(f)

    def _save_metadata(self, data: dict):
        with open(self._metadata_file, "w") as f:
            json.dump(data, f, default=str)

    async def save(
        self,
        content: bytes,
        function_id: str,
        filename: str,
        batch_id: str = None,
        content_type: str = "application/octet-stream",
        metadata: dict = None,
    ) -> dict:
        """保存文件"""
        file_id = str(uuid4())
        batch_id = batch_id or str(uuid4())

        dir_path = self.base_dir / function_id / batch_id
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / file_id

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        file_info = {
            "file_id": file_id,
            "batch_id": batch_id,
            "function_id": function_id,
            "filename": filename,
            "content_type": content_type,
            "size": len(content),
            "path": str(file_path),
            "uploaded_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        metadata = self._load_metadata()
        metadata[file_id] = file_info
        self._save_metadata(metadata)

        return {
            **file_info,
            "url": f"/api/files/{file_id}/content",
        }

    async def get(self, file_id: str) -> Optional[dict]:
        """读取文件信息"""
        metadata = self._load_metadata()
        return metadata.get(file_id)

    async def get_content(self, file_id: str) -> bytes:
        """读取文件内容"""
        file_info = await self.get(file_id)
        if not file_info:
            return None

        file_path = Path(file_info["path"])
        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete(self, file_id: str) -> bool:
        """删除文件"""
        metadata = self._load_metadata()
        if file_id not in metadata:
            return False

        file_info = metadata[file_id]
        file_path = Path(file_info["path"])

        if file_path.exists():
            file_path.unlink()

        del metadata[file_id]
        self._save_metadata(metadata)
        return True

    async def delete_batch(self, batch_id: str) -> bool:
        """删除整个批次"""
        metadata = self._load_metadata()
        to_delete = [
            file_id for file_id, info in metadata.items() if info["batch_id"] == batch_id
        ]

        for file_id in to_delete:
            file_path = Path(metadata[file_id]["path"])
            if file_path.exists():
                file_path.unlink()
            del metadata[file_id]

        self._save_metadata(metadata)
        return True

    async def list(self, function_id: str = None, batch_id: str = None) -> List[dict]:
        """列出文件"""
        metadata = self._load_metadata()
        files = list(metadata.values())

        if function_id:
            files = [f for f in files if f["function_id"] == function_id]
        if batch_id:
            files = [f for f in files if f["batch_id"] == batch_id]

        return files

    async def delete_all(self) -> dict:
        """删除所有上传文件"""
        metadata = self._load_metadata()
        deleted_count = 0
        deleted_files = []

        for file_id, file_info in metadata.items():
            file_path = Path(file_info["path"])
            if file_path.exists():
                file_path.unlink()
            deleted_files.append(file_id)
            deleted_count += 1

        # 清理空目录
        for function_dir in self.base_dir.iterdir():
            if function_dir.is_dir():
                for batch_dir in function_dir.iterdir():
                    if batch_dir.is_dir() and not any(batch_dir.iterdir()):
                        batch_dir.rmdir()
                if not any(function_dir.iterdir()):
                    function_dir.rmdir()

        self._save_metadata({})
        return {"deleted_count": deleted_count, "deleted_files": deleted_files}


file_storage = FileStorage()
