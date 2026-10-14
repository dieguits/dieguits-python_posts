from fastapi import FastAPI
from app.core.db import Base, engine
from app.api.v1.posts.router import router as post_router

# python3 -m venv venv
# source venv/bin/activate
# fastapi dev main.py
# uvicorn main:app --reload


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Blog")
    Base.metadata.create_all(bind=engine) # Dev, to create the table in case it not exists
    
    app.include_router(post_router)
    
    return app

app = create_app()