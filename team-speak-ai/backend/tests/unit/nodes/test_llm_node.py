"""LLM 节点测试 — 执行 + IO 端口 + think 解析"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.nodes.llm_node import LLMNode
from core.pipeline.registry import NodeRegistry


class TestLLMPorts:
    def test_registered(self):
        assert "llm" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("llm")
        ids = [p.id for p in td.ports.inputs]
        assert "llm-in" in ids
        assert "trigger-in" in ids
        assert "image-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("llm")
        ids = [p.id for p in td.ports.outputs]
        assert "stream-text-out" in ids
        assert "stream-think-out" in ids
        assert "batch-text-out" in ids
        assert "batch-think-out" in ids
        assert "done" in ids
        assert "meta-token-count" in ids
        assert "meta-model" in ids

    def test_llm_in_type(self):
        td = NodeRegistry.get_type_def("llm")
        inp = next(p for p in td.ports.inputs if p.id == "llm-in")
        assert inp.data_type == "messages"

    def test_stream_text_out_type(self):
        td = NodeRegistry.get_type_def("llm")
        out = next(p for p in td.ports.outputs if p.id == "stream-text-out")
        assert out.data_type == "string"


class TestLLMThinkParsing:
    def test_parse_think_tags(self):
        content = "Hello <think>thinking...</think> World"
        clean, think = LLMNode._parse_think(content)
        assert "Hello" in clean
        assert "World" in clean
        assert "thinking..." in think

    def test_parse_multiple_think_tags(self):
        content = "A <think>t1</think> B <think>t2</think> C"
        clean, think = LLMNode._parse_think(content)
        assert "A" in clean
        assert "B" in clean
        assert "C" in clean
        assert "t1" in think
        assert "t2" in think

    def test_parse_no_think_tags(self):
        clean, think = LLMNode._parse_think("Hello World")
        assert clean == "Hello World"
        assert think == ""

    def test_parse_empty_content(self):
        clean, think = LLMNode._parse_think("")
        assert clean == ""
        assert think == ""

    def test_parse_none_content(self):
        clean, think = LLMNode._parse_think(None)
        assert clean is None
        assert think == ""


class TestLLMImageInjection:
    def test_inject_images(self):
        messages = [{"role": "user", "content": "描述图片"}]
        images = [{"url": "data:image/png;base64,abc"}]
        effective = {"vision": True, "image_detail": "auto", "max_images": 4}
        result = LLMNode._inject_images(messages, images, effective)
        user_msg = result[-1]
        assert isinstance(user_msg["content"], list)
        assert user_msg["content"][0]["type"] == "text"
        assert user_msg["content"][1]["type"] == "image_url"

    def test_inject_images_limit(self):
        messages = [{"role": "user", "content": "描述"}]
        images = [{"url": f"img{i}"} for i in range(10)]
        effective = {"vision": True, "image_detail": "auto", "max_images": 3}
        result = LLMNode._inject_images(messages, images, effective)
        img_parts = [p for p in result[-1]["content"] if p.get("type") == "image_url"]
        assert len(img_parts) == 3

    def test_inject_no_user_message(self):
        messages = [{"role": "system", "content": "system"}]
        result = LLMNode._inject_images(messages, [], {"vision": True, "max_images": 4})
        assert len(result) == 1
