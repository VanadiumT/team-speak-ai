"""
NotificationManager — 通知持久化与查询

JSONL 存储，按 flow_id 分文件，支持分页查询和已读标记。
自动清理 7 天前的记录。
"""

import json
import uuid
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

NOTIFICATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "notifications"
READ_STATE_FILE = NOTIFICATIONS_DIR / "read_state.json"
RETENTION_DAYS = 7
MAX_ITEMS_PER_PAGE = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationManager:
    """通知管理器：持久化存储 + 分页查询 + 已读状态"""

    def __init__(self):
        self._unread_counts: dict[str, int] = {}  # flow_id → unread count
        self._read_ids: dict[str, set] = {}  # flow_id → set of read notification ids
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        self._initialized = True
        NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_read_state()
        self._cleanup_old()
        self._rebuild_unread_counts()

    def _load_read_state(self):
        """加载已读状态"""
        if not READ_STATE_FILE.exists():
            return
        try:
            with open(READ_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for flow_id, ids in data.items():
                self._read_ids[flow_id] = set(ids)
        except Exception as e:
            logger.warning(f"Failed to load read state: {e}")

    def _save_read_state(self):
        """持久化已读状态"""
        try:
            data = {fid: list(ids) for fid, ids in self._read_ids.items()}
            with open(READ_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save read state: {e}")

    def _flow_file(self, flow_id: str) -> Path:
        safe_id = flow_id.replace("/", "_").replace("\\", "_")
        return NOTIFICATIONS_DIR / f"{safe_id}.jsonl"

    def _rebuild_unread_counts(self):
        """启动时重建未读计数"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        for jsonl_file in NOTIFICATIONS_DIR.glob("*.jsonl"):
            flow_id = jsonl_file.stem
            read_set = self._read_ids.get(flow_id, set())
            count = 0
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        item = json.loads(line)
                        ts = datetime.fromisoformat(item["timestamp"])
                        if ts < cutoff:
                            continue
                        if item["id"] not in read_set:
                            count += 1
            except Exception:
                pass
            self._unread_counts[flow_id] = count

    def _cleanup_old(self):
        """清理超过 RETENTION_DAYS 天的通知"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        for jsonl_file in NOTIFICATIONS_DIR.glob("*.jsonl"):
            try:
                lines = []
                changed = False
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        item = json.loads(line)
                        ts = datetime.fromisoformat(item["timestamp"])
                        if ts >= cutoff:
                            lines.append(line)
                        else:
                            changed = True
                if changed:
                    with open(jsonl_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines) + "\n" if lines else "")
            except Exception as e:
                logger.warning(f"Cleanup error for {jsonl_file}: {e}")

    def save(self, flow_id: str, title: str, content: str, level: str = "info",
             node_id: str = None) -> dict:
        """保存一条通知，返回通知对象"""
        self._ensure_init()
        notification_id = str(uuid.uuid4())
        item = {
            "id": notification_id,
            "title": title,
            "content": content,
            "level": level,
            "node_id": node_id,
            "timestamp": _now_iso(),
        }

        try:
            with open(self._flow_file(flow_id), "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to save notification: {e}")

        # 更新未读计数
        self._unread_counts[flow_id] = self._unread_counts.get(flow_id, 0) + 1
        return item

    def list_notifications(self, flow_id: str, limit: int = MAX_ITEMS_PER_PAGE,
                           before: str = None) -> dict:
        """
        分页查询通知（倒序，最新的在前）。
        before: 上一页最后一条的 id（cursor 翻页）
        返回 {items: [...], unread: int, has_more: bool}
        """
        self._ensure_init()
        limit = min(limit, 50)

        jsonl_file = self._flow_file(flow_id)
        if not jsonl_file.exists():
            return {"items": [], "unread": self._unread_counts.get(flow_id, 0), "has_more": False}

        # 读取全部有效记录
        all_items = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    ts = datetime.fromisoformat(item["timestamp"])
                    if ts >= cutoff:
                        all_items.append(item)
        except Exception as e:
            logger.warning(f"Failed to read notifications: {e}")
            return {"items": [], "unread": 0, "has_more": False}

        read_set = self._read_ids.get(flow_id, set())

        # 标记已读状态
        for item in all_items:
            item["read"] = item["id"] in read_set

        # 倒序（最新在前）
        all_items.reverse()

        # cursor 分页
        if before:
            start_idx = 0
            for i, item in enumerate(all_items):
                if item["id"] == before:
                    start_idx = i + 1
                    break
            page_items = all_items[start_idx:start_idx + limit]
            has_more = start_idx + limit < len(all_items)
        else:
            page_items = all_items[:limit]
            has_more = len(all_items) > limit

        return {
            "items": page_items,
            "unread": self._unread_counts.get(flow_id, 0),
            "has_more": has_more,
        }

    def mark_read(self, flow_id: str, notification_id: str = None) -> int:
        """
        标记已读。notification_id 为空则标记该 flow 全部已读。
        返回新未读数。
        """
        self._ensure_init()

        if flow_id not in self._read_ids:
            self._read_ids[flow_id] = set()

        if notification_id:
            self._read_ids[flow_id].add(notification_id)
            self._unread_counts[flow_id] = max(0, self._unread_counts.get(flow_id, 0) - 1)
        else:
            # 全部已读：读取所有通知 id
            jsonl_file = self._flow_file(flow_id)
            if jsonl_file.exists():
                try:
                    with open(jsonl_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            item = json.loads(line)
                            self._read_ids[flow_id].add(item["id"])
                except Exception:
                    pass
            self._unread_counts[flow_id] = 0

        self._save_read_state()
        return self._unread_counts.get(flow_id, 0)

    def get_unread_count(self, flow_id: str) -> int:
        self._ensure_init()
        return self._unread_counts.get(flow_id, 0)


# ── 单例 ──────────────────────────────────────────────────────

_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
