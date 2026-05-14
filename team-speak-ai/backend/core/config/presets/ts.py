"""
TeamSpeak Bridge 连接预设管理器，持久化到 data/defaults/ts_presets.json

两层模型:
  Platform = 一个 Java TeamSpeak Bridge 实例 (ws_url + api_key)
  Model    = 该桥接的连接配置 (nickname, auto_reconnect 等)

注意: TeamSpeak 服务器参数 (host/password/channel) 由 Java 项目管理，
      这里的配置只关乎 Python←WS→Java Bridge 之间的连接。
"""

import json
import logging
import uuid as _uuid
from copy import deepcopy as _deepcopy
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_TS_MODEL_CONFIG = {
    "nickname": "TeamSpeakAI",
    "auto_reconnect": True,
    "reconnect_delay": 3.0,
}


class TeamSpeakPresetManager:
    """TS Bridge 连接预设"""

    def __init__(self, data_dir: str):
        self._path = Path(data_dir) / "defaults" / "ts_presets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Failed to load ts_presets.json, creating default")
        return self._create_default()

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _create_default(self) -> dict:
        from config import settings
        data = {
            "platforms": [
                {
                    "id": _uuid.uuid4().hex[:12],
                    "name": "本地桥接",
                    "ws_url": settings.ts_ws_url,
                    "api_key": "",
                    "models": [
                        {
                            **_DEFAULT_TS_MODEL_CONFIG,
                            "id": _uuid.uuid4().hex[:12],
                            "name": "默认配置",
                            "is_default": True,
                        }
                    ],
                }
            ]
        }
        self._data = data
        self._save()
        logger.info(f"Created default TS Bridge preset at {self._path}")
        return data

    def list_all(self) -> dict:
        return _deepcopy(self._data)

    def save_platform(self, platform: dict) -> dict:
        pid = platform.get("id")
        if pid:
            for i, p in enumerate(self._data["platforms"]):
                if p["id"] == pid:
                    for k, v in platform.items():
                        if k != "models":
                            self._data["platforms"][i][k] = v
                    self._save()
                    return self.list_all()
        platform = _deepcopy(platform)
        platform["id"] = _uuid.uuid4().hex[:12]
        platform.setdefault("models", [])
        self._data["platforms"].append(platform)
        self._save()
        return self.list_all()

    def delete_platform(self, platform_id: str) -> dict:
        self._data["platforms"] = [p for p in self._data["platforms"] if p["id"] != platform_id]
        self._save()
        return self.list_all()

    def duplicate_platform(self, platform_id: str) -> dict:
        for p in self._data["platforms"]:
            if p["id"] == platform_id:
                new_p = _deepcopy(p)
                new_p["id"] = _uuid.uuid4().hex[:12]
                new_p["name"] = p["name"] + " (副本)"
                for m in new_p.get("models", []):
                    m["id"] = _uuid.uuid4().hex[:12]
                self._data["platforms"].append(new_p)
                self._save()
                return self.list_all()
        raise ValueError(f"Platform not found: {platform_id}")

    def _find_platform(self, platform_id: str) -> tuple:
        for i, p in enumerate(self._data["platforms"]):
            if p["id"] == platform_id:
                return i, p
        raise ValueError(f"Platform not found: {platform_id}")

    def save_model(self, platform_id: str, model: dict) -> dict:
        idx, platform = self._find_platform(platform_id)
        mid = model.get("id")
        if mid:
            for j, m in enumerate(platform["models"]):
                if m["id"] == mid:
                    platform["models"][j] = _deepcopy(model)
                    self._save()
                    return self.list_all()
        model = _deepcopy(model)
        model["id"] = _uuid.uuid4().hex[:12]
        for key, default in _DEFAULT_TS_MODEL_CONFIG.items():
            model.setdefault(key, default)
        platform.setdefault("models", [])
        platform["models"].append(model)
        self._save()
        return self.list_all()

    def delete_model(self, platform_id: str, model_id: str) -> dict:
        _, platform = self._find_platform(platform_id)
        platform["models"] = [m for m in platform.get("models", []) if m["id"] != model_id]
        self._save()
        return self.list_all()

    def duplicate_model(self, platform_id: str, model_id: str) -> dict:
        _, platform = self._find_platform(platform_id)
        for m in platform.get("models", []):
            if m["id"] == model_id:
                new_m = _deepcopy(m)
                new_m["id"] = _uuid.uuid4().hex[:12]
                new_m["name"] = m["name"] + " (副本)"
                new_m["is_default"] = False
                platform["models"].append(new_m)
                self._save()
                return self.list_all()
        raise ValueError(f"Model not found: {model_id}")

    def get_platform(self, platform_id: str) -> Optional[dict]:
        for p in self._data["platforms"]:
            if p["id"] == platform_id:
                return _deepcopy(p)
        return None

    def get_model(self, platform_id: str, model_id: str) -> Optional[dict]:
        platform = self.get_platform(platform_id)
        if not platform:
            return None
        for m in platform.get("models", []):
            if m["id"] == model_id:
                return _deepcopy(m)
        return None

    def get_effective_config(self, platform_id: str, model_id: str,
                             overrides: Optional[dict] = None) -> dict:
        model = self.get_model(platform_id, model_id)
        if not model:
            raise ValueError(f"Model not found: {platform_id}/{model_id}")
        platform = self.get_platform(platform_id)

        config = {
            "ws_url": platform.get("ws_url", "ws://localhost:8080/teamspeak/voice"),
            "api_key": platform.get("api_key") or "",
            "nickname": model.get("nickname", "TeamSpeakAI"),
            "auto_reconnect": model.get("auto_reconnect", True),
            "reconnect_delay": model.get("reconnect_delay", 3.0),
        }

        if overrides:
            for key in ("nickname", "auto_reconnect", "reconnect_delay"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        return config


