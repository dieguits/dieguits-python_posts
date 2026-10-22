from ctypes import resize
import stat

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exception_handlers import http_exception_handler
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.api.v1.tags.repository import TagRepository
from app.api.v1.tags.schemas import TagCreate, TagPublic, TagUpdate
from app.core.db import get_db
from app.core.security import get_current_user


router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("", response_model=dict)
def list_tags(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    order_by: str = Query("id", pattern="(^id|name)$"),
    direction: str = Query("asc", pattern="^(asc|desc)$"),
    search: str | None = Query(None),
    db: Session = Depends(get_db)
):
    
    repository = TagRepository(db)
    
    return repository.list_tags(
        page=page, 
        per_page=per_page, 
        order_by=order_by, 
        direction=direction, 
        search=search
    )

@router.post("", response_model=TagPublic, 
             response_description="Tag Created", 
             status_code=status.HTTP_201_CREATED)
def create_tag(tag: TagCreate, db: Session = Depends(get_db), user= Depends(get_current_user)):
    repository = TagRepository(db)
    
    try:
        tag_created = repository.create_tag(name=tag.name)
        db.commit()
        db.refresh(tag_created)
        return tag_created
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating a tag")
    
@router.put("/{tag_id}", response_model=TagPublic, 
            response_description="Tag Updated",
            status_code=status.HTTP_200_OK)
def update_tag(
    tag_id: int, 
    data: TagUpdate, 
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
    ):
    
    repository = TagRepository(db)
    tag_updated = repository.update_tag(tag_id, data.name)
    
    if tag_updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Tag not found")
    
    try:
        db.commit()
        db.refresh(tag_updated)
        return TagPublic.model_validate(tag_updated)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error updating a tag")
        
@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    
    repository = TagRepository(db)
    # tag = repository.get_tag_by_id(tag_id)
    delete = repository.delete_tag(tag_id)
    
    if not delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Tag not found")
        
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting hte tag"
        )
        
@router.get("/popular/top")
def get_most_popular_tag(
    db: Session = Depends(get_db),
    user= Depends(get_current_user)
):
    repository = TagRepository(db)
    print("coming here to the router:::::::: ")
    row = repository.most_popular_tag()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There are not tags in use"
        )
        
    return row