from __future__ import annotations

import pytest

_created_product_id: str | None = None


@pytest.mark.asyncio(loop_scope="session")
async def test_create_product(client, auth_headers):
    global _created_product_id
    resp = await client.post(
        "/api/products/",
        json={
            "url": "https://www.amazon.com/dp/B09V3KXJPB",
            "name": "Test Product",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Product"
    assert data["is_active"] is True
    _created_product_id = data["id"]


@pytest.mark.asyncio(loop_scope="session")
async def test_create_product_auto_detects_platform(client, auth_headers):
    resp = await client.post(
        "/api/products/",
        json={
            "url": "https://www.amazon.co.uk/dp/B09TEST123",
            "name": "Amazon UK Product",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["platform"] == "amazon"


@pytest.mark.asyncio(loop_scope="session")
async def test_list_products(client, auth_headers):
    resp = await client.get("/api/products/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
    assert data["count"] >= 1


@pytest.mark.asyncio(loop_scope="session")
async def test_get_product_detail(client, auth_headers):
    resp = await client.get(f"/api/products/{_created_product_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == _created_product_id


@pytest.mark.asyncio(loop_scope="session")
async def test_update_product(client, auth_headers):
    resp = await client.patch(
        f"/api/products/{_created_product_id}",
        json={"name": "Updated Product Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Product Name"


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_product(client, auth_headers):
    resp = await client.delete(
        f"/api/products/{_created_product_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
