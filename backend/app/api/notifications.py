from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models.notification import Notification
from backend.app.models.user import User
from backend.app.schemas.notification import NotificationListResponse, NotificationResponse
from backend.app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    items, unread_count, total = await notification_service.get_notifications(
        current_user.id, db, unread_only=unread_only, limit=limit, offset=offset
    )
    return {
        "items": items,
        "unread_count": unread_count,
        "total": total,
    }


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ok = await notification_service.mark_as_read(
        notification_id, current_user.id, db
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one()
    return notif  # type: ignore[return-value]


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    count = await notification_service.mark_all_read(current_user.id, db)
    return {"marked_read": count}


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    count = await notification_service.get_unread_count(current_user.id, db)
    return {"unread_count": count}
