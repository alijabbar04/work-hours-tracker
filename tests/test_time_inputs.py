"""Reject ambiguous 12-hour inputs rather than silently miscount work."""

import datetime as dt

import pytest

from core.timeutil import parse_time


@pytest.mark.parametrize("value", ["0am", "0pm", "13am", "13pm", "24pm", "9:60", "-1:30"])
def test_invalid_times_are_rejected(value):
    with pytest.raises(ValueError):
        parse_time(value)


@pytest.mark.parametrize("value,expected", [
    ("12am", dt.time(0)), ("12pm", dt.time(12)),
    ("5:30pm", dt.time(17, 30)), ("17.30", dt.time(17, 30)),
])
def test_midnight_noon_and_24_hour_inputs(value, expected):
    assert parse_time(value) == expected
