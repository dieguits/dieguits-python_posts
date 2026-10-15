from fastapi import FastAPI
from app.core.db import Base, engine
from app.api.v1.posts.router import router as post_router
from app.api.v1.auth.router import router as auth_router

# python3 -m venv venv
# source venv/bin/activate
# fastapi dev main.py
# uvicorn main:app --reload

def create_app() -> FastAPI:
    app = FastAPI(title="Mini Blog")
    Base.metadata.create_all(bind=engine) # Dev, to create the table in case it not exists
    print("here we areeeeeeeee on mainnnnnnnnnnnnnnn")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(post_router)
    
    return app

app = create_app() 