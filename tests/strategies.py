"""Input domains for `aif fuzz`: types registered here are used wherever they appear in a contract signature."""

from hypothesis import strategies as st

from domain.models import Block, Booking, BookingStatus, DayLimit, Now, WeeklyRule

IDS = st.integers(min_value=0, max_value=3)
DAYS = st.integers(min_value=0, max_value=60)
MINUTES = st.integers(min_value=0, max_value=DayLimit.MINUTES)


@st.composite
def _ranges(draw: st.DrawFn) -> tuple[int, int]:
    start = draw(st.integers(min_value=0, max_value=DayLimit.MINUTES - 1))
    end = draw(st.integers(min_value=start + 1, max_value=DayLimit.MINUTES))
    return start, end


@st.composite
def weekly_rules(draw: st.DrawFn) -> WeeklyRule:
    start, end = draw(_ranges())
    return WeeklyRule(draw(IDS), draw(st.integers(min_value=0, max_value=6)), start, end)


@st.composite
def blocks(draw: st.DrawFn) -> Block:
    start, end = draw(_ranges())
    return Block(draw(IDS), draw(DAYS), start, end)


@st.composite
def bookings(draw: st.DrawFn) -> Booking:
    start, end = draw(_ranges())
    status = draw(st.sampled_from(list(BookingStatus)))
    return Booking(draw(IDS), draw(IDS), draw(IDS), draw(DAYS), start, end, "name", "+5511999999999", status, "token")


st.register_type_strategy(WeeklyRule, weekly_rules())
st.register_type_strategy(Block, blocks())
st.register_type_strategy(Booking, bookings())
st.register_type_strategy(
    Now, st.builds(Now, st.integers(min_value=0, max_value=100_000), st.integers(min_value=0, max_value=1439))
)
