"""SysVarManager 测试"""

import pytest
from core.variables.manager import SysVarManager


@pytest.fixture
def svm(tmp_data):
    return SysVarManager(str(tmp_data))


class TestSysVarCRUD:
    def test_get_nonexist_returns_default(self, svm):
        assert svm.get("nonexist", "fallback") == "fallback"
        assert svm.get("nonexist") is None

    def test_set_and_get(self, svm):
        svm.set("greeting", "你好")
        assert svm.get("greeting") == "你好"

    def test_set_overwrite(self, svm):
        svm.set("key", "v1")
        svm.set("key", "v2")
        assert svm.get("key") == "v2"

    def test_set_append(self, svm):
        svm.set("items", "a", "append")
        svm.set("items", "b", "append")
        assert svm.get("items") == ["a", "b"]

    def test_set_append_to_non_list(self, svm):
        svm.set("val", "single")
        svm.set("val", "appended", "append")
        assert svm.get("val") == ["single", "appended"]

    def test_delete(self, svm):
        svm.set("to_delete", "value")
        svm.delete("to_delete")
        assert svm.get("to_delete") is None

    def test_delete_nonexist_no_error(self, svm):
        svm.delete("nonexist")  # 不应抛异常

    def test_list_all(self, svm):
        svm.set("a", 1)
        svm.set("b", 2)
        all_vars = svm.list_all()
        assert all_vars == {"a": 1, "b": 2}


class TestSysVarPersistence:
    def test_persistence(self, svm):
        svm.set("persist_key", "persist_value")
        svm2 = SysVarManager(str(svm._file.parent))
        assert svm2.get("persist_key") == "persist_value"

    def test_corrupted_file_recovery(self, tmp_data):
        import json
        var_file = tmp_data / "system_vars.json"
        var_file.write_text("not json", encoding="utf-8")
        svm = SysVarManager(str(tmp_data))
        assert svm.list_all() == {}
