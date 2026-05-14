"""
Backend 配置权威源（Pydantic BaseSettings）。

配置优先级（高 → 低）：
  1. 环境变量 / .env 文件
  2. 本文件中的字段默认值（🔗 标记的参数有跨服务对齐要求，见 .env.example）
  3. Preset JSON 文件 (data/defaults/*.json) 提供各 AI 能力的平台+模型配置
  4. 节点级 config 覆盖（运行时由前端传入，保存在 flow JSON 中）

改动原则：此文件定义所有全局开关和连接信息。AI 提供者的具体参数
（temperature、voice_id 等）走 Preset 系统，不在此处硬编码。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # TeamSpeak（🔗 ts_ws_url 必须与 Java BridgeConfig.wsPort + wsPath 一致）
    ts_ws_url: str = "ws://localhost:8080/teamspeak/voice"
    ts_reconnect_interval: int = 5      # Python→Java WS 重连间隔（秒）
    ts_heartbeat_interval: int = 30     # 🔗 必须与 Java BridgeConfig.heartbeatIntervalSeconds 一致

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
    edge_tts_voice: str = "zh-CN-XiaoxiaoNeural"  # Edge TTS 默认语音

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
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # CORS（逗号分隔的允许来源列表，如 "http://localhost:5173,https://example.com"）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # WS 鉴权（空 = 不校验；设置后前端连接时必须带 ?token=xxx）
    ws_auth_token: str = ""

    # WebSocket 前端连接（🔗 必须与前端 pipeline.js 的 VITE_WS_* 一致）
    ws_heartbeat_timeout: int = 90      # 🔗 必须 ≥ 前端 VITE_WS_HEARTBEAT_TIMEOUT / 1000
    ws_max_msg_size: int = 65536        # 64KB

    class Config:
        env_file = ".env"


settings = Settings()