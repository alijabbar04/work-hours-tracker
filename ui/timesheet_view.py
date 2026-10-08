"""Timesheet view - read-only month table with edit/delete/open actions."""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core import config as cfgmod
from core.timeutil import month_display
from . import theme as th


class TimesheetView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=th.BG)
        self.app = app
        self._month_keys = []

        top = tk.Frame(self, bg=th.BG)
        top.pack(fill="x")
        tk.Label(top, text="Timesheet", bg=th.BG, fg=th.MINT,
                 font=th.FONT_H).pack(side="left")
        self.v_month = tk.StringVar()
        self.cb_month = ttk.Combobox(top, textvariable=self.v_month,
                                     state="readonly", width=16,
                                     style="D.TCombobox")
        self.cb_month.pack(side="right", ipady=2)
        self.cb_month.bind("<<ComboboxSelected>>", lambda _e: self.fill_table())
        tk.Label(top, text="Month", bg=th.BG, fg=th.MUTED,
                 font=th.FONT).pack(side="right", padx=8)

        cols = ("date", "day", "start", "finish", "brk", "hours", "ot",
                "type", "total", "pay")
        heads = ("Date", "Day", "Start", "Finish", "Break", "Hours", "OT",
                 "Type", "Total", "Pay £")
        widths = (78, 82, 52, 52, 48, 52, 42, 130, 52, 68)
        frame = tk.Frame(self, bg=th.BG)
        frame.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 style="D.Treeview", selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center",
                             stretch=(c == "type"))
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview,
                           style="D.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=horizontal.set)
        horizontal.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.tag_configure("weekend", background="#12291f")
        self.tree.tag_configure("totals", background=th.PANEL,
                                foreground=th.MINT)

        tk.Label(self, text="Summary (selected day)", bg=th.BG, fg=th.TXT,
                 font=th.FONT_B).pack(anchor="w", pady=(10, 2))
        self.detail = tk.Text(self, height=4, bg=th.FIELD, fg=th.TXT,
                              relief="flat", font=th.FONT_S, wrap="word",
                              state="disabled")
        self.detail.pack(fill="x")

        bar = tk.Frame(self, bg=th.BG)
        bar.pack(fill="x", pady=(10, 0))
        actions = [("Open in Excel", self.open_excel),
                   ("Open sync folder", self.open_mirror),
                   ("Import phone entries", self.import_phone),
                   ("Edit entry", self.edit_entry),
                   ("Delete entry", self.delete_entry)]
        for i, (label, command) in enumerate(actions):
            th.button(bar, label, command).grid(row=i // 3, column=i % 3,
                                               sticky="w", padx=(0, 8), pady=(0, 6))
        self.status = tk.Label(self, text="", bg=th.BG, fg=th.MUTED,
                               font=th.FONT_S)
        self.status.pack(anchor="w", pady=(8, 0))

    def refresh(self):
        months = self.app.store.months()
        self._month_keys = months
        labels = [month_display(y, m) for (y, m) in months]
        self.cb_month["values"] = labels
        if labels and self.v_month.get() not in labels:
            self.v_month.set(labels[-1])
        self.fill_table()

    def current_month(self):
        label = self.v_month.get()
        for (y, m) in self._month_keys:
            if month_display(y, m) == label:
                return (y, m)
        return None

    def fill_table(self):
        self.tree.delete(*self.tree.get_children())
        key = self.current_month()
        if not key:
            return
        entries = self.app.store.entries_for_month(*key)
        tot_h = tot_ot = tot_total = tot_pay = 0.0
        missing_rates = False
        for e in entries:
            rate = None
            try:
                rate = cfgmod.rate_for_date(self.app.cfg, e.date)
            except ValueError:
                missing_rates = True
            pay = e.pay(rate) if rate is not None else 0.0
            tot_h += e.hours_worked()
            tot_ot += e.overtime or 0
            tot_total += e.total_hours()
            tot_pay += pay
            tags = ("weekend",) if "Weekend" in e.type else ()
            self.tree.insert("", "end", iid=e.date.isoformat(), tags=tags, values=(
                e.date.strftime("%a %d %b"), e.date.strftime("%A"),
                e.start.strftime("%H:%M") if e.start else "",
                e.finish.strftime("%H:%M") if e.finish else "",
                e.break_min if e.break_min is not None else "",
                f"{e.hours_worked():.1f}", f"{e.overtime:g}", e.type,
                f"{e.total_hours():.1f}",
                f"{pay:,.2f}" if rate is not None else "?"))
        if entries:
            self.tree.insert("", "end", iid="__totals__", tags=("totals",),
                             values=("Totals", "", "", "", "", f"{tot_h:.1f}",
                                     f"{tot_ot:.1f}", "", f"{tot_total:.1f}",
                                     "Set rates" if missing_rates else f"{tot_pay:,.2f}"))

    def selected_entry(self):
        sel = self.tree.selection()
        if not sel or sel[0] == "__totals__":
            return None
        import datetime as dt
        return self.app.store.entry_for_date(dt.date.fromisoformat(sel[0]))

    def on_select(self, _e=None):
        e = self.selected_entry()
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        if e:
            self.detail.insert("1.0", e.summary)
        self.detail.config(state="disabled")

    def open_excel(self):
        if os.path.exists(cfgmod.WORKBOOK_PATH):
            os.startfile(cfgmod.WORKBOOK_PATH)
        else:
            self.status.config(text="No workbook yet — log a day first.", fg=th.RED)

    def open_mirror(self):
        d = self.app.cfg.get("onedrive_mirror_dir", "")
        if d and os.path.isdir(d):
            os.startfile(d)
        else:
            self.status.config(text="Choose an optional sync folder in Settings first.", fg=th.RED)

    def edit_entry(self):
        e = self.selected_entry()
        if not e:
            self.status.config(text="Select a day first.", fg=th.RED)
            return
        self.app.show_view("log")
        self.app.views["log"].load_entry(e)

    def import_phone(self):
        from .phone_sync import import_phone_entries
        import_phone_entries(self, self.app, silent_if_empty=False)

    def delete_entry(self):
        e = self.selected_entry()
        if not e:
            self.status.config(text="Select a day first.", fg=th.RED)
            return
        if not messagebox.askyesno(
                "Delete entry",
                f"Delete {e.date:%A %d %B %Y} ({e.total_hours():.1f} h)?\n"
                f"A backup is taken before every write.", parent=self):
            return
        self.status.config(text="Deleting…", fg=th.MUTED)
        threading.Thread(target=self._delete_worker, args=(e.date,),
                         daemon=True).start()

    def _delete_worker(self, d):
        try:
            self.app.store.delete(d)
        except PermissionError:
            self.after(0, lambda: self.status.config(
                text="Close the workbook in Excel, then try again.", fg=th.RED))
            return
        except Exception as ex:
            self.after(0, lambda ex=ex: self.status.config(
                text=f"Delete failed: {ex}", fg=th.RED))
            return
        self.after(0, self.app.on_data_changed)
        self.after(0, lambda: self.status.config(
            text=f"Deleted {d:%a %d %b}. ✓", fg=th.MINT))
