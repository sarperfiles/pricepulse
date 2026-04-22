from __future__ import annotations

import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_login_valid_credentials(client, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "testpassword123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio(loop_scope="session")
async def test_login_wrong_password(client, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_token(client, admin_user):
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "testpassword123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio(loop_scope="session")
async def test_protected_endpoint_without_token(client):
    resp = await client.get("/api/products/")
    assert resp.status_code in (401, 403)
