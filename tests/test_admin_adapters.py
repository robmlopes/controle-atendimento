from pathlib import Path

from adapters.sqlite_admin import SqliteAdmin
from adapters.sqlite_agenda import SqliteAgenda
from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from domain.models import Block, NewBooking, WeeklyRule


def _two_businesses(tmp_path: Path) -> tuple[Database, int, int, int, int, int, int]:
    db = Database(str(tmp_path / "admin.db"))
    db.migrate()
    catalog = SqliteCatalog(db)
    a, b = catalog.add_business("a", "A"), catalog.add_business("b", "B")
    pa, pb = catalog.add_professional(a.id, "Ana"), catalog.add_professional(b.id, "Beto")
    sa, sb = catalog.add_service(a.id, "Corte", 30, None), catalog.add_service(b.id, "Barba", 20, 1500)
    return db, a.id, b.id, pa.id, pb.id, sa.id, sb.id


def test_cross_business_writes_are_refused_and_change_nothing(tmp_path: Path) -> None:
    db, a, b, pa, pb, sa, sb = _two_businesses(tmp_path)
    admin = SqliteAdmin(db)
    assert admin.professional(a, pb) is None and admin.professional(a, pa) is not None
    assert not admin.add_rule(a, WeeklyRule(pb, 0, 540, 600))
    assert not admin.add_block(a, Block(pb, 5, 0, 1440))
    assert not admin.deactivate_professional(a, pb) and not admin.deactivate_service(a, sb)
    assert not admin.set_services(a, pb, (sa,))
    assert SqliteCatalog(db).rules(pb) == () and SqliteCatalog(db).blocks(pb, 5) == ()
    assert admin.professional(b, pb) is not None and len(admin.business_services(b)) == 1


def test_cross_business_remove_does_not_delete(tmp_path: Path) -> None:
    db, a, b, pa, pb, sa, sb = _two_businesses(tmp_path)
    admin = SqliteAdmin(db)
    assert admin.add_rule(b, WeeklyRule(pb, 0, 540, 600)) and admin.add_block(b, Block(pb, 5, 0, 1440))
    assert not admin.remove_rule(a, WeeklyRule(pb, 0, 540, 600)) and not admin.remove_block(a, Block(pb, 5, 0, 1440))
    assert len(SqliteCatalog(db).rules(pb)) == 1 and len(SqliteCatalog(db).blocks(pb, 5)) == 1
    assert admin.remove_rule(b, WeeklyRule(pb, 0, 540, 600)) and admin.remove_block(b, Block(pb, 5, 0, 1440))


def test_set_services_ignores_services_of_other_business(tmp_path: Path) -> None:
    db, a, b, pa, pb, sa, sb = _two_businesses(tmp_path)
    admin = SqliteAdmin(db)
    assert admin.set_services(a, pa, (sa, sb, sa))
    assert admin.linked_service_ids(pa) == (sa,)
    assert admin.set_services(a, pa, ()) and admin.linked_service_ids(pa) == ()


def test_deactivated_items_disappear_everywhere(tmp_path: Path) -> None:
    db, a, b, pa, pb, sa, sb = _two_businesses(tmp_path)
    admin, catalog = SqliteAdmin(db), SqliteCatalog(db)
    admin.set_services(a, pa, (sa,))
    assert admin.deactivate_service(a, sa) and not admin.deactivate_service(a, sa)
    assert catalog.services_of(pa) == () and catalog.service(sa) is None and admin.business_services(a) == ()
    assert admin.deactivate_professional(a, pa) and catalog.professionals(a) == ()
    assert not admin.add_rule(a, WeeklyRule(pa, 0, 540, 600))


def test_agenda_is_scoped_and_cancel_is_scoped(tmp_path: Path) -> None:
    db, a, b, pa, pb, sa, sb = _two_businesses(tmp_path)
    bookings, agenda = SqliteBookings(db), SqliteAgenda(db)
    bookings.create(NewBooking(pa, sa, 10, 600, 630, "Cli A", "+5511900000001", "ta"))
    bookings.create(NewBooking(pb, sb, 10, 600, 620, "Cli B", "+5511900000002", "tb"))
    items_a = agenda.agenda(a, 0, 20)
    assert [i.booking.customer_name for i in items_a] == ["Cli A"]
    assert items_a[0].professional_name == "Ana" and items_a[0].service_name == "Corte"
    other = agenda.agenda(b, 0, 20)[0].booking.id
    assert not agenda.cancel_for_business(a, other) and len(agenda.agenda(b, 0, 20)) == 1
    assert agenda.cancel_for_business(b, other) and agenda.cancel_for_business(b, other)
    assert agenda.agenda(b, 0, 20) == () and agenda.agenda(a, 11, 20) == ()
