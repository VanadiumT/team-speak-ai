"""
STT 平台预设 + 模型配置管理，持久化到 data/defaults/stt_presets.json
"""

import json
import logging
import uuid as _uuid
from copy import deepcopy as _deepcopy
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_STT_MODEL_CONFIG = {
    "language": "auto",
    "sample_rate": 16000,
}


class SttPresetManager:
    """STT 平台预设 + 模型配置管理"""

    def __init__(self, data_dir: str):
        self._path = Path(data_dir) / "defaults" / "stt_presets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Failed to load stt_presets.json, creating default")
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
                    "name": "本地 SenseVoice",
                    "provider": settings.stt_provider,
                    "api_key": "",
                    "api_url": "",
                    "model_dir": settings.sensevoice_model,
                    "device": settings.sensevoice_device,
                    "models": [
                        {
                            **_DEFAULT_STT_MODEL_CONFIG,
                            "id": _uuid.uuid4().hex[:12],
                            "name": "SenseVoiceSmall",
                            "is_default": True,
                        }
                    ],
                }
            ]
        }
        self._data = data
        self._save()
        logger.info(f"Created default STT preset at {self._path}")
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
        for key, default in _DEFAULT_STT_MODEL_CONFIG.items():
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
            "provider": platform.get("provider", "sensevoice"),
            "api_key": platform.get("api_key") or None,
            "api_url": platform.get("api_url") or None,
            "model_dir": platform.get("model_dir") or None,
            "device": platform.get("device") or "cpu",
            "model_name": model["name"],
            "language": model.get("language", "auto"),
            "sample_rate": model.get("sample_rate", 16000),
        }

        if overrides:
            for key in ("language", "sample_rate"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        from config import settings
        if not config["api_key"]:
            config["api_key"] = settings.minimax_api_key
        if not config["api_url"]:
            config["api_url"] = settings.minimax_api_url
        if not config["model_dir"]:
            config["model_dir"] = settings.sensevoice_model

        return config


