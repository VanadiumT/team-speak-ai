"""
ChunkReceiver —— 分块文件接收器

通过 WebSocket binary frame 接收文件分块，支持断点续传。
"""

import os
import struct
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CHUNK_SIZE = 256 * 1024       # 256 KB
UPLOAD_TIMEOUT_SEC = 60       # 60 秒无数据自动清理
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


class UploadSession:
    """单个上传会话"""
    def __init__(self, upload_id: str, msg_id: str, name: str, size: int,
                 mime_type: str, node_id: Optional[str], filepath: Path):
        self.upload_id = upload_id
        self.msg_id = msg_id
        self.name = name
        self.size = size
        self.mime_type = mime_type
        self.node_id = node_id
        self.filepath = filepath
        self.received = 0
        self.last_chunk_time = datetime.now(timezone.utc)
        self.fh = None


class ChunkReceiver:
    """分块文件接收管理器"""

    def __init__(self, upload_dir: str, max_file_size: int = MAX_FILE_SIZE):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self._sessions: dict[str, UploadSession] = {}
        self._msg_to_upload: dict[str, str] = {}  # msg_id → upload_id

    # ── 上传生命周期 ──────────────────────────────────────────

    def start_upload(self, msg_id: str, name: str, size: int,
                     mime_type: str, node_id: Optional[str] = None,
                     received: int = 0) -> dict:
        """发起上传请求，返回 {upload_id}"""
        if size > self.max_file_size:
            raise ValueError(f"File too large: {size} > {self.max_file_size}")

        upload_id = f"upl_{uuid.uuid4().hex[:12]}"
        session_dir = self.upload_dir / upload_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # 安全文件名
        safe_name = self._safe_filename(name)
        filepath = session_dir / safe_name

        session = UploadSession(
            upload_id=upload_id, msg_id=msg_id,
            name=name, size=size, mime_type=mime_type,
            node_id=node_id, filepath=filepath,
        )

        # 打开文件（追加模式，支持断点续传）
        mode = "ab" if received > 0 else "wb"
        session.fh = open(filepath, mode)
        if received > 0:
            session.received = received
            session.fh.seek(received)

        self._sessions[upload_id] = session
        self._msg_to_upload[msg_id] = upload_id
        logger.info(f"Upload started: {upload_id} ({name}, {size} bytes)")
        return {"upload_id": upload_id}

    def receive_chunk(self, msg_id: str, data: bytes) -> int:
        """接收一个数据分块，返回已接收字节数"""
        upload_id = self._msg_to_upload.get(msg_id)
        if not upload_id:
            raise ValueError(f"No upload session for msg_id: {msg_id}")

        session = self._sessions[upload_id]
        session.fh.write(data)
        session.received += len(data)
        session.last_chunk_time = datetime.now(timezone.utc)

        if session.received > session.size:
            session.received = session.size  # 防止溢出

        return session.received

    def complete_upload(self, msg_id: str) -> dict:
        """完成上传，校验并返回 {upload_id, file_id, name, size, mime_type}"""
        upload_id = self._msg_to_upload.get(msg_id)
        if not upload_id:
            raise ValueError(f"No upload session for msg_id: {msg_id}")

        session = self._sessions[upload_id]
        session.fh.close()
        session.fh = None

        # 校验文件完整性
        actual_size = os.path.getsize(session.filepath)
        if actual_size != session.size:
            # 允许关闭，但标记警告
            logger.warning(f"Upload size mismatch: expected {session.size}, got {actual_size}")

        # 保存元数据
        metadata_path = self.upload_dir / upload_id / "metadata.json"
        import json
        metadata = {
            "upload_id": upload_id,
            "file_id": f"file_{uuid.uuid4().hex[:12]}",
            "name": session.name,
            "size": actual_size,
            "mime_type": session.mime_type,
            "node_id": session.node_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        self._cleanup_session(upload_id)
        logger.info(f"Upload complete: {upload_id} → {metadata['file_id']}")
        return metadata

    def cancel_upload(self, upload_id: str) -> None:
        """取消上传，删除临时文件"""
        if upload_id in self._sessions:
            session = self._sessions[upload_id]
            if session.fh:
                session.fh.close()
            self._cleanup_session(upload_id)
            logger.info(f"Upload cancelled: {upload_id}")

    def get_session(self, upload_id: str) -> Optional[UploadSession]:
        return self._sessions.get(upload_id)

    def get_session_by_msg_id(self, msg_id: str) -> Optional[UploadSession]:
        upload_id = self._msg_to_upload.get(msg_id)
        if upload_id:
            return self._sessions.get(upload_id)
        return None

    async def cleanup_timeouts(self) -> None:
        """后台任务：清理超时的上传会话"""
        while True:
            await asyncio.sleep(30)
            now = datetime.now(timezone.utc)
            to_remove = []
            for uid, session in self._sessions.items():
                elapsed = (now - session.last_chunk_time).total_seconds()
                if elapsed > UPLOAD_TIMEOUT_SEC:
                    to_remove.append(uid)

            for uid in to_remove:
                logger.info(f"Cleaning up timed-out upload: {uid}")
                self.cancel_upload(uid)

    # ── 二进制帧解析（静态方法） ───────────────────────────────

    @staticmethod
    def parse_binary_frame(data: bytes) -> tuple[str, bytes]:
        """解析 binary frame: 返回 (msg_id, file_chunk)"""
        if len(data) < 4:
            raise ValueError("Binary frame too short (missing header)")
        header_len = struct.unpack(">I", data[:4])[0]
        if len(data) < 4 + header_len:
            raise ValueError("Binary frame truncated")
        msg_id = data[4:4 + header_len].decode("utf-8")
        file_chunk = data[4 + header_len:]
        return msg_id, file_chunk

    # ── 内部方法 ───────────────────────────────────────────────

    def _cleanup_session(self, upload_id: str) -> None:
        session = self._sessions.pop(upload_id, None)
        if session:
            self._msg_to_upload.pop(session.msg_id, None)

    @staticmethod
    def _safe_filename(name: str) -> str:
        """生成安全的文件名"""
        name = os.path.basename(name)
        # 替换危险字符
        safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
        return safe or "uploaded_file"


# 全局单例
_chunk_receiver: Optional[ChunkReceiver] = None


def get_chunk_receiver() -> ChunkReceiver:
    global _chunk_receiver
    if _chunk_receiver is None:
        raise RuntimeError("ChunkReceiver not initialized")
    return _chunk_receiver


def init_chunk_receiver(upload_dir: str, max_file_size: int = MAX_FILE_SIZE) -> ChunkReceiver:
    global _chunk_receiver
    _chunk_receiver = ChunkReceiver(upload_dir, max_file_size)
    return _chunk_receiver
