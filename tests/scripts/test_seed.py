"""Seeding is idempotent and gives the sample users their roles, history and preferences."""

import sqlite3
from pathlib import Path

from penny.catalog.images import PRODUCT_IMAGES, product_image_url
from scripts.seed import NEW_USER_ID, PRODUCTS, USERS
from tests.support import ESTABLISHED_USER, GUIDANCE_USER, PARALLEL_USER, seed_and_ingest

TABLES = (
    "schools",
    "users",
    "products",
    "promotions",
    "referral_codes",
    "purchases",
    "guidance_notes",
    "avoided_products",
)


def counts(path: Path) -> tuple[int, ...]:
    with sqlite3.connect(path) as db:
        return tuple(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES)


async def test_seeding_twice_changes_nothing(db_path: Path) -> None:
    before = counts(db_path)
    await seed_and_ingest(db_path)
    assert counts(db_path) == before


def test_seed_users_have_their_roles(db_path: Path) -> None:
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT count(*) FROM users").fetchone() == (len(USERS),)
        school = db.execute("SELECT school_id FROM users WHERE id = ?", (NEW_USER_ID,)).fetchone()
        assert school == (None,)
        for table in ("purchases", "referral_codes", "guidance_notes"):
            count = db.execute(f"SELECT count(*) FROM {table} WHERE user_id = ?", (NEW_USER_ID,))
            assert count.fetchone() == (0,), table
        assert db.execute(
            "SELECT count(*) FROM referral_codes WHERE user_id = ?", (ESTABLISHED_USER,)
        ).fetchone() == (1,)
        shared = db.execute(
            "SELECT count(DISTINCT school_id) FROM users WHERE id IN (?, ?)",
            (ESTABLISHED_USER, PARALLEL_USER),
        )
        assert shared.fetchone() == (1,)
        notes = [
            r[0]
            for r in db.execute(
                "SELECT text FROM guidance_notes WHERE user_id = ?", (GUIDANCE_USER,)
            )
        ]
        assert "Allergic to peanuts." in notes
        assert db.execute("SELECT count(*) FROM users WHERE time_zone IS NULL").fetchone() == (0,)


def test_purchase_history_is_varied_and_respects_each_household(db_path: Path) -> None:
    with sqlite3.connect(db_path) as db:
        bought = db.execute("SELECT count(DISTINCT product_id) FROM purchases").fetchone()[0]
        assert bought == len(PRODUCTS)
        per_user = db.execute(
            "SELECT count(*) FROM purchases GROUP BY user_id HAVING count(*) < 20"
        ).fetchall()
        assert per_user == []
        peanut_for_allergy = db.execute(
            "SELECT count(*) FROM purchases p JOIN products pr ON pr.id = p.product_id "
            "WHERE p.user_id = ? AND pr.name LIKE '%peanut%'",
            (GUIDANCE_USER,),
        )
        assert peanut_for_allergy.fetchone() == (0,)
        avoided_but_bought = db.execute(
            "SELECT count(*) FROM purchases p JOIN avoided_products a "
            "ON a.user_id = p.user_id AND a.product_id = p.product_id"
        )
        assert avoided_but_bought.fetchone() == (0,)
        top_by_school = db.execute(
            "SELECT u.school_id, p.product_id, count(*) AS n FROM purchases p "
            "JOIN users u ON u.id = p.user_id WHERE u.school_id IS NOT NULL "
            "GROUP BY u.school_id, p.product_id ORDER BY u.school_id, n DESC"
        ).fetchall()
        leaders = {school: product for school, product, _ in reversed(top_by_school)}
        assert len(set(leaders.values())) > 1  # schools don't all favor the same product


def test_every_product_image_ships_with_the_app(db_path: Path) -> None:
    """Images are assets in the package and image, never external URLs."""
    with sqlite3.connect(db_path) as db:
        rows = db.execute("SELECT name, image_url FROM products").fetchall()
    for name, url in rows:
        assert url == product_image_url(name)
        assert (PRODUCT_IMAGES / Path(url).name).is_file(), name
