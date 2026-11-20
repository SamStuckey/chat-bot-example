"""The migration builds the schema on an empty database and downgrades cleanly."""

import sqlite3
from pathlib import Path

from tests.support import migrate


def tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as db:
        return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_upgrade_and_downgrade(tmp_path: Path) -> None:
    path = tmp_path / "penny.db"
    migrate(path)
    upgraded = tables(path)
    assert {
        "schools",
        "users",
        "products",
        "purchases",
        "promotions",
        "turns",
        "messages",
        "messages_fts",
        "model_messages",
        "summaries",
    } <= upgraded

    migrate(path, "base", down=True)
    assert tables(path) == {"alembic_version"}
    migrate(path)
    assert tables(path) == upgraded
