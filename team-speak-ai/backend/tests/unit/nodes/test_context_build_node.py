"""ContextBuild 节点测试 — 执行 + IO 端口"""

import pytest
from core.nodes.context_build_node import ContextBuildNode
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return ContextBuildNode({
        "max_context_length": 4096,
        "_repeatable_ports": {"ctx": []},
        "_port_labels": {},
    })


class TestContextBuildPorts:
    def test_registered(self):
        assert "context_build" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("context_build")
        ids = [p.id for p in td.ports.inputs]
        assert "system-in" in ids
        assert "chat-in" in ids
        assert "req-in" in ids
        assert "trigger-in" in ids

    def test_repeatable_ctx_ports(self):
        td = NodeRegistry.get_type_def("context_build")
        ctx_ports = [p for p in td.ports.inputs if p.repeatable]
        assert len(ctx_ports) >= 1
        assert ctx_ports[0].group == "ctx"
        assert ctx_ports[0].data_type == "string"

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("context_build")
        ids = [p.id for p in td.ports.outputs]
        assert "ctx-out" in ids
        assert "done" in ids

    def test_ctx_out_type(self):
        td = NodeRegistry.get_type_def("context_build")
        out = next(p for p in td.ports.outputs if p.id == "ctx-out")
        assert out.data_type == "messages"


class TestContextBuildExecute:
    @pytest.mark.asyncio
    async def test_basic_user_message(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"_repeatable_ports": {"ctx": []}, "_port_labels": {}},
            inputs={"req": "你好"},
        )
        result = await node.execute(ctx, mock_emit)
        messages = result.data["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "你好" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_with_system_prompt(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"_repeatable_ports": {"ctx": []}, "_port_labels": {}},
            inputs={"system": "你是AI助手", "req": "你好"},
        )
        result = await node.execute(ctx, mock_emit)
        messages = result.data["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "你是AI助手"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_with_chat_history(self, node, make_context, mock_emit):
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]
        ctx = make_context(
            node_config={"_repeatable_ports": {"ctx": []}, "_port_labels": {}},
            inputs={"chat": history, "req": "继续"},
        )
        result = await node.execute(ctx, mock_emit)
        messages = result.data["messages"]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "你好"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    @pytest.mark.asyncio
    async def test_with_repeatable_ctx_ports(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={
                "_repeatable_ports": {"ctx": ["ctx-in1", "ctx-in2"]},
                "_port_labels": {"ctx-in1": "信息A", "ctx-in2": "信息B"},
            },
            inputs={"req": "分析", "ctx-in1": "数据A", "ctx-in2": "数据B"},
        )
        result = await node.execute(ctx, mock_emit)
        user_msg = result.data["messages"][-1]["content"]
        assert "数据A" in user_msg
        assert "数据B" in user_msg

    @pytest.mark.asyncio
    async def test_no_inputs_uses_default(self, node, make_context, mock_emit):
        ctx = make_context(
            node_config={"_repeatable_ports": {"ctx": []}, "_port_labels": {}},
            inputs={},
        )
        result = await node.execute(ctx, mock_emit)
        messages = result.data["messages"]
        assert messages[-1]["role"] == "user"
        assert "你自己" in messages[-1]["content"]
