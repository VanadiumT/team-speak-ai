"""TSOutput 节点测试 — IO 端口 + 分片逻辑"""

import base64
import pytest
from core.nodes.ts_output_node import _extract_b64_from_inputs, _chunk_audio_b64, _fallback_raw_split
from core.pipeline.registry import NodeRegistry


class TestTSOutputPorts:
    def test_registered(self):
        assert "ts_output" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("ts_output")
        ids = [p.id for p in td.ports.inputs]
        assert "stream-audio-in" in ids
        assert "batch-audio-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("ts_output")
        ids = [p.id for p in td.ports.outputs]
        assert "done" in ids

    def test_stream_audio_in_type(self):
        td = NodeRegistry.get_type_def("ts_output")
        inp = next(p for p in td.ports.inputs if p.id == "stream-audio-in")
        assert inp.data_type == "audio"

    def test_done_type(self):
        td = NodeRegistry.get_type_def("ts_output")
        out = next(p for p in td.ports.outputs if p.id == "done")
        assert out.data_type == "event"


class TestExtractB64:
    def test_from_batch_string(self):
        inputs = {"batch-audio": "aGVsbG8="}
        assert _extract_b64_from_inputs(inputs) == "aGVsbG8="

    def test_from_batch_dict(self):
        inputs = {"batch-audio": {"audio_b64": "aGVsbG8="}}
        assert _extract_b64_from_inputs(inputs) == "aGVsbG8="

    def test_from_stream_segments(self):
        inputs = {"stream-audio": [
            {"audio_b64": "aGVs"},
            {"audio_b64": "bG8="},
        ]}
        assert _extract_b64_from_inputs(inputs) == "aGVsbG8="

    def test_empty_inputs(self):
        assert _extract_b64_from_inputs({}) == ""


class TestFallbackRawSplit:
    def test_small_data_single_chunk(self):
        data = base64.b64encode(b"small").decode()
        chunks = _fallback_raw_split(data, 1000)
        assert len(chunks) == 1

    def test_large_data_multiple_chunks(self):
        data = base64.b64encode(b"x" * 10000).decode()
        chunks = _fallback_raw_split(data, 1000)
        assert len(chunks) > 1
