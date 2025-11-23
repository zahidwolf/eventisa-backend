from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

# Separate managers for different types of updates
event_manager = ConnectionManager()
ticket_manager = ConnectionManager()
admin_manager = ConnectionManager()
host_manager = ConnectionManager()
participant_manager = ConnectionManager()
user_manager=ConnectionManager()
qr_code_manager=ConnectionManager()