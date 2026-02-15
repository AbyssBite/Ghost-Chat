from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.db.base import Base
from app.db.session import engine

from app.api.v1.routes import auth, session

root = "/api/v1"
users = "/users"
sessions = "/sessions"

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables created (or already exist).")
    except Exception as e:
        print(f"Failed to create tables: {e}")
        raise
    yield

app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(auth.router, prefix=f"{root}{users}", tags=["User"])
app.include_router(session.router, prefix=f"{root}{users}{sessions}", tags=["Sessions"])