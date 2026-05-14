"""VAD 节点测试 — 执行 + IO 端口"""

import base64
import struct
import pytest
from core.nodes.vad_node import VADNode, _resolve_pcm
from core.pipeline.registry import NodeRegistry


class TestVADPorts:
    def test_registered(self):
        assert "vad" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("vad")
        ids = [p.id for p in td.ports.inputs]
        assert "stream-audio-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("vad")
        ids = [p.id for p in td.ports.outputs]
        assert "stream-chunk-out" in ids
        assert "trigger-out" in ids
        assert "done" in ids

    def test_stream_audio_in_type(self):
        td = NodeRegistry.get_type_def("vad")
        inp = next(p for p in td.ports.inputs if p.id == "stream-audio-in")
        assert inp.data_type == "audio"

    def test_stream_chunk_out_type(self):
        td = NodeRegistry.get_type_def("vad")
        out = next(p for p in td.ports.outputs if p.id == "stream-chunk-out")
        assert out.data_type == "audio"


class TestResolvePCM:
    def test_bytes_input(self):
        assert _resolve_pcm(b"audio") == b"audio"

    def test_bytearray_input(self):
        assert _resolve_pcm(bytearray(b"audio")) == b"audio"

    def test_string_base64(self):
        b64 = base64.b64encode(b"hello").decode()
        assert _resolve_pcm(b64) == b"hello"

    def test_dict_with_audio_key(self):
        data = {"audio": [b"part1", b"part2"]}
        assert _resolve_pcm(data) == b"part1part2"

    def test_dict_with_data_key(self):
        data = {"data": b"pcm_data"}
        assert _resolve_pcm(data) == b"pcm_data"

    def test_list_input(self):
        assert _resolve_pcm([b"a", b"b"]) == b"ab"

    def test_unsupported_returns_empty(self):
        assert _resolve_pcm(12345) == b""

    def test_invalid_base64_returns_empty(self):
        assert _resolve_pcm("not-base64!!!") == b""


class TestVADExecute:
    @pytest.mark.asyncio
    async def test_no_audio_returns_error(self, make_context, mock_emit):
        node = VADNode({})
        ctx = make_context(node_config={}, inputs={})
        result = await node.execute(ctx, mock_emit)
        assert result.trigger_next is False

    @pytest.mark.asyncio
    async def test_invalid_audio_returns_error(self, make_context, mock_emit):
        node = VADNode({})
        ctx = make_context(
            node_config={"platform_id": "", "model_id": "", "overrides": {}},
            inputs={"stream-audio": "not_valid_audio"},
        )
        # Mock preset fallback
        from core.nodes.vad_node import _DEFAULT_VAD_EFFECTIVE
        with patch.object(VADNode, '_resolve_vad_preset_config', return_value=_DEFAULT_VAD_EFFECTIVE):
            result = await node.execute(ctx, mock_emit)
        # Should return error since "not_valid_audio" decodes to empty bytes
        assert result.trigger_next is False or result.data.get("total_chunks", 1) == 0


# need patch import
from unittest.mock import patch
