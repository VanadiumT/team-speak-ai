"""
FlowManager —— 流程数据管理

负责流程的 CRUD、JSON 持久化、侧栏树构建。
"""

import json
import os
import re
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.pipeline.definition import (
    PipelineDefinition, NodeDefinition, ConnectionDef,
    FlowSummary, SidebarNode,
)
from core.exceptions import FlowNotFoundError, FlowValidationError, FlowCycleError

logger = logging.getLogger(__name__)


class FlowManager:
    """管理流程数据的 CRUD 和持久化"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.flows_dir = self.data_dir / "flows"
        self.flows_dir.mkdir(parents=True, exist_ok=True)
        self._groups_file = self.data_dir / "groups.json"
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, flow_id: str) -> asyncio.Lock:
        if flow_id not in self._locks:
            self._locks[flow_id] = asyncio.Lock()
        return self._locks[flow_id]

    # ── Groups persistence ─────────────────────────────────────

    def list_groups(self) -> list[str]:
        """读取显式创建的目录列表"""
        if not self._groups_file.exists():
            return []
        try:
            with open(self._groups_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_groups(self, groups: list[str]) -> None:
        """保存目录列表"""
        tmp = self._groups_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(set(groups)), f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._groups_file)

    def create_group(self, group_path: str) -> list[str]:
        """创建空目录（持久化到 groups.json）"""
        groups = self.list_groups()
        if group_path not in groups:
            groups.append(group_path)
            self._save_groups(groups)
        return groups

    def remove_group(self, group_path: str) -> list[str]:
        """从 groups.json 中移除目录"""
        groups = self.list_groups()
        groups = [g for g in groups if g != group_path and not g.startswith(group_path + "/")]
        self._save_groups(groups)
        return groups

    # ── Flow CRUD ──────────────────────────────────────────────

    def list_flows(self) -> list[FlowSummary]:
        """扫描 flows/ 目录，返回所有流程摘要"""
        summaries = []
        if not self.flows_dir.exists():
            return summaries
        for filepath in sorted(self.flows_dir.glob("*.json")):
            try:
                flow = self._load_json(filepath)
                summaries.append(FlowSummary(
                    id=flow.get("id", filepath.stem),
                    name=flow.get("name", filepath.stem),
                    group=flow.get("group", ""),
                    icon=flow.get("icon", "account_tree"),
                    node_count=len(flow.get("nodes", [])),
                    enabled=flow.get("enabled", True),
                    updated_at=self._get_mtime(filepath),
                ))
            except Exception as e:
                logger.warning(f"Failed to read flow summary from {filepath}: {e}")
        return summaries

    def load_flow(self, flow_id: str) -> PipelineDefinition:
        """从 JSON 文件加载完整流程定义"""
        filepath = self._flow_path(flow_id)
        if not filepath.exists():
            raise FlowNotFoundError(flow_id)
        data = self._load_json(filepath)
        return self._deserialize_flow(data)

    def _save_flow_locked(self, flow: PipelineDefinition) -> None:
        """原子写入到磁盘（内部方法，假设锁已持有）"""
        filepath = self._flow_path(flow.id)
        data = self._serialize_flow(flow)
        tmp_path = filepath.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)
        except OSError as e:
            logger.error(f"Failed to save flow {flow.id}: {e}")
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise

    async def save_flow(self, flow: PipelineDefinition) -> None:
        """序列化并原子写入到磁盘（加锁版）"""
        async with self._get_lock(flow.id):
            self._save_flow_locked(flow)

    async def delete_flow(self, flow_id: str) -> None:
        """删除流程 JSON 文件"""
        async with self._get_lock(flow_id):
            filepath = self._flow_path(flow_id)
            if filepath.exists():
                filepath.unlink()

    def create_flow(self, name: str, group: str = "", icon: str = "account_tree") -> PipelineDefinition:
        """创建新流程，生成唯一 ID（新建流程无竞争，无需加锁）"""
        flow_id = self._slugify(name)
        filepath = self._flow_path(flow_id)
        if filepath.exists():
            i = 2
            while True:
                flow_id = f"{self._slugify(name)}_{i}"
                filepath = self._flow_path(flow_id)
                if not filepath.exists():
                    break
                i += 1
        flow = PipelineDefinition(
            id=flow_id,
            name=name,
            group=group,
            icon=icon,
        )
        self._save_flow_locked(flow)
        return flow

    async def copy_flow(self, flow_id: str, new_name: str = None) -> PipelineDefinition:
        """复制流程，生成新 ID"""
        async with self._get_lock(flow_id):
            original = self.load_flow(flow_id)
        base_name = new_name or f"{original.name} (副本)"
        new_id = self._slugify(base_name)
        filepath = self._flow_path(new_id)
        if filepath.exists():
            i = 2
            while True:
                new_id = f"{self._slugify(base_name)}_{i}"
                filepath = self._flow_path(new_id)
                if not filepath.exists():
                    break
                i += 1
        copy_flow = PipelineDefinition(
            id=new_id,
            name=base_name,
            group=original.group,
            icon=original.icon,
            skill_prompt=original.skill_prompt,
            canvas=dict(original.canvas) if original.canvas else {"width": 2000, "height": 1500},
            nodes=[NodeDefinition(
                id=n.id, type=n.type, name=n.name,
                position=dict(n.position), config=dict(n.config),
                input_mappings=list(n.input_mappings),
                trigger=n.trigger, listener=n.listener,
            ) for n in original.nodes],
            connections=[ConnectionDef(
                id=c.id, from_node=c.from_node, from_port=c.from_port,
                to_node=c.to_node, to_port=c.to_port, type=c.type,
            ) for c in original.connections],
        )
        self._save_flow_locked(copy_flow)
        return copy_flow

    async def update_flow_group(self, flow_id: str, group: str) -> PipelineDefinition:
        """更新流程的分组"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.group = group
            self._save_flow_locked(flow)
            return flow

    async def update_flow_canvas(self, flow_id: str, canvas: dict) -> PipelineDefinition:
        """更新流程的画布尺寸"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.canvas = canvas
            self._save_flow_locked(flow)
            return flow

    async def update_flow_params(self, flow_id: str, params: dict) -> PipelineDefinition:
        """更新流程参数（合并写入）"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.params.update(params)
            self._save_flow_locked(flow)
            return flow

    async def delete_flow_param(self, flow_id: str, key: str) -> PipelineDefinition:
        """删除单个流程参数"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.params.pop(key, None)
            self._save_flow_locked(flow)
            return flow

    async def toggle_flow_enabled(self, flow_id: str) -> PipelineDefinition:
        """切换流程启用/禁用状态，返回新状态"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.enabled = not flow.enabled
            self._save_flow_locked(flow)
            return flow

    async def rename_group(self, old_group_path: str, new_group_path: str) -> int:
        """重命名分组：批量更新所有匹配路径的 flow 的 group 字段。返回更新数量。"""
        count = 0
        for filepath in sorted(self.flows_dir.glob("*.json")):
            try:
                flow_id = filepath.stem
                async with self._get_lock(flow_id):
                    flow = self.load_flow(flow_id)
                    if flow.group == old_group_path or flow.group.startswith(old_group_path + "/"):
                        if flow.group == old_group_path:
                            flow.group = new_group_path
                        else:
                            flow.group = new_group_path + flow.group[len(old_group_path):]
                        self._save_flow_locked(flow)
                        count += 1
            except Exception:
                logger.warning(f"Failed to rename group for {filepath.stem}", exc_info=True)
        return count

    async def delete_flows_in_group(self, group_path: str) -> int:
        """删除分组下所有流程。返回删除数量。"""
        count = 0
        for filepath in sorted(self.flows_dir.glob("*.json")):
            try:
                flow_id = filepath.stem
                async with self._get_lock(flow_id):
                    flow = self.load_flow(flow_id)
                    if flow.group == group_path or flow.group.startswith(group_path + "/"):
                        filepath.unlink()
                        count += 1
            except Exception:
                logger.warning(f"Failed to delete flow {filepath.stem}", exc_info=True)
        return count

    def export_flow(self, flow_id: str) -> dict:
        """导出流程为 JSON 字典"""
        flow = self.load_flow(flow_id)
        return self._serialize_flow(flow)

    async def import_flow(self, data: dict, overwrite: bool = False) -> PipelineDefinition:
        """从 JSON 字典导入流程"""
        flow_id = data.get("id", "")
        if not flow_id:
            raise FlowValidationError(flow_id="unknown", detail="Missing flow id in import data")
        filepath = self._flow_path(flow_id)
        async with self._get_lock(flow_id):
            if filepath.exists() and not overwrite:
                i = 2
                while True:
                    flow_id = f"{self._slugify(data.get('name', flow_id))}_{i}"
                    filepath = self._flow_path(flow_id)
                    if not filepath.exists():
                        break
                    i += 1
            flow = self._deserialize_flow(data)
            flow.id = flow_id
            self._save_flow_locked(flow)
            return flow

    def export_group_zip(self, group_path: str) -> bytes:
        """导出分组下所有流程为 ZIP，group 字段保留相对路径（去掉父前缀）"""
        import io
        import zipfile

        # 计算父前缀：group_path = "root/暗区" → parent_prefix = "root/"
        parts = group_path.split("/")
        parent_prefix = "/".join(parts[:-1]) + "/" if len(parts) > 1 else ""

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath in sorted(self.flows_dir.glob("*.json")):
                try:
                    flow = self.load_flow(filepath.stem)
                    if flow.group == group_path or flow.group.startswith(group_path + "/"):
                        data = self._serialize_flow(flow)
                        # 去掉父前缀，保留被点击分组名及以下相对路径
                        if parent_prefix and flow.group.startswith(parent_prefix):
                            data["group"] = flow.group[len(parent_prefix):]
                        zf.writestr(f"{flow.id}.json",
                                    json.dumps(data, ensure_ascii=False, indent=2))
                except Exception:
                    pass
        return buf.getvalue()

    def export_all_zip(self) -> bytes:
        """导出所有流程为 ZIP 字节流（保留原始 group 路径）"""
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath in sorted(self.flows_dir.glob("*.json")):
                try:
                    flow = self.load_flow(filepath.stem)
                    data = self._serialize_flow(flow)
                    zf.writestr(f"{flow.id}.json",
                                json.dumps(data, ensure_ascii=False, indent=2))
                except Exception:
                    pass
        return buf.getvalue()

    async def import_group_zip(self, zip_data: bytes, target_group: str = "",
                                overwrite: bool = False) -> list[PipelineDefinition]:
        """从 ZIP 导入流程，将 ZIP 内相对 group 路径拼接到 target_group 下"""
        import io
        import zipfile

        imported = []
        with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    data = json.loads(zf.read(name).decode("utf-8"))
                    # 拼接目标路径：ZIP 内相对路径 + 目标分组
                    rel_group = data.get("group", "")
                    if target_group:
                        data["group"] = target_group + "/" + rel_group if rel_group else target_group
                    else:
                        data["group"] = rel_group
                    flow = await self.import_flow(data, overwrite=overwrite)
                    imported.append(flow)
                except Exception as e:
                    logger.warning(f"Failed to import {name} from zip: {e}")
        return imported

    # ── 节点 CRUD ──────────────────────────────────────────────

    async def add_node(self, flow_id: str, node: NodeDefinition) -> PipelineDefinition:
        """向流程添加节点并持久化"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.nodes.append(node)
            self._save_flow_locked(flow)
            return flow

    async def remove_node(self, flow_id: str, node_id: str) -> PipelineDefinition:
        """删除节点及其所有关联连线"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.nodes = [n for n in flow.nodes if n.id != node_id]
            flow.connections = [
                c for c in flow.connections
                if c.from_node != node_id and c.to_node != node_id
            ]
            self._save_flow_locked(flow)
            return flow

    async def move_node(self, flow_id: str, node_id: str, x: float, y: float) -> PipelineDefinition:
        """更新节点位置"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            node = flow.get_node(node_id)
            if not node:
                raise FlowValidationError(flow_id=flow_id, detail=f"Node not found: {node_id}")
            node.position = {"x": x, "y": y}
            self._save_flow_locked(flow)
            return flow

    async def update_node_config(self, flow_id: str, node_id: str, config: dict) -> PipelineDefinition:
        """部分更新节点配置 (merge)"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            node = flow.get_node(node_id)
            if not node:
                raise FlowValidationError(flow_id=flow_id, detail=f"Node not found: {node_id}")
            node.config.update(config)
            self._save_flow_locked(flow)
            return flow

    async def rename_node(self, flow_id: str, node_id: str, name: str) -> PipelineDefinition:
        """重命名节点"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            node = flow.get_node(node_id)
            if not node:
                raise FlowValidationError(flow_id=flow_id, detail=f"Node not found: {node_id}")
            node.name = name
            self._save_flow_locked(flow)
            return flow

    # ── 连线 CRUD ──────────────────────────────────────────────

    async def add_connection(self, flow_id: str, conn: ConnectionDef) -> PipelineDefinition:
        """添加连线（调用前应已完成校验）"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.connections.append(conn)
            self._save_flow_locked(flow)
            return flow

    async def remove_connection(self, flow_id: str, connection_id: str) -> PipelineDefinition:
        """删除连线"""
        async with self._get_lock(flow_id):
            flow = self.load_flow(flow_id)
            flow.connections = [c for c in flow.connections if c.id != connection_id]
            self._save_flow_locked(flow)
            return flow

    def get_connection(self, flow_id: str, connection_id: str) -> Optional[ConnectionDef]:
        flow = self.load_flow(flow_id)
        return flow.get_connection(connection_id)

    # ── 校验 ───────────────────────────────────────────────────

    def validate_connection(self, flow_id: str, from_node: str, from_port: str,
                            to_node: str, to_port: str) -> Optional[str]:
        """校验连线合法性。返回 None 表示合法，否则返回错误信息。"""
        from core.pipeline.registry import NodeRegistry

        flow = self.load_flow(flow_id)
        from_n = flow.get_node(from_node)
        to_n = flow.get_node(to_node)

        if not from_n:
            return f"Source node not found: {from_node}"
        if not to_n:
            return f"Target node not found: {to_node}"

        # 获取节点类型的端口定义
        try:
            from_type = NodeRegistry.get_type_def(from_n.type)
            to_type = NodeRegistry.get_type_def(to_n.type)
        except ValueError as e:
            return str(e)

        # 检查端口存在性（含动态可重复端口）
        from_ports = {p.id for p in from_type.ports.outputs}
        to_ports = {p.id for p in to_type.ports.inputs}

        # 扩展可重复端口实例
        def _expand_repeatable(node, side):
            rp = node.config.get("_repeatable_ports", {})
            for group_ids in rp.values():
                for pid in group_ids:
                    yield pid

        from_ports.update(_expand_repeatable(from_n, "output"))
        to_ports.update(_expand_repeatable(to_n, "input"))

        if from_port not in from_ports:
            return f"Port '{from_port}' not found on node type '{from_n.type}'"
        if to_port not in to_ports:
            return f"Port '{to_port}' not found on node type '{to_n.type}'"

        # 检查类型兼容性
        from_type_def = next((p for p in from_type.ports.outputs if p.id == from_port), None)
        to_type_def = next((p for p in to_type.ports.inputs if p.id == to_port), None)
        # 如果通过 id 没找到，检查可重复端口模板
        if not from_type_def:
            for p in from_type.ports.outputs:
                if p.repeatable and p.group:
                    rp = from_n.config.get("_repeatable_ports", {}).get(p.group, [])
                    if from_port in rp:
                        from_type_def = p
                        break
        if not to_type_def:
            for p in to_type.ports.inputs:
                if p.repeatable and p.group:
                    rp = to_n.config.get("_repeatable_ports", {}).get(p.group, [])
                    if to_port in rp:
                        to_type_def = p
                        break
        if from_type_def and to_type_def:
            if not self._types_compatible(from_type_def.data_type, to_type_def.data_type):
                return f"Type mismatch: {from_type_def.data_type} → {to_type_def.data_type}"

        return None

    def would_create_cycle(self, flow_id: str, from_node: str, to_node: str) -> bool:
        """检查添加 from_node → to_node 是否会形成环"""
        flow = self.load_flow(flow_id)
        # 构建邻接表（不含待添加的边）
        adj: dict[str, set[str]] = {}
        for n in flow.nodes:
            adj[n.id] = set()
        for c in flow.connections:
            adj[c.from_node].add(c.to_node)
        # 添加候选边
        adj.setdefault(from_node, set()).add(to_node)

        # DFS 环检测
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n.id: WHITE for n in flow.nodes}
        color.setdefault(from_node, WHITE)
        color.setdefault(to_node, WHITE)

        def dfs(u: str) -> bool:
            color[u] = GRAY
            for v in adj.get(u, set()):
                if color.get(v, WHITE) == GRAY:
                    return True  # found cycle
                if color.get(v, WHITE) == WHITE:
                    if dfs(v):
                        return True
            color[u] = BLACK
            return False

        for n_id in color:
            if color[n_id] == WHITE:
                if dfs(n_id):
                    return True
        return False

    @staticmethod
    def _types_compatible(source_type: str, target_type: str) -> bool:
        """检查两个端口类型是否兼容"""
        if source_type == target_type:
            return True
        # "any" 是通配类型，与任意类型兼容
        if source_type == "any" or target_type == "any":
            return True
        compatible_pairs = {
            ("string", "string_array"),
            ("string_array", "messages"),
            ("string", "messages"),
        }
        return (source_type, target_type) in compatible_pairs or \
               (target_type, source_type) in compatible_pairs

    # ── 侧栏树构建 ────────────────────────────────────────────

    def build_sidebar_tree(self) -> list[SidebarNode]:
        """从所有流程生成侧栏树结构，合并显式创建的目录"""
        flows = self.list_flows()

        # 按 group 字段分组
        groups: dict[str, list[FlowSummary]] = {}
        for f in flows:
            group_key = f.group or "ungrouped"
            groups.setdefault(group_key, []).append(f)

        # 确保显式创建的目录即使没有流程也显示
        explicit_groups = self.list_groups()
        for eg in explicit_groups:
            if eg not in groups:
                groups[eg] = []

        children = []
        for group_key in sorted(groups.keys()):
            parts = [p.strip() for p in group_key.split("/") if p.strip()]
            self._insert_into_tree(children, parts, groups[group_key])

        return [
            SidebarNode(
                id="workflows", name="工作流", icon="account_tree", type="section",
                children=children,
            ),
            SidebarNode(
                id="node_settings", name="节点设置", icon="tune", type="section",
                children=[
                    SidebarNode(id="action:ocr_settings", name="OCR设置", icon="document_scanner", type="action"),
                    SidebarNode(id="action:llm_settings", name="LLM设置", icon="psychology", type="action"),
                    SidebarNode(id="action:stt_settings", name="STT设置", icon="mic", type="action"),
                    SidebarNode(id="action:tts_settings", name="TTS设置", icon="record_voice_over", type="action"),
                    SidebarNode(id="action:vad_settings", name="VAD设置", icon="voice_selection", type="action"),
                    SidebarNode(id="action:ts_settings", name="TeamSpeak连接", icon="headset_mic", type="action"),
                ],
            ),
            SidebarNode(
                id="system_settings", name="系统设置", icon="settings", type="section",
                children=[
                    SidebarNode(id="action:sys_vars", name="系统变量", icon="data_object", type="action"),
                    SidebarNode(id="action:shortcuts", name="系统快捷键", icon="keyboard", type="action"),
                ],
            ),
        ]

    def _insert_into_tree(self, siblings: list[SidebarNode], parts: list[str],
                          flows: list[FlowSummary], prefix: str = "") -> None:
        if not parts:
            for f in flows:
                siblings.append(SidebarNode(
                    id=f"flow:{f.id}", name=f.name, icon=f.icon,
                    type="flow_ref", flow_id=f.id,
                    enabled=f.enabled,
                ))
            return

        current_part = parts[0]
        full_path = prefix + "/" + current_part if prefix else current_part
        existing = next((c for c in siblings if c.name == current_part and c.type == "group"), None)
        if not existing:
            existing = SidebarNode(
                id=full_path, name=current_part,
                icon="folder", type="group",
            )
            siblings.append(existing)

        self._insert_into_tree(existing.children, parts[1:], flows, full_path)

    # ── 内部工具方法 ────────────────────────────────────────────

    def _flow_path(self, flow_id: str) -> Path:
        return self.flows_dir / f"{flow_id}.json"

    @staticmethod
    def _load_json(filepath: Path) -> dict:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON file {filepath}: {e}")
            raise FileNotFoundError(f"Corrupted flow file: {filepath}")
        except OSError as e:
            logger.error(f"Failed to read {filepath}: {e}")
            raise

    @staticmethod
    def _get_mtime(filepath: Path) -> str:
        ts = os.path.getmtime(filepath)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    @staticmethod
    def _slugify(name: str) -> str:
        """将名称转换为 slug，保留中文字符"""
        slug = name.lower().strip()
        # 保留字母、数字、中文、下划线、连字符，移除其他特殊字符
        slug = re.sub(r'[^\w\s一-鿿-]', '', slug)
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug or "untitled"

    def _deserialize_node(self, data: dict) -> NodeDefinition:
        """反序列化单个节点"""
        from core.pipeline.definition import InputMapping, TriggerConfig
        input_mappings = [
            InputMapping(
                from_node=m["from_node"], as_field=m["as_field"],
                source_field=m.get("source_field", ""),
                required=m.get("required", True),
            )
            for m in data.get("input_mappings", [])
        ]
        trigger = None
        if data.get("trigger"):
            t = data["trigger"]
            trigger = TriggerConfig(
                type=t.get("type", "on_complete"),
                source_node=t.get("source_node", ""),
                keywords=t.get("keywords", []),
                wait_all_data=t.get("wait_all_data", False),
            )
        return NodeDefinition(
            id=data["id"], type=data["type"],
            name=data.get("name", ""),
            position=data.get("position", {"x": 0, "y": 0}),
            config=data.get("config", {}),
            input_mappings=input_mappings,
            trigger=trigger,
            listener=data.get("listener", False),
        )

    # ── 序列化 / 反序列化 ──────────────────────────────────────

    def _serialize_flow(self, flow: PipelineDefinition) -> dict:
        return {
            "id": flow.id,
            "name": flow.name,
            "group": flow.group,
            "icon": flow.icon,
            "enabled": flow.enabled,
            "skill_prompt": flow.skill_prompt,
            "canvas": flow.canvas,
            "params": flow.params,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "name": n.name,
                    "position": n.position,
                    "config": n.config,
                    "input_mappings": [
                        {"from_node": m.from_node, "as_field": m.as_field,
                         "source_field": m.source_field, "required": m.required}
                        for m in n.input_mappings
                    ],
                    "trigger": {
                        "type": n.trigger.type,
                        "source_node": n.trigger.source_node,
                        "keywords": n.trigger.keywords,
                        "wait_all_data": n.trigger.wait_all_data,
                    } if n.trigger else None,
                    "listener": n.listener,
                }
                for n in flow.nodes
            ],
            "connections": [
                {
                    "id": c.id,
                    "from_node": c.from_node,
                    "from_port": c.from_port,
                    "to_node": c.to_node,
                    "to_port": c.to_port,
                    "type": c.type,
                }
                for c in flow.connections
            ],
        }

    @staticmethod
    def _deserialize_flow(data: dict) -> PipelineDefinition:
        from core.pipeline.definition import InputMapping, TriggerConfig

        nodes = []
        for nd in data.get("nodes", []):
            input_mappings = [
                InputMapping(
                    from_node=m["from_node"],
                    as_field=m["as_field"],
                    source_field=m.get("source_field", ""),
                    required=m.get("required", True),
                )
                for m in nd.get("input_mappings", [])
            ]
            trigger = None
            if nd.get("trigger"):
                t = nd["trigger"]
                trigger = TriggerConfig(
                    type=t.get("type", "on_complete"),
                    source_node=t.get("source_node", ""),
                    keywords=t.get("keywords", []),
                    wait_all_data=t.get("wait_all_data", False),
                )
            nodes.append(NodeDefinition(
                id=nd["id"],
                type=nd["type"],
                name=nd.get("name", ""),
                position=nd.get("position", {"x": 0, "y": 0}),
                config=nd.get("config", {}),
                input_mappings=input_mappings,
                trigger=trigger,
                listener=nd.get("listener", False),
            ))

        connections = [
            ConnectionDef(
                id=c["id"],
                from_node=c["from_node"],
                from_port=c.get("from_port", ""),
                to_node=c["to_node"],
                to_port=c.get("to_port", ""),
                type=c.get("type", "data"),
            )
            for c in data.get("connections", [])
        ]

        return PipelineDefinition(
            id=data["id"],
            name=data.get("name", ""),
            group=data.get("group", ""),
            icon=data.get("icon", "account_tree"),
            enabled=data.get("enabled", True),
            skill_prompt=data.get("skill_prompt", ""),
            canvas=data.get("canvas", {"width": 2000, "height": 1500}),
            params=data.get("params", {}),
            nodes=nodes,
            connections=connections,
        )


