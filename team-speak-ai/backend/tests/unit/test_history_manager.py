"""HistoryManager 测试"""

import pytest
from core.history.manager import HistoryManager


@pytest.fixture
def hm(tmp_data):
    return HistoryManager(str(tmp_data))


class TestRecordOperation:
    @pytest.mark.asyncio
    async def test_record_and_undo(self, hm):
        op = await hm.record_operation("f1", "node.add", {"node_id": "n1"}, {"node_id": "n1"})
        assert op["action"] == "node.add"
        assert hm.can_undo("f1") is True
        assert hm.can_redo("f1") is False

    @pytest.mark.asyncio
    async def test_undo(self, hm):
        await hm.record_operation("f1", "node.add", {"node_id": "n1"}, {"node_id": "n1"})
        op = await hm.undo("f1")
        assert op is not None
        assert op["action"] == "node.add"
        assert hm.can_undo("f1") is False
        assert hm.can_redo("f1") is True

    @pytest.mark.asyncio
    async def test_redo(self, hm):
        await hm.record_operation("f1", "node.add", {"node_id": "n1"}, {"node_id": "n1"})
        await hm.undo("f1")
        op = await hm.redo("f1")
        assert op is not None
        assert hm.can_undo("f1") is True
        assert hm.can_redo("f1") is False

    @pytest.mark.asyncio
    async def test_undo_empty_returns_none(self, hm):
        result = await hm.undo("f1")
        assert result is None

    @pytest.mark.asyncio
    async def test_redo_empty_returns_none(self, hm):
        result = await hm.redo("f1")
        assert result is None

    @pytest.mark.asyncio
    async def test_new_operation_clears_redo(self, hm):
        await hm.record_operation("f1", "node.add", {"node_id": "n1"}, {"node_id": "n1"})
        await hm.undo("f1")
        assert hm.can_redo("f1") is True
        await hm.record_operation("f1", "node.add", {"node_id": "n2"}, {"node_id": "n2"})
        assert hm.can_redo("f1") is False


class TestMergeWindow:
    def test_should_merge_same_action_same_node(self, hm):
        from datetime import datetime, timezone
        prev = {"action": "node.update_config", "forward": {"node_id": "n1"},
                "timestamp": datetime.now(timezone.utc).isoformat()}
        curr = {"action": "node.update_config", "forward": {"node_id": "n1"},
                "timestamp": datetime.now(timezone.utc).isoformat()}
        assert hm._should_merge(prev, curr) is True

    def test_should_not_merge_different_action(self, hm):
        from datetime import datetime, timezone
        prev = {"action": "node.add", "forward": {"node_id": "n1"},
                "timestamp": datetime.now(timezone.utc).isoformat()}
        curr = {"action": "node.update_config", "forward": {"node_id": "n1"},
                "timestamp": datetime.now(timezone.utc).isoformat()}
        assert hm._should_merge(prev, curr) is False

    def test_should_not_merge_different_node(self, hm):
        from datetime import datetime, timezone
        prev = {"action": "node.update_config", "forward": {"node_id": "n1"},
                "timestamp": datetime.now(timezone.utc).isoformat()}
        curr = {"action": "node.update_config", "forward": {"node_id": "n2"},
                "timestamp": datetime.now(timezone.utc).isoformat()}
        assert hm._should_merge(prev, curr) is False

    def test_merge_ops(self, hm):
        prev = {"seq": 1, "action": "node.update_config", "timestamp": "t1",
                "forward": {"node_id": "n1", "config": {"text": "a"}},
                "reverse": {"node_id": "n1", "config": {"text": ""}}}
        curr = {"seq": 2, "action": "node.update_config", "timestamp": "t2",
                "forward": {"node_id": "n1", "config": {"text": "ab"}},
                "reverse": {"node_id": "n1", "config": {"text": "a"}}}
        merged = hm._merge_ops(prev, curr)
        assert merged["seq"] == 1
        assert merged["forward"]["config"]["text"] == "ab"
        assert merged["reverse"]["config"]["text"] == ""


class TestHistoryState:
    @pytest.mark.asyncio
    async def test_history_state(self, hm):
        state = hm.history_state("f1")
        assert state["can_undo"] is False
        assert state["can_redo"] is False

        await hm.record_operation("f1", "node.add", {"node_id": "n1"}, {"node_id": "n1"})
        state = hm.history_state("f1")
        assert state["can_undo"] is True
        assert state["last_action"] == "node.add"


class TestPersistence:
    @pytest.mark.asyncio
    async def test_jsonl_persistence(self, hm):
        await hm.record_operation("f1", "node.add", {"node_id": "n1"}, {"node_id": "n1"})
        await hm.record_operation("f1", "node.add", {"node_id": "n2"}, {"node_id": "n2"})

        # 重新加载
        hm2 = HistoryManager(str(hm.history_dir.parent))
        hm2.load_history("f1")
        assert hm2.can_undo("f1") is True

    @pytest.mark.asyncio
    async def test_stack_size_limit(self, hm):
        for i in range(105):
            await hm.record_operation("f1", "node.add", {"node_id": f"n{i}"}, {"node_id": f"n{i}"})
        stack = hm._get_undo_stack("f1")
        assert len(stack) <= 100
