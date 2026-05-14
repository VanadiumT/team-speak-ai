"""AudioPlayer 节点测试 — 执行 + IO 端口"""

import base64
import pytest
from core.nodes.audio_player_node import AudioPlayerNode, _extract_b64_from_inputs, _audio_format
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return AudioPlayerNode({"volume": 1.0, "auto_play": True})


class TestAudioPlayerPorts:
    def test_registered(self):
        assert "audio_player" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("audio_player")
        ids = [p.id for p in td.ports.inputs]
        assert "stream-audio-in" in ids
        assert "batch-audio-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("audio_player")
        ids = [p.id for p in td.ports.outputs]
        assert "stream-audio-out" in ids
        assert "batch-audio-out" in ids
        assert "done" in ids

    def test_stream_audio_in_type(self):
        td = NodeRegistry.get_type_def("audio_player")
        inp = next(p for p in td.ports.inputs if p.id == "stream-audio-in")
        assert inp.data_type == "audio"

    def test_done_type(self):
        td = NodeRegistry.get_type_def("audio_player")
        out = next(p for p in td.ports.outputs if p.id == "done")
        assert out.data_type == "event"


class TestAudioPlayerHelpers:
    def test_extract_from_batch_string(self):
        inputs = {"batch-audio": "aGVsbG8="}
        assert _extract_b64_from_inputs(inputs) == "aGVsbG8="

    def test_extract_from_batch_dict(self):
        inputs = {"batch-audio": {"audio_b64": "aGVsbG8="}}
        assert _extract_b64_from_inputs(inputs) == "aGVsbG8="

    def test_extract_from_stream_segments(self):
        inputs = {"stream-audio": [
            {"audio_b64": "aGVs"},
            {"audio_b64": "bG8="},
        ]}
        assert _extract_b64_from_inputs(inputs) == "aGVsbG8="

    def test_audio_format_from_batch_dict(self):
        inputs = {"batch-audio": {"format": "mp3"}}
        assert _audio_format(inputs) == "mp3"

    def test_audio_format_default(self):
        assert _audio_format({}) == "wav"


class TestAudioPlayerExecute:
    @pytest.mark.asyncio
    async def test_no_audio(self, node, make_context, mock_emit):
        ctx = make_context(node_config={}, inputs={})
        result = await node.execute(ctx, mock_emit)
        assert result.data["played"] is False

    @pytest.mark.asyncio
    async def test_batch_play(self, node, make_context, mock_emit):
        b64 = base64.b64encode(b"fake_wav").decode()
        ctx = make_context(
            node_config={},
            inputs={"batch-audio": {"audio_b64": b64, "format": "wav"}},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["played"] is True
        assert result.data["mode"] == "batch"
        assert result.data["batch-audio"]["audio_b64"] == b64
