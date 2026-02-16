from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.base import Base
from app.db.session import engine
from app.core.config import settings

from app.api.v1.routes import auth, session, user, setting, ws_chat

root = "/api/v1"
ath = "/auth"
usr = "/users"
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

# CORS for frontend (e.g. Next.js on localhost:3000)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{root}{ath}", tags=["Auth"])
app.include_router(session.router, prefix=f"{root}{usr}{sessions}", tags=["Sessions"])
app.include_router(user.router, prefix=f"{root}{usr}", tags=["User"])
app.include_router(setting.router, prefix=f"{root}{usr}", tags=["Settings"])
app.include_router(ws_chat.router, tags=["Websocket"])