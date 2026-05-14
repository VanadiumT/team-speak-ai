"""SysVarRead + SysVarWrite 节点测试 — 执行 + IO 端口"""

import pytest
from core.nodes.sys_var_read_node import SysVarReadNode
from core.nodes.sys_var_write_node import SysVarWriteNode
from core.pipeline.registry import NodeRegistry


class TestSysVarReadPorts:
    def test_registered(self):
        assert "sys_var_read" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("sys_var_read")
        ids = [p.id for p in td.ports.inputs]
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("sys_var_read")
        ids = [p.id for p in td.ports.outputs]
        assert "data-out" in ids
        assert "done" in ids


class TestSysVarReadExecute:
    @pytest.mark.asyncio
    async def test_read_existing(self, make_context, mock_emit, mock_app_context):
        mock_app_context.sys_var_manager.set("api_url", "https://example.com")
        node = SysVarReadNode({"key": "api_url", "default_value": ""})
        ctx = make_context(node_config={"key": "api_url", "default_value": ""})
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_read_missing_returns_default(self, make_context, mock_emit, mock_app_context):
        node = SysVarReadNode({"key": "missing", "default_value": "fallback"})
        ctx = make_context(node_config={"key": "missing", "default_value": "fallback"})
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] == "fallback"

    @pytest.mark.asyncio
    async def test_read_empty_key(self, make_context, mock_emit):
        node = SysVarReadNode({"key": "", "default_value": ""})
        ctx = make_context(node_config={"key": ""})
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] == ""


class TestSysVarWritePorts:
    def test_registered(self):
        assert "sys_var_write" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("sys_var_write")
        ids = [p.id for p in td.ports.inputs]
        assert "data-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("sys_var_write")
        ids = [p.id for p in td.ports.outputs]
        assert "data-out" in ids
        assert "done" in ids


class TestSysVarWriteExecute:
    @pytest.mark.asyncio
    async def test_write_overwrite(self, make_context, mock_emit, mock_app_context):
        node = SysVarWriteNode({"key": "theme", "merge_mode": "overwrite"})
        ctx = make_context(
            node_config={"key": "theme", "merge_mode": "overwrite"},
            inputs={"data": "dark"},
        )
        result = await node.execute(ctx, mock_emit)
        assert mock_app_context.sys_var_manager.get("theme") == "dark"
        assert result.data["value"] == "dark"

    @pytest.mark.asyncio
    async def test_write_empty_key(self, make_context, mock_emit):
        node = SysVarWriteNode({"key": "", "merge_mode": "overwrite"})
        ctx = make_context(node_config={"key": ""}, inputs={"data": "val"})
        result = await node.execute(ctx, mock_emit)
        assert result.data["key"] == ""

    @pytest.mark.asyncio
    async def test_write_no_data_skips(self, make_context, mock_emit):
        node = SysVarWriteNode({"key": "k", "merge_mode": "overwrite"})
        ctx = make_context(node_config={"key": "k"}, inputs={})
        result = await node.execute(ctx, mock_emit)
        assert result.data["value"] is None
