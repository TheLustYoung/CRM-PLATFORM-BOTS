"""The Alembic migration must produce exactly the schema the models describe (PostgreSQL only)."""
import os
from pathlib import Path
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from backend.database import Base

URL = os.getenv("TEST_DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not URL, reason="set TEST_DATABASE_URL to a disposable PostgreSQL database")


def alembic_config(connection) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "database" / "migrations"))
    config.attributes["connection"] = connection
    return config


def test_upgrade_matches_models_and_downgrades():
    engine = create_engine(URL)
    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    with engine.begin() as conn:
        command.upgrade(alembic_config(conn), "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], f"migration differs from models: {diff}"
        assert {"users", "download_jobs", "uploaded_files", "audit_logs"} <= set(inspect(conn).get_table_names())
    with engine.begin() as conn:
        command.downgrade(alembic_config(conn), "base")
    with engine.connect() as conn:
        assert set(inspect(conn).get_table_names()) <= {"alembic_version"}
    engine.dispose()
