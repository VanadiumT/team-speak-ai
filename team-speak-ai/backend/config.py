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

    # MiniMax TTS
    minimax_tts_model: str = "speech-2.8-hd"
    minimax_voice_id: str = "male-qn-qingse"
    minimax_speed: float = 1.0
    minimax_vol: float = 1

    # LLM Provider (openai)
    llm_provider: str = "openai"

    # OpenAI (MiniMax OpenAI 兼容)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.minimaxi.com/v1"
    openai_model: str = "MiniMax-M2.7"
    openai_reasoning_split: bool = True  # MiniMax 思考过程分离

    # OCR Provider (easyocr, paddleocr)
    ocr_provider: str = "easyocr"

    # PaddleOCR
    paddleocr_det_model: str = "ch"
    paddleocr_rec_model: str = "ch"
    paddleocr_use_angle_cls: bool = True
    paddleocr_use_gpu: bool = False

    # Pipeline
    pipeline_config_dir: str = "config/pipelines"

    # 数据目录（流程 JSON、默认配置、操作历史、上传文件）
    data_dir: str = "./data"

    # 文件存储
    upload_dir: str = "./data/uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_upload_size: int = 100 * 1024 * 1024  # 100MB (WebSocket binary upload)

    # Logger
    log_provider: str = "file"
    log_dir: str = "logs"
    log_keep_days: int = 30

    # WebSocket
    ws_reconnect_interval: int = 3000  # ms
    ws_max_reconnect_attempts: int = 10
    ws_max_connections_per_ip: int = 5

    class Config:
        env_file = ".env"


settings = Settings()