"""Copy all platform data from a SQLite database into an empty, migrated PostgreSQL database.

    python -m infrastructure.scripts.sqlite_to_postgres sqlite:///local/dev.db postgresql+psycopg://user:pass@host/db

Used to move the local development data to PostgreSQL. The target schema is created with
Alembic first; tables are copied in foreign-key order and naive SQLite timestamps are UTC.
"""
import sys
from datetime import timezone
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, create_engine, func, select
from backend.database import Base
import backend.models  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


def migrate(target_connection):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "database" / "migrations"))
    config.attributes["connection"] = target_connection
    command.upgrade(config, "head")


def utc(row: dict, table) -> dict:
    for column in table.columns:
        value = row.get(column.name)
        if isinstance(column.type, DateTime) and value is not None and value.tzinfo is None:
            row[column.name] = value.replace(tzinfo=timezone.utc)
    return row


def copy(source_url: str, target_url: str) -> dict[str, int]:
    source, target = create_engine(source_url), create_engine(target_url)
    copied = {}
    with source.connect() as src, target.begin() as dst:
        migrate(dst)
        for table in Base.metadata.sorted_tables:  # parents before children
            if dst.scalar(select(func.count()).select_from(table)):
                raise SystemExit(f"Target table {table.name} is not empty; refusing to overwrite")
            rows = [utc(dict(r._mapping), table) for r in src.execute(select(table))]
            if rows:
                dst.execute(table.insert(), rows)
            copied[table.name] = len(rows)
    return copied


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    for name, count in copy(sys.argv[1], sys.argv[2]).items():
        print(f"{name:24} {count}")
