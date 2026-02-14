from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.db.base import Base
from app.db.session import engine


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

app = FastAPI(lifespan=lifespan)