import logging
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import ws_teamspeak, ws_main

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TeamSpeak AI Backend",
    version="0.1.0",
    description="TeamSpeak Voice Bridge with AI capabilities"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_teamspeak.router)  # /ws/teamspeak — 语音桥接
app.include_router(ws_main.router)       # /ws — 统一管理端点


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "TeamSpeak AI Backend",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    from api.routes.ws_teamspeak import ts_client
    from core.app_context import get_app_context
    ctx = get_app_context()
    return {
        "status": "healthy",
        "teamspeak_connected": ts_client.connected,
        "pipelines_loaded": len(ctx.pipeline_engine.get_definitions()),
    }


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("TeamSpeak AI Backend Starting...")
    logger.info(f"Server: {settings.host}:{settings.port}")
    logger.info(f"TeamSpeak WS URL: {settings.ts_ws_url}")
    logger.info(f"STT Provider: {settings.stt_provider}")
    logger.info(f"TTS Provider: {settings.tts_provider}")
    logger.info(f"OCR Provider: {settings.ocr_provider}")
    logger.info(f"Log Provider: {settings.log_provider} -> {settings.log_dir}")
    logger.info("=" * 50)

    # 计算目录路径
    data_dir = os.path.join(os.path.dirname(__file__), settings.data_dir)
    os.makedirs(data_dir, exist_ok=True)
    upload_dir = os.path.join(os.path.dirname(__file__), settings.upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    config_dir = getattr(settings, "pipeline_config_dir", "config/pipelines")
    abs_config_dir = os.path.join(os.path.dirname(__file__), config_dir)
    if not os.path.exists(abs_config_dir):
        logger.warning(f"Pipeline config dir not found: {abs_config_dir}")
        abs_config_dir = ""

    # 初始化结构化日志模块
    from core.logger.factory import create_logger, LoggerProvider
    from core.logger.handler import install_logger

    log_instance = create_logger(
        LoggerProvider(settings.log_provider),
        {"log_dir": settings.log_dir, "keep_days": settings.log_keep_days},
    )
    install_logger(log_instance)
    logger.info(f"Logger initialized: {settings.log_provider} -> {settings.log_dir}")

    # 一次性创建所有应用服务（替代原来的 12 次 init_xxx 调用）
    from core.app_context import AppContext, set_app_context

    ctx = AppContext.create(
        data_dir=data_dir,
        upload_dir=upload_dir,
        max_upload_size=settings.max_upload_size,
        pipeline_config_dir=abs_config_dir,
    )
    set_app_context(ctx)

    # 启动后台任务
    ctx.start_background_tasks()

    # 连接 TeamSpeak Voice Bridge
    from api.routes.ws_teamspeak import ts_client
    logger.info("Attempting to connect to TeamSpeak Voice Bridge...")
    success = await ts_client.connect()
    if success:
        logger.info("Successfully connected to TeamSpeak Voice Bridge")
    else:
        logger.warning("Failed to connect to TeamSpeak Voice Bridge")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    from api.routes.ws_teamspeak import ts_client
    await ts_client.disconnect()
    from core.app_context import get_app_context
    try:
        ctx = get_app_context()
        await ctx.shutdown()
    except RuntimeError:
        pass  # AppContext was never initialized
    from core.logger.handler import close_logger
    close_logger()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
