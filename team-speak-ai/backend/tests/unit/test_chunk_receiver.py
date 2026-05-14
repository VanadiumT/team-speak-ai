"""ChunkReceiver 测试"""

import struct
import pytest
from core.upload.chunk_receiver import ChunkReceiver


@pytest.fixture
def receiver(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return ChunkReceiver(str(upload_dir))


class TestStartUpload:
    def test_start_upload_returns_id(self, receiver):
        result = receiver.start_upload("msg1", "test.wav", 1024, "audio/wav")
        assert "upload_id" in result
        assert result["upload_id"].startswith("upl_")

    def test_start_upload_too_large(self, receiver):
        with pytest.raises(ValueError, match="File too large"):
            receiver.start_upload("msg1", "big.wav", 999999999, "audio/wav")

    def test_start_upload_creates_session(self, receiver):
        result = receiver.start_upload("msg1", "test.wav", 1024, "audio/wav")
        session = receiver.get_session(result["upload_id"])
        assert session is not None
        assert session.name == "test.wav"
        assert session.size == 1024


class TestReceiveChunk:
    def test_receive_chunk(self, receiver):
        receiver.start_upload("msg1", "test.bin", 100, "application/octet-stream")
        received = receiver.receive_chunk("msg1", b"\x00" * 50)
        assert received == 50

    def test_receive_multiple_chunks(self, receiver):
        receiver.start_upload("msg1", "test.bin", 100, "application/octet-stream")
        receiver.receive_chunk("msg1", b"\x00" * 30)
        received = receiver.receive_chunk("msg1", b"\x00" * 30)
        assert received == 60

    def test_receive_chunk_no_session_raises(self, receiver):
        with pytest.raises(ValueError, match="No upload session"):
            receiver.receive_chunk("nonexist", b"\x00" * 10)

    def test_receive_chunk_exceeds_size(self, receiver):
        receiver.start_upload("msg1", "test.bin", 10, "application/octet-stream")
        received = receiver.receive_chunk("msg1", b"\x00" * 50)
        assert received == 10  # 不应超过声明大小


class TestCompleteUpload:
    def test_complete_upload(self, receiver, tmp_path):
        receiver.start_upload("msg1", "test.bin", 5, "application/octet-stream")
        receiver.receive_chunk("msg1", b"hello")
        result = receiver.complete_upload("msg1")
        assert "upload_id" in result
        assert "file_id" in result
        assert result["name"] == "test.bin"

    def test_complete_no_session_raises(self, receiver):
        with pytest.raises(ValueError, match="No upload session"):
            receiver.complete_upload("nonexist")


class TestCancelUpload:
    def test_cancel_upload(self, receiver):
        result = receiver.start_upload("msg1", "test.bin", 100, "application/octet-stream")
        receiver.cancel_upload(result["upload_id"])
        assert receiver.get_session(result["upload_id"]) is None

    def test_cancel_nonexist_no_error(self, receiver):
        receiver.cancel_upload("nonexist")  # 不应抛异常


class TestBinaryFrameParsing:
    def test_parse_valid_frame(self):
        msg_id = "test_msg"
        chunk = b"audio_data"
        header = msg_id.encode("utf-8")
        frame = struct.pack(">I", len(header)) + header + chunk
        parsed_id, parsed_chunk = ChunkReceiver.parse_binary_frame(frame)
        assert parsed_id == "test_msg"
        assert parsed_chunk == b"audio_data"

    def test_parse_frame_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            ChunkReceiver.parse_binary_frame(b"\x00")

    def test_parse_frame_empty_header(self):
        frame = struct.pack(">I", 0)  # header_len = 0
        with pytest.raises(ValueError, match="empty msg_id"):
            ChunkReceiver.parse_binary_frame(frame)

    def test_parse_frame_truncated(self):
        frame = struct.pack(">I", 100) + b"short"
        with pytest.raises(ValueError, match="truncated"):
            ChunkReceiver.parse_binary_frame(frame)


class TestSafeFilename:
    def test_safe_filename(self):
        assert ChunkReceiver._safe_filename("test.wav") == "test.wav"
        # os.path.basename 会取最后一段
        result = ChunkReceiver._safe_filename("../../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert ChunkReceiver._safe_filename("file name.wav") == "file name.wav"
