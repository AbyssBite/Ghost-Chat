from fastapi import WebSocket
from typing import Dict, List


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, chat_id: str, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, chat_id: str, websocket: WebSocket):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].remove(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(
        self, chat_id: str, message: dict, exclude: WebSocket | None = None
    ):
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                if connection != exclude:
                    await connection.send_json(message)
