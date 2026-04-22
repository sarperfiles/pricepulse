from __future__ import annotations

import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_list_notifications_empty(client, auth_headers):
    resp = await client.get("/api/notifications/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_unread_count(client, auth_headers):
    resp = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] == 0
