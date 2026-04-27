import json
import os
import glob
from datetime import datetime, date
from threading import Lock
from typing import Optional

from core.logger.base import BaseLogger, LogEntry, PipelineEvent


class FileLogger(BaseLogger):
    """JSON Lines 文件日志，按日轮转"""

    def __init__(self, log_dir: str = "logs", keep_days: int = 30):
        self._log_dir = log_dir
        self._keep_days = keep_days
        self._lock = Lock()
        self._current_date: Optional[date] = None
        self._file_handle: Optional[object] = None
        os.makedirs(log_dir, exist_ok=True)
        self._cleanup_old_logs()

    def _log_path(self, dt: date) -> str:
        return os.path.join(self._log_dir, f"app-{dt.isoformat()}.jsonl")

    def _rotate(self, dt: date) -> None:
        if self._current_date == dt and self._file_handle and not self._file_handle.closed:
            return
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()
        self._current_date = dt
        self._file_handle = open(self._log_path(dt), "a", encoding="utf-8")

    def _cleanup_old_logs(self) -> None:
        cutoff = date.today()
        for fpath in glob.glob(os.path.join(self._log_dir, "app-*.jsonl")):
            try:
                basename = os.path.basename(fpath)
                file_date = date.fromisoformat(basename[4:-6])
                if (cutoff - file_date).days > self._keep_days:
                    os.remove(fpath)
            except (ValueError, OSError):
                pass

    def log(self, entry: LogEntry) -> None:
        dt = entry.timestamp.date()
        payload = {
            "type": "log",
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.value,
            "module": entry.module_name,
            "message": entry.message,
            **(entry.extra if entry.extra else {}),
        }
        with self._lock:
            try:
                self._rotate(dt)
                self._file_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self._file_handle.flush()
            except Exception:
                pass

    def log_event(self, event: PipelineEvent) -> None:
        dt = event.timestamp.date()
        payload = {
            "type": "pipeline_event",
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "pipeline_id": event.pipeline_id,
            "execution_id": event.execution_id,
            "node_id": event.node_id,
            "data": event.data,
        }
        with self._lock:
            try:
                self._rotate(dt)
                self._file_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self._file_handle.flush()
            except Exception:
                pass

    def close(self) -> None:
        with self._lock:
            if self._file_handle and not self._file_handle.closed:
                self._file_handle.close()
                self._file_handle = None
