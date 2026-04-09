# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Admin published apps endpoints."""

import json
from typing import Any, Dict, List

import redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.security import get_admin_user
from app.models.user import User
from app.schemas.admin import AdminPublishedAppItem, AdminPublishedAppListResponse

router = APIRouter()


def _get_publish_redis_client() -> redis.Redis:
    redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
    return redis.from_url(redis_url, decode_responses=True)


@router.get("/published-apps", response_model=AdminPublishedAppListResponse)
def list_published_apps(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(
        None, description="Search by app name/public url/workspace"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """List currently published apps from Redis constraint keys."""
    redis_client = _get_publish_redis_client()

    items: List[Dict[str, Any]] = []
    for key in redis_client.scan_iter(match="publish:user:*"):
        if ":none:" in key:
            continue
        raw = redis_client.get(key)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items.append(payload)

    if search:
        keyword = search.lower()

        def _matched(item: Dict[str, Any]) -> bool:
            return keyword in " ".join(
                [
                    str(item.get("app_name", "")).lower(),
                    str(item.get("public_url", "")).lower(),
                    str(item.get("workspace_name", "")).lower(),
                ]
            )

        items = [item for item in items if _matched(item)]

    items.sort(key=lambda item: item.get("published_at") or "", reverse=True)
    total = len(items)

    start = (page - 1) * limit
    end = start + limit
    paged_items = items[start:end]

    response_items = [
        AdminPublishedAppItem.model_validate(item) for item in paged_items
    ]
    return AdminPublishedAppListResponse(total=total, items=response_items)
