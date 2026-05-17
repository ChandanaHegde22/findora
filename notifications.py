from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from router.auth import get_current_user
import models, schemas
 
router = APIRouter()
 
 
@router.get("/", response_model=List[schemas.NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    return db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(50).all()
 
 
@router.patch("/{notif_id}/read", status_code=204)
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == current_user.id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
 
 
@router.patch("/mark-all-read", status_code=204)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()