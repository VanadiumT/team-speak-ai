from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ControlCommand(BaseModel):
    action: str
    params: dict = {}


@router.post("/control")
async def control_endpoint(command: ControlCommand):
    """控制命令端点"""
    action = command.action
    params = command.params

    if action == "connect_teamspeak":
        return {"status": "ok", "message": "Connecting to TeamSpeak..."}
    elif action == "disconnect_teamspeak":
        return {"status": "ok", "message": "Disconnecting from TeamSpeak..."}
    elif action == "send_voice":
        return {"status": "ok", "message": "Voice sent"}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.get("/status")
async def get_status():
    """获取服务状态"""
    return {
        "teamspeak_connected": False,
        "stt_provider": "whisper",
        "uptime": 0,
    }
