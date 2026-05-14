"""EventEmitter 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from core.pipeline.emitter import EventEmitter
from core.pipeline.context import NodeState


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.broadcast_to_flow = AsyncMock()
    return engine


@pytest.fixture
def emitter(mock_engine):
    return EventEmitter(mock_engine, "test_flow")


class TestEmitNodeStatus:
    @pytest.mark.asyncio
    async def test_emit_status_changed(self, emitter, mock_engine):
        await emitter.emit_node_status_changed("n1", NodeState.PROCESSING, summary="处理中")
        mock_engine.broadcast_to_flow.assert_called_once()
        args = mock_engine.broadcast_to_flow.call_args
        assert args[0][0] == "test_flow"
        assert args[0][1] == "node.status_changed"
        params = args[0][2]
        assert params["node_id"] == "n1"
        assert params["status"] == "processing"
        assert params["summary"] == "处理中"

    @pytest.mark.asyncio
    async def test_emit_status_string(self, emitter, mock_engine):
        await emitter.emit_node_status_changed("n1", "completed")
        params = mock_engine.broadcast_to_flow.call_args[0][2]
        assert params["status"] == "completed"

    @pytest.mark.asyncio
    async def test_emit_with_condition_result(self, emitter, mock_engine):
        await emitter.emit_node_status_changed("n1", "completed", condition_result="matched")
        params = mock_engine.broadcast_to_flow.call_args[0][2]
        assert params["condition_result"] == "matched"


class TestEmitNodeUpdate:
    @pytest.mark.asyncio
    async def test_emit_update_compat(self, emitter, mock_engine):
        await emitter.emit_node_update("n1", "processing", "处理中", progress=0.5)
        params = mock_engine.broadcast_to_flow.call_args[0][2]
        assert params["node_id"] == "n1"
        assert params["progress"] == 0.5


class TestEmitLogEntry:
    @pytest.mark.asyncio
    async def test_emit_log_entry(self, emitter, mock_engine):
        await emitter.emit_node_log_entry("n1", "info", "日志消息")
        args = mock_engine.broadcast_to_flow.call_args
        assert args[0][1] == "node.log_entry"
        params = args[0][2]
        assert params["node_id"] == "n1"
        assert params["level"] == "info"
        assert params["message"] == "日志消息"
        assert "timestamp" in params


class TestEmitPipeline:
    @pytest.mark.asyncio
    async def test_emit_pipeline_start(self, emitter, mock_engine):
        await emitter.emit_pipeline_start("exec_001")
        params = mock_engine.broadcast_to_flow.call_args[0][2]
        assert params["execution_id"] == "exec_001"

    @pytest.mark.asyncio
    async def test_emit_pipeline_complete(self, emitter, mock_engine):
        await emitter.emit_pipeline_complete("exec_001")
        args = mock_engine.broadcast_to_flow.call_args
        assert args[0][1] == "pipeline.completed"


class TestEmitError:
    @pytest.mark.asyncio
    async def test_emit_node_error(self, emitter, mock_engine):
        await emitter.emit_node_error("n1", "出错了")
        args = mock_engine.broadcast_to_flow.call_args
        assert args[0][1] == "node.error"
        assert args[0][2]["error"] == "出错了"

    @pytest.mark.asyncio
    async def test_emit_node_complete(self, emitter, mock_engine):
        await emitter.emit_node_complete("n1", {"text": "结果"})
        args = mock_engine.broadcast_to_flow.call_args
        assert args[0][1] == "node.completed"
        assert args[0][2]["output"] == {"text": "结果"}
