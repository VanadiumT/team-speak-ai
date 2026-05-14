"""Start 节点测试 — 执行 + IO 端口"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.nodes.start_node import StartNode
from core.pipeline.context import NodeOutput
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return StartNode({"auto_run": True, "init_params": {}})


class TestStartNodePorts:
    """Start 节点 IO 端口定义测试"""

    def test_registered(self):
        assert "start" in NodeRegistry.list_types()

    def test_no_input_ports(self):
        td = NodeRegistry.get_type_def("start")
        assert len(td.ports.inputs) == 0

    def test_event_output_port(self):
        td = NodeRegistry.get_type_def("start")
        out = next(p for p in td.ports.outputs if p.id == "event-out")
        assert out.data_type == "event"
        assert out.visibility == "always"
        assert out.position.side == "right"

    def test_data_output_port(self):
        td = NodeRegistry.get_type_def("start")
        out = next(p for p in td.ports.outputs if p.id == "data-out")
        assert out.data_type == "any"
        assert out.visibility == "on-demand"


class TestStartNodeExecute:
    """Start 节点执行逻辑测试"""

    @pytest.mark.asyncio
    async def test_execute_no_params(self, node, make_context, mock_emit):
        ctx = make_context(node_type="start", node_config={"auto_run": True, "init_params": {}})
        result = await node.execute(ctx, mock_emit)
        assert isinstance(result, NodeOutput)
        assert result.trigger_next is True
        assert result.data == {"params": {}}

    @pytest.mark.asyncio
    async def test_execute_with_params(self, node, make_context, mock_emit, mock_app_context, tmp_data):
        # 先创建 flow 文件，因为 StartNode 会调用 fm.update_flow_params
        from core.flow.manager import FlowManager
        fm = FlowManager(str(tmp_data))
        fm.create_flow("test_flow")

        ctx = make_context(
            node_type="start",
            node_config={"auto_run": True, "init_params": {"greeting": "你好", "lang": "zh"}},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["params"] == {"greeting": "你好", "lang": "zh"}
        assert ctx.accumulated_context["greeting"] == "你好"
        assert ctx.accumulated_context["lang"] == "zh"

    @pytest.mark.asyncio
    async def test_execute_emits_status(self, node, make_context, mock_emit):
        ctx = make_context(node_type="start", node_config={"auto_run": True, "init_params": {}})
        await node.execute(ctx, mock_emit)
        # 应该调用了 emit_node_status_changed
        assert mock_emit.emit_node_status_changed.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_emits_log(self, node, make_context, mock_emit):
        ctx = make_context(node_type="start")
        await node.execute(ctx, mock_emit)
        mock_emit.emit_node_log_entry.assert_called_once()
