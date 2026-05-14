"""Flow 持久化集成测试"""

import json
import pytest
from core.flow.manager import FlowManager
from core.pipeline.definition import NodeDefinition, ConnectionDef


@pytest.fixture
def fm(tmp_data):
    return FlowManager(str(tmp_data))


class TestFlowJsonPersistence:
    def test_flow_survives_reload(self, fm):
        flow = fm.create_flow("持久化测试")
        flow_id = flow.id

        # 重新加载
        loaded = fm.load_flow(flow_id)
        assert loaded.name == "持久化测试"
        assert loaded.id == flow_id

    @pytest.mark.asyncio
    async def test_nodes_survive_reload(self, fm):
        flow = fm.create_flow("节点持久化")
        await fm.add_node(flow.id, NodeDefinition(id="n1", type="start", name="开始"))
        await fm.add_node(flow.id, NodeDefinition(id="n2", type="llm", name="LLM"))

        loaded = fm.load_flow(flow.id)
        assert len(loaded.nodes) == 2
        assert loaded.nodes[0].type == "start"
        assert loaded.nodes[1].type == "llm"

    @pytest.mark.asyncio
    async def test_connections_survive_reload(self, fm):
        flow = fm.create_flow("连线持久化")
        await fm.add_node(flow.id, NodeDefinition(id="n1", type="start", name="开始"))
        await fm.add_node(flow.id, NodeDefinition(id="n2", type="text_input", name="文本"))
        conn = ConnectionDef(id="c1", from_node="n1", from_port="event-out",
                              to_node="n2", to_port="trigger-in")
        await fm.add_connection(flow.id, conn)

        loaded = fm.load_flow(flow.id)
        assert len(loaded.connections) == 1
        assert loaded.connections[0].from_node == "n1"

    @pytest.mark.asyncio
    async def test_config_survives_reload(self, fm):
        flow = fm.create_flow("配置持久化")
        await fm.add_node(flow.id, NodeDefinition(
            id="n1", type="text_input", name="文本",
            config={"text": "Hello", "mode": "static"},
        ))

        loaded = fm.load_flow(flow.id)
        assert loaded.nodes[0].config["text"] == "Hello"
        assert loaded.nodes[0].config["mode"] == "static"

    @pytest.mark.asyncio
    async def test_params_survive_reload(self, fm):
        flow = fm.create_flow("参数持久化")
        await fm.update_flow_params(flow.id, {"greeting": "你好", "lang": "zh"})

        loaded = fm.load_flow(flow.id)
        assert loaded.params["greeting"] == "你好"
        assert loaded.params["lang"] == "zh"

    def test_json_file_is_valid_json(self, fm, tmp_data):
        fm.create_flow("JSON校验")
        files = list((tmp_data / "flows").glob("*.json"))
        assert len(files) == 1
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "id" in data
        assert "name" in data
        assert "nodes" in data
        assert "connections" in data

    @pytest.mark.asyncio
    async def test_group_persistence(self, fm):
        flow = fm.create_flow("分组测试")
        await fm.update_flow_group(flow.id, "暗区/子分组")

        loaded = fm.load_flow(flow.id)
        assert loaded.group == "暗区/子分组"

    def test_groups_json_persistence(self, fm):
        fm.create_group("group_a")
        fm.create_group("group_b")
        fm2 = FlowManager(str(fm.data_dir))
        groups = fm2.list_groups()
        assert "group_a" in groups
        assert "group_b" in groups
