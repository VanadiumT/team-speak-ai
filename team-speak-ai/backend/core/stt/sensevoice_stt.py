import io
import asyncio
import tempfile
import os
import wave
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, AsyncIterator
import numpy as np
import soundfile as sf

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
from core.stt.base import BaseSTT


# 全局线程池，避免阻塞事件循环
_executor: Optional[ThreadPoolExecutor] = None


def get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sensevoice_")
    return _executor


class SenseVoiceSTT(BaseSTT):
    """SenseVoice 语音识别实现 - 支持实时流式转写"""

    # SenseVoice 期望的采样率
    TARGET_SAMPLE_RATE = 16000

    def __init__(
        self,
        model_dir: str = "iic/SenseVoiceSmall",
        device: str = "cpu",
        disable_vad: bool = True,
    ):
        """
        初始化 SenseVoice 模型

        Args:
            model_dir: ModelScope 模型名称或本地路径
            device: 设备类型 ("cuda", "cpu")
            disable_vad: 是否禁用 VAD (实时语音建议禁用)
        """
        self.model = AutoModel(
            model=model_dir,
            trust_remote_code=True,
            device=device,
            vad_model="fsmn-vad" if not disable_vad else None,
            vad_kwargs={"max_single_segment_time": 30000},
        )
        self.device = device

    def _resample_audio(self, audio_data: bytes, original_sr: int = 48000) -> bytes:
        """
        重采样音频到 SenseVoice 期望的 16kHz

        Args:
            audio_data: 原始音频数据 (bytes)
            original_sr: 原始采样率 (默认 48000 for Opus)

        Returns:
            重采样后的 PCM 音频数据 (bytes)
        """
        try:
            # 尝试用 soundfile 加载
            audio_np, sr = sf.read(io.BytesIO(audio_data), dtype='float32')

            # 如果原始采样率不是目标采样率，则重采样
            if sr != self.TARGET_SAMPLE_RATE:
                from scipy import signal
                num_samples = int(len(audio_np) * self.TARGET_SAMPLE_RATE / sr)
                audio_np = signal.resample(audio_np, num_samples)

            # 单声道
            if len(audio_np.shape) > 1:
                audio_np = audio_np[:, 0]

            # 归一化到 [-1, 1] 然后转换为 int16
            audio_np = np.clip(audio_np, -1.0, 1.0)
            audio_int16 = (audio_np * 32767).astype(np.int16)

            return audio_int16.tobytes()

        except Exception as e:
            # 如果处理失败，返回原始数据
            return audio_data

    def _write_wav(self, filepath: str, audio_data: bytes, sample_rate: int):
        """使用标准库写入 WAV 文件"""
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)  # mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)

    def _transcribe_sync(self, audio_data: bytes) -> str:
        """
        同步转写方法 (在线程池中执行，不阻塞事件循环)

        Args:
            audio_data: 音频数据 (bytes)

        Returns:
            识别的文本
        """
        # 重采样到 16kHz
        resampled_data = self._resample_audio(audio_data)

        # 创建临时 WAV 文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        try:
            # 写入标准 WAV 文件
            self._write_wav(temp_path, resampled_data, self.TARGET_SAMPLE_RATE)

            # 调用模型进行识别
            result = self.model.generate(
                input=temp_path,
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=60,
            )

            # 解析结果
            if result and len(result) > 0:
                text = result[0].get("text", "")
                return rich_transcription_postprocess(text)

            return ""

        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def transcribe(self, audio_data: bytes) -> str:
        """
        异步非阻塞转写

        Args:
            audio_data: 原始音频数据 (支持多种格式)

        Returns:
            识别的文本
        """
        loop = asyncio.get_event_loop()
        executor = get_executor()

        # 在线程池中执行阻塞的转写操作
        result = await loop.run_in_executor(
            executor,
            self._transcribe_sync,
            audio_data
        )
        return result

    async def transcribe_stream(self, audio_stream, sample_rate: int = 48000):
        """
        流式转写 (实时语音场景)

        Args:
            audio_stream: 音频流 (可迭代的 bytes)
            sample_rate: 音频采样率 (默认 48000 for TeamSpeak Opus)

        Yields:
            识别的文本片段
        """
        loop = asyncio.get_event_loop()
        executor = get_executor()

        buffer = bytearray()
        chunk_size = 16000 * 2 * 1  # 16kHz * 16bit * 1sec

        async for chunk in self._async_audio_iter(audio_stream):
            buffer.extend(chunk)

            # 当累积了足够的数据时进行转写
            while len(buffer) >= chunk_size:
                audio_data = bytes(buffer[:chunk_size])
                buffer = buffer[chunk_size:]

                # 非阻塞转写
                result = await loop.run_in_executor(
                    executor,
                    self._transcribe_sync,
                    audio_data
                )

                if result:
                    yield result

    async def _async_audio_iter(self, audio_stream) -> AsyncIterator[bytes]:
        """
        异步迭代音频流

        Args:
            audio_stream: 同步可迭代对象

        Yields:
            音频数据片段
        """
        for chunk in audio_stream:
            yield chunk
            # 允许其他协程执行
            await asyncio.sleep(0)

    async def transcribe_bytes(self, audio_data: bytes, sample_rate: int = 48000) -> str:
        """
        直接转写字节数据 (便捷方法)

        Args:
            audio_data: 音频字节数据
            sample_rate: 采样率

        Returns:
            识别的文本
        """
        return await self.transcribe(audio_data)
