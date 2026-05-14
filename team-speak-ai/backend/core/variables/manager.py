"""
SysVarManager — 系统变量管理

全局跨流程的持久化变量存储。数据保存在 data/system_vars.json。
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SysVarManager:
    """系统变量管理器"""

    def __init__(self, data_dir: str):
        self._file = Path(data_dir) / "system_vars.json"
        self._data: dict = {}
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load {self._file}, resetting to empty: {e}")
                self._data = {}

    def _save(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._file)
        except Exception as e:
            logger.error(f"Failed to save system_vars.json: {e}")
            # 清理临时文件
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value, merge_mode: str = "overwrite"):
        if merge_mode == "append":
            existing = self._data.get(key, [])
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(value)
            self._data[key] = existing
        else:
            self._data[key] = value
        self._save()

    def delete(self, key: str):
        self._data.pop(key, None)
        self._save()

    def list_all(self) -> dict:
        return dict(self._data)
