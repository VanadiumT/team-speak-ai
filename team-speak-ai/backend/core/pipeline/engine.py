"""
Pipeline 编排引擎

核心职责：
1. 加载 Pipeline 定义（YAML 配置）
2. 管理执行实例（每个功能页可同时运行多个 execution）
3. 调度节点执行（按依赖关系和触发条件自动流转）
4. 维护 WebSocket 订阅关系（feature → [ws, ...]）
5. 对外暴露 EventEmitter 用于推送实时事件
"""

import asyncio
import logging
import uuid
from datetime import datetime

# 导入所有节点类型，确保 @register 装饰器执行
import core.nodes  # noqa: F401
from typing import Optional

from core.pipeline.definition import (
    PipelineDefinition, NodeDefinition, TriggerConfig, InputMapping
)
from core.pipeline.context import NodeContext, NodeState, NodeOutput, NodeRuntime
from core.pipeline.registry import NodeRegistry
from core.pipeline.emitter import EventEmitter
from core.logger.handler import log_pipeline_event
from core.logger.base import PipelineEvent

logger = logging.getLogger(__name__)


class PipelineInstance:
    """一次 Pipeline 执行实例"""

    def __init__(self, execution_id: str, pipeline_def: PipelineDefinition):
        self.execution_id = execution_id
        self.pipeline_def = pipeline_def
        self.node_runtimes: dict[str, NodeRuntime] = {
            n.id: NodeRuntime(node_def_id=n.id)
            for n in pipeline_def.nodes
        }
        self.status: str = "running"  # running | completed | error
        self.started_at = datetime.now()
        self.accumulated_context: dict = {
            "ocr_texts": [],
            "stt_history": [],
            "llm_messages": [],
            "skill_prompt": "",
        }

    def get_runtime(self, node_id: str) -> Optional[NodeRuntime]:
        return self.node_runtimes.get(node_id)

    def set_node_status(self, node_id: str, status: NodeState, **kwargs):
        rt = self.get_runtime(node_id)
        if rt:
            rt.status = status
            for k, v in kwargs.items():
                setattr(rt, k, v)

    def get_listener_runtimes(self) -> list[NodeRuntime]:
        return [
            rt for rt in self.node_runtimes.values()
            if any(
                n.id == rt.node_def_id and n.listener
                for n in self.pipeline_def.nodes
            )
        ]

    @property
    def all_completed(self) -> bool:
        return all(
            rt.status in (NodeState.COMPLETED, NodeState.ERROR)
            for rt in self.node_runtimes.values()
        )


class PipelineEngine:
    """Pipeline 编排引擎（全局单例）"""

    def __init__(self):
        self._definitions: dict[str, PipelineDefinition] = {}
        self._instances: dict[str, PipelineInstance] = {}
        self._ws_connections: dict[str, set] = {}  # feature_id → {ws, ...}
        self._node_registry = NodeRegistry()
        self._running_flows: set[str] = set()  # 编辑锁

    # ── 定义管理 ──

    def load_yaml(self, yaml_path: str):
        """从 YAML 加载一个 Pipeline 定义"""
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        nodes = []
        for n in data.get("nodes", []):
            trigger = None
            if "trigger" in n:
                t = n["trigger"]
                trigger = TriggerConfig(
                    type=t.get("type", "on_complete"),
                    source_node=t.get("source_node", ""),
                    keywords=t.get("keywords", []),
                )
            input_mappings = []
            for m in n.get("input_mappings", []):
                input_mappings.append(InputMapping(
                    from_node=m["from"],
                    as_field=m.get("as", m["from"]),
                    source_field=m.get("source_field", ""),
                    required=m.get("required", True),
                ))

            nodes.append(NodeDefinition(
                id=n["id"],
                type=n["type"],
                name=n.get("name", n["id"]),
                config=n.get("config", {}),
                input_mappings=input_mappings,
                trigger=trigger,
                listener=n.get("listener", False),
            ))

        pd = PipelineDefinition(
            id=data["id"],
            name=data["name"],
            group=data.get("group", ""),
            icon=data.get("icon", ""),
            nodes=nodes,
            skill_prompt=data.get("skill_prompt", ""),
        )
        self._definitions[pd.id] = pd
        logger.info(f"Pipeline loaded: {pd.id} ({pd.name}), {len(nodes)} nodes")
        return pd

    def load_definitions_from_dir(self, config_dir: str):
        """加载目录下所有 YAML 定义"""
        import os
        import glob
        for fpath in glob.glob(os.path.join(config_dir, "*.yaml")):
            self.load_yaml(fpath)
        logger.info(f"Loaded {len(self._definitions)} pipeline definitions")

    def get_definition(self, feature_id: str) -> Optional[PipelineDefinition]:
        return self._definitions.get(feature_id)

    def get_definitions(self) -> list[dict]:
        """返回给前端的序列化定义列表"""
        result = []
        for pd in self._definitions.values():
            result.append({
                "id": pd.id,
                "name": pd.name,
                "group": pd.group,
                "icon": pd.icon,
                "nodes": [
                    {
                        "id": n.id,
                        "type": n.type,
                        "name": n.name,
                        "config": n.config,
                        "listener": n.listener,
                        "trigger": {
                            "type": n.trigger.type,
                            "source_node": n.trigger.source_node,
                            "keywords": n.trigger.keywords,
                        } if n.trigger else None,
                        "input_mappings": [
                            {
                                "from_node": m.from_node,
                                "as_field": m.as_field,
                                "source_field": m.source_field,
                                "required": m.required,
                            }
                            for m in n.input_mappings
                        ],
                    }
                    for n in pd.nodes
                ],
                "skill_prompt": pd.skill_prompt,
            })
        return result

    # ── WebSocket 订阅管理 ──

    def register_ws(self, feature_id: str, ws):
        """WebSocket 订阅某个 feature 的事件"""
        if feature_id not in self._ws_connections:
            self._ws_connections[feature_id] = set()
        self._ws_connections[feature_id].add(ws)

    def unregister_ws(self, feature_id: str, ws):
        """取消订阅"""
        if feature_id in self._ws_connections:
            self._ws_connections[feature_id].discard(ws)

    def unregister_ws_all(self, ws):
        """WebSocket 断开时清理所有订阅"""
        for feature_id in list(self._ws_connections.keys()):
            self._ws_connections[feature_id].discard(ws)

    def get_ws_connections(self, feature_id: str) -> set:
        return self._ws_connections.get(feature_id, set())

    # ── 实例管理 ──

    def get_instance(self, execution_id: str) -> Optional[PipelineInstance]:
        return self._instances.get(execution_id)

    def list_instances(self, feature_id: str) -> list[PipelineInstance]:
        return [
            inst for inst in self._instances.values()
            if inst.pipeline_def.id == feature_id
        ]

    def start_pipeline(self, feature_id: str, initial_input: dict = None) -> str:
        """启动一个新的 Pipeline 执行"""
        pd = self.get_definition(feature_id)
        if not pd:
            raise ValueError(f"Unknown pipeline: {feature_id}")

        execution_id = f"{feature_id}_{uuid.uuid4().hex[:8]}"
        instance = PipelineInstance(execution_id, pd)
        self._instances[execution_id] = instance

        logger.info(f"Pipeline started: {feature_id} [{execution_id}]")
        log_pipeline_event(PipelineEvent(
            event_type="pipeline_start",
            pipeline_id=pd.id,
            execution_id=execution_id,
            data={"feature_id": feature_id},
        ))

        # 存入 skill_prompt 供 context_build 节点使用
        instance.accumulated_context["skill_prompt"] = pd.skill_prompt

        # 后台自动启动 listener 节点
        for node_def in pd.get_listener_nodes():
            asyncio.ensure_future(
                self._run_listener_node(execution_id, node_def)
            )

        return execution_id

    def start_pipeline_from_flow(self, flow_id: str, initial_input: dict = None) -> str:
        """从 FlowManager 加载流程并启动执行"""
        from core.flow.manager import get_flow_manager
        fm = get_flow_manager()
        flow = fm.load_flow(flow_id)

        # 转换为 PipelineDefinition
        pd = self._flowdef_to_pipeline_def(flow)
        self._definitions[flow_id] = pd

        # 编辑锁
        self._running_flows.add(flow_id)

        execution_id = self._start(pd, initial_input)
        return execution_id

    def is_running(self, flow_id: str) -> bool:
        return flow_id in self._running_flows

    @property
    def active_instance_count(self) -> int:
        return len(self._instances)

    def _flowdef_to_pipeline_def(self, flow) -> PipelineDefinition:
        """将 FlowDef (PipelineDefinition from JSON) 转换为引擎可用的定义"""
        nodes = []
        for n in flow.nodes:
            nodes.append(NodeDefinition(
                id=n.id, type=n.type, name=n.name,
                position=n.position, config=n.config,
                input_mappings=n.input_mappings,
                trigger=n.trigger, listener=n.listener,
            ))
        return PipelineDefinition(
            id=flow.id, name=flow.name, group=flow.group,
            icon=flow.icon, skill_prompt=flow.skill_prompt,
            canvas=flow.canvas, nodes=nodes, connections=flow.connections,
        )

    def _start(self, pd: PipelineDefinition, initial_input: dict = None) -> str:
        """内部启动方法"""
        execution_id = f"{pd.id}_{uuid.uuid4().hex[:8]}"
        instance = PipelineInstance(execution_id, pd)
        self._instances[execution_id] = instance

        logger.info(f"Pipeline started: {pd.id} [{execution_id}]")
        log_pipeline_event(PipelineEvent(
            event_type="pipeline_start",
            pipeline_id=pd.id,
            execution_id=execution_id,
            data={"feature_id": pd.id},
        ))

        instance.accumulated_context["skill_prompt"] = pd.skill_prompt

        for node_def in pd.get_listener_nodes():
            asyncio.ensure_future(
                self._run_listener_node(execution_id, node_def)
            )

        return execution_id

    def delete_instance(self, execution_id: str):
        """删除 Pipeline 实例，同时释放编辑锁"""
        instance = self._instances.pop(execution_id, None)
        if instance:
            log_pipeline_event(PipelineEvent(
                event_type="pipeline_deleted",
                pipeline_id=instance.pipeline_def.id,
                execution_id=execution_id,
            ))
            # 释放编辑锁
            self._running_flows.discard(instance.pipeline_def.id)
        logger.info(f"Pipeline instance deleted: {execution_id}")

    # ── 节点执行 ──

    async def execute_node(self, execution_id: str, node_id: str, user_input: dict = None):
        """执行一个 action 节点"""
        instance = self.get_instance(execution_id)
        if not instance:
            logger.warning(f"Instance not found: {execution_id}")
            return

        pd = instance.pipeline_def
        node_def = pd.get_node(node_id)
        if not node_def:
            logger.warning(f"Node not found: {node_id}")
            return

        node_cls = self._node_registry.create(node_def.type, node_def.config)
        runtime = instance.get_runtime(node_id)

        # 收集输入
        inputs = {}
        for mapping in node_def.input_mappings:
            source_rt = instance.get_runtime(mapping.from_node)
            if source_rt and source_rt.output:
                source_key = mapping.source_field or mapping.as_field
                val = source_rt.output.data.get(source_key)
                if val is not None:
                    inputs[mapping.as_field] = val
                elif mapping.required:
                    await self._fail_node(instance, node_id, f"Missing input: {mapping.as_field}")
                    return

        # 用户输入覆盖
        if user_input:
            inputs.update(user_input)

        # 构建上下文
        ctx = NodeContext(
            pipeline_id=pd.id,
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_def.type,
            node_config=node_def.config,
            inputs=inputs,
            accumulated_context=instance.accumulated_context,
        )

        emit = EventEmitter(self, pd.id)

        # 执行
        runtime.status = NodeState.PROCESSING
        await emit.emit_node_update(node_id, "processing", f"执行中...")
        await emit.emit_node_log_entry(node_id, "info", f"开始执行: {node_def.name}")

        log_pipeline_event(PipelineEvent(
            event_type="node_start",
            pipeline_id=pd.id,
            execution_id=execution_id,
            node_id=node_id,
            data={"node_type": node_def.type},
        ))

        try:
            output = await node_cls.execute(ctx, emit)
            runtime.status = NodeState.COMPLETED
            runtime.output = output
            runtime.summary = str(output.data)[:80] if output.data else "完成"

            await emit.emit_node_complete(node_id, output.data)
            await emit.emit_node_log_entry(node_id, "success", f"完成: {runtime.summary}")
            log_pipeline_event(PipelineEvent(
                event_type="node_complete",
                pipeline_id=pd.id,
                execution_id=execution_id,
                node_id=node_id,
                data={"summary": runtime.summary},
            ))

            # 累积到 instance context
            for k, v in output.data.items():
                if k in instance.accumulated_context:
                    if isinstance(instance.accumulated_context[k], list):
                        instance.accumulated_context[k].append(v)
                    else:
                        instance.accumulated_context[k] = v

            # 自动触发下游（如果有 next_on_complete 配置）
            if output.trigger_next:
                await self._trigger_downstream(instance, node_id)

        except Exception as e:
            logger.exception(f"Node {node_id} execution error")
            await self._fail_node(instance, node_id, str(e), emit)

    async def _run_listener_node(self, execution_id: str, node_def: NodeDefinition):
        """后台运行常驻监听节点（如 stt_listen），循环监听"""
        instance = self.get_instance(execution_id)
        if not instance:
            return

        while True:
            node_cls = self._node_registry.create(node_def.type, node_def.config)
            runtime = instance.get_runtime(node_def.id)

            # 重置运行时状态（保留 accumulated_context）
            runtime.output = None
            runtime.error = None
            runtime.summary = ""
            runtime.data = {}

            ctx = NodeContext(
                pipeline_id=instance.pipeline_def.id,
                execution_id=execution_id,
                node_id=node_def.id,
                node_type=node_def.type,
                node_config=node_def.config,
                inputs={},
                accumulated_context=instance.accumulated_context,
            )
            emit = EventEmitter(self, instance.pipeline_def.id)

            runtime.status = NodeState.PROCESSING
            await emit.emit_node_update(node_def.id, "listening", "监听中...")
            await emit.emit_node_log_entry(node_def.id, "info", "开始监听...")

            log_pipeline_event(PipelineEvent(
                event_type="listener_start",
                pipeline_id=instance.pipeline_def.id,
                execution_id=execution_id,
                node_id=node_def.id,
            ))

            try:
                output = await node_cls.execute(ctx, emit)
                runtime.status = NodeState.COMPLETED
                runtime.output = output
                await emit.emit_node_complete(node_def.id, output.data)

                # 累积到 context
                for k, v in output.data.items():
                    if isinstance(instance.accumulated_context.get(k), list):
                        instance.accumulated_context[k].append(v)
                    else:
                        instance.accumulated_context[k] = v

                # 触发下游（context_build → llm → tts → ts_output）
                await self._trigger_downstream(instance, node_def.id)

                # 继续下一轮监听
                log_pipeline_event(PipelineEvent(
                    event_type="listener_cycle",
                    pipeline_id=instance.pipeline_def.id,
                    execution_id=execution_id,
                    node_id=node_def.id,
                ))
                logger.info(f"Listener {node_def.id} loop next round")

            except asyncio.CancelledError:
                log_pipeline_event(PipelineEvent(
                    event_type="listener_cancelled",
                    pipeline_id=instance.pipeline_def.id,
                    execution_id=execution_id,
                    node_id=node_def.id,
                ))
                logger.info(f"Listener {node_def.id} cancelled")
                break
            except Exception as e:
                logger.exception(f"Listener node {node_def.id} error")
                await self._fail_node(instance, node_def.id, str(e), emit)
                break

    async def _trigger_downstream(self, instance: PipelineInstance, completed_node_id: str):
        """节点完成后，自动触发符合条件的下游节点"""
        pd = instance.pipeline_def
        for node_def in pd.nodes:
            if node_def.listener:
                continue
            if node_def.trigger and node_def.trigger.source_node == completed_node_id:
                # 触发条件匹配
                await self.execute_node(instance.execution_id, node_def.id)
                return

    async def _fail_node(self, instance: PipelineInstance, node_id: str, error: str, emit: EventEmitter = None):
        runtime = instance.get_runtime(node_id)
        if runtime:
            runtime.status = NodeState.ERROR
            runtime.error = error
        if emit:
            await emit.emit_node_error(node_id, error)
        log_pipeline_event(PipelineEvent(
            event_type="node_error",
            pipeline_id=instance.pipeline_def.id,
            execution_id=instance.execution_id,
            node_id=node_id,
            data={"error": error},
        ))
        logger.error(f"Node {node_id} failed: {error}")

    # ── 前端消息处理 ──

    async def handle_node_action(self, data: dict):
        """处理前端发来的 node_action 消息"""
        feature_id = data.get("feature_id", "")
        node_id = data.get("node_id", "")
        action = data.get("action", "")
        payload = data.get("payload", {})

        # 查找或创建 instance
        instances = self.list_instances(feature_id)
        if not instances:
            execution_id = self.start_pipeline(feature_id)
        else:
            execution_id = instances[-1].execution_id

        pd = self.get_definition(feature_id)
        node_def = pd.get_node(node_id) if pd else None

        if action == "upload":
            # 上传文件 → 存到 instance context + 触发节点
            instance = self.get_instance(execution_id)
            if instance and payload.get("file"):
                instance.accumulated_context["uploaded_file"] = payload["file"]
            await self.execute_node(execution_id, node_id, {"file": payload.get("file")})

        elif action == "trigger":
            # 直接触发节点执行
            await self.execute_node(execution_id, node_id)

        elif action == "restart":
            # 重新开始 → 删除旧的 instance，创建新的
            self.delete_instance(execution_id)
            self.start_pipeline(feature_id)

        elif action == "input_text":
            # 文本输入
            await self.execute_node(execution_id, node_id, {"text": payload.get("text", "")})


engine = PipelineEngine()
