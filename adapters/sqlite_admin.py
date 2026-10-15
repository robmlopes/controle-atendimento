"""SQLite implementation of CatalogAdmin: every statement is scoped to the business of the caller."""

from typing import Any

from adapters.sqlite_db import Database
from domain.models import Block, Business, Professional, Service, WeeklyRule

OWNED = "professional_id IN (SELECT id FROM professionals WHERE id = ? AND business_id = ? AND active = 1)"


def _service(row: tuple[Any, ...]) -> Service:
    return Service(row[0], row[1], row[2], row[3], row[4])


class SqliteAdmin:
    def __init__(self, db: Database) -> None:
        self.db = db

    def business(self, business_id: int) -> Business | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id, slug, name, whatsapp FROM businesses WHERE id = ?", (business_id,)
            ).fetchone()
        return None if row is None else Business(row[0], row[1], row[2], row[3])

    def is_slug_available(self, slug: str, exclude_business_id: int) -> bool:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM businesses WHERE slug = ? AND id != ?", (slug, exclude_business_id)
            ).fetchone()
        return row is None

    def update_business(self, business_id: int, name: str, slug: str, whatsapp: str | None) -> bool:
        if not self.is_slug_available(slug, business_id):
            return False
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "UPDATE businesses SET name = ?, slug = ?, whatsapp = ? WHERE id = ?",
                (name, slug, whatsapp, business_id),
            )
        return cur.rowcount == 1

    def professional(self, business_id: int, professional_id: int) -> Professional | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id, business_id, name, active, commission_pct FROM professionals"
                " WHERE id = ? AND business_id = ? AND active = 1",
                (professional_id, business_id),
            ).fetchone()
        return None if row is None else Professional(row[0], row[1], row[2], bool(row[3]), int(row[4]))

    def update_professional(self, business_id: int, professional_id: int, name: str, commission_pct: int) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "UPDATE professionals SET name = ?, commission_pct = ? WHERE id = ? AND business_id = ? AND active = 1",
                (name, commission_pct, professional_id, business_id),
            )
        return cur.rowcount == 1

    def business_services(self, business_id: int) -> tuple[Service, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT id, business_id, name, duration_min, price_cents FROM services"
                " WHERE business_id = ? AND active = 1 ORDER BY name",
                (business_id,),
            ).fetchall()
        return tuple(_service(r) for r in rows)

    def linked_service_ids(self, professional_id: int) -> tuple[int, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT service_id FROM professional_services WHERE professional_id = ?", (professional_id,)
            ).fetchall()
        return tuple(r[0] for r in rows)

    def blocks_from(self, professional_id: int, from_day: int) -> tuple[Block, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT professional_id, day, start_min, end_min FROM blocks WHERE professional_id = ? AND day >= ?"
                " ORDER BY day, start_min",
                (professional_id, from_day),
            ).fetchall()
        return tuple(Block(r[0], r[1], r[2], r[3]) for r in rows)

    def deactivate_professional(self, business_id: int, professional_id: int) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "UPDATE professionals SET active = 0 WHERE id = ? AND business_id = ? AND active = 1",
                (professional_id, business_id),
            )
        return cur.rowcount == 1

    def deactivate_service(self, business_id: int, service_id: int) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "UPDATE services SET active = 0 WHERE id = ? AND business_id = ? AND active = 1",
                (service_id, business_id),
            )
        return cur.rowcount == 1

    def set_services(self, business_id: int, professional_id: int, service_ids: tuple[int, ...]) -> bool:
        with self.db.connection(write=True) as conn:
            owned = conn.execute(
                "SELECT 1 FROM professionals WHERE id = ? AND business_id = ? AND active = 1",
                (professional_id, business_id),
            ).fetchone()
            if owned is None:
                return False
            valid = [
                row[0]
                for sid in set(service_ids)
                for row in conn.execute(
                    "SELECT id FROM services WHERE id = ? AND business_id = ? AND active = 1", (sid, business_id)
                )
            ]
            conn.execute("DELETE FROM professional_services WHERE professional_id = ?", (professional_id,))
            conn.executemany(
                "INSERT INTO professional_services(professional_id, service_id) VALUES (?, ?)",
                [(professional_id, sid) for sid in valid],
            )
        return True

    def add_rule(self, business_id: int, rule: WeeklyRule) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO weekly_rules(professional_id, weekday, start_min, end_min)"
                " SELECT id, ?, ?, ? FROM professionals WHERE id = ? AND business_id = ? AND active = 1",
                (rule.weekday, rule.start_min, rule.end_min, rule.professional_id, business_id),
            )
        return cur.rowcount == 1

    def remove_rule(self, business_id: int, rule: WeeklyRule) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                f"DELETE FROM weekly_rules WHERE {OWNED} AND weekday = ? AND start_min = ? AND end_min = ?",
                (rule.professional_id, business_id, rule.weekday, rule.start_min, rule.end_min),
            )
        return cur.rowcount >= 1

    def add_block(self, business_id: int, block: Block) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO blocks(professional_id, day, start_min, end_min)"
                " SELECT id, ?, ?, ? FROM professionals WHERE id = ? AND business_id = ? AND active = 1",
                (block.day, block.start_min, block.end_min, block.professional_id, business_id),
            )
        return cur.rowcount == 1

    def remove_block(self, business_id: int, block: Block) -> bool:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                f"DELETE FROM blocks WHERE {OWNED} AND day = ? AND start_min = ? AND end_min = ?",
                (block.professional_id, business_id, block.day, block.start_min, block.end_min),
            )
        return cur.rowcount >= 1
