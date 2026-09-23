"""Add evidence tables; retire the unused incidents table only when empty."""
from sqlalchemy import inspect, text
from app.database.database import Base, engine
from app.models.user import User
from app.models.evidence import Investigation, Evidence

Base.metadata.create_all(engine, tables=[Investigation.__table__, Evidence.__table__])
with engine.begin() as connection:
    schema = inspect(connection)
    vehicle_columns = {column['name'] for column in schema.get_columns('vehicles')}
    if 'plate_raw_text' not in vehicle_columns:
        connection.execute(text('ALTER TABLE vehicles ADD COLUMN plate_raw_text VARCHAR(100) NULL'))
    existing_vehicle_indexes = {index['name'] for index in inspect(connection).get_indexes('vehicles')}
    if 'ix_vehicles_camera_first_seen' not in existing_vehicle_indexes:
        connection.execute(text('CREATE INDEX ix_vehicles_camera_first_seen ON vehicles (camera_id, first_seen)'))
    if 'ix_vehicles_plate_first_seen' not in existing_vehicle_indexes:
        connection.execute(text('CREATE INDEX ix_vehicles_plate_first_seen ON vehicles (number_plate, first_seen)'))
    existing_detection_indexes = {index['name'] for index in inspect(connection).get_indexes('detections')}
    if 'ix_detections_camera_timestamp' not in existing_detection_indexes:
        connection.execute(text('CREATE INDEX ix_detections_camera_timestamp ON detections (camera_id, timestamp)'))
    if inspect(connection).has_table('incidents'):
        count = connection.execute(text('SELECT COUNT(*) FROM incidents')).scalar_one()
        if count:
            raise RuntimeError('Legacy incidents contains data. Archive and review it before retiring the table; no data was deleted.')
        connection.execute(text('DROP TABLE incidents'))
print('Evidence/ANPR columns and investigation indexes ready. Empty legacy incidents table retired when present.')
