"""节点注册表测试"""

import pytest
from core.pipeline.registry import NodeRegistry


class TestNodeRegistry:
    def test_list_types(self):
        types = NodeRegistry.list_types()
        assert "start" in types
        assert "text_input" in types
        assert "display_text" in types
        assert "llm" in types
        assert "tts" in types
        assert "ocr" in types
        assert "stt_listen" in types
        assert "stt_history" in types
        assert "vad" in types
        assert "ts_input" in types
        assert "ts_output" in types
        assert "audio_player" in types
        assert "flow_var_read" in types
        assert "flow_var_write" in types
        assert "sys_var_read" in types
        assert "sys_var_write" in types
        assert "context_build" in types
        assert "input_image" in types

    def test_list_type_defs(self):
        defs = NodeRegistry.list_type_defs()
        assert len(defs) >= 18
        type_names = [d.type for d in defs]
        assert "start" in type_names
        assert "llm" in type_names

    def test_get_type_def(self):
        td = NodeRegistry.get_type_def("start")
        assert td.type == "start"
        assert td.name == "开始"
        assert len(td.ports.outputs) >= 1

    def test_get_type_def_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown node type"):
            NodeRegistry.get_type_def("nonexist")

    def test_create_node(self):
        node = NodeRegistry.create("start", {"auto_run": True})
        assert node.node_type == "start"
        assert node.config == {"auto_run": True}

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown node type"):
            NodeRegistry.create("nonexist", {})

    def test_start_node_ports(self):
        td = NodeRegistry.get_type_def("start")
        assert len(td.ports.inputs) == 0
        output_ids = [p.id for p in td.ports.outputs]
        assert "event-out" in output_ids
        assert "data-out" in output_ids

    def test_llm_node_ports(self):
        td = NodeRegistry.get_type_def("llm")
        input_ids = [p.id for p in td.ports.inputs]
        assert "llm-in" in input_ids
        assert "trigger-in" in input_ids
        assert "image-in" in input_ids
        output_ids = [p.id for p in td.ports.outputs]
        assert "stream-text-out" in output_ids
        assert "batch-text-out" in output_ids
        assert "done" in output_ids

    def test_text_input_node_ports(self):
        td = NodeRegistry.get_type_def("text_input")
        input_ids = [p.id for p in td.ports.inputs]
        assert "text-in" in input_ids
        assert "trigger-in" in input_ids
        output_ids = [p.id for p in td.ports.outputs]
        assert "text-out" in output_ids
        assert "done" in output_ids

    def test_context_build_repeatable_ports(self):
        td = NodeRegistry.get_type_def("context_build")
        ctx_ports = [p for p in td.ports.inputs if p.repeatable]
        assert len(ctx_ports) >= 1
        assert ctx_ports[0].group == "ctx"
        assert ctx_ports[0].min == 0
        assert ctx_ports[0].max == 20

    def test_tts_node_ports(self):
        td = NodeRegistry.get_type_def("tts")
        input_ids = [p.id for p in td.ports.inputs]
        assert "stream-text-in" in input_ids
        assert "batch-text-in" in input_ids
        output_ids = [p.id for p in td.ports.outputs]
        assert "stream-audio-out" in output_ids
        assert "batch-audio-out" in output_ids

    def test_vad_node_ports(self):
        td = NodeRegistry.get_type_def("vad")
        input_ids = [p.id for p in td.ports.inputs]
        assert "stream-audio-in" in input_ids
        output_ids = [p.id for p in td.ports.outputs]
        assert "stream-chunk-out" in output_ids
        assert "trigger-out" in output_ids

    def test_ocr_node_ports(self):
        td = NodeRegistry.get_type_def("ocr")
        input_ids = [p.id for p in td.ports.inputs]
        assert "ocr-in" in input_ids
        output_ids = [p.id for p in td.ports.outputs]
        assert "ocr-out" in output_ids
        assert "line-count" in output_ids
        assert "provider" in output_ids
