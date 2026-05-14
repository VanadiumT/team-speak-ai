"""STTListen 节点测试 — 执行 + IO 端口"""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.nodes.stt_listen_node import STTListenNode
from core.pipeline.registry import NodeRegistry


class TestSTTListenPorts:
    def test_registered(self):
        assert "stt_listen" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("stt_listen")
        ids = [p.id for p in td.ports.inputs]
        assert "stream-audio-in" in ids
        assert "batch-audio-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("stt_listen")
        ids = [p.id for p in td.ports.outputs]
        assert "stream-text-out" in ids
        assert "batch-text-out" in ids
        assert "done" in ids

    def test_stream_audio_in_type(self):
        td = NodeRegistry.get_type_def("stt_listen")
        inp = next(p for p in td.ports.inputs if p.id == "stream-audio-in")
        assert inp.data_type == "audio"

    def test_stream_text_out_type(self):
        td = NodeRegistry.get_type_def("stt_listen")
        out = next(p for p in td.ports.outputs if p.id == "stream-text-out")
        assert out.data_type == "string"


class TestSTTListenAudioDecode:
    def test_decode_bytes(self):
        result = STTListenNode._decode_audio_input(b"audio_data")
        assert result == b"audio_data"

    def test_decode_string_base64(self):
        b64 = base64.b64encode(b"hello").decode()
        result = STTListenNode._decode_audio_input(b64)
        assert result == b"hello"

    def test_decode_list_of_chunks(self):
        chunk1 = base64.b64encode(b"part1").decode()
        chunk2 = base64.b64encode(b"part2").decode()
        result = STTListenNode._decode_audio_input([chunk1, chunk2])
        assert result == b"part1part2"

    def test_decode_list_of_bytes(self):
        result = STTListenNode._decode_audio_input([b"part1", b"part2"])
        assert result == b"part1part2"

    def test_decode_unsupported_type(self):
        with pytest.raises(TypeError, match="Unsupported"):
            STTListenNode._decode_audio_input(12345)


class TestSTTListenExecute:
    @pytest.mark.asyncio
    async def test_no_audio_returns_empty(self, make_context, mock_emit):
        node = STTListenNode({})
        ctx = make_context(node_config={}, inputs={})
        mock_stt = MagicMock()
        mock_stt.transcribe = AsyncMock(return_value="text")
        with patch("core.nodes.stt_listen_node.STTListenNode._resolve_stt_legacy_config",
                    return_value={"provider": "sensevoice", "model_dir": "", "device": "cpu",
                                  "api_key": "", "api_url": "", "language": "auto",
                                  "sample_rate": 16000, "model_name": "default"}), \
             patch("core.nodes.stt_listen_node.STTListenNode._get_stt_from_config",
                    return_value=mock_stt):
            result = await node.execute(ctx, mock_emit)
        assert result.trigger_next is False
