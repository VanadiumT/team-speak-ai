"""日志系统测试"""

import json
import pytest
from datetime import datetime, date
from pathlib import Path

from core.logger.base import LogLevel, LogEntry, PipelineEvent
from core.logger.file_logger import FileLogger
from core.logger.context import trace_context, get_trace_id, set_trace_id, generate_trace_id


class TestFileLogger:
    """FileLogger 测试"""

    def test_basic_log(self, tmp_path):
        logger = FileLogger(log_dir=str(tmp_path), keep_days=30)
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            module_name="test",
            message="test message",
        )
        logger.log(entry)

        # 检查日志文件已创建
        log_files = list(tmp_path.glob("app-*.jsonl"))
        assert len(log_files) == 1

        # 检查日志内容
        content = log_files[0].read_text(encoding="utf-8")
        data = json.loads(content.strip())
        assert data["type"] == "log"
        assert data["level"] == "INFO"
        assert data["module"] == "test"
        assert data["message"] == "test message"

    def test_level_filtering(self, tmp_path):
        logger = FileLogger(log_dir=str(tmp_path), keep_days=30, min_level=LogLevel.WARNING)

        # DEBUG 和 INFO 应该被过滤
        logger.log(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.DEBUG,
            module_name="test",
            message="debug message",
        ))
        logger.log(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            module_name="test",
            message="info message",
        ))

        # WARNING 和 ERROR 应该被记录
        logger.log(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.WARNING,
            module_name="test",
            message="warning message",
        ))
        logger.log(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            module_name="test",
            message="error message",
        ))

        log_files = list(tmp_path.glob("app-*.jsonl"))
        assert len(log_files) == 1

        lines = log_files[0].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        data1 = json.loads(lines[0])
        assert data1["level"] == "WARNING"

        data2 = json.loads(lines[1])
        assert data2["level"] == "ERROR"

    def test_pipeline_event(self, tmp_path):
        logger = FileLogger(log_dir=str(tmp_path), keep_days=30)
        event = PipelineEvent(
            event_type="node_start",
            flow_id="test_flow",
            execution_id="exec_1",
            node_id="node_1",
            data={"node_type": "llm"},
        )
        logger.log_event(event)

        log_files = list(tmp_path.glob("app-*.jsonl"))
        assert len(log_files) == 1

        content = log_files[0].read_text(encoding="utf-8")
        data = json.loads(content.strip())
        assert data["type"] == "pipeline_event"
        assert data["event_type"] == "node_start"
        assert data["flow_id"] == "test_flow"

    def test_trace_id_in_extra(self, tmp_path):
        logger = FileLogger(log_dir=str(tmp_path), keep_days=30)

        # 设置 trace_id
        token = set_trace_id("test-trace-123")

        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            module_name="test",
            message="test message",
            extra={"trace_id": get_trace_id()},
        )
        logger.log(entry)

        # 恢复 trace_id
        from core.logger.context import trace_id_var
        trace_id_var.reset(token)

        log_files = list(tmp_path.glob("app-*.jsonl"))
        content = log_files[0].read_text(encoding="utf-8")
        data = json.loads(content.strip())
        assert data["trace_id"] == "test-trace-123"


class TestTraceContext:
    """trace_id 上下文管理测试"""

    def test_default_trace_id(self):
        assert get_trace_id() == "-"

    def test_set_trace_id(self):
        token = set_trace_id("custom-id")
        assert get_trace_id() == "custom-id"
        from core.logger.context import trace_id_var
        trace_id_var.reset(token)

    def test_generate_trace_id(self):
        tid = generate_trace_id()
        assert len(tid) == 8
        assert tid.isalnum()

    def test_trace_context_manager(self):
        with trace_context() as tid:
            assert get_trace_id() == tid
            assert len(tid) == 8

        # 退出后应该恢复默认值
        assert get_trace_id() == "-"

    def test_trace_context_with_custom_id(self):
        with trace_context("my-trace") as tid:
            assert tid == "my-trace"
            assert get_trace_id() == "my-trace"

    def test_trace_context_exception_safety(self):
        """确保异常时也能正确恢复"""
        try:
            with trace_context("error-trace") as tid:
                assert get_trace_id() == "error-trace"
                raise ValueError("test error")
        except ValueError:
            pass

        assert get_trace_id() == "-"
