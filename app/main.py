import os 
from datetime import datetime
from fastapi import Body, FastAPI, HTTPException, Query, Path, status, Depends
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from typing import Optional, List, Literal, Union
from math import ceil
from sqlalchemy import create_engine, Integer, String, Text, DateTime, select, func, UniqueConstraint, ForeignKey, Table, Column
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column, relationship, selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from dotenv import load_dotenv

# python3 -m venv venv  
# source venv/bin/activate
# fastapi dev main.py
# uvicorn main:app --reload

load_dotenv()



post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tags_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

class AuthorORM(Base):
    __tablename__ = "authors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    posts: Mapped[List[PostORM]] = relationship(back_populates="author")

class TagORM(Base):
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    
    posts: Mapped[List[PostORM]] = relationship(
        secondary=post_tags,
        back_populates="tags",
        lazy="selectin"
    )

class PostORM(Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("title", name="unique_post_title"),)
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Optional["AuthorORM"]] = relationship(back_populates="posts")
    
    tags: Mapped[List["TagORM"]] = relationship(
        secondary=post_tags,
        back_populates="posts",
        lazy="selectin",
        passive_deletes=True
    )
    
Base.metadata.create_all(bind=engine) # Dev, to create the table in case it not exists


app = FastAPI(title="Mini Blog")

class Tag(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Tag name"
        )
    
    model_config = ConfigDict(from_attributes=True)
    
class Author(BaseModel):
    name: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="Author Name"
    )
    email: EmailStr
    
    model_config = ConfigDict(from_attributes=True)

class PostBase(BaseModel):
    title: str
    content: str
    # This creates an empty list
    tags: Optional[List[Tag]] = Field(default_factory=list)
    author: Optional[Author] = None
    
    model_config = ConfigDict(from_attributes=True)
    
class PostCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="Post title (min length 4 characters, and max 50)",
        examples=["My first post fast api"]
    )
    content: Optional[str] = Field(
        default="Content by default",
        min_length=10,
        description="Content post with min length 10 characters",
        examples=["This is a content valid for this field"]
    )
    tags: List[Tag] = Field(default_factory=list)
    author: Optional[Author] = None
    
    @field_validator("title")
    @classmethod # to manipulate at class level
    def not_allowed_title(cls, value: str) -> str:
        values_not_allowed = ["spam", "where 1=1", "where 1 = 1", "delete *"]
        for val in values_not_allowed:
            if val.lower() in value.lower():
                raise ValueError(f"The title can not contain this value: ({val})")
        return value

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=4, max_length=50)
    content: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
    
class PostPublic(PostBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class PostSummary(BaseModel):
    id: int
    title: str
    
    model_config = ConfigDict(from_attributes=True)

class PaginationPost(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool
    order_by: Literal["id", "title"]
    direction: Literal["asc", "desc"]
    search: Optional[str] = None
    items: List[PostPublic]

@app.get("/")
def home():
    return {'message': 'Welcome to my Mini Blog by Diego Perez'}


@app.get("/posts", response_model=PaginationPost)
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
    
    results = select(PostORM)
    
    if query:
        # this is a list comprehension  
        results = results.where(PostORM.title.ilike(f"%{query}%")) 
        
        
    total = db.scalar(select(func.count()).select_from(
        results.subquery())) or 0
    total_pages = ceil(total/per_page) if total > 0 else 0
    
    current_page = 1 if total_pages == 0 else min(page, total_pages)
    
    if order_by == "id":
        order_col = PostORM.id
    else:
        order_col = func.lower(PostORM.title)
    
    results = results.order_by(order_col.asc() if direction == "asc" else order_col.desc())
    
    if total_pages == 0:
        items: List[PostORM] = []
    else:
        start = (current_page - 1) * per_page
        items = db.execute(results.limit(per_page).offset(start)).scalars().all()
        
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

@app.get("/posts/by-tags", response_model=List[PostPublic])
def filter_by_task(
    tags: List[str] = Query(
        ...,
        min_length=1,
        description="One or more tags. Example: ?tags=python&tags=fastapi"
    ),
    db: Session = Depends(get_db)
    ):
    
    normalize_tag_names = [tag.strip().lower() for tag in tags if tag.strip()]
    
    if not normalize_tag_names:
        return []
    
    post_list = (
        select(PostORM)
        .options(
            selectinload(PostORM.tags),
            joinedload(PostORM.author),
        ).where(PostORM.tags.any(func.lower(TagORM.name).in_(normalize_tag_names)))
        .order_by(PostORM.id.asc())
        )
    
    posts = db.execute(post_list).scalars().all()
    
    return posts

@app.get("/posts/{post_id}", 
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
    
    # this option is faster that doing db.get alone
    post_find = select(PostORM).where(PostORM.id == post_id)
    post = db.execute(post_find).scalar_one_or_none()
    
    # post = db.get(PostORM, post_id)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if include_content:
        return PostPublic.model_validate(post, from_attributes=True)
    
    return PostSummary.model_validate(post, from_attributes=True)
    
    
@app.post("/posts", 
          response_model=PostPublic, 
          response_description="Post was created",
          status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    author_obj = None
    
    if post.author:
        author_obj = db.execute(
            select(AuthorORM).where(AuthorORM.email == post.author.email)
        ).scalar_one_or_none()
        
        if not author_obj:
            author_obj = AuthorORM(name = post.author.name,
                                   email = post.author.email)
            db.add(author_obj)
            db.flush()
        
         
    new_post = PostORM(title=post.title, content=post.content, author=author_obj)
    
    for tag in post.tags:
        tag_obj = db.execute(
            select(TagORM).where(TagORM.name.ilike(tag.name))
        ).scalar_one_or_none()
        
        if not tag_obj:
            tag_obj = TagORM(name=tag.name)
            db.add(tag_obj)
            db.flush()
            
        new_post.tags.append(tag_obj)
    
    try:
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Title already exist")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating the post")
    
@app.put("/posts/{post_id}", 
         response_model=PostPublic,
         response_description="Post updated correctly.",
         response_model_exclude_none=True)
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db)):
    
    post = db.get(PostORM, post_id)
    
    if not post:
            raise HTTPException(status_code=404, detail="Post not found")
    
    updates = data.model_dump(exclude_unset=True)
    
    for key, value in updates.items():
        setattr(post, key, value)
    
    try:
        db.add(post)
        db.commit()
        db.refresh(post)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating the post")
    
    return post

# 204 status code is just to send the code without anything else
@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    
    post = db.get(PostORM, post_id)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    
    return
