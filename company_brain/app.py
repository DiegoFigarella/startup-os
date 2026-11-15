from __future__ import annotations

import hmac
import os
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .contracts import IngestItem
from .store import CompanyBrainStore

app = FastAPI(title="Company Brain", version="0.1.0")


class IngestRequest(BaseModel):
    source: str
    external_id: str
    occurred_at: datetime
    author: str = ""
    place: str = ""
    text: str
    canonical_url: str = ""
    revision: str = ""
    scopes: list[str] = Field(min_length=1)


def store() -> CompanyBrainStore:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return CompanyBrainStore(database_url)


def require_key(value: str | None) -> None:
    expected = os.environ.get("COMPANY_BRAIN_API_KEY")
    if not expected or not value or not hmac.compare_digest(value, expected):
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/items", status_code=201)
def ingest(request: IngestRequest, x_company_brain_key: str | None = Header(default=None)) -> dict[str, bool]:
    require_key(x_company_brain_key)
    try:
        item = IngestItem(
            source=request.source,
            external_id=request.external_id,
            occurred_at=request.occurred_at,
            author=request.author,
            place=request.place,
            text=request.text,
            canonical_url=request.canonical_url,
            revision=request.revision,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"created": store().ingest(item, request.scopes)}


@app.get("/v1/items")
def recent(scope: str, limit: int = 50, x_company_brain_key: str | None = Header(default=None)) -> list[dict[str, object]]:
    require_key(x_company_brain_key)
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return store().recent(scope, limit)
