"""
ConfigDefaultsManager —— 默认配置管理

管理节点类型和流程的默认配置，存储于 data/defaults/。
"""

import json
import logging
from pathlib import Path
from typing import Optional

from core.pipeline.registry import NodeRegistry

logger = logging.getLogger(__name__)


class ConfigDefaultsManager:
    """节点类型默认配置持久化"""

    def __init__(self, data_dir: str):
        self.defaults_dir = Path(data_dir) / "defaults"
        self.defaults_dir.mkdir(parents=True, exist_ok=True)

    def load_default(self, scope: str, target_id: Optional[str] = None) -> dict:
        """加载默认配置"""
        if scope == "node" and target_id:
            return self._load_node_default(target_id)
        elif scope == "flow":
            return self._load_flow_default(target_id or "global")
        return {}

    def save_default(self, scope: str, target_id: Optional[str],
                     config: dict) -> None:
        """保存默认配置"""
        if scope == "node" and target_id:
            self._save_node_default(target_id, config)
        elif scope == "flow":
            self._save_flow_default(target_id or "global", config)

    def _node_default_path(self, node_type: str) -> Path:
        return self.defaults_dir / f"node_{node_type}.json"

    def _load_node_default(self, node_type: str) -> dict:
        """加载节点类型默认配置。优先使用已保存的默认，回退到 NodeTypeDef.default_config。"""
        path = self._node_default_path(node_type)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f).get("config", {})
            except Exception as e:
                logger.warning(f"Failed to load node default for {node_type}: {e}")
        try:
            return dict(NodeRegistry.get_type_def(node_type).default_config)
        except ValueError:
            return {}

    def _save_node_default(self, node_type: str, config: dict) -> None:
        """保存节点类型默认配置"""
        path = self._node_default_path(node_type)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "scope": "node",
                "target_id": node_type,
                "config": config,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved node default config: {node_type}")

    def _load_flow_default(self, flow_id: str) -> dict:
        path = self.defaults_dir / f"flow_{flow_id}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f).get("config", {})
            except Exception as e:
                logger.warning(f"Failed to load flow default: {e}")
        return {}

    def _save_flow_default(self, flow_id: str, config: dict) -> None:
        path = self.defaults_dir / f"flow_{flow_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "scope": "flow",
                "target_id": flow_id,
                "config": config,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved flow default config: {flow_id}")


# 全局单例
_defaults_manager: Optional[ConfigDefaultsManager] = None


def get_defaults_manager() -> ConfigDefaultsManager:
    global _defaults_manager
    if _defaults_manager is None:
        raise RuntimeError("ConfigDefaultsManager not initialized")
    return _defaults_manager


def init_defaults_manager(data_dir: str) -> ConfigDefaultsManager:
    global _defaults_manager
    _defaults_manager = ConfigDefaultsManager(data_dir)
    return _defaults_manager


# ═══════════════════════════════════════════════════════════════
# LLM Preset Manager
# ═══════════════════════════════════════════════════════════════

import uuid as _uuid
from copy import deepcopy as _deepcopy

_DEFAULT_MODEL_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "top_p": 1.0,
    "streaming": True,
    "thinking_mode": "off",
    "vision": False,
    "image_detail": "auto",
    "max_images": 4,
    "system_prompt": "",
    "max_context_tokens": 0,
    "response_format": "text",
    "stop": [],
    "extra": {},
}


class PresetManager:
    """LLM 平台预设 + 模型配置管理，持久化到 data/defaults/llm_presets.json"""

    def __init__(self, data_dir: str):
        self._path = Path(data_dir) / "defaults" / "llm_presets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Failed to load llm_presets.json, creating default")
        return self._create_default()

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _create_default(self) -> dict:
        """首次启动时自动创建默认平台 + 模型，使用 settings 默认值"""
        from config import settings
        data = {
            "platforms": [
                {
                    "id": _uuid.uuid4().hex[:12],
                    "name": "默认 OpenAI 平台",
                    "provider": settings.llm_provider,
                    "base_url": settings.openai_base_url,
                    "api_key": "",
                    "models": [
                        {
                            **_DEFAULT_MODEL_CONFIG,
                            "id": _uuid.uuid4().hex[:12],
                            "name": settings.openai_model,
                            "is_default": True,
                            "thinking_mode": "separate" if settings.openai_reasoning_split else "off",
                        }
                    ],
                }
            ]
        }
        self._data = data
        self._save()
        logger.info(f"Created default LLM preset at {self._path}")
        return data

    def list_all(self) -> dict:
        return _deepcopy(self._data)

    # ── 平台 CRUD ──

    def save_platform(self, platform: dict) -> dict:
        """创建或更新平台。有 id=更新，无 id=新建。返回完整 data"""
        pid = platform.get("id")
        if pid:
            for i, p in enumerate(self._data["platforms"]):
                if p["id"] == pid:
                    # Merge: update fields except models (managed separately)
                    for k, v in platform.items():
                        if k != "models":
                            self._data["platforms"][i][k] = v
                    self._save()
                    return self.list_all()
        # 新建
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

    # ── 模型 CRUD ──

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
        for key, default in _DEFAULT_MODEL_CONFIG.items():
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

    # ── 查询 ──

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
        """合并平台 + 模型 + 节点覆盖 → 最终 LLM 配置"""
        model = self.get_model(platform_id, model_id)
        if not model:
            raise ValueError(f"Model not found: {platform_id}/{model_id}")
        platform = self.get_platform(platform_id)

        config = {
            "provider": platform.get("provider", "openai"),
            "base_url": platform.get("base_url") or None,
            "api_key": platform.get("api_key") or None,
            "model": model["name"],
            "reasoning_split": model.get("thinking_mode") == "separate",
            "thinking_mode": model.get("thinking_mode", "off"),
            "temperature": model.get("temperature"),
            "max_tokens": model.get("max_tokens"),
            "top_p": model.get("top_p"),
            "streaming": model.get("streaming", True),
            "vision": model.get("vision", False),
            "image_detail": model.get("image_detail", "auto"),
            "max_images": model.get("max_images", 4),
            "system_prompt": model.get("system_prompt", ""),
            "max_context_tokens": model.get("max_context_tokens", 0),
            "response_format": model.get("response_format", "text"),
            "stop": model.get("stop", []),
            "extra": _deepcopy(model.get("extra", {})),
        }

        # 应用节点级覆盖
        if overrides:
            for key in ("temperature", "max_tokens", "system_prompt", "streaming"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        # api_key / base_url 空则回退全局 settings
        from config import settings
        if not config["api_key"]:
            config["api_key"] = settings.openai_api_key
        if not config["base_url"]:
            config["base_url"] = settings.openai_base_url

        # 防呆：去掉用户误输入的尾部 /chat/completions 路径段
        if config["base_url"]:
            config["base_url"] = config["base_url"].rstrip("/")
            for suffix in ("/chat/completions", "/v1/chat/completions"):
                if config["base_url"].endswith(suffix):
                    config["base_url"] = config["base_url"][:-len(suffix)]
                    break

        return config


# LLM 预设单例
_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    global _preset_manager
    if _preset_manager is None:
        raise RuntimeError("PresetManager not initialized")
    return _preset_manager


def init_preset_manager(data_dir: str) -> PresetManager:
    global _preset_manager
    _preset_manager = PresetManager(data_dir)
    return _preset_manager


# ═══════════════════════════════════════════════════════════════
# TTS Preset Manager
# ═══════════════════════════════════════════════════════════════

_DEFAULT_TTS_MODEL_CONFIG = {
    "voice_id": "male-qn-qingse",
    "speed": 1.0,
    "vol": 1.0,
    "pitch": 0,
    "emotion": "",
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1,
    "streaming": True,
    "language_boost": None,
}


class TtsPresetManager:
    """TTS 平台预设 + 模型配置管理，持久化到 data/defaults/tts_presets.json"""

    def __init__(self, data_dir: str):
        self._path = Path(data_dir) / "defaults" / "tts_presets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Failed to load tts_presets.json, creating default")
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
                    "name": "默认 MiniMax TTS",
                    "provider": "minimax",
                    "api_key": "",
                    "models": [
                        {
                            **_DEFAULT_TTS_MODEL_CONFIG,
                            "id": _uuid.uuid4().hex[:12],
                            "name": settings.minimax_tts_model,
                            "is_default": True,
                        }
                    ],
                }
            ]
        }
        self._data = data
        self._save()
        logger.info(f"Created default TTS preset at {self._path}")
        return data

    def list_all(self) -> dict:
        return _deepcopy(self._data)

    # ── 平台 CRUD ──

    def save_platform(self, platform: dict) -> dict:
        pid = platform.get("id")
        if pid:
            for i, p in enumerate(self._data["platforms"]):
                if p["id"] == pid:
                    # Merge: update fields except models (managed separately)
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

    # ── 模型 CRUD ──

    def _find_platform(self, platform_id: str) -> tuple:
        for i, p in enumerate(self._data["platforms"]):
            if p["id"] == platform_id:
                return i, p
        raise ValueError(f"Platform not found: {platform_id}")

    def save_model(self, platform_id: str, model: dict) -> dict:
        idx, platform = self._find_platform(platform_id)
        platform.setdefault("models", [])
        mid = model.get("id")
        if mid:
            for j, m in enumerate(platform["models"]):
                if m["id"] == mid:
                    platform["models"][j] = _deepcopy(model)
                    self._save()
                    return self.list_all()
        model = _deepcopy(model)
        model["id"] = _uuid.uuid4().hex[:12]
        for key, default in _DEFAULT_TTS_MODEL_CONFIG.items():
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

    # ── 查询 ──

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
        """合并平台 + 模型 + 节点覆盖 → 最终 TTS 配置"""
        model = self.get_model(platform_id, model_id)
        if not model:
            raise ValueError(f"Model not found: {platform_id}/{model_id}")
        platform = self.get_platform(platform_id)

        config = {
            "provider": platform.get("provider", "minimax"),
            "api_key": platform.get("api_key") or None,
            "model": model["name"],
            "voice_id": model.get("voice_id", "male-qn-qingse"),
            "speed": model.get("speed", 1.0),
            "vol": model.get("vol", 1.0),
            "pitch": model.get("pitch", 0),
            "emotion": model.get("emotion") or "",
            "sample_rate": model.get("sample_rate", 32000),
            "bitrate": model.get("bitrate", 128000),
            "format": model.get("format", "mp3"),
            "channel": model.get("channel", 1),
            "streaming": model.get("streaming", True),
            "language_boost": model.get("language_boost"),
        }

        # 节点级覆盖
        if overrides:
            for key in ("speed", "vol", "pitch", "voice_id"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        # api_key 空则回退全局 settings
        from config import settings
        if not config["api_key"]:
            config["api_key"] = settings.minimax_api_key

        return config


# TTS 预设单例
_tts_preset_manager: Optional[TtsPresetManager] = None


def get_tts_preset_manager() -> TtsPresetManager:
    global _tts_preset_manager
    if _tts_preset_manager is None:
        raise RuntimeError("TtsPresetManager not initialized")
    return _tts_preset_manager


def init_tts_preset_manager(data_dir: str) -> TtsPresetManager:
    global _tts_preset_manager
    _tts_preset_manager = TtsPresetManager(data_dir)
    return _tts_preset_manager


# ═══════════════════════════════════════════════════════════════
# STT Preset Manager
# ═══════════════════════════════════════════════════════════════

_DEFAULT_STT_MODEL_CONFIG = {
    "language": "auto",
    "sample_rate": 16000,
}


class SttPresetManager:
    """STT 平台预设 + 模型配置管理，持久化到 data/defaults/stt_presets.json"""

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

    # ── 平台 CRUD ──

    def save_platform(self, platform: dict) -> dict:
        pid = platform.get("id")
        if pid:
            for i, p in enumerate(self._data["platforms"]):
                if p["id"] == pid:
                    # Merge: update fields except models (managed separately)
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

    # ── 模型 CRUD ──

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

    # ── 查询 ──

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
        """合并平台 + 模型 + 节点覆盖 → 最终 STT 配置"""
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

        # 节点级覆盖
        if overrides:
            for key in ("language", "sample_rate"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        # fallback: 空字段回退到全局 settings
        from config import settings
        if not config["api_key"]:
            config["api_key"] = settings.minimax_api_key
        if not config["api_url"]:
            config["api_url"] = settings.minimax_api_url
        if not config["model_dir"]:
            config["model_dir"] = settings.sensevoice_model

        return config


# ═══════════════════════════════════════════════════════════════
# OCR Preset Manager
# ═══════════════════════════════════════════════════════════════

_DEFAULT_OCR_MODEL_CONFIG = {
    "lang_list": ["ch_sim", "en"],
    "lang": "ch",
    "gpu": False,
    "use_angle_cls": True,
    "confidence_threshold": 0.3,
}


class OcrPresetManager:
    """OCR 平台预设 + 模型配置管理，持久化到 data/defaults/ocr_presets.json"""

    def __init__(self, data_dir: str):
        self._path = Path(data_dir) / "defaults" / "ocr_presets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Failed to load ocr_presets.json, creating default")
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
                    "name": "本地 EasyOCR",
                    "provider": "easyocr",
                    "models": [
                        {
                            **_DEFAULT_OCR_MODEL_CONFIG,
                            "id": _uuid.uuid4().hex[:12],
                            "name": "中英混合 (CPU)",
                            "is_default": True,
                            "gpu": False,
                            "lang_list": ["ch_sim", "en"],
                        }
                    ],
                },
                {
                    "id": _uuid.uuid4().hex[:12],
                    "name": "本地 PaddleOCR",
                    "provider": "paddleocr",
                    "det_model_dir": settings.paddleocr_det_model,
                    "rec_model_dir": settings.paddleocr_rec_model,
                    "models": [
                        {
                            **_DEFAULT_OCR_MODEL_CONFIG,
                            "id": _uuid.uuid4().hex[:12],
                            "name": "中文高精度",
                            "is_default": True,
                            "lang": "ch",
                            "use_angle_cls": True,
                            "gpu": False,
                        }
                    ],
                },
            ]
        }
        self._data = data
        self._save()
        logger.info(f"Created default OCR preset at {self._path}")
        return data

    def list_all(self) -> dict:
        return _deepcopy(self._data)

    # ── 平台 CRUD ──

    def save_platform(self, platform: dict) -> dict:
        pid = platform.get("id")
        if pid:
            for i, p in enumerate(self._data["platforms"]):
                if p["id"] == pid:
                    # Merge: update fields except models (managed separately)
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

    # ── 模型 CRUD ──

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
        for key, default in _DEFAULT_OCR_MODEL_CONFIG.items():
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

    # ── 查询 ──

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
        """合并平台 + 模型 + 节点覆盖 → 最终 OCR 配置"""
        model = self.get_model(platform_id, model_id)
        if not model:
            raise ValueError(f"Model not found: {platform_id}/{model_id}")
        platform = self.get_platform(platform_id)

        config = {
            "provider": platform.get("provider", "easyocr"),
            "label": f"{platform.get('name', '')} / {model.get('name', '')}".strip(" /"),
            "lang_list": model.get("lang_list", ["ch_sim", "en"]),
            "lang": model.get("lang", "ch"),
            "gpu": model.get("gpu", False),
            "use_angle_cls": model.get("use_angle_cls", True),
            "confidence_threshold": model.get("confidence_threshold", 0.3),
            "det_model_dir": platform.get("det_model_dir", ""),
            "rec_model_dir": platform.get("rec_model_dir", ""),
        }

        if overrides:
            for key in ("lang_list", "lang", "gpu", "use_angle_cls", "confidence_threshold"):
                if key in overrides and overrides[key] is not None:
                    config[key] = overrides[key]

        # fallback: PaddleOCR 模型路径
        from config import settings
        if not config["det_model_dir"]:
            config["det_model_dir"] = settings.paddleocr_det_model
        if not config["rec_model_dir"]:
            config["rec_model_dir"] = settings.paddleocr_rec_model

        return config


# OCR 预设单例
_ocr_preset_manager: Optional[OcrPresetManager] = None


def get_ocr_preset_manager() -> OcrPresetManager:
    global _ocr_preset_manager
    if _ocr_preset_manager is None:
        raise RuntimeError("OcrPresetManager not initialized")
    return _ocr_preset_manager


def init_ocr_preset_manager(data_dir: str) -> OcrPresetManager:
    global _ocr_preset_manager
    _ocr_preset_manager = OcrPresetManager(data_dir)
    return _ocr_preset_manager


# ═══════════════════════════════════════════════════════════════
# VAD Preset Manager
# ═══════════════════════════════════════════════════════════════

_DEFAULT_VAD_MODEL_CONFIG = {
    "vad_mode": 3,
    "frame_duration_ms": 20,
    "hangover_ms": 600,
    "sample_rate": 16000,
    "min_speech_ms": 300,
}


class VadPresetManager:
    """VAD 预设 + 模型配置管理，持久化到 data/defaults/vad_presets.json"""

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


# VAD 预设单例
_vad_preset_manager: Optional[VadPresetManager] = None


def get_vad_preset_manager() -> VadPresetManager:
    global _vad_preset_manager
    if _vad_preset_manager is None:
        raise RuntimeError("VadPresetManager not initialized")
    return _vad_preset_manager


def init_vad_preset_manager(data_dir: str) -> VadPresetManager:
    global _vad_preset_manager
    _vad_preset_manager = VadPresetManager(data_dir)
    return _vad_preset_manager


# ═══════════════════════════════════════════════════════════════
# TeamSpeak Bridge 连接预设管理器
# ═══════════════════════════════════════════════════════════════
#
# 两层模型:
#   Platform = 一个 Java TeamSpeak Bridge 实例 (ws_url + api_key)
#   Model    = 该桥接的连接配置 (nickname, auto_reconnect 等)
#
# 注意: TeamSpeak 服务器参数 (host/password/channel) 由 Java 项目管理，
#       这里的配置只关乎 Python ←WS→ Java Bridge 之间的连接。

_DEFAULT_TS_MODEL_CONFIG = {
    "nickname": "TeamSpeakAI",
    "auto_reconnect": True,
    "reconnect_delay": 3.0,
}


class TeamSpeakPresetManager:
    """TS Bridge 连接预设，持久化到 data/defaults/ts_presets.json"""

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

    # ── 平台 (桥接实例) CRUD ──

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

    # ── 模型 (连接配置) CRUD ──

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

    # ── 查询 ──

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
        """合并桥接 + 连接配置 → 最终 WS 连接参数"""
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


# TS 预设单例
_ts_preset_manager: Optional[TeamSpeakPresetManager] = None


def get_ts_preset_manager() -> TeamSpeakPresetManager:
    global _ts_preset_manager
    if _ts_preset_manager is None:
        raise RuntimeError("TeamSpeakPresetManager not initialized")
    return _ts_preset_manager


def init_ts_preset_manager(data_dir: str) -> TeamSpeakPresetManager:
    global _ts_preset_manager
    _ts_preset_manager = TeamSpeakPresetManager(data_dir)
    return _ts_preset_manager


# STT 预设单例
_stt_preset_manager: Optional[SttPresetManager] = None


def get_stt_preset_manager() -> SttPresetManager:
    global _stt_preset_manager
    if _stt_preset_manager is None:
        raise RuntimeError("SttPresetManager not initialized")
    return _stt_preset_manager


def init_stt_preset_manager(data_dir: str) -> SttPresetManager:
    global _stt_preset_manager
    _stt_preset_manager = SttPresetManager(data_dir)
    return _stt_preset_manager
