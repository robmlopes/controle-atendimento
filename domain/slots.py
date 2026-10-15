"""Free slot computation: pure, no I/O."""

from aif import contract

from domain.models import Block, Booking, BookingStatus, WeeklyRule

WEEK_DAYS = 7


def _overlaps(start: int, end: int, other_start: int, other_end: int) -> bool:
    return start < other_end and other_start < end


def _busy_ranges(
    professional_id: int, blocks: tuple[Block, ...], bookings: tuple[Booking, ...], day: int
) -> tuple[tuple[int, int], ...]:
    blocked = tuple((b.start_min, b.end_min) for b in blocks if b.professional_id == professional_id and b.day == day)
    booked = tuple(
        (b.start_min, b.end_min)
        for b in bookings
        if b.professional_id == professional_id and b.day == day and b.status == BookingStatus.CONFIRMED
    )
    return blocked + booked


def _grid_starts(rule: WeeklyRule, duration_min: int, step_min: int) -> range:
    first = -(-rule.start_min // step_min) * step_min
    return range(first, rule.end_min - duration_min + 1, step_min)


def _is_future(day: int, start: int, now_day: int, now_min: int) -> bool:
    return day > now_day or (day == now_day and start >= now_min)


@contract(
    requires=lambda professional_id, duration_min, step_min: duration_min > 0 and step_min > 0,
    ensures=lambda r, day, now_day, now_min, step_min: (
        list(r) == sorted(set(r)) and all(s % step_min == 0 and _is_future(day, s, now_day, now_min) for s in r)
    ),
    effects=[],
)
def free_slots(
    professional_id: int,
    rules: tuple[WeeklyRule, ...],
    blocks: tuple[Block, ...],
    bookings: tuple[Booking, ...],
    duration_min: int,
    day: int,
    now_day: int,
    now_min: int,
    step_min: int,
) -> tuple[int, ...]:
    """Start minutes (multiples of step_min) at which a service of duration_min can be booked on `day`.

    A slot is free when it fits entirely inside a weekly rule of the professional for that weekday, overlaps
    no block and no confirmed booking, and does not start before (now_day, now_min).
    """
    busy = _busy_ranges(professional_id, blocks, bookings, day)
    starts: set[int] = set()
    for rule in rules:
        if rule.professional_id != professional_id or rule.weekday != day % WEEK_DAYS:
            continue
        for start in _grid_starts(rule, duration_min, step_min):
            if _is_future(day, start, now_day, now_min) and not any(
                _overlaps(start, start + duration_min, b_start, b_end) for b_start, b_end in busy
            ):
                starts.add(start)
    return tuple(sorted(starts))
