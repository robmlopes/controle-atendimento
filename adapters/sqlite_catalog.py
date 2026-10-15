"""SQLite implementation of the CatalogRead and CatalogWrite ports."""

from typing import Any

from adapters.sqlite_db import Database
from domain.models import Block, Business, Professional, Service, WeeklyRule


def _service(row: tuple[Any, ...]) -> Service:
    price = None if row[4] is None else int(row[4])
    return Service(int(row[0]), int(row[1]), str(row[2]), int(row[3]), price)


class SqliteCatalog:
    def __init__(self, db: Database) -> None:
        self.db = db

    def business_by_slug(self, slug: str) -> Business | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT id, slug, name, whatsapp FROM businesses WHERE slug = ?", (slug,)).fetchone()
        return None if row is None else Business(row[0], row[1], row[2], row[3])

    def professionals(self, business_id: int) -> tuple[Professional, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT id, business_id, name, active, commission_pct FROM professionals"
                " WHERE business_id = ? AND active = 1 ORDER BY name",
                (business_id,),
            ).fetchall()
        return tuple(Professional(r[0], r[1], r[2], bool(r[3]), int(r[4])) for r in rows)

    def services_of(self, professional_id: int) -> tuple[Service, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT s.id, s.business_id, s.name, s.duration_min, s.price_cents FROM services s"
                " JOIN professional_services ps ON ps.service_id = s.id"
                " WHERE ps.professional_id = ? AND s.active = 1 ORDER BY s.name",
                (professional_id,),
            ).fetchall()
        return tuple(_service(r) for r in rows)

    def service(self, service_id: int) -> Service | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id, business_id, name, duration_min, price_cents FROM services WHERE id = ? AND active = 1",
                (service_id,),
            ).fetchone()
        return None if row is None else _service(row)

    def rules(self, professional_id: int) -> tuple[WeeklyRule, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT professional_id, weekday, start_min, end_min FROM weekly_rules WHERE professional_id = ?",
                (professional_id,),
            ).fetchall()
        return tuple(WeeklyRule(r[0], r[1], r[2], r[3]) for r in rows)

    def blocks(self, professional_id: int, day: int) -> tuple[Block, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT professional_id, day, start_min, end_min FROM blocks WHERE professional_id = ? AND day = ?",
                (professional_id, day),
            ).fetchall()
        return tuple(Block(r[0], r[1], r[2], r[3]) for r in rows)

    def add_business(self, slug: str, name: str) -> Business:
        with self.db.connection(write=True) as conn:
            cur = conn.execute("INSERT INTO businesses(slug, name) VALUES (?, ?)", (slug, name))
        return Business(int(cur.lastrowid or 0), slug, name)

    def add_professional(self, business_id: int, name: str, commission_pct: int = 100) -> Professional:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO professionals(business_id, name, commission_pct) VALUES (?, ?, ?)",
                (business_id, name, commission_pct),
            )
        return Professional(int(cur.lastrowid or 0), business_id, name, True, commission_pct)

    def add_service(self, business_id: int, name: str, duration_min: int, price_cents: int | None) -> Service:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO services(business_id, name, duration_min, price_cents) VALUES (?, ?, ?, ?)",
                (business_id, name, duration_min, price_cents),
            )
        return Service(int(cur.lastrowid or 0), business_id, name, duration_min, price_cents)

    def link_service(self, professional_id: int, service_id: int) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO professional_services(professional_id, service_id) VALUES (?, ?)",
                (professional_id, service_id),
            )

    def add_rule(self, rule: WeeklyRule) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO weekly_rules(professional_id, weekday, start_min, end_min) VALUES (?, ?, ?, ?)",
                (rule.professional_id, rule.weekday, rule.start_min, rule.end_min),
            )

    def add_block(self, block: Block) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO blocks(professional_id, day, start_min, end_min) VALUES (?, ?, ?, ?)",
                (block.professional_id, block.day, block.start_min, block.end_min),
            )
