"""AudioBus 测试"""

import asyncio
import pytest
from core.audio.audio_bus import AudioBus


@pytest.fixture
def bus():
    return AudioBus()


class TestAudioBusPubSub:
    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self, bus):
        bus.subscribe("listener_1")
        assert bus.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self, bus):
        bus.subscribe("listener_1")
        bus.unsubscribe("listener_1")
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self, bus):
        bus.subscribe("listener_1")
        await bus.publish(b"audio_data", sender_id=1)
        frame = await bus.get_audio("listener_1", timeout=1.0)
        assert frame is not None
        assert frame["data"] == b"audio_data"
        assert frame["sender_id"] == 1

    @pytest.mark.asyncio
    async def test_publish_to_multiple_subscribers(self, bus):
        bus.subscribe("l1")
        bus.subscribe("l2")
        await bus.publish(b"data")
        f1 = await bus.get_audio("l1", timeout=1.0)
        f2 = await bus.get_audio("l2", timeout=1.0)
        assert f1 is not None
        assert f2 is not None

    @pytest.mark.asyncio
    async def test_get_audio_unsubscribed_returns_none(self, bus):
        result = await bus.get_audio("nonexist", timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_audio_timeout_returns_none(self, bus):
        bus.subscribe("listener_1")
        result = await bus.get_audio("listener_1", timeout=0.05)
        assert result is None

    @pytest.mark.asyncio
    async def test_queue_full_drops_oldest(self, bus):
        bus.subscribe("listener_1", maxsize=2)
        await bus.publish(b"frame1")
        await bus.publish(b"frame2")
        await bus.publish(b"frame3")  # 应该丢弃 frame1
        f1 = await bus.get_audio("listener_1", timeout=1.0)
        assert f1["data"] == b"frame2"

    @pytest.mark.asyncio
    async def test_subscriber_count(self, bus):
        assert bus.subscriber_count == 0
        bus.subscribe("a")
        bus.subscribe("b")
        assert bus.subscriber_count == 2
        bus.unsubscribe("a")
        assert bus.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_subscribe_idempotent(self, bus):
        bus.subscribe("l1")
        bus.subscribe("l1")  # 不应创建第二个
        assert bus.subscriber_count == 1
