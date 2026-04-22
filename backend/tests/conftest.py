from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.models.base import Base
from backend.app.services.auth_service import create_access_token, hash_password

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://pricepulse:pricepulse_dev@localhost:5432/pricepulse"
)

engine = create_async_engine(DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(setup_database) -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(setup_database) -> AsyncClient:
    from backend.app.main import app
    from backend.app.db.session import get_db

    async def _override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def admin_user(setup_database):
    from backend.app.models.user import User

    async with TestSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email="admin@test.com",
            password_hash=hash_password("testpassword123"),
            display_name="Test Admin",
            is_active=True,
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(loop_scope="session")
async def auth_headers(admin_user) -> dict[str, str]:
    token = create_access_token(
        subject=str(admin_user.id),
        extra_claims={"is_admin": True},
    )
    return {"Authorization": f"Bearer {token}"}
