"""SysVar 持久化集成测试"""

import pytest
from core.variables.manager import SysVarManager


class TestSysVarPersistence:
    def test_set_survives_reload(self, tmp_data):
        svm = SysVarManager(str(tmp_data))
        svm.set("key1", "value1")
        svm.set("key2", {"nested": True})

        svm2 = SysVarManager(str(tmp_data))
        assert svm2.get("key1") == "value1"
        assert svm2.get("key2") == {"nested": True}

    def test_append_survives_reload(self, tmp_data):
        svm = SysVarManager(str(tmp_data))
        svm.set("items", "a", "append")
        svm.set("items", "b", "append")

        svm2 = SysVarManager(str(tmp_data))
        assert svm2.get("items") == ["a", "b"]

    def test_delete_survives_reload(self, tmp_data):
        svm = SysVarManager(str(tmp_data))
        svm.set("to_delete", "value")
        svm.delete("to_delete")

        svm2 = SysVarManager(str(tmp_data))
        assert svm2.get("to_delete") is None

    def test_file_is_valid_json(self, tmp_data):
        import json
        svm = SysVarManager(str(tmp_data))
        svm.set("k", "v")
        with open(tmp_data / "system_vars.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"k": "v"}
