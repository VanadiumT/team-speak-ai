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
from typing import Callable, Optional

from core.pipeline.definition import (
    PipelineDefinition, NodeDefinition, TriggerConfig, InputMapping,
    port_input_key, port_output_key,
)
from core.pipeline.context import NodeContext, NodeState, NodeOutput, NodeRuntime, _STREAM_END
from core.pipeline.registry import NodeRegistry
from core.pipeline.emitter import EventEmitter
from core.nodes.base import BaseNode
from core.logger.handler import log_pipeline_event
from core.logger.base import PipelineEvent
from core.logger.context import trace_context
from core.exceptions import (
    NodeExecutionError,
    NodeConfigError,
    StreamingError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderAuthError,
)

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
        self.listener_tasks: list[asyncio.Task] = []  # 后台监听任务引用
        self.use_envelope: bool = False  # 实例级信封协议标志
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
        self._node_registry = NodeRegistry()
        self._running_flows: set[str] = set()  # 编辑锁

        self._flow_broadcast_fn: dict[str, Callable] = {}  # flow_id → async broadcast_fn
        self._lock = asyncio.Lock()  # 保护 check-then-act 临界区
        self._pending_executions: set[tuple[str, str]] = set()  # (execution_id, node_id) 防重复触发

    # ── 定义管理 ──

    def get_definition(self, flow_id: str) -> Optional[PipelineDefinition]:
        return self._definitions.get(flow_id)

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

    # ── 广播管理 ──

    def register_flow_broadcast_fn(self, flow_id: str, fn):
        """注册 flow 级别的广播函数（由 ws_main 的 _flow_subscribers 使用）"""
        self._flow_broadcast_fn[flow_id] = fn

    def unregister_flow_broadcast_fn(self, flow_id: str):
        """取消注册 flow 广播函数"""
        self._flow_broadcast_fn.pop(flow_id, None)

    async def broadcast_to_flow(self, flow_id: str, action: str, params: dict):
        """广播到指定 flow 的所有 WS 客户端（包括 /ws 订阅者）"""
        # 先尝试匹配精确 flow_id，再尝试 __all__ 通配
        fn = self._flow_broadcast_fn.get(flow_id) or self._flow_broadcast_fn.get("__all__")
        if fn:
            try:
                await fn(flow_id, action, params)
            except Exception as e:
                logger.warning(f"Flow broadcast failed for {flow_id}: {e}")

    # ── 实例管理 ──

    def get_instance(self, execution_id: str) -> Optional[PipelineInstance]:
        return self._instances.get(execution_id)

    def list_instances(self, flow_id: str) -> list[PipelineInstance]:
        return [
            inst for inst in self._instances.values()
            if inst.pipeline_def.id == flow_id
        ]

    def start_pipeline(self, flow_id: str, initial_input: dict = None) -> str:
        """启动一个新的 Pipeline 执行"""
        pd = self.get_definition(flow_id)
        if not pd:
            raise ValueError(f"Unknown pipeline: {flow_id}")

        execution_id = f"{flow_id}_{uuid.uuid4().hex[:8]}"
        instance = PipelineInstance(execution_id, pd)
        self._instances[execution_id] = instance

        logger.info(f"Pipeline started: {flow_id} [{execution_id}]")
        log_pipeline_event(PipelineEvent(
            event_type="pipeline_start",
            flow_id=pd.id,
            execution_id=execution_id,
            data={"flow_id": flow_id},
        ))

        # 存入 skill_prompt 供 context_build 节点使用
        instance.accumulated_context["skill_prompt"] = pd.skill_prompt

        # 后台自动启动 listener 节点
        for node_def in pd.get_listener_nodes():
            asyncio.ensure_future(
                self._run_listener_node(execution_id, node_def)
            )

        return execution_id

    async def start_pipeline_from_flow(self, flow_id: str, initial_input: dict = None) -> str:
        """从 FlowManager 加载流程并启动执行"""
        async with self._lock:
            if flow_id in self._running_flows:
                raise RuntimeError(f"Flow '{flow_id}' is already running. Stop it first.")
            self._running_flows.add(flow_id)

        from core.app_context import get_app_context
        fm = get_app_context().flow_manager
        flow = fm.load_flow(flow_id)

        pd = self._flowdef_to_pipeline_def(flow)
        self._definitions[flow_id] = pd

        execution_id = self._start(pd, initial_input)
        # 设置信封协议标志在实例级别
        instance = self._instances.get(execution_id)
        if instance:
            instance.use_envelope = True
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
            canvas=flow.canvas, params=flow.params,
            nodes=nodes, connections=flow.connections,
        )

    def _start(self, pd: PipelineDefinition, initial_input: dict = None) -> str:
        """内部启动方法"""
        execution_id = f"{pd.id}_{uuid.uuid4().hex[:8]}"
        instance = PipelineInstance(execution_id, pd)
        self._instances[execution_id] = instance

        logger.info(f"Pipeline started: {pd.id} [{execution_id}]")
        log_pipeline_event(PipelineEvent(
            event_type="pipeline_start",
            flow_id=pd.id,
            execution_id=execution_id,
            data={"flow_id": pd.id},
        ))

        instance.accumulated_context["skill_prompt"] = pd.skill_prompt

        # 加载流程参数到 accumulated_context（供 flow_var_read 等节点读取）
        for key, value in pd.params.items():
            instance.accumulated_context[key] = value

        # 同步已有连线到执行系统（trigger / input_mapping）
        _sync_connections_to_nodes(pd)

        for node_def in pd.get_listener_nodes():
            task = asyncio.ensure_future(
                self._run_listener_node(execution_id, node_def)
            )
            instance.listener_tasks.append(task)

        # 找到所有 auto_run 的 start 节点，并行执行
        start_nodes = [
            n for n in pd.nodes
            if n.type == "start" and n.config.get("auto_run", True)
        ]
        if start_nodes:
            logger.info(f"Executing {len(start_nodes)} start node(s) for {pd.id}")
            async def run_start_nodes():
                try:
                    await asyncio.gather(*(
                        self.execute_node(execution_id, n.id)
                        for n in start_nodes
                    ))
                except Exception as e:
                    logger.exception(f"Start node execution error for {pd.id}: {e}")
                finally:
                    # 检查是否所有非监听节点已完成（有等待中的节点则不结束）
                    inst = self.get_instance(execution_id)
                    all_done = inst and all(
                        rt.status in (NodeState.COMPLETED, NodeState.ERROR)
                        for nid, rt in inst.node_runtimes.items()
                        if not any(n.listener for n in pd.nodes if n.id == nid)
                    )
                    if all_done:
                        self._running_flows.discard(pd.id)
                        try:
                            emit = EventEmitter(self, pd.id)
                            await emit.emit_pipeline_complete(execution_id)
                        except Exception as e2:
                            logger.error(f"Failed to emit pipeline.completed for {pd.id}: {e2}")
            asyncio.ensure_future(run_start_nodes())
        else:
            # 无 start 节点也无 listener → 立即完成
            if not pd.get_listener_nodes():
                self._running_flows.discard(pd.id)

        return execution_id

    def delete_instance(self, execution_id: str):
        """删除 Pipeline 实例，同时释放编辑锁并取消后台任务"""
        instance = self._instances.pop(execution_id, None)
        if instance:
            # 取消所有后台监听任务
            for task in instance.listener_tasks:
                if not task.done():
                    task.cancel()
            log_pipeline_event(PipelineEvent(
                event_type="pipeline_deleted",
                flow_id=instance.pipeline_def.id,
                execution_id=execution_id,
            ))
            # 释放编辑锁
            self._running_flows.discard(instance.pipeline_def.id)
        logger.info(f"Pipeline instance deleted: {execution_id}")

    # ── 流式执行方法 ──

    @staticmethod
    def _supports_streaming(node_cls) -> bool:
        """检查节点是否覆写了 execute_stream"""
        return type(node_cls).execute_stream is not BaseNode.execute_stream

    def _build_node_context(self, instance: 'PipelineInstance', node_def: NodeDefinition) -> Optional[NodeContext]:
        """收集上游输入 + 构建 NodeContext。供 batch 和 streaming 两条路径复用。
        若 required 输入缺失则返回 None。"""
        pd = instance.pipeline_def
        inputs = {}
        for mapping in node_def.input_mappings:
            source_rt = instance.get_runtime(mapping.from_node)
            if source_rt and source_rt.output:
                source_key = mapping.source_field or mapping.as_field
                val = source_rt.output.data.get(source_key)
                if val is None and source_rt.output.data:
                    for k, v in source_rt.output.data.items():
                        if v is not None:
                            val = v
                            break
                if val is not None:
                    inputs[mapping.as_field] = val
                elif mapping.required:
                    return None  # 调用方负责 fail_node
        return NodeContext(
            flow_id=pd.id, execution_id=instance.execution_id,
            node_id=node_def.id, node_type=node_def.type,
            node_config=node_def.config, inputs=inputs,
            accumulated_context=instance.accumulated_context,
        )

    def _detect_streaming_chain(self, instance: 'PipelineInstance', start_id: str) -> list:
        """沿 stream-* 端口 data 连线追踪流式链，返回 [A, B, ...]。
        要求链长 >= 2 且每个节点支持 execute_stream。否则返回空列表。"""
        pd = instance.pipeline_def
        chain = [start_id]
        current = start_id

        while True:
            nd = pd.get_node(current)
            if nd is None:
                break
            nc = self._node_registry.create(nd.type, nd.config)
            if not self._supports_streaming(nc):
                break
            next_id = None
            for conn in pd.connections:
                if (conn.from_node == current and conn.type == "data"
                        and conn.from_port.startswith("stream-")
                        and conn.to_port.startswith("stream-")):
                    tgt = pd.get_node(conn.to_node)
                    if tgt is None:
                        continue
                    tc = self._node_registry.create(tgt.type, tgt.config)
                    if self._supports_streaming(tc) and conn.to_node not in chain:
                        next_id = conn.to_node
                        break
            if next_id:
                chain.append(next_id)
                current = next_id
            else:
                break

        if len(chain) < 2:
            return []

        # 校验链的第一个节点是否有流式上游输入
        # 如果没有 stream-input 来源，不应走流式链路（会因 stream_input=None 崩溃）
        first_nd = pd.get_node(chain[0])
        if first_nd and first_nd.input_mappings:
            has_stream_input = False
            for m in first_nd.input_mappings:
                for conn in pd.connections:
                    if (conn.to_node == chain[0] and conn.from_node == m.from_node
                            and conn.to_port.startswith("stream-")
                            and conn.from_port.startswith("stream-")):
                        has_stream_input = True
                        break
                if has_stream_input:
                    break
            if not has_stream_input:
                return []

        return chain

    def _finalize_node_output(self, instance: 'PipelineInstance', node_id: str,
                               output: NodeOutput, runtime: NodeRuntime):
        """设置 runtime 为 COMPLETED，将 final 输出累积到 instance context"""
        runtime.output = output
        runtime.status = NodeState.COMPLETED
        runtime.summary = (
            str(output.data.get("text", output.data.get("value", "")))[:40]
            if output.data else "完成"
        )
        for k, v in output.data.items():
            if k in instance.accumulated_context:
                acc = instance.accumulated_context[k]
                if isinstance(acc, list):
                    acc.append(v)
                else:
                    instance.accumulated_context[k] = v

    async def _execute_chain_streaming(self, instance: 'PipelineInstance', chain: list):
        """并行执行流式链：producer → Queue → consumer → Queue → ..."""
        pd = instance.pipeline_def
        n = len(chain)
        channels = [asyncio.Queue(maxsize=8) for _ in range(n - 1)]

        async def _run_producer(node_id: str, out_ch: asyncio.Queue):
            nd = pd.get_node(node_id)
            nc = self._node_registry.create(nd.type, nd.config)
            rt = instance.get_runtime(node_id)
            rt.status = NodeState.PROCESSING
            emit = EventEmitter(self, pd.id)

            ctx = self._build_node_context(instance, nd)
            if ctx is None:
                missing = next((m.as_field for m in nd.input_mappings
                                if m.required and not instance.get_runtime(m.from_node)), "?")
                await self._fail_node(instance, node_id, f"Missing input: {missing}", emit)
                await out_ch.put(_STREAM_END)
                raise RuntimeError(f"Missing required input for {node_id}")

            await emit.emit_node_update(node_id, NodeState.PROCESSING, "流式处理中...")

            try:
                async for output in nc.execute_stream(ctx, emit):
                    await out_ch.put(output)
                    if not output.final:
                        rt.output = output
                await out_ch.put(_STREAM_END)
            except Exception as e:
                logger.exception(f"Streaming producer {node_id} error")
                await self._fail_node(instance, node_id, str(e), emit)
                await out_ch.put(_STREAM_END)  # 通知 consumer 结束
                raise

        async def _run_consumer(node_id: str, in_ch: asyncio.Queue, out_ch: asyncio.Queue = None):
            nd = pd.get_node(node_id)
            nc = self._node_registry.create(nd.type, nd.config)
            rt = instance.get_runtime(node_id)
            rt.status = NodeState.PROCESSING
            emit = EventEmitter(self, pd.id)

            ctx = self._build_node_context(instance, nd)
            if ctx is None:
                ctx = NodeContext(
                    flow_id=pd.id, execution_id=instance.execution_id,
                    node_id=node_id, node_type=nd.type,
                    node_config=nd.config, inputs={},
                    accumulated_context=instance.accumulated_context,
                )
            ctx.stream_input = in_ch

            await emit.emit_node_update(node_id, NodeState.PROCESSING, "流式处理中...")

            try:
                async for output in nc.execute_stream(ctx, emit):
                    if out_ch is not None:
                        await out_ch.put(output)
                    if not output.final:
                        rt.output = output
                    else:
                        self._finalize_node_output(instance, node_id, output, rt)
                if out_ch is not None:
                    await out_ch.put(_STREAM_END)
            except Exception as e:
                logger.exception(f"Streaming consumer {node_id} error")
                await self._fail_node(instance, node_id, str(e), emit)
                if out_ch is not None:
                    await out_ch.put(_STREAM_END)
                raise

        try:
            async with asyncio.TaskGroup() as tg:
                for i, node_id in enumerate(chain):
                    out_ch = channels[i] if i < n - 1 else None
                    if i == 0:
                        tg.create_task(_run_producer(node_id, out_ch))
                    else:
                        tg.create_task(_run_consumer(node_id, channels[i - 1], out_ch))
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error(f"Streaming chain error: {exc}")

        # 流式链结束后，触发链中所有节点的非流式下游
        for node_id in chain:
            await self._trigger_downstream(instance, node_id)

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

        ctx = self._build_node_context(instance, node_def)
        if ctx is None:
            await self._fail_node(instance, node_id, "Missing required input")
            return

        # 用户输入覆盖
        if user_input:
            ctx.inputs.update(user_input)

        runtime = instance.get_runtime(node_id)

        emit = EventEmitter(self, pd.id)

        # 执行
        runtime.status = NodeState.PROCESSING
        await emit.emit_node_update(node_id, NodeState.PROCESSING, f"执行中...")
        await emit.emit_node_log_entry(node_id, "info", f"开始执行: {node_def.name}")

        log_pipeline_event(PipelineEvent(
            event_type="node_start",
            flow_id=pd.id,
            execution_id=execution_id,
            node_id=node_id,
            data={"node_type": node_def.type},
        ))

        try:
            output = await node_cls.execute(ctx, emit)
            runtime.output = output

            if output.trigger_next:
                runtime.status = NodeState.COMPLETED
                runtime.summary = str(output.data.get("text", output.data.get("value", "")))[:40] if output.data else "完成"

                await emit.emit_node_complete(node_id, output.data)
                await emit.emit_node_log_entry(node_id, "success", f"完成: {runtime.summary}")
                log_pipeline_event(PipelineEvent(
                    event_type="node_complete",
                    flow_id=pd.id,
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

                # 自动触发下游
                await self._trigger_downstream(instance, node_id)

        except NodeExecutionError as e:
            logger.error(f"[Engine:{pd.id}:{execution_id}] Node execution error: {e.message}")
            await self._fail_node(instance, node_id, e.to_dict(), emit)
        except NodeConfigError as e:
            logger.error(f"[Engine:{pd.id}:{execution_id}] Node config error: {e.message}")
            await self._fail_node(instance, node_id, e.to_dict(), emit)
        except (ProviderConnectionError, ProviderTimeoutError, ProviderAuthError) as e:
            logger.error(f"[Engine:{pd.id}:{execution_id}] Provider error: {e.message}")
            await self._fail_node(instance, node_id, e.to_dict(), emit)
        except Exception as e:
            logger.exception(f"[Engine:{pd.id}:{execution_id}] Unexpected error in node {node_id}")
            await self._fail_node(instance, node_id, {"error_code": "INTERNAL_ERROR", "message": str(e)}, emit)

    async def _run_listener_node(self, execution_id: str, node_def: NodeDefinition):
        """后台运行常驻监听节点（如 stt_listen），循环监听"""
        instance = self.get_instance(execution_id)
        if not instance:
            return

        loopback = node_def.config.get("loopback", False)
        if loopback:
            from api.routes.ws_teamspeak import ts_client
            ts_client.loopback_enabled = True
            logger.info(f"Loopback early-enabled by listener {node_def.id}")

        try:
            while True:
                node_cls = self._node_registry.create(node_def.type, node_def.config)
                runtime = instance.get_runtime(node_def.id)

                # 重置运行时状态（保留 accumulated_context）
                runtime.output = None
                runtime.error = None
                runtime.summary = ""
                runtime.data = {}

                ctx = NodeContext(
                    flow_id=instance.pipeline_def.id,
                    execution_id=execution_id,
                    node_id=node_def.id,
                    node_type=node_def.type,
                    node_config=node_def.config,
                    inputs={},
                    accumulated_context=instance.accumulated_context,
                )
                emit = EventEmitter(self, instance.pipeline_def.id)

                runtime.status = NodeState.PROCESSING
                await emit.emit_node_update(node_def.id, NodeState.LISTENING, "监听中...")
                await emit.emit_node_log_entry(node_def.id, "info", "开始监听...")

                log_pipeline_event(PipelineEvent(
                    event_type="listener_start",
                    flow_id=instance.pipeline_def.id,
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

                    # 提前设回 PROCESSING，避免下游链完成时误判为流程结束
                    runtime.status = NodeState.PROCESSING

                    # 触发下游（context_build → llm → tts → ts_output）
                    await self._trigger_downstream(instance, node_def.id)

                    # 继续下一轮监听
                    log_pipeline_event(PipelineEvent(
                        event_type="listener_cycle",
                        flow_id=instance.pipeline_def.id,
                        execution_id=execution_id,
                        node_id=node_def.id,
                    ))
                    logger.info(f"Listener {node_def.id} loop next round")

                except asyncio.CancelledError:
                    log_pipeline_event(PipelineEvent(
                        event_type="listener_cancelled",
                        flow_id=instance.pipeline_def.id,
                        execution_id=execution_id,
                        node_id=node_def.id,
                    ))
                    logger.info(f"Listener {node_def.id} cancelled")
                    break
                except (ProviderTimeoutError, ProviderConnectionError) as e:
                    # 瞬态故障：记录警告但继续循环
                    logger.warning(f"Listener {node_def.id} transient error: {e.message}, retrying...")
                    await emit.emit_node_log_entry(node_def.id, "warning", f"瞬态错误: {e.message}，继续监听...")
                    continue
                except NodeExecutionError as e:
                    logger.error(f"Listener {node_def.id} execution error: {e.message}")
                    await self._fail_node(instance, node_def.id, e.to_dict(), emit)
                    break
                except Exception as e:
                    logger.exception(f"Listener {node_def.id} unexpected error")
                    await self._fail_node(instance, node_def.id, {"error_code": "INTERNAL_ERROR", "message": str(e)}, emit)
                    break
        finally:
            if loopback:
                from api.routes.ws_teamspeak import ts_client
                ts_client.loopback_enabled = False
                logger.info(f"Loopback disabled by listener {node_def.id}")

    async def _trigger_downstream(self, instance: PipelineInstance, completed_node_id: str):
        """节点完成后，自动触发下游。

        规则:
        - 有 trigger → 以 trigger 为准，不等 data
        - 无 trigger → 等所有 data 上游完成才触发一次

        使用 _lock 防止多个完成节点同时触发同一下游节点。
        """
        async with self._lock:
            pd = instance.pipeline_def
            triggered = set()
            logger.info(f"_trigger_downstream: completed={completed_node_id}")

            def _all_data_ready(nd: NodeDefinition) -> bool:
                for m in nd.input_mappings:
                    if m.from_node == completed_node_id:
                        continue  # 刚刚完成的节点，始终视为就绪
                    src_rt = instance.get_runtime(m.from_node)
                    if not src_rt or src_rt.status != NodeState.COMPLETED:
                        return False
                return True

            for node_def in pd.nodes:
                if node_def.listener:
                    continue

                if node_def.trigger:
                    # 有 trigger：只看 trigger 信号
                    if node_def.trigger.source_node == completed_node_id:
                        triggered.add(node_def.id)
                else:
                    # 无 trigger：等全部 data 上游都完成才触发
                    if node_def.input_mappings and _all_data_ready(node_def):
                        is_source = any(m.from_node == completed_node_id for m in node_def.input_mappings)
                        if is_source:
                            triggered.add(node_def.id)
                            logger.info(f"_trigger_downstream: triggering={node_def.id} from {completed_node_id}")

            # 去重：过滤掉已在执行中的下游节点
            deduped = set()
            for nid in triggered:
                key = (instance.execution_id, nid)
                if key in self._pending_executions:
                    logger.info(f"_trigger_downstream: skip {nid} (already pending)")
                    continue
                self._pending_executions.add(key)
                deduped.add(nid)

        logger.info(f"_trigger_downstream: triggered set={deduped}")
        streaming_handled = set()

        # 先从完成节点（生产者）开始检测流式链
        chain = self._detect_streaming_chain(instance, completed_node_id)
        if chain:
            await self._execute_chain_streaming(instance, chain)
            streaming_handled.update(chain)

        for nid in deduped:
            if nid in streaming_handled:
                self._pending_executions.discard((instance.execution_id, nid))
                continue
            try:
                await self.execute_node(instance.execution_id, nid)
            finally:
                self._pending_executions.discard((instance.execution_id, nid))

        # 检查是否所有非监听节点已完成，且所有监听节点已终止
        all_non_listeners_done = all(
            rt.status in (NodeState.COMPLETED, NodeState.ERROR)
            for nid, rt in instance.node_runtimes.items()
            if not any(n.listener for n in pd.nodes if n.id == nid)
        )
        listeners_all_done = all(
            rt.status in (NodeState.COMPLETED, NodeState.ERROR)
            for nid, rt in instance.node_runtimes.items()
            if any(n.listener for n in pd.nodes if n.id == nid)
        )
        if all_non_listeners_done and listeners_all_done:
            self._running_flows.discard(pd.id)
            emit = EventEmitter(self, pd.id)
            await emit.emit_pipeline_complete(instance.execution_id)

    async def _fail_node(self, instance: PipelineInstance, node_id: str, error: dict | str, emit: EventEmitter = None):
        """统一节点失败处理

        Args:
            error: 可以是 str（旧格式）或 dict（新结构化格式，含 error_code, message, context 等）
        """
        if isinstance(error, dict):
            error_msg = error.get("message", str(error))
            error_data = error
        else:
            error_msg = str(error)
            error_data = {"error": error_msg}

        runtime = instance.get_runtime(node_id)
        if runtime:
            runtime.status = NodeState.ERROR
            runtime.error = error_msg
        if emit:
            await emit.emit_node_error(node_id, error_data)
        log_pipeline_event(PipelineEvent(
            event_type="node_error",
            flow_id=instance.pipeline_def.id,
            execution_id=instance.execution_id,
            node_id=node_id,
            data=error_data,
        ))
        logger.error(f"Node {node_id} failed: {error_msg}")

    # ── 前端消息处理 ──

    async def handle_node_action(self, data: dict):
        """处理前端发来的 node_action 消息"""
        flow_id = data.get("flow_id", "")
        node_id = data.get("node_id", "")
        action = data.get("action", "")
        payload = data.get("payload", {})

        # 查找或创建 instance（加锁防并发重复创建）
        async with self._lock:
            instances = self.list_instances(flow_id)
            if not instances:
                execution_id = self.start_pipeline(flow_id)
            else:
                execution_id = instances[-1].execution_id

        pd = self.get_definition(flow_id)
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
            self.start_pipeline(flow_id)

        elif action == "input_text":
            # 文本输入
            await self.execute_node(execution_id, node_id, {"text": payload.get("text", "")})




def _sync_connections_to_nodes(pd: PipelineDefinition) -> None:
    """将 connections[] 同步到节点的 trigger / input_mapping（兼容已有流程）"""
    from core.pipeline.definition import InputMapping, TriggerConfig
    for conn in pd.connections:
        target = pd.get_node(conn.to_node)
        if not target:
            continue
        if conn.type == "event":
            if not target.trigger or target.trigger.source_node != conn.from_node:
                target.trigger = TriggerConfig(
                    type="on_complete",
                    source_node=conn.from_node,
                )
        elif conn.type == "data":
            as_field = port_input_key(conn.to_port)
            source_field = port_output_key(conn.from_port)
            existing = next((m for m in target.input_mappings
                           if m.from_node == conn.from_node and m.as_field == as_field), None)
            if existing:
                existing.source_field = source_field
            else:
                target.input_mappings.append(InputMapping(
                    from_node=conn.from_node,
                    as_field=as_field,
                    source_field=source_field,
                ))


engine = PipelineEngine()
