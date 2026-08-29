from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ...database.database import get_db
from ...models.watchlist import Watchlist
from ...auth.jwt import get_current_user

router = APIRouter()

class WatchlistCreate(BaseModel):
    registration_number: str
    category: str
    priority: str
    description: Optional[str] = None

class WatchlistResponse(BaseModel):
    id: int
    registration_number: str
    category: str
    priority: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[WatchlistResponse])
def get_watchlist(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(Watchlist).order_by(Watchlist.created_at.desc()).all()

@router.post("/", response_model=WatchlistResponse)
def add_to_watchlist(item: WatchlistCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_item = Watchlist(
        registration_number=item.registration_number.upper().strip(),
        category=item.category.upper(),
        priority=item.priority.upper(),
        description=item.description,
        status="ACTIVE"
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{id}")
def remove_from_watchlist(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    item = db.query(Watchlist).filter(Watchlist.id == id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"status": "deleted"}
