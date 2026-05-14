"""DisplayText 节点测试 — 执行 + IO 端口"""

import pytest
from core.nodes.display_text_node import DisplayTextNode
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return DisplayTextNode({"text": "", "mode": "passthrough"})


class TestDisplayTextPorts:
    def test_registered(self):
        assert "display_text" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("display_text")
        ids = [p.id for p in td.ports.inputs]
        assert "text-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("display_text")
        ids = [p.id for p in td.ports.outputs]
        assert "text-out" in ids
        assert "done" in ids

    def test_text_out_type(self):
        td = NodeRegistry.get_type_def("display_text")
        out = next(p for p in td.ports.outputs if p.id == "text-out")
        assert out.data_type == "string"


class TestDisplayTextPassthrough:
    @pytest.mark.asyncio
    async def test_passthrough_upstream_text(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"mode": "passthrough"},
            inputs={"text": "上游文本"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "上游文本"
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_passthrough_no_upstream_uses_config(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "静态文本", "mode": "passthrough"},
            inputs={},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "静态文本"

    @pytest.mark.asyncio
    async def test_static_mode_uses_config(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "配置文本", "mode": "static"},
            inputs={"text": "上游文本"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "配置文本"


class TestDisplayTextVarResolution:
    @pytest.mark.asyncio
    async def test_resolve_param_var(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "值=$param.key", "mode": "static"},
            accumulated_context={"key": "hello"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "值=hello"

    @pytest.mark.asyncio
    async def test_resolve_sys_var(self, node, make_context, mock_emit, mock_app_context):
        mock_app_context.sys_var_manager.set("sys_key", "sys_val")
        ctx = make_context(
            node_config={"text": "系统=$sys.sys_key", "mode": "static"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "系统=sys_val"

    @pytest.mark.asyncio
    async def test_unresolved_var_kept_as_is(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "$param.nonexist", "mode": "static"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "$param.nonexist"
