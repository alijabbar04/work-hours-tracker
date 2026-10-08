"""Import entries logged on the phone.

The mobile app's "Send to PC" exports whentry_*.json files which the user
saves into <onedrive_mirror_dir>/inbox/. This module scans that folder,
validates each file into an Entry, and (after the caller confirms) the app
upserts them and archives the files into inbox/imported/.
"""

import datetime as dt
import glob
import json
import math
import os
import shutil

from .excel_store import Entry
from .mobile import INBOX_DIRNAME
from .timeutil import TYPES, hours_between

MAX_FILE_BYTES = 256 * 1024


def inbox_dir(cfg):
    mirror = cfg.get("onedrive_mirror_dir")
    return os.path.join(mirror, INBOX_DIRNAME) if mirror else None


def scan(cfg):
    """Return (pending, errors).

    pending: list of (path, Entry) parsed from inbox JSON files.
    errors:  list of (path, message) for files that couldn't be parsed.
    """
    d = inbox_dir(cfg)
    pending, errors = [], []
    if not d or not os.path.isdir(d):
        return pending, errors
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            if os.path.islink(path) or os.path.getsize(path) > MAX_FILE_BYTES:
                raise ValueError("entry file is a link or exceeds 256 KB")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            pending.append((path, parse_entry(raw)))
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append((path, str(e)))
    return pending, errors


def parse_entry(raw):
    """Validate a phone JSON payload into an Entry. Raises ValueError."""
    if not isinstance(raw, dict) or raw.get("app") != "work-hours-tracker":
        raise ValueError("not a work-hours-tracker entry file")
    if raw.get("version") != 1:
        raise ValueError("unsupported entry file version")
    date = dt.date.fromisoformat(str(raw["date"]))
    start = _t(raw.get("start"))
    finish = _t(raw.get("finish"))
    brk = raw.get("break_min")
    if brk not in (None, ""):
        if isinstance(brk, bool) or not str(brk).isdigit():
            raise ValueError("break must be a whole number of minutes")
        brk = int(brk)
        if not 0 <= brk <= 1440:
            raise ValueError("break must be between 0 and 1440 minutes")
    else:
        brk = None
    ot = float(raw.get("overtime") or 0)
    if isinstance(raw.get("overtime"), bool) or not math.isfinite(ot) or not 0 <= ot <= 24:
        raise ValueError("overtime must be between 0 and 24 hours")
    typ = str(raw.get("type") or "Office")
    if typ not in TYPES:
        raise ValueError("unknown work type")
    if (start is None) != (finish is None):
        raise ValueError("start and finish must both be provided or both blank")
    if start and finish and (finish <= start or hours_between(start, finish, brk) < 0):
        raise ValueError("finish must be after start, with break inside the shift")
    if not isinstance(raw.get("summary", ""), str):
        raise ValueError("summary must be text")
    summary = str(raw.get("summary") or "").strip() or "• No tasks recorded"
    if len(summary) > 20000:
        raise ValueError("summary exceeds 20000 characters")
    return Entry(date=date, start=start, finish=finish, break_min=brk,
                 overtime=ot, type=typ, summary=summary)


def _t(v):
    if v in (None, ""):
        return None
    h, m = str(v).split(":", 1)
    return dt.time(int(h), int(m))


def archive(path):
    """Move an imported file into inbox/imported/ without replacing an archive.

    Return True on success so the caller can report any files still waiting.
    """
    dest_dir = os.path.join(os.path.dirname(path), "imported")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(path))
        if os.path.exists(dest):
            stem, ext = os.path.splitext(dest)
            dest = f"{stem}_{dt.datetime.now():%Y%m%d%H%M%S%f}{ext}"
        shutil.move(path, dest)
        return True
    except OSError:
        return False
