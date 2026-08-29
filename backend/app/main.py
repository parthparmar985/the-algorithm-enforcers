from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.database import Base, engine

# Import models so they are registered with SQLAlchemy
from .models.user import User
from .models.camera import Camera
from .models.detection import Detection
from .models.vehicle import Vehicle
from .models.vehicle import Vehicle
from .models.alert import Alert
from .models.incident import Incident
from .models.watchlist import Watchlist

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

os.makedirs("uploads/snapshots", exist_ok=True)

app = FastAPI(title="AI CCTV Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="uploads"), name="static")

from .api.routes import auth

from .api.routes import cameras

from .api.routes import video

from .api.routes import detections
from .api.routes import vehicles
from .api.routes import alerts
from .api.routes import search
from .api.routes import analytics
from .api.routes import watchlist
from .websocket.manager import manager
from fastapi import WebSocket, WebSocketDisconnect

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(detections.router, prefix="/api/detections", tags=["detections"])
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])

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
