"""NotificationManager 测试"""

import pytest
from core.notification.manager import NotificationManager


@pytest.fixture
def nm(tmp_data):
    return NotificationManager(str(tmp_data))


class TestNotificationSave:
    def test_save_returns_item(self, nm):
        item = nm.save("f1", "标题", "内容", "info", "n1")
        assert item["title"] == "标题"
        assert item["content"] == "内容"
        assert item["event_type"] == "info"
        assert item["node_id"] == "n1"
        assert "id" in item
        assert "timestamp" in item

    def test_save_increments_unread(self, nm):
        nm.save("f1", "t1", "c1")
        nm.save("f1", "t2", "c2")
        assert nm.get_unread_count("f1") == 2

    def test_unread_count_per_flow(self, nm):
        nm.save("f1", "t1", "c1")
        nm.save("f2", "t2", "c2")
        assert nm.get_unread_count("f1") == 1
        assert nm.get_unread_count("f2") == 1


class TestNotificationList:
    def test_list_returns_items(self, nm):
        nm.save("f1", "标题A", "内容A")
        nm.save("f1", "标题B", "内容B")
        result = nm.list_notifications("f1")
        assert len(result["items"]) == 2
        assert result["unread"] == 2

    def test_list_with_limit(self, nm):
        for i in range(5):
            nm.save("f1", f"t{i}", f"c{i}")
        result = nm.list_notifications("f1", limit=3)
        assert len(result["items"]) == 3
        assert result["has_more"] is True

    def test_list_empty_flow(self, nm):
        result = nm.list_notifications("empty_flow")
        assert result["items"] == []
        assert result["unread"] == 0

    def test_list_items_have_read_field(self, nm):
        nm.save("f1", "t1", "c1")
        result = nm.list_notifications("f1")
        assert "read" in result["items"][0]
        assert result["items"][0]["read"] is False


class TestNotificationMarkRead:
    def test_mark_single_read(self, nm):
        item = nm.save("f1", "t1", "c1")
        remaining = nm.mark_read("f1", item["id"])
        assert remaining == 0
        assert nm.get_unread_count("f1") == 0

    def test_mark_all_read(self, nm):
        nm.save("f1", "t1", "c1")
        nm.save("f1", "t2", "c2")
        remaining = nm.mark_read("f1")
        assert remaining == 0
        result = nm.list_notifications("f1")
        assert all(i["read"] for i in result["items"])

    def test_mark_read_preserves_other_flows(self, nm):
        nm.save("f1", "t1", "c1")
        nm.save("f2", "t2", "c2")
        nm.mark_read("f1")
        assert nm.get_unread_count("f2") == 1


class TestNotificationPersistence:
    def test_persistence(self, nm):
        nm.save("f1", "持久化测试", "内容")
        nm2 = NotificationManager(str(nm._notifications_dir.parent))
        result = nm2.list_notifications("f1")
        assert len(result["items"]) == 1
