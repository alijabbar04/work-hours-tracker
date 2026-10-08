"""Invoice view - pick a month, preview totals by rate, generate the PDF."""

import datetime as dt
import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core import config as cfgmod, invoice as inv
from core.timeutil import month_display, month_last_day
from . import theme as th


class InvoiceView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=th.BG)
        self.app = app
        self._month_keys = []

        tk.Label(self, text="Invoice", bg=th.BG, fg=th.MINT,
                 font=th.FONT_H).pack(anchor="w")
        self.hint = tk.Label(self, text="", bg=th.BG, fg=th.MUTED, font=th.FONT)
        self.hint.pack(anchor="w", pady=(0, 10))

        row = tk.Frame(self, bg=th.BG)
        row.pack(fill="x")
        tk.Label(row, text="Month", bg=th.BG, fg=th.TXT, font=th.FONT,
                 width=12, anchor="w").pack(side="left")
        self.v_month = tk.StringVar()
        self.cb_month = ttk.Combobox(row, textvariable=self.v_month,
                                     state="readonly", width=16,
                                     style="D.TCombobox")
        self.cb_month.pack(side="left", ipady=2)
        self.cb_month.bind("<<ComboboxSelected>>", lambda _e: self.update_preview())

        f = tk.Frame(self, bg=th.BG)
        f.pack(fill="x", pady=6)
        tk.Label(f, text="Invoice no.", bg=th.BG, fg=th.TXT, font=th.FONT,
                 width=12, anchor="w").pack(side="left")
        self.e_number = th.entry(f, "", width=8)
        self.e_number.pack(side="left", ipady=4)

        tk.Label(self, text="Preview", bg=th.BG, fg=th.TXT,
                 font=th.FONT_B).pack(anchor="w", pady=(12, 4))
        self.preview = tk.Text(self, height=12, bg=th.FIELD, fg=th.TXT,
                               relief="flat", font=("Consolas", 10),
                               wrap="none", state="disabled")
        self.preview.pack(fill="both", expand=True)

        self.status = tk.Label(self, text="", bg=th.BG, fg=th.MUTED,
                               font=th.FONT_S)
        self.status.pack(anchor="w", pady=(8, 4))

        bar = tk.Frame(self, bg=th.BG)
        bar.pack(fill="x")
        self.btn_gen = th.button(bar, "Generate PDF", self.generate, primary=True)
        self.btn_gen.pack(side="left")
        th.button(bar, "Open invoices folder",
                  lambda: os.startfile(cfgmod.INVOICE_DIR)).pack(side="left", padx=8)

    def refresh(self):
        months = self.app.store.months()
        self._month_keys = months
        labels = [month_display(y, m) for (y, m) in months]
        self.cb_month["values"] = labels

        # auto-suggest: within 3 days of month end -> offer current month,
        # otherwise default to the previous month with data
        today = dt.date.today()
        suggestion = None
        if labels:
            if (month_last_day(today.year, today.month) - today).days <= 3 \
                    and (today.year, today.month) in months:
                suggestion = month_display(today.year, today.month)
                self.hint.config(text="Month end is close — this month is pre-selected.")
            else:
                self.hint.config(text="")
                suggestion = labels[-1]
        if suggestion and self.v_month.get() not in labels:
            self.v_month.set(suggestion)
        self.e_number.delete(0, "end")
        self.e_number.insert(0, str(self.app.cfg["invoice"].get("next_number", 1)))
        self.update_preview()

    def current_month(self):
        for (y, m) in self._month_keys:
            if month_display(y, m) == self.v_month.get():
                return (y, m)
        return None

    def update_preview(self):
        key = self.current_month()
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        if key:
            try:
                data = inv.build_invoice_data(self.app.store.entries,
                                              self.app.cfg, key[0], key[1],
                                              number=0)
                lines = [f"{'Charge':44}{'Hours':>8}{'Rate':>8}{'Amount £':>12}",
                         "-" * 72]
                for rate, hours, amount in data.groups:
                    lines.append(f"{'Contract hours worked @ £%.2f/hour' % rate:44}"
                                 f"{hours:>8.1f}{rate:>8.2f}{amount:>12,.2f}")
                lines += ["-" * 72,
                          f"{'TOTAL':44}{data.total_hours:>8.1f}{'':>8}"
                          f"{data.total_amount:>12,.2f}",
                          "", f"{len(data.lines)} days logged in "
                              f"{month_display(*key)}."]
                notes = inv.footnotes(data)
                if notes:
                    lines += ["", "Footnote: " + notes]
                self.preview.insert("1.0", "\n".join(lines))
            except ValueError as e:
                self.preview.insert("1.0", f"Cannot price this month: {e}")
        self.preview.config(state="disabled")

    def generate(self):
        key = self.current_month()
        if not key:
            self.status.config(text="No month selected.", fg=th.RED)
            return
        try:
            number = int(self.e_number.get().strip())
            if number < 1:
                raise ValueError
        except ValueError:
            self.status.config(text="Invoice number must be a positive whole number.", fg=th.RED)
            return
        path = os.path.join(cfgmod.INVOICE_DIR,
                            inv.default_filename(self.app.cfg, *key))
        if os.path.exists(path):
            if not messagebox.askyesno(
                    "Invoice exists",
                    f"{os.path.basename(path)} already exists. Overwrite it?",
                    parent=self):
                return
        self.btn_gen.config(state="disabled", text="Generating…")
        self.status.config(text="Building PDF…", fg=th.MUTED)
        threading.Thread(target=self._worker, args=(key, number),
                         daemon=True).start()

    def _worker(self, key, number):
        try:
            path, data = inv.generate(self.app.store.entries, self.app.cfg,
                                      key[0], key[1], number)
            # mirror to OneDrive invoices folder (best effort)
            mirror_note = ""
            mirror_dir = self.app.cfg.get("onedrive_mirror_dir", "")
            if mirror_dir and self.app.cfg.get("mirror_invoices", False):
                try:
                    inv_mirror = os.path.join(mirror_dir, "invoices")
                    os.makedirs(inv_mirror, exist_ok=True)
                    shutil.copy2(path, inv_mirror)
                except OSError:
                    mirror_note = "  (OneDrive copy failed)"
            # bump the counter
            self.app.cfg["invoice"]["next_number"] = number + 1
            cfgmod.save_config(self.app.cfg)
            os.startfile(path)
            self.after(0, lambda: self._done(
                f"Saved {os.path.basename(path)} — £{data.total_amount:,.2f} "
                f"over {data.total_hours:.1f} h.{mirror_note}", True))
        except Exception as e:
            self.after(0, lambda e=e: self._done(f"Failed: {e}", False))

    def _done(self, msg, ok):
        self.status.config(text=msg, fg=(th.MINT if ok else th.RED))
        self.btn_gen.config(state="normal", text="Generate PDF")
        self.e_number.delete(0, "end")
        self.e_number.insert(0, str(self.app.cfg["invoice"].get("next_number", 1)))
