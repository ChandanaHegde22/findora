from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from router.auth import get_current_user
import models, schemas
from matcher import find_matches
from notifications_service import create_match_notifications
import shutil, os, uuid
 
router = APIRouter()
 
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
 
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE_MB = 5
 
 
def save_image(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid image format. Use JPG, PNG, or WEBP.")
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/uploads/{filename}"
 
 
# ─── Create Item ─────────────────────────────────────────────────────────────────
 
@router.post("/", response_model=schemas.ItemOut, status_code=201)
async def create_item(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    status: str = Form(...),
    location: str = Form(...),
    date_lost_or_found: str = Form(...),
    contact_email: str = Form(...),
    contact_phone: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    # Validate via schema
    item_data = schemas.ItemCreate(
        title=title, description=description, category=category,
        status=status, location=location, date_lost_or_found=date_lost_or_found,
        contact_email=contact_email, contact_phone=contact_phone
    )
 
    image_path = None
    if image and image.filename:
        image_path = save_image(image)
 
    item = models.Item(
        **item_data.dict(),
        image_path=image_path,
        owner_id=current_user.id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
 
    # Auto-find matches and notify
    opposite_status = "found" if status == "lost" else "lost"
    candidates = db.query(models.Item).filter(
        models.Item.status == opposite_status,
        models.Item.is_resolved == False
    ).all()
    matches = find_matches(item, candidates)
    if matches:
        create_match_notifications(db, item, matches)
 
    return item
 
 
# ─── List / Search Items ──────────────────────────────────────────────────────────
 
@router.get("/", response_model=List[schemas.ItemOut])
def get_items(
    status: Optional[str] = Query(None, description="lost or found"),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Search keyword"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(models.Item).filter(models.Item.is_resolved == False)
 
    if status:
        query = query.filter(models.Item.status == status)
    if category:
        query = query.filter(models.Item.category == category)
    if q:
        search = f"%{q}%"
        query = query.filter(or_(
            models.Item.title.ilike(search),
            models.Item.description.ilike(search),
            models.Item.location.ilike(search),
        ))
 
    return query.order_by(models.Item.date_reported.desc()).offset(skip).limit(limit).all()
 
 
# ─── Get Single Item ──────────────────────────────────────────────────────────────
 
@router.get("/{item_id}", response_model=schemas.ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
 
 
# ─── Get Matches for an Item ──────────────────────────────────────────────────────
 
@router.get("/{item_id}/matches", response_model=List[schemas.MatchResult])
def get_matches(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
 
    opposite_status = "found" if item.status == "lost" else "lost"
    candidates = db.query(models.Item).filter(
        models.Item.status == opposite_status,
        models.Item.is_resolved == False
    ).all()
 
    matches = find_matches(item, candidates)
    return [schemas.MatchResult(item=m["item"], score=m["score"], reason=m["reason"]) for m in matches]
 
 
# ─── Update Item ──────────────────────────────────────────────────────────────────
 
@router.patch("/{item_id}", response_model=schemas.ItemOut)
def update_item(
    item_id: int,
    updates: schemas.ItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
 
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(item, field, value)
 
    db.commit()
    db.refresh(item)
    return item
 
 
# ─── Delete Item ──────────────────────────────────────────────────────────────────
 
@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
 
    db.delete(item)
    db.commit()
 
 
# ─── My Items ─────────────────────────────────────────────────────────────────────
 
@router.get("/user/my-items", response_model=List[schemas.ItemOut])
def my_items(
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user),
):
    return db.query(models.Item).filter(
        models.Item.owner_id == current_user.id
    ).order_by(models.Item.date_reported.desc()).all()