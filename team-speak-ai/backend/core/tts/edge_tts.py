import asyncio
import edge_tts
from core.tts.base import BaseTTS


class EdgeTTS(BaseTTS):
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        """将文本转为语音"""
        communicate = edge_tts.Communicate(text, self.voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    async def synthesize_stream(self, text: str):
        """流式合成"""
        communicate = edge_tts.Communicate(text, self.voice)
        async for chunk in communicate.stream():
            yield chunk
