from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.alert_rule import AlertRule
from backend.app.models.notification import Notification


async def evaluate_alerts(
    product_id: uuid.UUID,
    old_price: Decimal | None,
    new_price: Decimal,
    db: AsyncSession,
) -> list[Notification]:
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.product_id == product_id,
            AlertRule.is_active.is_(True),
        )
    )
    rules = result.scalars().all()

    notifications: list[Notification] = []

    for rule in rules:
        triggered = False
        title = ""
        msg = ""

        if rule.rule_type == "target_price" and rule.target_price is not None:
            if new_price <= rule.target_price:
                triggered = True
                title = "Target price reached!"
                msg = (
                    f"The price dropped to {new_price}, which is at or below "
                    f"your target of {rule.target_price}."
                )

        elif rule.rule_type == "pct_change" and rule.pct_threshold is not None:
            if old_price is not None and old_price > 0:
                pct = abs(
                    (new_price - old_price) / old_price * Decimal("100")
                )
                if pct >= rule.pct_threshold:
                    triggered = True
                    direction = "dropped" if new_price < old_price else "increased"
                    title = "Price {} by {:.1f}%!".format(direction, pct)
                    msg = (
                        f"The price {direction} from {old_price} to {new_price} "
                        f"({pct:.1f}% change), exceeding your "
                        f"{rule.pct_threshold}% threshold."
                    )

        if triggered:
            notif = Notification(
                user_id=rule.user_id,
                product_id=product_id,
                alert_rule_id=rule.id,
                title=title,
                message=msg,
                old_price=old_price,
                new_price=new_price,
            )
            db.add(notif)
            notifications.append(notif)

    if len(notifications) > 0:
        await db.flush()

    return notifications
