import sqlalchemy
from sqlalchemy import create_engine, text
import os
import sys

print("Connecting to MySQL to create database if not exists...")
try:
    engine = create_engine('mysql+pymysql://root:@localhost:3306/')
    with engine.connect() as conn:
        conn.execute(text('CREATE DATABASE IF NOT EXISTS ai_cctv'))
        conn.commit()
    print("Database verified.")
except Exception as e:
    print(f"Failed to connect to MySQL! Error: {e}")
    sys.exit(1)

print("Creating tables...")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import Base, engine as app_engine
from app.models.user import User
from app.models.camera import Camera
from app.models.detection import Detection
from app.models.vehicle import Vehicle
from app.models.alert import Alert
from app.models.evidence import Investigation, Evidence

try:
    Base.metadata.create_all(bind=app_engine)
    print("All tables successfully generated!")
except Exception as e:
    print(f"Failed to generate tables! Error: {e}")
