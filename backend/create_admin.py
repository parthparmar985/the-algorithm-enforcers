import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal
from app.models.user import User
from app.auth.password import get_password_hash

try:
    db = SessionLocal()
    exist = db.query(User).filter(User.email=='admin@police.local').first()
    if not exist:
        admin = User(name='Admin', email='admin@police.local', password_hash=get_password_hash('password123'), role='ADMIN')
        db.add(admin)
        db.commit()
        print("\nSUCCESS: Admin user created!")
    else:
        print("\nSUCCESS: Admin user already exists!")
except Exception as e:
    print(f"\nERROR: Something went wrong generating user. Make sure XAMPP MySQL is active. Error: {e}")
