from fastapi import WebSocket
from typing import List, Optional
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_alert(self, alert_data: dict):
        if "type" not in alert_data:
            alert_data["type"] = "ALERT"
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(alert_data))
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_progress(self, progress_data: dict):
        if "type" not in progress_data:
            progress_data["type"] = "PROGRESS"
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(progress_data))
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    def broadcast_alert_sync(self, alert_data: dict):
        """Thread-safe sync wrapper for broadcasting alerts from background threads."""
        target_loop = self.loop
        if not target_loop or not target_loop.is_running():
            try:
                target_loop = asyncio.get_event_loop()
            except Exception:
                target_loop = None
        
        if target_loop and target_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_alert(alert_data), target_loop)
        else:
            try:
                asyncio.run(self.broadcast_alert(alert_data))
            except Exception:
                pass

    def broadcast_progress_sync(self, progress_data: dict):
        """Thread-safe sync wrapper for broadcasting progress from background threads."""
        target_loop = self.loop
        if not target_loop or not target_loop.is_running():
            try:
                target_loop = asyncio.get_event_loop()
            except Exception:
                target_loop = None

        if target_loop and target_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_progress(progress_data), target_loop)
        else:
            try:
                asyncio.run(self.broadcast_progress(progress_data))
            except Exception:
                pass

manager = ConnectionManager()

