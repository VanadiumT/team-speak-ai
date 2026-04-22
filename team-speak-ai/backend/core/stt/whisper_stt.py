import io
from faster_whisper import WhisperModel
from core.stt.base import BaseSTT


class WhisperSTT(BaseSTT):
    def __init__(self, model_name: str = "base", device: str = "cuda"):
        self.model = WhisperModel(model_name, device=device)

    async def transcribe(self, audio_data: bytes) -> str:
        """将音频数据转为文本"""
        audio_file = io.BytesIO(audio_data)
        segments, _ = self.model.transcribe(audio_file, language="auto")
        text = "".join([seg.text for seg in segments])
        return text.strip()

    async def transcribe_stream(self, audio_stream, sample_rate: int):
        """流式转写"""
        pass
