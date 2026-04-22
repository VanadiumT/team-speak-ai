import httpx
from core.stt.base import BaseSTT


class MiniMaxSTT(BaseSTT):
    def __init__(self, api_key: str, api_url: str = "https://api.minimax.chat/v1"):
        self.api_key = api_key
        self.api_url = api_url
        self.client = httpx.AsyncClient()

    async def transcribe(self, audio_data: bytes) -> str:
        """将音频数据转为文本"""
        response = await self._call_api(audio_data)
        return response.get("text", "")

    async def _call_api(self, audio_data: bytes) -> dict:
        """调用 MiniMax API"""
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"model": "speech-01"}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = await self.client.post(
            f"{self.api_url}/speech/transcribe",
            files=files,
            data=data,
            headers=headers,
        )
        return response.json()

    async def transcribe_stream(self, audio_stream, sample_rate: int):
        """流式转写"""
        pass
