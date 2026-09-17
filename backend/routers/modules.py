import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from lib.db import db
from lib.security import user_id_from_request
from models import CreateModuleItemRequest, ModuleItem

router = APIRouter(prefix="/modules", tags=["modules"])
ALLOWED = {"documents", "competency", "results", "assessment"}


def _check(kind: str) -> str:
    if kind not in ALLOWED:
        raise HTTPException(status_code=404, detail="Module not found")
    return kind


@router.get("/{kind}", response_model=list[ModuleItem])
async def list_items(kind: str, request: Request):
    _check(kind)
    user_id = user_id_from_request(request)
    docs = await db.module_items.find({"user_id": user_id, "kind": kind}).sort("updated_at", -1).to_list(100)
    return [ModuleItem(**{k: x[k] for k in ("id", "kind", "title", "description", "status", "updated_at")}) for x in docs]


@router.post("/{kind}", response_model=ModuleItem)
async def create_item(kind: str, payload: CreateModuleItemRequest, request: Request):
    _check(kind)
    user_id = user_id_from_request(request)
    doc = {"id": str(uuid.uuid4()), "user_id": user_id, "kind": kind, "title": payload.title, "description": payload.description, "status": "active", "updated_at": datetime.now(timezone.utc)}
    await db.module_items.insert_one(doc)
    return ModuleItem(**{k: doc[k] for k in ("id", "kind", "title", "description", "status", "updated_at")})
