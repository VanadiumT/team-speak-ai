from pydantic import BaseModel
from typing import Optional


class VoiceMessage(BaseModel):
    """TeamSpeak 语音消息"""
    type: str  # VOICE, WHISPER
    sender_id: int
    sender_name: Optional[str] = None
    codec_type: str
    timestamp: int
    sequence: int
    data: str  # Base64


class SendVoiceMessage(BaseModel):
    """发送语音消息"""
    type: str = "SEND_VOICE"
    data: str  # Base64
