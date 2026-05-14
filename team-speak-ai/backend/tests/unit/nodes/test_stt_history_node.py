"""STTHistory 节点测试 — 执行 + IO 端口"""

import pytest
from core.nodes.stt_history_node import STTHistoryNode
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return STTHistoryNode({"max_entries": 20, "keywords": []})


class TestSTTHistoryPorts:
    def test_registered(self):
        assert "stt_history" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("stt_history")
        ids = [p.id for p in td.ports.inputs]
        assert "hist-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("stt_history")
        ids = [p.id for p in td.ports.outputs]
        assert "hist-out" in ids
        assert "hist-trigger" in ids
        assert "done" in ids

    def test_hist_in_type(self):
        td = NodeRegistry.get_type_def("stt_history")
        inp = next(p for p in td.ports.inputs if p.id == "hist-in")
        assert inp.data_type == "string"

    def test_hist_out_type(self):
        td = NodeRegistry.get_type_def("stt_history")
        out = next(p for p in td.ports.outputs if p.id == "hist-out")
        assert out.data_type == "string_array"


class TestSTTHistoryExecute:
    @pytest.mark.asyncio
    async def test_collects_text(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": []},
            inputs={"text": "你好世界"},
        )
        result = await node.execute(ctx, mock_emit)
        assert "你好世界" in result.data["history"]

    @pytest.mark.asyncio
    async def test_accumulates_history(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": []},
            inputs={"text": "第二句"},
            accumulated_context={"stt_history": ["第一句"]},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["history"] == ["第一句", "第二句"]

    @pytest.mark.asyncio
    async def test_limits_history_window(self, node, make_context, mock_emit):
        history = [f"sentence_{i}" for i in range(25)]
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": []},
            inputs={"text": "new"},
            accumulated_context={"stt_history": history},
        )
        result = await node.execute(ctx, mock_emit)
        assert len(result.data["history"]) == 20

    @pytest.mark.asyncio
    async def test_keyword_match(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": ["你好"]},
            inputs={"text": "你好世界"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["trigger_keyword"] == "你好"
        assert result.data["condition_result"] == "matched"

    @pytest.mark.asyncio
    async def test_keyword_no_match(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": ["不存在"]},
            inputs={"text": "其他内容"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["condition_result"] == "skipped"

    @pytest.mark.asyncio
    async def test_no_keywords_default_trigger(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": []},
            inputs={"text": "任意文本"},
        )
        result = await node.execute(ctx, mock_emit)
        assert "condition_result" not in result.data
        assert "history" in result.data

    @pytest.mark.asyncio
    async def test_empty_input(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"max_entries": 20, "keywords": []},
            inputs={},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["history"] == []
