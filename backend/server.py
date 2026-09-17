import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from lib.db import client, db, ensure_indexes  # noqa: E402
from routers.auth import router as auth_router  # noqa: E402
from routers.conversations import router as conversations_router  # noqa: E402
from routers.modules import router as modules_router  # noqa: E402
from routers.providers import router as providers_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())
    yield
    client.close()


app = FastAPI(title="Statx AI API", version="1.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"service": "statx-ai", "status": "online"}


@api_router.get("/health")
async def health():
    return {"status": "ok", "service": "statx-ai"}


@api_router.get("/ready")
async def ready():
    try:
        await db.command("ping")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ready", "database": "ok"}


@api_router.get("/dashboard")
async def dashboard():
    return {"status": "ready", "product": "Statx AI", "capabilities": ["multi-provider routing", "automatic fallback", "web search citations"]}


api_router.include_router(auth_router)
api_router.include_router(providers_router)
api_router.include_router(conversations_router)
api_router.include_router(modules_router)

origins = [x.strip() for x in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_credentials="*" not in origins,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("statx")

# Keep this include last: all application endpoints are registered on api_router above.
app.include_router(api_router)