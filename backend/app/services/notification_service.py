from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification


async def get_notifications(
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Notification], int, int]:
    base = select(Notification).where(Notification.user_id == user_id)

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar_one()

    unread_q = select(func.count()).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    unread = (await db.execute(unread_q)).scalar_one()

    q = base.order_by(Notification.created_at.desc())
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    items = list(result.scalars().all())

    return items, unread, total


async def mark_as_read(
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await db.execute(query)
    notif = result.scalar_one_or_none()
    if notif is None:
        return False
    notif.is_read = True
    await db.flush()
    return True


async def mark_all_read(user_id: uuid.UUID, db: AsyncSession) -> int:
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount  # type: ignore[return-value]


async def get_unread_count(user_id: uuid.UUID, db: AsyncSession) -> int:
    q = select(func.count()).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    result = await db.execute(q)
    count = result.scalar_one()
    return count
