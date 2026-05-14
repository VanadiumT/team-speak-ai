"""TSInput 节点测试 — IO 端口"""

import pytest
from core.pipeline.registry import NodeRegistry


class TestTSInputPorts:
    def test_registered(self):
        assert "ts_input" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("ts_input")
        ids = [p.id for p in td.ports.inputs]
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("ts_input")
        ids = [p.id for p in td.ports.outputs]
        assert "stream-pcm-out" in ids
        assert "trigger-out" in ids

    def test_trigger_in_type(self):
        td = NodeRegistry.get_type_def("ts_input")
        inp = next(p for p in td.ports.inputs if p.id == "trigger-in")
        assert inp.data_type == "event"
        assert inp.visibility == "on-demand"

    def test_stream_pcm_out_type(self):
        td = NodeRegistry.get_type_def("ts_input")
        out = next(p for p in td.ports.outputs if p.id == "stream-pcm-out")
        assert out.data_type == "audio"

    def test_trigger_out_type(self):
        td = NodeRegistry.get_type_def("ts_input")
        out = next(p for p in td.ports.outputs if p.id == "trigger-out")
        assert out.data_type == "event"
        assert out.visibility == "always"

    def test_default_config(self):
        td = NodeRegistry.get_type_def("ts_input")
        assert td.default_config["sample_rate"] == 16000
        assert td.default_config["channels"] == 1
        assert td.default_config["loopback"] is False
