"""Smoke-test desktop views with invented data and an isolated data folder."""

import copy
import datetime as dt
import os
import tkinter as tk

import pytest

from core import ai, config
from core.excel_store import Entry, ExcelStore


@pytest.mark.skipif(os.name != "nt" and not os.environ.get("DISPLAY"), reason="Desktop display required")
def test_desktop_views_with_private_demo_data(tmp_path, monkeypatch):
    for name, path in {
        "DATA_DIR": tmp_path,
        "WORKBOOK_PATH": tmp_path / "Work_Hours_Tracker.xlsx",
        "BACKUP_DIR": tmp_path / "backups",
        "INVOICE_DIR": tmp_path / "invoices",
        "CONFIG_PATH": tmp_path / "config.json",
    }.items():
        monkeypatch.setattr(config, name, str(path))
    monkeypatch.setattr(ai, "get_api_key", lambda: None)
    from app import MainApp

    cfg = copy.deepcopy(config.DEFAULT_CONFIG)
    cfg["rates"] = [{"effective_date": "2024-01-01", "rate": 20.0}]
    store = ExcelStore(cfg=cfg)
    store.upsert(Entry(dt.date(2024, 2, 12), dt.time(9), dt.time(17), 30,
                       summary="Example task for interface testing"))
    root = tk.Tk()
    root.withdraw()
    try:
        app = MainApp(root, cfg, store)
        for view in ("log", "timesheet", "invoice", "dashboard", "settings"):
            app.show_view(view)
            root.update_idletasks()
            assert app.views[view].winfo_exists()
        # A small window must keep the save control reachable by scrolling.
        app.show_view("log")
        root.geometry("800x540")
        root.deiconify()
        root.update()
        log = app.views["log"]
        settings = app.views["settings"]
        log.canvas.yview_moveto(1)
        root.update()
        canvas_top = log.canvas.winfo_rooty()
        save_top = log.btn_save.winfo_rooty()
        assert canvas_top <= save_top
        assert save_top + log.btn_save.winfo_height() <= canvas_top + log.canvas.winfo_height()
        assert log.body.winfo_width() == log.canvas.winfo_width()
        settings_scroll = settings.canvas.yview()
        log.sub.event_generate("<MouseWheel>", delta=120)
        root.update()
        assert settings.canvas.yview() == settings_scroll
        assert store.entries[0].pay(20) == 150.0
        assert not cfg["onedrive_mirror_dir"]
    finally:
        root.destroy()
