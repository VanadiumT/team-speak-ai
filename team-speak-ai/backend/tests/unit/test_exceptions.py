"""异常体系测试"""

import pytest
from core.exceptions import (
    AppBaseException,
    NodeExecutionError,
    NodeConfigError,
    StreamingError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderAuthError,
    FlowNotFoundError,
    FlowValidationError,
    FlowCycleError,
    WSProtocolError,
    WSClientDisconnected,
    AudioBusError,
    AudioDecodeError,
)


class TestAppBaseException:
    """AppBaseException 基类测试"""

    def test_basic_creation(self):
        exc = AppBaseException("test error")
        assert exc.message == "test error"
        assert exc.context == {}
        assert exc.cause is None

    def test_with_context(self):
        exc = AppBaseException("test", context={"key": "value"})
        assert exc.context == {"key": "value"}

    def test_with_cause(self):
        cause = ValueError("root cause")
        exc = AppBaseException("test", cause=cause)
        assert exc.cause is cause

    def test_to_dict(self):
        exc = AppBaseException("test error", context={"key": "value"})
        d = exc.to_dict()
        assert d["error_code"] == "APP_ERROR"
        assert d["message"] == "test error"
        assert d["context"] == {"key": "value"}


class TestNodeExecutionError:
    """NodeExecutionError 测试"""

    def test_creation(self):
        exc = NodeExecutionError("node_1", "llm", "LLM call failed")
        assert exc.node_id == "node_1"
        assert exc.node_type == "llm"
        assert "llm:node_1" in exc.message
        assert exc.error_code == "NODE_EXECUTION"

    def test_with_cause(self):
        cause = TimeoutError("timeout")
        exc = NodeExecutionError("node_1", "llm", "timeout", cause=cause)
        assert exc.cause is cause
        d = exc.to_dict()
        assert d["cause"] == "timeout"


class TestProviderErrors:
    """Provider 异常测试"""

    def test_connection_error(self):
        exc = ProviderConnectionError("openai", "Connection refused")
        assert exc.provider == "openai"
        assert exc.error_code == "PROVIDER_CONNECTION"

    def test_timeout_error(self):
        exc = ProviderTimeoutError("minimax")
        assert exc.provider == "minimax"
        assert exc.error_code == "PROVIDER_TIMEOUT"

    def test_auth_error(self):
        exc = ProviderAuthError("openai", "Invalid API key")
        assert exc.error_code == "PROVIDER_AUTH"


class TestFlowErrors:
    """Flow 异常测试"""

    def test_not_found(self):
        exc = FlowNotFoundError("my_flow")
        assert exc.flow_id == "my_flow"
        assert exc.error_code == "FLOW_NOT_FOUND"

    def test_validation_error(self):
        exc = FlowValidationError("my_flow", "Missing start node")
        assert exc.flow_id == "my_flow"
        assert exc.error_code == "FLOW_VALIDATION"

    def test_cycle_error(self):
        exc = FlowCycleError("my_flow", "A -> B -> C -> A")
        assert exc.error_code == "FLOW_CYCLE"


class TestWSErrors:
    """WebSocket 异常测试"""

    def test_protocol_error(self):
        exc = WSProtocolError("Invalid message format")
        assert exc.error_code == "WS_PROTOCOL"

    def test_client_disconnected(self):
        exc = WSClientDisconnected("client_123")
        assert exc.error_code == "WS_CLIENT_DISCONNECTED"


class TestAudioErrors:
    """音频异常测试"""

    def test_bus_error(self):
        exc = AudioBusError("Subscribe failed")
        assert exc.error_code == "AUDIO_BUS_ERROR"

    def test_decode_error(self):
        exc = AudioDecodeError("Invalid MP3 header")
        assert exc.error_code == "AUDIO_DECODE_ERROR"


class TestExceptionHierarchy:
    """异常继承关系测试"""

    def test_all_inherit_app_base(self):
        exceptions = [
            NodeExecutionError("n", "t", "d"),
            NodeConfigError("n", "t", "d"),
            StreamingError("n", "d"),
            ProviderConnectionError("p", "d"),
            ProviderTimeoutError("p"),
            ProviderAuthError("p"),
            FlowNotFoundError("f"),
            FlowValidationError("f", "d"),
            FlowCycleError("f"),
            WSProtocolError("d"),
            WSClientDisconnected(),
            AudioBusError("d"),
            AudioDecodeError("d"),
        ]
        for exc in exceptions:
            assert isinstance(exc, AppBaseException)
            assert isinstance(exc, Exception)
