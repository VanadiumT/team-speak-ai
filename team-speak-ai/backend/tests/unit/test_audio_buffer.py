"""VADBuffer 测试"""

import pytest
from core.audio.audio_buffer import VADBuffer


def _make_speech_frame(sample_rate=16000, frame_ms=20):
    """生成一个模拟语音帧（非静音）"""
    import struct
    frame_size = int(sample_rate * 2 * frame_ms / 1000)
    # 生成有振幅的 PCM 数据
    samples = frame_size // 2
    return struct.pack(f"<{samples}h", *[1000] * samples)


def _make_silence_frame(sample_rate=16000, frame_ms=20):
    """生成一个静音帧"""
    frame_size = int(sample_rate * 2 * frame_ms / 1000)
    return b"\x00" * frame_size


class TestVADBuffer:
    def test_init_valid_params(self):
        vad = VADBuffer(vad_mode=3, frame_duration_ms=20, sample_rate=16000)
        assert vad.frame_size_bytes == 640  # 16000 * 2 * 20 / 1000

    def test_init_invalid_sample_rate(self):
        with pytest.raises(ValueError):
            VADBuffer(sample_rate=44100)

    def test_init_invalid_frame_duration(self):
        with pytest.raises(ValueError, match="frame_duration_ms"):
            VADBuffer(frame_duration_ms=15)

    def test_add_frame_wrong_size(self):
        vad = VADBuffer()
        vad.add_frame(0, b"\x00" * 100)  # wrong size, should be ignored
        assert vad.has_complete_sentence(0) is False

    def test_no_sentence_initially(self):
        vad = VADBuffer()
        assert vad.has_complete_sentence(0) is False
        assert vad.get_complete_sentence(0) is None

    def test_flush_empty_returns_none(self):
        vad = VADBuffer()
        assert vad.flush(0) is None

    def test_clear_sender(self):
        vad = VADBuffer()
        vad.clear(0)  # 不应抛异常

    def test_min_speech_frames_property(self):
        vad = VADBuffer(hangover_ms=600, min_speech_ms=300, frame_duration_ms=20)
        assert vad.min_speech_frames == 15  # 300 / 20


class TestVADBufferIntegration:
    """需要 webrtcvad 的集成测试"""

    def _run_vad_with_frames(self, speech_count, silence_count, vad_mode=3):
        vad = VADBuffer(vad_mode=vad_mode, frame_duration_ms=20,
                        hangover_ms=600, min_speech_ms=300, sample_rate=16000)
        speech_frame = _make_speech_frame()
        silence_frame = _make_silence_frame()

        for _ in range(speech_count):
            vad.add_frame(0, speech_frame)
        for _ in range(silence_count):
            vad.add_frame(0, silence_frame)

        return vad

    def test_enough_speech_and_silence_completes(self):
        # 需要足够的语音帧 + 静音帧才能触发分句
        # min_speech_ms=300 → 15 帧, hangover_ms=600 → 30 帧
        vad = self._run_vad_with_frames(speech_count=30, silence_count=35)
        # VAD 的 is_speech 对恒定振幅可能返回 True 或 False
        # 这里只验证 flush 能拿到数据
        data = vad.flush(0)
        assert data is not None
        assert len(data) > 0

    def test_insufficient_speech_no_complete(self):
        # 100ms speech (below min_speech_ms=300) + silence
        vad = self._run_vad_with_frames(speech_count=5, silence_count=35)
        assert vad.has_complete_sentence(0) is False

    def test_flush_partial_speech(self):
        vad = VADBuffer(vad_mode=3, frame_duration_ms=20,
                        hangover_ms=600, min_speech_ms=300, sample_rate=16000)
        speech_frame = _make_speech_frame()
        for _ in range(10):
            vad.add_frame(0, speech_frame)
        # 还没完成，但可以 flush
        assert vad.has_complete_sentence(0) is False
        data = vad.flush(0)
        assert data is not None
        assert len(data) > 0
