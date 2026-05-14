"""FlowManager 测试"""

import json
import pytest
from pathlib import Path

from core.flow.manager import FlowManager
from core.exceptions import FlowNotFoundError, FlowValidationError


class TestFlowManager:
    """FlowManager CRUD 测试"""

    def test_create_flow(self, tmp_data_dir):
        fm = FlowManager(str(tmp_data_dir))
        flow = fm.create_flow("My Flow")
        assert flow.name == "My Flow"
        assert flow.id == "my_flow"
        assert (tmp_data_dir / "flows" / "my_flow.json").exists()

    def test_list_flows(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        flows = fm.list_flows()
        assert len(flows) == 1
        assert flows[0].id == "test_flow"

    def test_load_flow(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        flow = fm.load_flow("test_flow")
        assert flow.id == "test_flow"
        assert len(flow.nodes) == 2

    def test_load_flow_not_found(self, tmp_data_dir):
        fm = FlowManager(str(tmp_data_dir))
        with pytest.raises(FlowNotFoundError) as exc_info:
            fm.load_flow("nonexistent")
        assert exc_info.value.flow_id == "nonexistent"

    def test_delete_flow(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        import asyncio
        asyncio.run(fm.delete_flow("test_flow"))
        assert not sample_flow_file.exists()

    def test_create_group(self, tmp_data_dir):
        fm = FlowManager(str(tmp_data_dir))
        groups = fm.create_group("my_group")
        assert "my_group" in groups

    def test_remove_group(self, tmp_data_dir):
        fm = FlowManager(str(tmp_data_dir))
        fm.create_group("my_group")
        groups = fm.remove_group("my_group")
        assert "my_group" not in groups


class TestFlowManagerNodeOperations:
    """节点操作测试"""

    def test_move_node(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        import asyncio
        flow = asyncio.run(fm.move_node("test_flow", "start_1", 200, 300))
        node = flow.get_node("start_1")
        assert node.position == {"x": 200, "y": 300}

    def test_move_node_not_found(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        import asyncio
        with pytest.raises(FlowValidationError):
            asyncio.run(fm.move_node("test_flow", "nonexistent", 200, 300))

    def test_update_node_config(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        import asyncio
        flow = asyncio.run(fm.update_node_config("test_flow", "llm_1", {"temperature": 0.8}))
        node = flow.get_node("llm_1")
        assert node.config["temperature"] == 0.8

    def test_rename_node(self, tmp_data_dir, sample_flow_file):
        fm = FlowManager(str(tmp_data_dir))
        import asyncio
        flow = asyncio.run(fm.rename_node("test_flow", "start_1", "New Start"))
        node = flow.get_node("start_1")
        assert node.name == "New Start"
