import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import ws_client, ws_teamspeak, control, files, tts

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TeamSpeak AI Backend",
    version="0.1.0",
    description="TeamSpeak Voice Bridge with AI capabilities"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ws_client.router, tags=["client"])
app.include_router(ws_teamspeak.router, tags=["teamspeak"])
app.include_router(control.router, prefix="/api", tags=["control"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(tts.router, prefix="/api", tags=["tts"])


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
    return {
        "status": "healthy",
        "teamspeak_connected": ts_client.connected
    }


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("TeamSpeak AI Backend Starting...")
    logger.info(f"Server: {settings.host}:{settings.port}")
    logger.info(f"TeamSpeak WS URL: {settings.ts_ws_url}")
    logger.info(f"STT Provider: {settings.stt_provider}")
    logger.info(f"TTS Provider: {settings.tts_provider}")
    logger.info("=" * 50)

    from api.routes.ws_teamspeak import ts_client
    from api.routes.ws_client import event_bus
    logger.info("Attempting to connect to TeamSpeak Voice Bridge...")
    success = await ts_client.connect()
    if success:
        logger.info("Successfully connected to TeamSpeak Voice Bridge")
        await event_bus.broadcast("teamspeak_connected", {})
    else:
        logger.warning("Failed to connect to TeamSpeak Voice Bridge - will retry on first connection")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    from api.routes.ws_teamspeak import ts_client
    await ts_client.disconnect()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
