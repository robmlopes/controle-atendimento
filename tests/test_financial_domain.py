from domain.panel import compute_commission, is_valid_commission


def test_is_valid_commission() -> None:
    assert is_valid_commission(0) is True
    assert is_valid_commission(50) is True
    assert is_valid_commission(100) is True
    assert is_valid_commission(-1) is False
    assert is_valid_commission(101) is False


def test_compute_commission_normal() -> None:
    # 60% of R$ 50,00 (5000 cents) = R$ 30,00 (3000 cents)
    assert compute_commission(5000, 60) == 3000
    # 50% of R$ 35,00 (3500 cents) = R$ 17,50 (1750 cents)
    assert compute_commission(3500, 50) == 1750
    # 100% of R$ 40,00 (4000 cents) = 4000
    assert compute_commission(4000, 100) == 4000


def test_compute_commission_edge_cases() -> None:
    assert compute_commission(None, 60) == 0
    assert compute_commission(0, 60) == 0
    assert compute_commission(5000, 0) == 0
    # Rounding check: 33% of 1000 cents = 330 cents
    assert compute_commission(1000, 33) == 330
