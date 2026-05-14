"""OCR 节点测试 — IO 端口"""

import pytest
from core.pipeline.registry import NodeRegistry


class TestOCRPorts:
    def test_registered(self):
        assert "ocr" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("ocr")
        ids = [p.id for p in td.ports.inputs]
        assert "ocr-in" in ids
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("ocr")
        ids = [p.id for p in td.ports.outputs]
        assert "ocr-out" in ids
        assert "done" in ids
        assert "line-count" in ids
        assert "provider" in ids

    def test_ocr_in_type(self):
        td = NodeRegistry.get_type_def("ocr")
        inp = next(p for p in td.ports.inputs if p.id == "ocr-in")
        assert inp.data_type == "image"

    def test_ocr_out_type(self):
        td = NodeRegistry.get_type_def("ocr")
        out = next(p for p in td.ports.outputs if p.id == "ocr-out")
        assert out.data_type == "string"

    def test_line_count_type(self):
        td = NodeRegistry.get_type_def("ocr")
        out = next(p for p in td.ports.outputs if p.id == "line-count")
        assert out.data_type == "number"

    def test_provider_type(self):
        td = NodeRegistry.get_type_def("ocr")
        out = next(p for p in td.ports.outputs if p.id == "provider")
        assert out.data_type == "string"

    def test_trigger_in_type(self):
        td = NodeRegistry.get_type_def("ocr")
        inp = next(p for p in td.ports.inputs if p.id == "trigger-in")
        assert inp.data_type == "event"
        assert inp.visibility == "on-demand"

    def test_done_type(self):
        td = NodeRegistry.get_type_def("ocr")
        out = next(p for p in td.ports.outputs if p.id == "done")
        assert out.data_type == "event"
        assert out.visibility == "on-demand"
