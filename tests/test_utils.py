from core.utils import calculate_age


class TestCalculateAge:
    def test_typical_age(self):
        assert calculate_age("1995-06-15") > 28

    def test_empty_string_returns_zero(self):
        assert calculate_age("") == 0

    def test_none_returns_zero(self):
        assert calculate_age(None) == 0

    def test_invalid_format_returns_zero(self):
        assert calculate_age("not-a-date") == 0

    def test_invalid_date_returns_zero(self):
        assert calculate_age("1995-13-45") == 0

    def test_future_date(self):
        age = calculate_age("2100-01-01")
        assert age <= 0
