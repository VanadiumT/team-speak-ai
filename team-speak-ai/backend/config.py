from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # TeamSpeak
    ts_ws_url: str = "ws://localhost:8080/teamspeak/voice"
    ts_reconnect_interval: int = 5
    ts_heartbeat_interval: int = 25

    # STT Provider (whisper, minimax, sensevoice)
    stt_provider: str = "sensevoice"

    # SenseVoice (本地 STT - 阿里开源)
    sensevoice_model: str = "iic/SenseVoiceSmall"
    sensevoice_device: str = "cpu"  # 默认使用 CPU

    # Whisper (本地 STT)
    whisper_model: str = "base"
    whisper_device: str = "cuda"

    # MiniMax STT
    minimax_api_key: str = ""
    minimax_api_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "speech-01"

    # TTS
    tts_provider: str = "edge"

    # 文件存储
    upload_dir: str = "./uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    # WebSocket
    ws_reconnect_interval: int = 3000  # ms
    ws_max_reconnect_attempts: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
