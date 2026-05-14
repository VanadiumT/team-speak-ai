"""公共 fixtures — 测试基础设施"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tests.factories import make_context as _make_context
from core.variables.manager import SysVarManager
from core.flow.manager import FlowManager
from core.notification.manager import NotificationManager
from core.history.manager import HistoryManager
from core.app_context import AppContext, set_app_context


@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时 data 目录结构，隔离测试环境"""
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    defaults_dir = tmp_path / "defaults"
    defaults_dir.mkdir()
    return tmp_path


@pytest.fixture
def tmp_data(tmp_data_dir):
    """tmp_data 别名 — 大量测试文件使用此名称"""
    return tmp_data_dir


@pytest.fixture
def sample_flow_data(sample_flow):
    """sample_flow_data 别名"""
    return sample_flow


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


@pytest.fixture
def make_context():
    """返回 factories.make_context 工厂函数，测试中可传参调用"""
    return _make_context


@pytest.fixture
def mock_app_context(tmp_data_dir):
    """创建真实的 AppContext 并注册为全局实例，供节点 get_app_context() 使用"""
    ctx = AppContext()
    ctx.data_dir = str(tmp_data_dir)
    ctx.flow_manager = FlowManager(str(tmp_data_dir))
    ctx.sys_var_manager = SysVarManager(str(tmp_data_dir))
    ctx.notification_manager = NotificationManager(str(tmp_data_dir))
    ctx.history_manager = HistoryManager(str(tmp_data_dir))
    set_app_context(ctx)
    yield ctx
    set_app_context(None)
