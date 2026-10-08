"""Time parsing and date helpers for same-day work entries."""

import datetime as dt

TYPES = ["Office", "Office (no break)", "Office + home eve",
         "Weekend (home)", "Work from home"]


def parse_time(s):
    """Accept '9', '9:00', '09:00', '17.30', '5:30pm'. Blank -> None."""
    s = (s or "").strip().lower().replace(".", ":")
    if not s:
        return None
    ampm = None
    if s.endswith("am") or s.endswith("pm"):
        ampm, s = s[-2:], s[:-2].strip()
    if ":" in s:
        h, m = s.split(":", 1)
        h, m = int(h), int(m or 0)
    else:
        h, m = int(s), 0
    if ampm and not 1 <= h <= 12:
        raise ValueError("Use hours 1–12 with am or pm.")
    if ampm == "pm" and h < 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    return dt.time(h, m)


def hours_between(start, finish, break_min):
    """Worked hours from start/finish times minus break minutes. 0 if either missing."""
    if start is None or finish is None:
        return 0.0
    delta = (dt.datetime.combine(dt.date.min, finish)
             - dt.datetime.combine(dt.date.min, start)).total_seconds() / 3600.0
    return round(delta - (break_min or 0) / 60.0, 4)


def month_key(d):
    """(year, month) key for a date."""
    return (d.year, d.month)


def month_sheet_name(year, month):
    return dt.date(year, month, 1).strftime("%b %Y")


def month_display(year, month):
    return dt.date(year, month, 1).strftime("%B %Y")


def month_last_day(year, month):
    if month == 12:
        return dt.date(year, 12, 31)
    return dt.date(year, month + 1, 1) - dt.timedelta(days=1)


def tax_year_of(d):
    """UK tax year start-year for a date (6 Apr - 5 Apr)."""
    return d.year if (d.month, d.day) >= (4, 6) else d.year - 1


def tax_year_label(start_year):
    return f"{start_year}/{(start_year + 1) % 100:02d}"
