from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.database import Base, engine

# Import models so they are registered with SQLAlchemy
from .models.user import User
from .models.camera import Camera
from .models.detection import Detection
from .models.vehicle import Vehicle
from .models.alert import Alert
from .models.evidence import Investigation, Evidence
from .models.watchlist import Watchlist
import asyncio
import contextlib

Base.metadata.create_all(bind=engine)

# Seed an admin account automatically on startup
try:
    from .database.database import SessionLocal
    from .auth.password import get_password_hash
    db = SessionLocal()
    if not db.query(User).filter(User.email == "admin@ai.local").first():
        db.add(User(
            name="Sentinel Admin", 
            email="admin@ai.local", 
            password_hash=get_password_hash("admin123"), 
            role="ADMIN"
        ))
        db.commit()
    db.close()
except Exception as e:
    print(f"Error seeding admin: {e}")

import os
from fastapi.staticfiles import StaticFiles

upload_dir = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(os.path.join(upload_dir, "snapshots"), exist_ok=True)

app = FastAPI(title="AI CCTV Intelligence Platform")

# Production-grade CORS config
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=upload_dir), name="static")

from .api.routes import auth
from .api.routes import cameras
from .api.routes import video
from .api.routes import detections
from .api.routes import vehicles
from .api.routes import alerts
from .api.routes import search
from .api.routes import analytics
from .api.routes import watchlist
from .api.routes import evidence
from .websocket.manager import manager
from fastapi import WebSocket, WebSocketDisconnect

@app.on_event("startup")
async def startup_event():
    manager.loop = asyncio.get_running_loop()
    if os.getenv("CAMERA_HEALTH_MONITOR_ENABLED", "true").lower() == "true" and not getattr(app.state, "camera_health_task", None):
        from .services.camera_health import monitor_loop
        app.state.camera_health_stop = asyncio.Event()
        app.state.camera_health_task = asyncio.create_task(monitor_loop(app.state.camera_health_stop))


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "camera_health_task", None)
    stop = getattr(app.state, "camera_health_stop", None)
    if stop:
        stop.set()
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        app.state.camera_health_task = None

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(detections.router, prefix="/api/detections", tags=["detections"])
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["evidence"])

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "AI CCTV Backend is running"}

