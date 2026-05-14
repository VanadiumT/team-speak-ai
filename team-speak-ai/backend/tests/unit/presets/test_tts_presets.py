"""TTS 预设管理器测试"""

import pytest
from core.config.presets.tts import TtsPresetManager


@pytest.fixture
def pm(tmp_data):
    return TtsPresetManager(str(tmp_data))


class TestTtsPresetCRUD:
    def test_list_all_has_platforms(self, pm):
        data = pm.list_all()
        assert "platforms" in data

    def test_save_platform(self, pm):
        result = pm.save_platform({"name": "Edge TTS", "provider": "edge"})
        names = [p["name"] for p in result["platforms"]]
        assert "Edge TTS" in names

    def test_save_model(self, pm):
        data = pm.list_all()
        if data["platforms"]:
            pid = data["platforms"][0]["id"]
            result = pm.save_model(pid, {"name": "voice-1", "voice_id": "zh-CN-XiaoxiaoNeural"})
            p = next(p for p in result["platforms"] if p["id"] == pid)
            names = [m["name"] for m in p["models"]]
            assert "voice-1" in names

    def test_get_effective_config(self, pm):
        data = pm.list_all()
        if data["platforms"]:
            pid = data["platforms"][0]["id"]
            models = data["platforms"][0]["models"]
            if models:
                mid = models[0]["id"]
                effective = pm.get_effective_config(pid, mid, {})
                assert "provider" in effective
