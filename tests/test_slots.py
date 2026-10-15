from hypothesis import given
from hypothesis import strategies as st

from domain.models import Block, Booking, BookingStatus, WeeklyRule
from domain.slots import free_slots
from tests.strategies import DAYS, IDS, MINUTES, blocks, bookings, weekly_rules

MONDAY = 0
MORNING = WeeklyRule(1, MONDAY, 9 * 60, 12 * 60)


def _booking(start: int, end: int, status: str = BookingStatus.CONFIRMED) -> Booking:
    return Booking(1, 1, 1, MONDAY, start, end, "Ana", "+5511999999999", status, "tok")


def _slots(
    rules: tuple[WeeklyRule, ...],
    block_list: tuple[Block, ...] = (),
    booking_list: tuple[Booking, ...] = (),
    duration: int = 30,
    now_day: int = -1,
    now_min: int = 0,
) -> tuple[int, ...]:
    return free_slots(1, rules, block_list, booking_list, duration, MONDAY, now_day, now_min, 15)


def test_rule_range_generates_grid_slots() -> None:
    assert _slots((MORNING,), duration=60) == (540, 555, 570, 585, 600, 615, 630, 645, 660)


def test_slot_must_end_inside_range() -> None:
    assert _slots((MORNING,), duration=180) == (540,)
    assert _slots((MORNING,), duration=181) == ()


def test_confirmed_booking_removes_overlapping_slots() -> None:
    result = _slots((MORNING,), booking_list=(_booking(600, 630),))
    assert 585 not in result and 600 not in result and 615 not in result
    assert 570 in result and 630 in result


def test_cancelled_booking_does_not_block() -> None:
    assert _slots((MORNING,), booking_list=(_booking(600, 630, BookingStatus.CANCELLED),)) == _slots((MORNING,))


def test_whole_day_block_removes_everything() -> None:
    assert _slots((MORNING,), block_list=(Block(1, MONDAY, 0, 1440),)) == ()


def test_lunch_break_is_two_rules() -> None:
    rules = (WeeklyRule(1, MONDAY, 540, 600), WeeklyRule(1, MONDAY, 780, 840))
    assert _slots(rules, duration=60) == (540, 780)


def test_past_slots_are_removed_today() -> None:
    assert _slots((MORNING,), duration=60, now_day=MONDAY, now_min=650) == (660,)
    assert min(_slots((MORNING,), now_day=MONDAY, now_min=650)) >= 650
    assert _slots((MORNING,), now_day=MONDAY + 1) == ()


def test_other_professional_data_is_ignored() -> None:
    other = WeeklyRule(2, MONDAY, 0, 1440)
    assert _slots((other,)) == ()


@given(
    st.tuples(weekly_rules(), weekly_rules()),
    st.tuples(blocks()),
    st.tuples(bookings(), bookings()),
    st.integers(min_value=1, max_value=240),
    DAYS,
    DAYS,
    MINUTES,
    IDS,
)
def test_free_slots_properties(
    rules: tuple[WeeklyRule, ...],
    block_list: tuple[Block, ...],
    booking_list: tuple[Booking, ...],
    duration: int,
    day: int,
    now_day: int,
    now_min: int,
    pid: int,
) -> None:
    result = free_slots(pid, rules, block_list, booking_list, duration, day, now_day, now_min, 15)
    assert list(result) == sorted(set(result))
    for s in result:
        assert s % 15 == 0
        assert any(
            r.professional_id == pid and r.weekday == day % 7 and r.start_min <= s <= r.end_min - duration
            for r in rules
        )
        assert not any(
            b.professional_id == pid and b.day == day and s < b.end_min and b.start_min < s + duration
            for b in block_list
        )
        assert not any(
            b.status == BookingStatus.CONFIRMED
            and b.professional_id == pid
            and b.day == day
            and s < b.end_min
            and b.start_min < s + duration
            for b in booking_list
        )
        assert day > now_day or (day == now_day and s >= now_min)
