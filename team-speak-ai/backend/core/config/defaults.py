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
