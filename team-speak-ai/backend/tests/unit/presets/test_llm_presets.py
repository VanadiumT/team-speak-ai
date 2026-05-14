"""LLM 预设管理器测试"""

import pytest
from core.config.presets.llm import PresetManager


@pytest.fixture
def pm(tmp_data):
    return PresetManager(str(tmp_data))


class TestPresetManagerCRUD:
    def test_list_all_has_platforms(self, pm):
        data = pm.list_all()
        assert "platforms" in data
        assert len(data["platforms"]) >= 1

    def test_default_platform_has_model(self, pm):
        data = pm.list_all()
        platform = data["platforms"][0]
        assert "id" in platform
        assert "name" in platform
        assert "models" in platform
        assert len(platform["models"]) >= 1

    def test_save_platform_new(self, pm):
        result = pm.save_platform({"name": "测试平台", "provider": "openai",
                                    "base_url": "https://api.test.com", "api_key": "key123"})
        names = [p["name"] for p in result["platforms"]]
        assert "测试平台" in names

    def test_save_platform_update(self, pm):
        data = pm.list_all()
        pid = data["platforms"][0]["id"]
        pm.save_platform({"id": pid, "name": "修改后"})
        data2 = pm.list_all()
        p = next(p for p in data2["platforms"] if p["id"] == pid)
        assert p["name"] == "修改后"

    def test_delete_platform(self, pm):
        result = pm.save_platform({"name": "待删除", "provider": "openai"})
        pid = [p for p in result["platforms"] if p["name"] == "待删除"][0]["id"]
        pm.delete_platform(pid)
        data = pm.list_all()
        ids = [p["id"] for p in data["platforms"]]
        assert pid not in ids

    def test_save_model_new(self, pm):
        data = pm.list_all()
        pid = data["platforms"][0]["id"]
        result = pm.save_model(pid, {"name": "gpt-4", "temperature": 0.5})
        p = next(p for p in result["platforms"] if p["id"] == pid)
        names = [m["name"] for m in p["models"]]
        assert "gpt-4" in names

    def test_save_model_update(self, pm):
        data = pm.list_all()
        pid = data["platforms"][0]["id"]
        mid = data["platforms"][0]["models"][0]["id"]
        pm.save_model(pid, {"id": mid, "temperature": 0.9})
        data2 = pm.list_all()
        p = next(p for p in data2["platforms"] if p["id"] == pid)
        m = next(m for m in p["models"] if m["id"] == mid)
        assert m["temperature"] == 0.9

    def test_delete_model(self, pm):
        data = pm.list_all()
        pid = data["platforms"][0]["id"]
        result = pm.save_model(pid, {"name": "temp-model"})
        mid = [m for m in next(p for p in result["platforms"] if p["id"] == pid)["models"]
               if m["name"] == "temp-model"][0]["id"]
        pm.delete_model(pid, mid)
        data2 = pm.list_all()
        p = next(p for p in data2["platforms"] if p["id"] == pid)
        mids = [m["id"] for m in p["models"]]
        assert mid not in mids


class TestGetEffectiveConfig:
    def test_effective_config(self, pm):
        data = pm.list_all()
        pid = data["platforms"][0]["id"]
        mid = data["platforms"][0]["models"][0]["id"]
        effective = pm.get_effective_config(pid, mid, {})
        assert "provider" in effective
        assert "model" in effective

    def test_effective_config_with_overrides(self, pm):
        data = pm.list_all()
        pid = data["platforms"][0]["id"]
        mid = data["platforms"][0]["models"][0]["id"]
        effective = pm.get_effective_config(pid, mid, {"temperature": 0.1})
        assert effective["temperature"] == 0.1

    def test_effective_config_nonexist_raises(self, pm):
        with pytest.raises((ValueError, KeyError)):
            pm.get_effective_config("nonexist", "nonexist", {})


class TestPresetPersistence:
    def test_persistence(self, tmp_data):
        pm = PresetManager(str(tmp_data))
        pm.save_platform({"name": "持久化测试", "provider": "openai"})
        pm2 = PresetManager(str(tmp_data))
        data = pm2.list_all()
        names = [p["name"] for p in data["platforms"]]
        assert "持久化测试" in names
