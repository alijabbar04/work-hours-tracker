"""Config, paths and rate-table resolution for Work Hours Tracker.

All user data lives under %LOCALAPPDATA%\\WorkHoursTracker. Personal details,
bank details and rates are stored in config.json only - never in code.
"""

import copy
import datetime as dt
import json
import math
import os
import sys

APP_NAME = "WorkHoursTracker"


def data_directory():
    """Use an explicit sandbox when supplied, otherwise the OS's local app data."""
    override = os.environ.get("WORK_HOURS_TRACKER_DATA_DIR", "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, APP_NAME)


DATA_DIR = data_directory()
WORKBOOK_PATH = os.path.join(DATA_DIR, "Work_Hours_Tracker.xlsx")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
INVOICE_DIR = os.path.join(DATA_DIR, "invoices")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

KEYRING_SERVICE = "WorkHoursTracker.Anthropic"
KEYRING_USER = "api_key"

BACKUP_KEEP = 30

DEFAULT_CONFIG = {
    "rates": [],  # list of {"effective_date": "YYYY-MM-DD", "rate": float}
    "personal": {"name": "", "address_lines": [], "email": "", "phone": ""},
    "bill_to": {"lines": []},
    "payment": {"account_name": "", "sort_code": "", "account_no": ""},
    "invoice": {
        "next_number": 1,
        "self_employed_note": "",
        "thanks_template": "Thank you. Please quote invoice {number} as the reference.",
    },
    "onedrive_mirror_dir": "",  # explicit opt-in; local-only on a new install
    "mobile_copy_dirs": [],  # extra folders that get a copy of the mobile app
    "mobile_export_enabled": False,
    "mobile_include_invoice_details": False,
    "mirror_invoices": False,
    "ai_notes_consent": False,
    "reminder_enabled": False,
    "defaults": {"start": "09:00", "finish": "17:30", "break_min": "30", "type": "Office"},
    "onboarding_complete": False,
}


def ensure_dirs():
    for p in (DATA_DIR, BACKUP_DIR, INVOICE_DIR):
        os.makedirs(p, exist_ok=True)


def load_config():
    ensure_dirs()
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            stored = json.load(f)
        if not isinstance(stored, dict):
            raise ValueError("Settings must contain a JSON object. Restore config.json from a backup.")
        for field in ("personal", "bill_to", "payment", "invoice", "defaults"):
            if field in stored and not isinstance(stored[field], dict):
                raise ValueError(f"Settings field '{field}' must be an object.")
        if "rates" in stored and not isinstance(stored["rates"], list):
            raise ValueError("Settings rates must be a list.")
        _deep_update(cfg, stored)
    return cfg


def save_config(cfg):
    ensure_dirs()
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def _deep_update(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


# ----------------------------- rate table -----------------------------
def sorted_rates(cfg):
    """Rate table as [(date, rate)] sorted by effective date ascending."""
    out = []
    for item in cfg.get("rates", []):
        try:
            d = dt.date.fromisoformat(str(item["effective_date"]))
            rate = float(item["rate"])
            if not math.isfinite(rate) or rate < 0:
                continue
            out.append((d, rate))
        except (KeyError, ValueError, TypeError):
            continue
    out.sort(key=lambda t: t[0])
    return out


def rate_for_date(cfg, d):
    """The hourly rate in force on date d (latest effective_date <= d).

    Raises ValueError if the table is empty or every entry starts after d,
    so a mis-configured table can never silently price a row at 0.
    """
    rates = sorted_rates(cfg)
    chosen = None
    for eff, rate in rates:
        if eff <= d:
            chosen = rate
    if chosen is None:
        raise ValueError(f"No pay rate configured for {d.isoformat()} - check Settings > Rates.")
    return chosen


def format_rate(rate):
    """Numeric literal for Excel formulas, with unnecessary zeroes removed."""
    return f"{rate:g}"
