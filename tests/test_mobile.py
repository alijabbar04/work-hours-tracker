"""Tests: mobile app generation and phone-inbox import."""

import datetime as dt
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import inbox, mobile
from core.excel_store import Entry

CFG = {
    "rates": [
        {"effective_date": "2024-01-01", "rate": 20.0},
        {"effective_date": "2024-07-01", "rate": 25.0},
    ],
    "personal": {"name": "Test Person", "address_lines": ["1 Road"],
                 "email": "test@example.invalid", "phone": "0"},
    "bill_to": {"lines": ["Client Ltd"]},
    "payment": {"account_name": "T", "sort_code": "00-00-00", "account_no": "1"},
    "invoice": {"next_number": 3, "self_employed_note": "note",
                "thanks_template": "Ref {number}."},
    "mobile_export_enabled": True,
    "defaults": {"start": "09:00", "finish": "17:30", "break_min": "30",
                 "type": "Office"},
}

ENTRIES = [
    Entry(dt.date(2024, 6, 26), dt.time(9), dt.time(17, 30), 30, 0,
          "Office", "• built a thing"),
    Entry(dt.date(2024, 7, 4), None, None, None, 5.0,
          "Weekend (home)", "• weekend work"),
]


class TestMobileGeneration:
    def test_payload_roundtrip(self):
        p = mobile.build_payload(ENTRIES, CFG)
        assert p["entries"][0] == {"d": "2024-06-26", "s": "09:00", "f": "17:30",
                                   "b": 30, "o": 0, "t": "Office",
                                   "su": "• built a thing"}
        assert p["entries"][1]["s"] is None
        assert p["rates"] == [{"d": "2024-01-01", "r": 20.0},
                              {"d": "2024-07-01", "r": 25.0}]
        assert p["invoice"]["next_number"] == 1  # details private by default
        json.dumps(p)  # must be JSON-serialisable

    def test_html_embeds_data_and_is_selfcontained(self):
        html = mobile.render_html(ENTRIES, CFG)
        assert "__WH_DATA__" not in html
        assert '"2024-06-26"' in html
        assert "<script src" not in html          # no external JS
        assert 'href="http' not in html           # no external CSS
        assert "api.anthropic.com" not in html
        assert "localStorage" not in html
        assert "fetch(" not in html

    def test_script_close_escaped(self):
        evil = [Entry(dt.date(2024, 7, 1), dt.time(9), dt.time(17), 0, 0,
                      "Office", "notes with </script> inside")]
        html = mobile.render_html(evil, CFG)
        payload_part = html.split('type="application/json">')[1]
        assert "</script> inside" not in payload_part.split("</script>")[0] \
            or "<\\/script> inside" in payload_part

    def test_export_all_writes_targets(self, tmp_path):
        cfg = dict(CFG)
        cfg["onedrive_mirror_dir"] = str(tmp_path / "mirror")
        cfg["mobile_copy_dirs"] = [str(tmp_path / "extra")]
        results = mobile.export_all(ENTRIES, cfg)
        assert all(err is None for _p, err in results)
        assert (tmp_path / "mirror" / mobile.MOBILE_FILENAME).exists()
        assert (tmp_path / "extra" / mobile.MOBILE_FILENAME).exists()
        assert (tmp_path / "mirror" / "inbox").is_dir()

    def test_export_never_raises_on_bad_dir(self):
        cfg = dict(CFG)
        cfg["onedrive_mirror_dir"] = "Z:\\definitely\\not\\a\\drive"
        cfg["mobile_copy_dirs"] = []
        results = mobile.export_all(ENTRIES, cfg)
        assert results and results[0][1] is not None  # error captured, not raised

    def test_inbox_label_from_mirror_path(self):
        cfg = dict(CFG)
        cfg["onedrive_mirror_dir"] = \
            "C:\\Users\\x\\OneDrive\\Documents\\Work Hours Tracker"
        assert mobile.inbox_label(cfg) == \
            "OneDrive › Documents › Work Hours Tracker › inbox"
        cfg["onedrive_mirror_dir"] = "C:\\Users\\x\\OneDrive - Company\\WH"
        assert mobile.inbox_label(cfg) == "OneDrive › WH › inbox"

    def test_inbox_label_embedded_in_html(self):
        cfg = dict(CFG)
        cfg["onedrive_mirror_dir"] = \
            "C:\\Users\\x\\OneDrive\\Documents\\Work Hours Tracker"
        html = mobile.render_html(ENTRIES, cfg)
        assert "OneDrive › Documents › Work Hours Tracker › inbox" in html
        assert "WorkHoursTracker › inbox" not in html  # old hardcoded path gone


class TestReconcileMirror:
    def make_store(self, tmp_path, monkeypatch):
        from core import config as cfgmod
        from core.excel_store import ExcelStore
        monkeypatch.setattr(cfgmod, "DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setattr(cfgmod, "BACKUP_DIR", str(tmp_path / "backups"))
        monkeypatch.setattr(cfgmod, "INVOICE_DIR", str(tmp_path / "inv"))
        cfg = dict(CFG)
        cfg["onedrive_mirror_dir"] = str(tmp_path / "mirror")
        cfg["mobile_copy_dirs"] = []
        store = ExcelStore(path=str(tmp_path / "data" / "wb.xlsx"), cfg=cfg)
        store.entries = list(ENTRIES)
        store.save()
        return store, tmp_path / "mirror" / "wb.xlsx"

    def test_up_to_date_mirror_is_untouched(self, tmp_path, monkeypatch):
        store, mirror_file = self.make_store(tmp_path, monkeypatch)
        assert mirror_file.exists()
        assert store.reconcile_mirror() is False  # already current

    def test_missing_mirror_is_healed(self, tmp_path, monkeypatch):
        store, mirror_file = self.make_store(tmp_path, monkeypatch)
        mirror_file.unlink()
        (tmp_path / "mirror" / mobile.MOBILE_FILENAME).unlink()
        assert store.reconcile_mirror() is True
        assert mirror_file.exists()
        assert (tmp_path / "mirror" / mobile.MOBILE_FILENAME).exists()

    def test_stale_mirror_is_healed(self, tmp_path, monkeypatch):
        import os
        store, mirror_file = self.make_store(tmp_path, monkeypatch)
        old = mirror_file.stat().st_mtime - 3600
        os.utime(mirror_file, (old, old))
        assert store.reconcile_mirror() is True

    def test_unreachable_mirror_returns_false(self, tmp_path, monkeypatch):
        store, _ = self.make_store(tmp_path, monkeypatch)
        store.cfg["onedrive_mirror_dir"] = "Z:\\nope"
        assert store.reconcile_mirror() is False  # no exception


class TestInbox:
    def make_file(self, tmp_path, cfg, payload, name="whentry_x.json"):
        d = tmp_path / "mirror" / "inbox"
        d.mkdir(parents=True, exist_ok=True)
        path = d / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def cfg(self, tmp_path):
        c = dict(CFG)
        c["onedrive_mirror_dir"] = str(tmp_path / "mirror")
        return c

    def good_payload(self):
        return {"app": "work-hours-tracker", "version": 1, "date": "2024-07-21",
                "start": "09:00", "finish": "17:30", "break_min": 30,
                "overtime": 1.5, "type": "Office", "summary": "• from phone"}

    def test_scan_parses_valid_entry(self, tmp_path):
        cfg = self.cfg(tmp_path)
        self.make_file(tmp_path, cfg, self.good_payload())
        pending, errors = inbox.scan(cfg)
        assert not errors and len(pending) == 1
        e = pending[0][1]
        assert e.date == dt.date(2024, 7, 21)
        assert e.start == dt.time(9, 0) and e.finish == dt.time(17, 30)
        assert e.break_min == 30 and e.overtime == 1.5
        assert e.summary == "• from phone"

    def test_weekend_entry_without_times(self, tmp_path):
        cfg = self.cfg(tmp_path)
        p = self.good_payload()
        p.update(start=None, finish=None, break_min=None, overtime=5,
                 type="Weekend (home)")
        self.make_file(tmp_path, cfg, p)
        pending, errors = inbox.scan(cfg)
        assert not errors
        e = pending[0][1]
        assert e.start is None and e.break_min is None and e.overtime == 5.0

    def test_foreign_json_rejected(self, tmp_path):
        cfg = self.cfg(tmp_path)
        self.make_file(tmp_path, cfg, {"app": "other", "date": "2024-07-21"})
        pending, errors = inbox.scan(cfg)
        assert not pending and len(errors) == 1

    def test_bad_date_rejected(self, tmp_path):
        cfg = self.cfg(tmp_path)
        p = self.good_payload()
        p["date"] = "yesterday"
        self.make_file(tmp_path, cfg, p)
        pending, errors = inbox.scan(cfg)
        assert not pending and len(errors) == 1

    def test_archive_moves_file(self, tmp_path):
        cfg = self.cfg(tmp_path)
        path = self.make_file(tmp_path, cfg, self.good_payload())
        inbox.archive(path)
        assert not os.path.exists(path)
        assert os.path.exists(os.path.join(os.path.dirname(path), "imported",
                                           os.path.basename(path)))

    def test_missing_inbox_is_empty(self, tmp_path):
        cfg = self.cfg(tmp_path)  # inbox dir never created
        pending, errors = inbox.scan(cfg)
        assert pending == [] and errors == []
