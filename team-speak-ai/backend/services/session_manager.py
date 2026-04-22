from typing import Dict, Optional
from datetime import datetime
from uuid import uuid4


class Session:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid4())
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.data: Dict = {}

    def update_activity(self):
        self.last_active = datetime.now()


class SessionManager:
    """会话管理"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self, session_id: str = None) -> Session:
        session = Session(session_id)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session:
            session.update_activity()
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list:
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
            }
            for s in self._sessions.values()
        ]


session_manager = SessionManager()
