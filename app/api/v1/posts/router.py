from fastapi import APIRouter, Query, Depends, Path, HTTPException, status
from math import ceil
from typing import Optional, List, Union, Literal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.db import get_db
from .schemas import (PostPublic, PaginationPost,
                      PostCreate, PostUpdate, PostSummary)
from ..posts.repository import PostRepository
from app.core.security import oauth2_scheme, get_current_user

router = APIRouter(prefix="/posts", tags=["posts"])

def get_fake_user():
    return {"username": "diego", "role": "admin"}

@router.get("/me")
def read_me(user:dict = Depends(get_fake_user)):
    return {"user": user}

@router.get("", response_model=PaginationPost)
def list_posts(
    text: Optional[str] = Query(
        default = None,
        deprecated=True,
        description = "Obsolete Param, use query instead."
    ),
    query: Optional[str] = Query(
            default = None,
            description = "Text to search on title",
            alias="search",
            min_length=3,
            max_length=10,
            pattern=r"^[\w\sáéíóúÁÉÍÓÚüÜ-]+$"
        ),
    per_page: int = Query(
        10, ge=1, le=50,
        description="Number of results (1-50)"
    ),
    page: int = Query(
        1, ge=1,
        description="Page number (>=1)"
    ),
    order_by: Literal["id", "title"] = Query(
        "id", description="Order Field"
    ),
    direction: Literal["asc", "desc"] = Query(
        "asc", description="Order direction"
    ),
    db: Session = Depends(get_db)
    ):
    
    repository = PostRepository(db)
    query = query or text
    
    total, items = repository.search(query, order_by, direction, page, per_page)
    
    total_pages = ceil(total/per_page) if total > 0 else 0
    current_page = 1 if total_pages == 0 else min(page, total_pages)
    
    has_prev = current_page > 1
    has_next = current_page < total_pages if total_pages > 0 else False
    
    return  PaginationPost(
        page=current_page,
        per_page=per_page, 
        total=total,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        order_by=order_by,
        direction=direction,
        search=query,
        items=items
        )
    
@router.get("/by-tags", response_model=List[PostPublic])
def filter_by_task(
    tags: List[str] = Query(
        ...,
        min_length=1,
        description="One or more tags. Example: ?tags=python&tags=fastapi"
    ),
    db: Session = Depends(get_db)
    ):
    
    repository = PostRepository(db)
    return repository.by_tags(tags)


@router.get("/{post_id}", 
         response_model=Union[PostPublic, PostSummary], 
         response_description="Post Found")
def get_post(post_id: int = Path(
        ...,
        ge=1,
        title="Post id",
        description="Post identifier should be grater that 0",
        example=1
    ), include_content: bool = Query(default = True,  description = "Include the content"),
       db: Session = Depends(get_db)
    ):
    
    repository = PostRepository(db)
    post = repository.get(post_id)
        
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if include_content:
        return PostPublic.model_validate(post, from_attributes=True)
    
    return PostSummary.model_validate(post, from_attributes=True)
  

@router.post("", 
          response_model=PostPublic, 
          response_description="Post was created",
          status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, 
                db: Session = Depends(get_db), 
                user=Depends(get_current_user)):
    
    repository = PostRepository(db)
        
    try:
        new_post = repository.create_post(
            title=post.title, 
            content=post.content, 
            author=user,
            tags=[tag.model_dump() for tag in post.tags]
            )
        db.commit()
        db.refresh(new_post)
        return new_post
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Title already exist")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating the post")

@router.put("/{post_id}", 
         response_model=PostPublic,
         response_description="Post updated correctly.",
         response_model_exclude_none=True)
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db)):
    
    repository = PostRepository(db)
    post = repository.get(post_id)
    
    if not post:
            raise HTTPException(status_code=404, detail="Post not found")
    
    try:
        #convert into a dictionary
        updates = data.model_dump(exclude_unset=True)
        post_updated = repository.update_post(post, updates)
        db.commit()
        db.refresh(post_updated)
        return post_updated
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating the post")
     

# 204 status code is just to send the code without anything else
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    repository = PostRepository(db)
    post = repository.get(post_id)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    try:
        repository.delete_post(post)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting the post")

@router.get("/secure")
def secure_endpoint(token:str = Depends(oauth2_scheme)):
    return {"message": "Access with token", "token_received": token}