"""
SysVarManager — 系统变量管理

全局跨流程的持久化变量存储。数据保存在 data/system_vars.json。
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_manager: Optional["SysVarManager"] = None


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
            except Exception:
                self._data = {}

    def _save(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._file)

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


def init_sys_var_manager(data_dir: str) -> SysVarManager:
    global _manager
    _manager = SysVarManager(data_dir)
    logger.info(f"SysVarManager initialized: {len(_manager.list_all())} variables")
    return _manager


def get_sys_var_manager() -> SysVarManager:
    if _manager is None:
        raise RuntimeError("SysVarManager not initialized")
    return _manager
