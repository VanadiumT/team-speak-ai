import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from core.tts.factory import TTSProvider, create_tts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["tts"])

_tts_instance = None


def get_tts_instance():
    """获取或创建 TTS 实例"""
    global _tts_instance
    if _tts_instance is None:
        provider = TTSProvider(settings.tts_provider)
        tts_config = {
            "edge": {
                "voice": getattr(settings, "edge_voice", "zh-CN-XiaoxiaoNeural"),
            },
            "minimax": {
                "api_key": settings.minimax_api_key,
                "model": settings.minimax_tts_model,
                "voice_id": settings.minimax_voice_id,
                "speed": settings.minimax_speed,
                "vol": settings.minimax_vol,
            },
        }
        config = tts_config.get(settings.tts_provider, tts_config["edge"])
        _tts_instance = create_tts(provider, config)
        logger.info(f"TTS instance created: {settings.tts_provider}")
    return _tts_instance


class SynthesizeRequest(BaseModel):
    text: str


@router.post("/synthesize")
async def synthesize_text(request: SynthesizeRequest):
    """
    将文本合成语音

    返回: MP3 音频文件
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        tts = get_tts_instance()
        audio_data = await tts.synthesize(request.text)
        return {"success": True, "audio_size": len(audio_data)}
    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers():
    """列出可用的 TTS 提供商"""
    return {
        "providers": [p.value for p in TTSProvider],
        "current": settings.tts_provider,
    }
