import asyncio
import json
import ssl
import os
from typing import AsyncGenerator

import websockets

from core.tts.base import BaseTTS


class MiniMaxTTS(BaseTTS):
    """MiniMax Text-to-Speech via WebSocket streaming"""

    def __init__(
        self,
        api_key: str = "",
        model: str = "speech-2.8-hd",
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: float = 0,
        sample_rate: int = 32000,
        bitrate: int = 128000,
        file_format: str = "mp3",
        channel: int = 1,
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.model = model
        self.voice_id = voice_id
        self.speed = speed
        self.vol = vol
        self.pitch = pitch
        self.sample_rate = sample_rate
        self.bitrate = bitrate
        self.file_format = file_format
        self.channel = channel
        self._ws = None

    async def _connect(self):
        """Establish WebSocket connection"""
        url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        ws = await websockets.connect(url, additional_headers=headers, ssl=ssl_context)
        response = json.loads(await ws.recv())
        if response.get("event") == "connected_success":
            return ws
        raise ConnectionError(f"Connection failed: {response}")

    async def _start_task(self, ws):
        """Send task start request"""
        start_msg = {
            "event": "task_start",
            "model": self.model,
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": self.speed,
                "vol": self.vol,
                "pitch": self.pitch,
                "english_normalization": False,
            },
            "audio_setting": {
                "sample_rate": self.sample_rate,
                "bitrate": self.bitrate,
                "format": self.file_format,
                "channel": self.channel,
            },
        }
        await ws.send(json.dumps(start_msg))
        response = json.loads(await ws.recv())
        if response.get("event") == "task_started":
            return True
        raise ConnectionError(f"Task start failed: {response}")

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio (non-streaming)"""
        audio_chunks = []
        async for chunk in self.synthesize_stream(text):
            audio_chunks.append(chunk)
        return b"".join(audio_chunks)

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream audio chunks from text"""
        ws = await self._connect()
        await self._start_task(ws)

        try:
            await ws.send(json.dumps({"event": "task_continue", "text": text}))

            while True:
                response = json.loads(await ws.recv())

                if "data" in response and "audio" in response["data"]:
                    audio_hex = response["data"]["audio"]
                    if audio_hex:
                        yield bytes.fromhex(audio_hex)

                if response.get("is_final"):
                    break

        finally:
            await ws.send(json.dumps({"event": "task_finish"}))
            await ws.close()
