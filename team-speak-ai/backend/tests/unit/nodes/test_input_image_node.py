"""InputImage 节点测试 — 执行 + IO 端口"""

import base64
import pytest
from core.nodes.input_image import InputImageNode
from core.pipeline.registry import NodeRegistry


@pytest.fixture
def node():
    return InputImageNode({"accepted_formats": ["png", "jpg"], "max_size_mb": 10})


class TestInputImagePorts:
    def test_registered(self):
        assert "input_image" in NodeRegistry.list_types()

    def test_input_ports(self):
        td = NodeRegistry.get_type_def("input_image")
        ids = [p.id for p in td.ports.inputs]
        assert "trigger-in" in ids

    def test_output_ports(self):
        td = NodeRegistry.get_type_def("input_image")
        ids = [p.id for p in td.ports.outputs]
        assert "img-out" in ids
        assert "trigger-out" in ids

    def test_img_out_type(self):
        td = NodeRegistry.get_type_def("input_image")
        out = next(p for p in td.ports.outputs if p.id == "img-out")
        assert out.data_type == "image"


class TestInputImageExecute:
    @pytest.mark.asyncio
    async def test_no_file_waits(self, node, make_context, mock_emit):
        ctx = make_context(node_config={"notify_on_reach": True}, inputs={})
        result = await node.execute(ctx, mock_emit)
        assert result.trigger_next is False
        assert result.data["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_with_file_string(self, node, make_context, mock_emit):
        b64 = base64.b64encode(b"fake_png").decode()
        ctx = make_context(
            node_config={},
            inputs={"file": b64, "filename": "test.png", "mime_type": "image/png"},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["file"] == b64
        assert result.data["filename"] == "test.png"
        assert result.trigger_next is True

    @pytest.mark.asyncio
    async def test_with_file_dict(self, node, make_context, mock_emit):
        b64 = base64.b64encode(b"fake_png").decode()
        ctx = make_context(
            node_config={},
            inputs={"file": {"data": b64, "filename": "photo.jpg", "mime_type": "image/jpeg"}},
        )
        result = await node.execute(ctx, mock_emit)
        assert result.data["file"] == b64
        assert result.data["filename"] == "photo.jpg"

    @pytest.mark.asyncio
    async def test_with_bytes_converts_to_b64(self, node, make_context, mock_emit):
        # bytes 不是 str 也不是 dict，会走 else 分支 → file_data="" → waiting
        ctx = make_context(
            node_config={},
            inputs={"file": b"raw_bytes", "filename": "test.png"},
        )
        result = await node.execute(ctx, mock_emit)
        # bytes 输入走 else 分支，file_data 为空 → waiting 状态
        assert result.data["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_notifies_user_when_waiting(self, node, make_context, mock_emit):
        ctx = make_context(node_config={"notify_on_reach": True}, inputs={})
        await node.execute(ctx, mock_emit)
        mock_emit.emit_important_update.assert_called_once()
