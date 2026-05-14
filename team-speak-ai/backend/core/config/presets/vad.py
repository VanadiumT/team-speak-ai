"""
VAD 预设 + 模型配置管理，持久化到 data/defaults/vad_presets.json
"""

import json
import logging
import uuid as _uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_VAD_MODEL_CONFIG = {
    "vad_mode": 3,
    "frame_duration_ms": 20,
    "hangover_ms": 600,
    "sample_rate": 16000,
    "min_speech_ms": 300,
}


class VadPresetManager:
    """VAD 预设 + 模型配置管理"""

    def __init__(self, data_dir: str):
        self._path = Path(data_dir) / "defaults" / "vad_presets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Failed to load vad_presets.json, creating default")
        return self._create_default()

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _create_default(self) -> dict:
        data = {
            "platforms": [
                {
                    "name": "默认 WebRTC VAD",
                    "provider": "webrtcvad",
                    "id": _uuid.uuid4().hex[:12],
                    "models": [
                        {
                            "name": "默认 (Mode 3 · 最激进)",
                            "is_default": True,
                            "vad_mode": 3,
                            "frame_duration_ms": 20,
                            "hangover_ms": 600,
                            "sample_rate": 16000,
                            "min_speech_ms": 300,
                            "id": _uuid.uuid4().hex[:12],
                        }
                    ],
                }
            ]
        }
        self._data = data
        self._save()
        return data

    def list_all(self) -> dict:
        import copy
        return copy.deepcopy(self._data)

    def get_platform(self, platform_id: str) -> Optional[dict]:
        for p in self._data["platforms"]:
            if p["id"] == platform_id:
                return p
        return None

    def get_model(self, platform_id: str, model_id: str) -> Optional[dict]:
        platform = self.get_platform(platform_id)
        if not platform:
            return None
        for m in platform.get("models", []):
            if m["id"] == model_id:
                return m
        return None

    def save_platform(self, platform: dict):
        if "id" in platform and platform["id"]:
            existing = self.get_platform(platform["id"])
            if existing:
                existing.update(platform)
            else:
                self._data["platforms"].append(platform)
        else:
            platform["id"] = _uuid.uuid4().hex[:12]
            self._data["platforms"].append(platform)
        self._save()

    def delete_platform(self, platform_id: str):
        self._data["platforms"] = [p for p in self._data["platforms"] if p["id"] != platform_id]
        self._save()

    def duplicate_platform(self, platform_id: str):
        platform = self.get_platform(platform_id)
        if not platform:
            raise ValueError(f"Platform not found: {platform_id}")
        import copy
        new_platform = copy.deepcopy(platform)
        new_platform["id"] = _uuid.uuid4().hex[:12]
        new_platform["name"] = f"{platform['name']} (副本)"
        for m in new_platform.get("models", []):
            m["id"] = _uuid.uuid4().hex[:12]
            m["is_default"] = False
        self._data["platforms"].append(new_platform)
        self._save()

    def save_model(self, platform_id: str, model: dict):
        platform = self.get_platform(platform_id)
        if not platform:
            raise ValueError(f"Platform not found: {platform_id}")
        if "id" in model and model["id"]:
            existing = self.get_model(platform_id, model["id"])
            if existing:
                existing.update(model)
            else:
                platform.setdefault("models", []).append(model)
        else:
            model["id"] = _uuid.uuid4().hex[:12]
            platform.setdefault("models", []).append(model)
        if model.get("is_default"):
            for m in platform.get("models", []):
                if m["id"] != model["id"]:
                    m["is_default"] = False
        self._save()

    def delete_model(self, platform_id: str, model_id: str):
        platform = self.get_platform(platform_id)
        if not platform:
            raise ValueError(f"Platform not found: {platform_id}")
        platform["models"] = [m for m in platform.get("models", []) if m["id"] != model_id]
        self._save()

    def duplicate_model(self, platform_id: str, model_id: str):
        model = self.get_model(platform_id, model_id)
        if not model:
            raise ValueError(f"Model not found: {platform_id}/{model_id}")
        import copy
        new_model = copy.deepcopy(model)
        new_model["id"] = _uuid.uuid4().hex[:12]
        new_model["name"] = f"{model['name']} (副本)"
        new_model["is_default"] = False
        platform = self.get_platform(platform_id)
        platform.setdefault("models", []).append(new_model)
        self._save()

    def get_effective_config(self, platform_id: str, model_id: str,
                             overrides: Optional[dict] = None) -> dict:
        model = self.get_model(platform_id, model_id)
        if not model:
            raise ValueError(f"Model not found: {platform_id}/{model_id}")
        platform = self.get_platform(platform_id)

        config = {
            "provider": platform.get("provider", "webrtcvad"),
            "vad_mode": model.get("vad_mode", 3),
            "frame_duration_ms": model.get("frame_duration_ms", 20),
            "hangover_ms": model.get("hangover_ms", 600),
            "sample_rate": model.get("sample_rate", 16000),
            "min_speech_ms": model.get("min_speech_ms", 300),
        }

        if overrides:
            for key in ("vad_mode", "hangover_ms", "min_speech_ms", "frame_duration_ms"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        return config


