"""公共 fixtures — 测试基础设施"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时 data 目录结构，隔离测试环境"""
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    defaults_dir = tmp_path / "defaults"
    defaults_dir.mkdir()
    return tmp_path


@pytest.fixture
def sample_flow():
    """示例流程 JSON"""
    return {
        "id": "test_flow",
        "name": "Test Flow",
        "group": "",
        "icon": "account_tree",
        "nodes": [
            {
                "id": "start_1",
                "type": "start",
                "name": "Start",
                "position": {"x": 100, "y": 100},
                "config": {"init_params": {"greeting": "hello"}},
                "input_mappings": [],
                "trigger": None,
                "listener": False,
            },
            {
                "id": "llm_1",
                "type": "llm",
                "name": "LLM",
                "position": {"x": 300, "y": 100},
                "config": {
                    "platform_id": "openai",
                    "model_id": "gpt-4",
                    "streaming": True,
                },
                "input_mappings": [],
                "trigger": None,
                "listener": False,
            },
        ],
        "connections": [
            {
                "id": "conn_1",
                "from_node": "start_1",
                "from_port": "out",
                "to_node": "llm_1",
                "to_port": "messages",
                "type": "data",
            }
        ],
        "canvas": {"width": 2000, "height": 1500},
    }


@pytest.fixture
def sample_flow_file(tmp_data_dir, sample_flow):
    """写入示例流程 JSON 文件"""
    flow_file = tmp_data_dir / "flows" / "test_flow.json"
    flow_file.write_text(json.dumps(sample_flow, ensure_ascii=False, indent=2), encoding="utf-8")
    return flow_file


@pytest.fixture
def mock_emit():
    """模拟 EventEmitter，捕获所有 emit 调用"""
    emit = AsyncMock()
    emit.emit_node_update = AsyncMock()
    emit.emit_node_complete = AsyncMock()
    emit.emit_node_error = AsyncMock()
    emit.emit_node_log_entry = AsyncMock()
    emit.emit_node_status_changed = AsyncMock()
    emit.emit_important_update = AsyncMock()
    emit.emit_pipeline_complete = AsyncMock()
    return emit


@pytest.fixture
def mock_websocket():
    """模拟 WebSocket 连接"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.receive_json = AsyncMock()
    return ws
