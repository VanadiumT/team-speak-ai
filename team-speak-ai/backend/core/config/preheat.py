"""
模型预热配置管理

持久化到 data/defaults/preheat.json，控制各 AI 能力是否在启动时预热。
"""

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = {
    "enabled": True,
    "ocr": {"enabled": True},
    "stt": {"enabled": True},
}


@dataclass
class ProviderPreheatConfig:
    enabled: bool = True


@dataclass
class PreheatConfig:
    enabled: bool = True  # 全局开关
    ocr: ProviderPreheatConfig = field(default_factory=ProviderPreheatConfig)
    stt: ProviderPreheatConfig = field(default_factory=ProviderPreheatConfig)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "ocr": asdict(self.ocr),
            "stt": asdict(self.stt),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreheatConfig":
        return cls(
            enabled=data.get("enabled", True),
            ocr=ProviderPreheatConfig(**data.get("ocr", {})),
            stt=ProviderPreheatConfig(**data.get("stt", {})),
        )


class PreheatConfigManager:
    """预热配置 CRUD，持久化到 JSON 文件"""

    def __init__(self, data_dir: str):
        self._path = os.path.join(data_dir, "defaults", "preheat.json")
        self._config = self._load()

    def _load(self) -> PreheatConfig:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return PreheatConfig.from_dict(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load preheat config: {e}, using defaults")
        return PreheatConfig()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)

    def get_config(self) -> PreheatConfig:
        return self._config

    def get_config_dict(self) -> dict:
        return self._config.to_dict()

    def update_config(self, patch: dict) -> dict:
        """部分更新配置并保存"""
        current = self._config.to_dict()
        if "enabled" in patch:
            current["enabled"] = bool(patch["enabled"])
        for key in ("ocr", "stt"):
            if key in patch and isinstance(patch[key], dict):
                current[key].update(patch[key])
        self._config = PreheatConfig.from_dict(current)
        self._save()
        logger.info(f"Preheat config updated: {self._config.to_dict()}")
        return self._config.to_dict()
