"""TextInput 节点测试 — 执行 + IO 端口"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from core.nodes.text_input_node import TextInputNode
from core.pipeline.context import NodeOutput
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return TextInputNode({"text": "", "mode": "static"})


class TestTextInputPorts:
    def test_registered(self):
        assert "text_input" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("text_input")
        ids = [p.id for p in td.ports.inputs]
        assert "text-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("text_input")
        ids = [p.id for p in td.ports.outputs]
        assert "text-out" in ids
        assert "done" in ids

    def test_text_out_port_type(self):
        td = NodeRegistry.get_type_def("text_input")
        out = next(p for p in td.ports.outputs if p.id == "text-out")
        assert out.data_type == "string"

    def test_trigger_in_port_type(self):
        td = NodeRegistry.get_type_def("text_input")
        inp = next(p for p in td.ports.inputs if p.id == "trigger-in")
        assert inp.data_type == "event"
        assert inp.visibility == "on-demand"


class TestTextInputStaticMode:
    @pytest.mark.asyncio
    async def test_static_text_output(self, node, make_context, mock_emit):
        ctx = make_context(node_config={"text": "Hello World", "mode": "static"})
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "Hello World"
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_static_empty_text(self, node, make_context, mock_emit):
        ctx = make_context(node_config={"text": "", "mode": "static"})
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == ""
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_static_resolves_param_var(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "Hello $param.name", "mode": "static"},
            accumulated_context={"name": "Alice"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "Hello Alice"


class TestTextInputInteractiveMode:
    @pytest.mark.asyncio
    async def test_interactive_no_input_waits(self, node, make_context, mock_emit):
        ctx = make_context(node_config={"text": "", "mode": "interactive"})
        result = await node.execute(ctx, mock_emit)
        assert result.trigger_next is False
        assert result.data["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_interactive_with_input(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "", "mode": "interactive"},
            inputs={"text": "用户输入"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["text"] == "用户输入"
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_interactive_notifies_user(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"text": "", "mode": "interactive", "notify_on_reach": True},
        )
        await node.execute(ctx, mock_emit)
        mock_emit.emit_important_update.assert_called_once()
