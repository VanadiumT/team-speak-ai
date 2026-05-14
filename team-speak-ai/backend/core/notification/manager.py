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

RETENTION_DAYS = 7
MAX_ITEMS_PER_PAGE = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationManager:
    """通知管理器：持久化存储 + 分页查询 + 已读状态"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self._notifications_dir = Path(data_dir) / "notifications"
        else:
            self._notifications_dir = Path(__file__).resolve().parent.parent.parent / "data" / "notifications"
        self._read_state_file = self._notifications_dir / "read_state.json"
        self._unread_counts: dict[str, int] = {}
        self._read_ids: dict[str, set] = {}
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        self._initialized = True
        self._notifications_dir.mkdir(parents=True, exist_ok=True)
        self._load_read_state()
        self._cleanup_old()
        self._rebuild_unread_counts()

    def _load_read_state(self):
        if not self._read_state_file.exists():
            return
        try:
            with open(self._read_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for flow_id, ids in data.items():
                self._read_ids[flow_id] = set(ids)
        except Exception as e:
            logger.warning(f"Failed to load read state: {e}")

    def _save_read_state(self):
        try:
            data = {fid: list(ids) for fid, ids in self._read_ids.items()}
            with open(self._read_state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save read state: {e}")

    def _flow_file(self, flow_id: str) -> Path:
        safe_id = flow_id.replace("/", "_").replace("\\", "_")
        return self._notifications_dir / f"{safe_id}.jsonl"

    def _rebuild_unread_counts(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        for jsonl_file in self._notifications_dir.glob("*.jsonl"):
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
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        for jsonl_file in self._notifications_dir.glob("*.jsonl"):
            try:
                lines = []
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        item = json.loads(line)
                        ts = datetime.fromisoformat(item["timestamp"])
                        if ts >= cutoff:
                            lines.append(line)
                with open(jsonl_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n" if lines else "")
            except Exception as e:
                logger.warning(f"Failed to cleanup notifications for {jsonl_file.stem}: {e}")

    def save(self, flow_id: str, title: str, content: str,
             event_type: str = "info", node_id: Optional[str] = None) -> dict:
        self._ensure_init()
        item = {
            "id": str(uuid.uuid4()),
            "flow_id": flow_id,
            "title": title,
            "content": content,
            "event_type": event_type,
            "node_id": node_id,
            "timestamp": _now_iso(),
        }
        filepath = self._flow_file(flow_id)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._unread_counts[flow_id] = self._unread_counts.get(flow_id, 0) + 1
        return item

    def list_notifications(self, flow_id: str, limit: int = 20,
                           before: Optional[str] = None) -> dict:
        self._ensure_init()
        filepath = self._flow_file(flow_id)
        items = []
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        items.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Failed to read notifications for {flow_id}: {e}")

        items.reverse()
        if before:
            idx = next((i for i, it in enumerate(items) if it["id"] == before), len(items))
            items = items[idx:]
        items = items[:limit]
        read_set = self._read_ids.get(flow_id, set())
        for item in items:
            item["read"] = item["id"] in read_set
        has_more = len(items) == limit
        return {
            "items": items,
            "unread": self._unread_counts.get(flow_id, 0),
            "has_more": has_more,
        }

    def mark_read(self, flow_id: str, notification_id: Optional[str] = None) -> int:
        self._ensure_init()
        if flow_id not in self._read_ids:
            self._read_ids[flow_id] = set()
        if notification_id:
            self._read_ids[flow_id].add(notification_id)
            self._unread_counts[flow_id] = max(0, self._unread_counts.get(flow_id, 0) - 1)
        else:
            filepath = self._flow_file(flow_id)
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
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
