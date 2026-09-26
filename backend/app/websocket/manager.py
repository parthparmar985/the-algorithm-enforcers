from fastapi import WebSocket
from typing import List
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            self.loop = asyncio.get_running_loop()
        except:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_alert(self, alert_data: dict):
        for connection in list(self.active_connections):
            try:
                await asyncio.wait_for(connection.send_text(json.dumps(alert_data)), timeout=2)
            except Exception:
                self.disconnect(connection)
                
    async def broadcast_progress(self, progress_data: dict):
        for connection in list(self.active_connections):
            try:
                await asyncio.wait_for(connection.send_text(json.dumps(progress_data)), timeout=2)
            except Exception:
                self.disconnect(connection)

    def sync_broadcast_progress(self, progress_data: dict):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_progress(progress_data), self.loop)

    def sync_broadcast_alert(self, alert_data: dict):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_alert(alert_data), self.loop)

    # Compatibility with health/evidence callers.
    broadcast_alert_sync = sync_broadcast_alert

manager = ConnectionManager()
