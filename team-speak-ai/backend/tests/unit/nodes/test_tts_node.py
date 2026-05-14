"""TTS 节点测试 — 执行 + IO 端口"""

import pytest
from core.nodes.tts_node import TTSNode
from core.pipeline.registry import NodeRegistry


class TestTTSPorts:
    def test_registered(self):
        assert "tts" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("tts")
        ids = [p.id for p in td.ports.inputs]
        assert "stream-text-in" in ids
        assert "batch-text-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("tts")
        ids = [p.id for p in td.ports.outputs]
        assert "stream-audio-out" in ids
        assert "batch-audio-out" in ids
        assert "done" in ids

    def test_stream_text_in_type(self):
        td = NodeRegistry.get_type_def("tts")
        inp = next(p for p in td.ports.inputs if p.id == "stream-text-in")
        assert inp.data_type == "string"

    def test_stream_audio_out_type(self):
        td = NodeRegistry.get_type_def("tts")
        out = next(p for p in td.ports.outputs if p.id == "stream-audio-out")
        assert out.data_type == "audio"


class TestTTSSentenceSplit:
    def test_split_sentences(self):
        node = TTSNode({})
        result = node._split_sentences("你好。世界！")
        assert len(result) == 2
        assert "你好。" in result[0]
        assert "世界！" in result[1]

    def test_split_no_delimiter(self):
        node = TTSNode({})
        result = node._split_sentences("没有标点的文本")
        assert len(result) == 1

    def test_split_empty(self):
        node = TTSNode({})
        result = node._split_sentences("")
        assert result == []

    def test_split_multiline(self):
        node = TTSNode({})
        result = node._split_sentences("第一行\n第二行\n第三行")
        assert len(result) == 3


class TestTTSLegacyConfig:
    def test_resolve_legacy_edge(self):
        result = TTSNode._resolve_legacy_config({"engine": "edge"})
        assert result["provider"] == "edge"
        assert "voice_id" in result

    def test_resolve_legacy_minimax(self):
        result = TTSNode._resolve_legacy_config({"engine": "minimax"})
        assert result["provider"] == "minimax"
