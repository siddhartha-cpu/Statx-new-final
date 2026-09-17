"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "users": [IndexModel([("email", ASCENDING)], name="email_unique", unique=True)],
    "sessions": [IndexModel([("expires_at", ASCENDING)], name="expires_at")],
    "conversations": [IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)], name="user_updated")],
    "messages": [IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)], name="conversation_created")],
    "provider_connections": [IndexModel([("user_id", ASCENDING), ("provider_id", ASCENDING)], name="user_provider", unique=True)],
    "provider_preferences": [IndexModel([("user_id", ASCENDING)], name="user_unique", unique=True)],
    "provider_health": [IndexModel([("user_id", ASCENDING), ("provider_id", ASCENDING)], name="user_provider_health", unique=True)],
    "module_items": [IndexModel([("user_id", ASCENDING), ("kind", ASCENDING), ("updated_at", DESCENDING)], name="user_kind_updated")],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
