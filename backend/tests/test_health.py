from __future__ import annotations

import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
