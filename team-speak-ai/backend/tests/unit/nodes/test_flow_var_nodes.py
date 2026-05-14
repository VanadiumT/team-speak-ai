"""FlowVarRead + FlowVarWrite 节点测试 — 执行 + IO 端口"""

import pytest
from core.nodes.flow_var_read_node import FlowVarReadNode
from core.nodes.flow_var_write_node import FlowVarWriteNode
from core.pipeline.registry import NodeRegistry


class TestFlowVarReadPorts:
    def test_registered(self):
        assert "flow_var_read" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("flow_var_read")
        ids = [p.id for p in td.ports.inputs]
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("flow_var_read")
        ids = [p.id for p in td.ports.outputs]
        assert "data-out" in ids
        assert "done" in ids

    def test_data_out_type(self):
        td = NodeRegistry.get_type_def("flow_var_read")
        out = next(p for p in td.ports.outputs if p.id == "data-out")
        assert out.data_type == "string"


class TestFlowVarReadExecute:
    @pytest.mark.asyncio
    async def test_read_existing_var(self, make_context, mock_emit):
        node = FlowVarReadNode({"key": "greeting", "default_value": ""})
        ctx = make_context(
            node_config={"key": "greeting", "default_value": ""},
            accumulated_context={"greeting": "你好"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] == "你好"
        assert result.data["key"] == "greeting"
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_read_missing_var_returns_default(self, make_context, mock_emit):
        node = FlowVarReadNode({"key": "missing", "default_value": "默认"})
        ctx = make_context(node_config={"key": "missing", "default_value": "默认"})
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] == "默认"

    @pytest.mark.asyncio
    async def test_read_empty_key(self, make_context, mock_emit):
        node = FlowVarReadNode({"key": "", "default_value": ""})
        ctx = make_context(node_config={"key": "", "default_value": ""})
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] == ""
        assert result.data["key"] == ""


class TestFlowVarWritePorts:
    def test_registered(self):
        assert "flow_var_write" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("flow_var_write")
        ids = [p.id for p in td.ports.inputs]
        assert "data-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("flow_var_write")
        ids = [p.id for p in td.ports.outputs]
        assert "data-out" in ids
        assert "done" in ids

    def test_data_in_type(self):
        td = NodeRegistry.get_type_def("flow_var_write")
        inp = next(p for p in td.ports.inputs if p.id == "data-in")
        assert inp.data_type == "string"


class TestFlowVarWriteExecute:
    @pytest.mark.asyncio
    async def test_write_overwrite(self, make_context, mock_emit):
        node = FlowVarWriteNode({"key": "name", "merge_mode": "overwrite"})
        ctx = make_context(
            node_config={"key": "name", "merge_mode": "overwrite"},
            inputs={"data": "Alice"},
        )
        result = await node.execute(ctx, mock_emit)
        assert ctx.accumulated_context["name"] == "Alice"
        assert result.data["value"] == "Alice"
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_write_append(self, make_context, mock_emit):
        node = FlowVarWriteNode({"key": "items", "merge_mode": "append"})
        ctx = make_context(
            node_config={"key": "items", "merge_mode": "append"},
            inputs={"data": "item1"},
            accumulated_context={"items": []},
        )
        await node.execute(ctx, mock_emit)
        assert ctx.accumulated_context["items"] == ["item1"]

    @pytest.mark.asyncio
    async def test_write_append_to_non_list(self, make_context, mock_emit):
        node = FlowVarWriteNode({"key": "val", "merge_mode": "append"})
        ctx = make_context(
            node_config={"key": "val", "merge_mode": "append"},
            inputs={"data": "new"},
            accumulated_context={"val": "old"},
        )
        await node.execute(ctx, mock_emit)
        assert ctx.accumulated_context["val"] == ["old", "new"]

    @pytest.mark.asyncio
    async def test_write_empty_key(self, make_context, mock_emit):
        node = FlowVarWriteNode({"key": "", "merge_mode": "overwrite"})
        ctx = make_context(node_config={"key": ""}, inputs={"data": "val"})
        result = await node.execute(ctx, mock_emit)
        assert result.data["key"] == ""
