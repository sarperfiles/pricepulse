from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.deps import get_current_user
from backend.app.models.alert_rule import AlertRule
from backend.app.models.product import Product
from backend.app.models.user import User
from backend.app.schemas.alert_rule import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate

router = APIRouter(prefix="/api/products", tags=["alert_rules"])


async def _verify_product_ownership(
    pid: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Product:
    result = await db.execute(
        select(Product).where(Product.id == pid, Product.user_id == user_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.post(
    "/{product_id}/alerts",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alert_rule(
    product_id: uuid.UUID,
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRule:
    await _verify_product_ownership(product_id, current_user.id, db)

    # not sure if this is the best way to validate
    if body.rule_type not in ("target_price", "pct_change"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rule_type must be 'target_price' or 'pct_change'",
        )

    rule = AlertRule(
        product_id=product_id,
        user_id=current_user.id,
        rule_type=body.rule_type,
        target_price=body.target_price,
        pct_threshold=body.pct_threshold,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.get("/{product_id}/alerts", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AlertRule]:
    await _verify_product_ownership(product_id, current_user.id, db)

    q = (
        select(AlertRule)
        .where(AlertRule.product_id == product_id, AlertRule.user_id == current_user.id)
        .order_by(AlertRule.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


@router.patch("/alerts/{alert_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    alert_id: uuid.UUID,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRule:
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )
    await db.delete(rule)
    await db.flush()
