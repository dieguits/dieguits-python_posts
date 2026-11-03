from typing import Optional, List, Literal, Annotated
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from fastapi import Form

class Tag(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=60,
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
    image_url: Optional[str] = None
    
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
    # author: Optional[Author] = None
    
    @field_validator("title")
    @classmethod # to manipulate at class level
    def not_allowed_title(cls, value: str) -> str:
        values_not_allowed = ["spam", "where 1=1", "where 1 = 1", "delete *"]
        for val in values_not_allowed:
            if val.lower() in value.lower():
                raise ValueError(f"The title can not contain this value: ({val})")
        return value
    
    @classmethod
    def as_form(
        cls,
        title: Annotated[str, Form(min_length=3)],
        content: Annotated[str, Form(min_length=10)],
        tags: Annotated[Optional[List[str]], Form()] = None,
    ):
        # tag_objs = []
        # for t in tags:
        #     print(f"The tags coming here::::::: {t}")
        #     tag_objs.append(t)
        tag_objs = [Tag(name=t) for t in (tags or [])]
        print("The tags converted:::::: ", tag_objs)
        return cls(title=title, content=content, tags=tag_objs)

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
