import os
import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.database import Base, session
from backend.main import app
from backend.models import Admin, Bot
from backend.services import limits, queue
from backend.services.auth import hasher


@pytest.fixture(autouse=True)
def fake_infrastructure(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(limits, "redis_client", lambda: redis)
    enqueued = []
    monkeypatch.setattr(queue, "enqueue", lambda job_id, priority=False: enqueued.append(job_id))
    return enqueued


POSTGRES_URL = os.getenv("TEST_DATABASE_URL")  # e.g. postgresql+psycopg://media:...@127.0.0.1:5432/media_test


@pytest.fixture
def db():
    """SQLite in memory by default; a real PostgreSQL when TEST_DATABASE_URL is set (never production!)."""
    if POSTGRES_URL:
        engine = create_engine(POSTGRES_URL)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as db:
        for kind in ("video", "media", "files"):
            db.add(Bot(id=kind, username=f"{kind}_test_bot"))
        db.commit()
        yield db
        db.rollback()
    if POSTGRES_URL:
        Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[session] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client, db):
    db.add(Admin(username="operator", password_hash=hasher.hash("test-password-only")))
    db.commit()
    client.headers["Origin"] = "http://testserver"
    result = client.post("/api/auth/login", json={"username": "operator", "password": "test-password-only"})
    assert result.status_code == 200
    assert "HttpOnly" in result.headers["set-cookie"]
    yield client
