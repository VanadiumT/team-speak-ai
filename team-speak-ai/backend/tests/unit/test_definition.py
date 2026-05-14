"""Pipeline 定义模型测试"""

import pytest
from core.pipeline.definition import (
    PipelineDefinition, NodeDefinition, ConnectionDef,
    InputMapping, TriggerConfig, FlowSummary, SidebarNode,
    PortDef, PortsDef, PortPosition, NodeTypeDef, TabDef,
    port_input_key, port_output_key,
)


class TestPortDef:
    def test_create_port(self):
        p = PortDef(id="text-in", label="文本输入", data_type="string",
                     position=PortPosition(side="left", top=30))
        assert p.id == "text-in"
        assert p.data_type == "string"
        assert p.visibility == "always"
        assert p.repeatable is False

    def test_on_demand_port(self):
        p = PortDef(id="data-out", label="数据", data_type="any",
                     position=PortPosition(side="right", top=30),
                     visibility="on-demand")
        assert p.visibility == "on-demand"

    def test_repeatable_port(self):
        p = PortDef(id="ctx-in1", label="信息1", data_type="string",
                     position=PortPosition(side="left", top=114),
                     visibility="on-demand", repeatable=True,
                     group="ctx", min=0, max=20)
        assert p.repeatable is True
        assert p.group == "ctx"
        assert p.min == 0
        assert p.max == 20


class TestNodeTypeDef:
    def test_create_type_def(self):
        td = NodeTypeDef(
            type="start", name="开始", icon="play_arrow", color="secondary",
            default_config={"auto_run": True},
            tabs=[TabDef(id="config", label="配置")],
            ports=PortsDef(inputs=[], outputs=[
                PortDef(id="event-out", label="启动信号", data_type="event",
                         position=PortPosition(side="right", top=30)),
            ]),
        )
        assert td.type == "start"
        assert len(td.ports.outputs) == 1
        assert td.ports.outputs[0].id == "event-out"


class TestPipelineDefinition:
    def test_get_node(self, sample_flow_data):
        flow = PipelineDefinition(
            id=sample_flow_data["id"],
            name=sample_flow_data["name"],
            nodes=[
                NodeDefinition(id="n1", type="start", name="开始"),
                NodeDefinition(id="n2", type="text_input", name="文本"),
            ],
        )
        assert flow.get_node("n1") is not None
        assert flow.get_node("n1").type == "start"
        assert flow.get_node("nonexist") is None

    def test_get_connection(self):
        flow = PipelineDefinition(
            id="f1", name="test",
            connections=[ConnectionDef(id="c1", from_node="n1", from_port="out",
                                        to_node="n2", to_port="in")],
        )
        assert flow.get_connection("c1") is not None
        assert flow.get_connection("nonexist") is None

    def test_get_listener_nodes(self):
        flow = PipelineDefinition(
            id="f1", name="test",
            nodes=[
                NodeDefinition(id="n1", type="start", name="开始", listener=False),
                NodeDefinition(id="n2", type="stt_listen", name="STT", listener=True),
                NodeDefinition(id="n3", type="llm", name="LLM", listener=False),
            ],
        )
        listeners = flow.get_listener_nodes()
        assert len(listeners) == 1
        assert listeners[0].id == "n2"

    def test_get_action_nodes(self):
        flow = PipelineDefinition(
            id="f1", name="test",
            nodes=[
                NodeDefinition(id="n1", type="start", name="开始", listener=False),
                NodeDefinition(id="n2", type="stt_listen", name="STT", listener=True),
            ],
        )
        actions = flow.get_action_nodes()
        assert len(actions) == 1
        assert actions[0].id == "n1"


class TestPortKeyDerivation:
    def test_known_input_keys(self):
        assert port_input_key("llm-in") == "messages"
        assert port_input_key("stream-text-in") == "stream-text"
        assert port_input_key("batch-text-in") == "batch-text"
        assert port_input_key("stream-audio-in") == "stream-audio"
        assert port_input_key("batch-audio-in") == "batch-audio"

    def test_generic_input_key(self):
        assert port_input_key("text-in") == "text"
        assert port_input_key("ocr-in") == "ocr"
        assert port_input_key("trigger-in") == "trigger"

    def test_known_output_keys(self):
        assert port_output_key("data-out") == "value"
        assert port_output_key("text-out") == "text"
        assert port_output_key("img-out") == "file"
        assert port_output_key("ocr-out") == "text"
        assert port_output_key("ctx-out") == "messages"
        assert port_output_key("stream-text-out") == "response"
        assert port_output_key("stream-think-out") == "reasoning"
        assert port_output_key("stream-audio-out") == "stream-audio-out"

    def test_generic_output_key(self):
        assert port_output_key("done") == "done"
        assert port_output_key("hist-out") == "hist"
