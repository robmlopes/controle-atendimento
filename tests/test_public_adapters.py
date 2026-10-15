from pathlib import Path

from adapters.sqlite_admin import SqliteAdmin
from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from domain.models import NewBooking


def _setup(tmp_path: Path) -> tuple[Database, int, int, int]:
    db = Database(str(tmp_path / "public.db"))
    db.migrate()
    catalog = SqliteCatalog(db)
    business = catalog.add_business("barbearia", "Barbearia")
    pro = catalog.add_professional(business.id, "Zé")
    service = catalog.add_service(business.id, "Corte", 30, 3500)
    return db, business.id, pro.id, service.id


def test_business_whatsapp_round_trip(tmp_path: Path) -> None:
    db, bid, _, _ = _setup(tmp_path)
    admin, catalog = SqliteAdmin(db), SqliteCatalog(db)
    assert catalog.business_by_slug("barbearia").whatsapp is None  # type: ignore[union-attr]
    assert admin.update_business(bid, "Barbearia Nova", "barbearia-nova", "+5511999998888")
    assert catalog.business_by_slug("barbearia-nova").whatsapp == "+5511999998888"  # type: ignore[union-attr]
    assert admin.business(bid).name == "Barbearia Nova"  # type: ignore[union-attr]
    assert admin.business(bid).slug == "barbearia-nova"  # type: ignore[union-attr]
    catalog.add_business("outra", "Outra")
    assert not admin.update_business(bid, "Conflito", "outra", None)


def test_view_by_token_returns_names(tmp_path: Path) -> None:
    db, _, pid, sid = _setup(tmp_path)
    bookings = SqliteBookings(db)
    bookings.create(NewBooking(pid, sid, 10, 600, 630, "Ana", "+5511999990000", "tok-view"))
    view = bookings.view_by_token("tok-view")
    assert view is not None
    assert view.professional_name == "Zé" and view.service_name == "Corte" and view.business_name == "Barbearia"
    assert view.booking.customer_name == "Ana" and view.booking.status == "confirmed"
    bookings.cancel("tok-view")
    assert bookings.view_by_token("tok-view").booking.status == "cancelled"  # type: ignore[union-attr]
    assert bookings.view_by_token("missing") is None


def test_active_count_for_phone_counts_only_future_confirmed_in_same_business(tmp_path: Path) -> None:
    db, bid_a, pa, sa = _setup(tmp_path)
    cat = SqliteCatalog(db)
    bid_b = cat.add_business("outra", "Outra").id
    pb = cat.add_professional(bid_b, "Beto").id
    sb = cat.add_service(bid_b, "Barba", 20, None).id
    b = SqliteBookings(db)
    b.create(NewBooking(pa, sa, 10, 600, 630, "Ana", "+5511999990000", "t1"))
    b.create(NewBooking(pa, sa, 11, 600, 630, "Ana", "+5511999990000", "t2"))
    b.create(NewBooking(pa, sa, 5, 600, 630, "Ana", "+5511999990000", "t-past"))
    b.create(NewBooking(pa, sa, 12, 600, 630, "Ana", "+5511999990000", "t-cancelled"))
    b.cancel("t-cancelled")
    b.create(NewBooking(pb, sb, 10, 600, 620, "Ana", "+5511999990000", "t-other-biz"))
    assert b.active_count_for_phone(bid_a, "+5511999990000", 10) == 2
    assert b.active_count_for_phone(bid_a, "+5511999990000", 11) == 1
    assert b.active_count_for_phone(bid_b, "+5511999990000", 10) == 1
