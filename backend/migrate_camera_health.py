"""Add non-destructive camera health fields to an existing database."""
from sqlalchemy import inspect, text

from app.database.database import engine


COLUMNS = {
    "health_status": "VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN'",
    "last_health_check": "DATETIME NULL",
    "last_online_at": "DATETIME NULL",
    "last_frame_at": "DATETIME NULL",
    "latency_ms": "INTEGER NULL",
    "consecutive_failures": "INTEGER NOT NULL DEFAULT 0",
    "stream_available": "BOOLEAN NOT NULL DEFAULT 0",
    "health_message": "VARCHAR(500) NULL",
}

with engine.begin() as connection:
    existing = {column["name"] for column in inspect(connection).get_columns("cameras")}
    for name, definition in COLUMNS.items():
        if name not in existing:
            connection.execute(text(f"ALTER TABLE cameras ADD COLUMN {name} {definition}"))
    indexes = {index["name"] for index in inspect(connection).get_indexes("cameras")}
    if "ix_cameras_health_status" not in indexes:
        connection.execute(text("CREATE INDEX ix_cameras_health_status ON cameras (health_status)"))

print("Camera health columns and index ready; existing camera records preserved.")
