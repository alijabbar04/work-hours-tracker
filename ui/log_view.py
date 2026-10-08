"""Log Today view - the original popup flow plus a live hours/pay preview."""

import datetime as dt
import math
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core import ai, config as cfgmod
from core.excel_store import Entry
from core.timeutil import TYPES, parse_time, hours_between
from . import theme as th
from .scroll_frame import ScrollableFrame


class LogView(ScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=th.BG)
        self.app = app
        self.q = queue.Queue()
        self._edit_original_date = None

        tk.Label(self.body, text="Log Today", bg=th.BG, fg=th.MINT,
                 font=th.FONT_H).pack(anchor="w")
        self.sub = tk.Label(self.body, text=dt.date.today().strftime("%A %d %B %Y"),
                            bg=th.BG, fg=th.MUTED, font=th.FONT)
        self.sub.pack(anchor="w", pady=(0, 12))

        grid = tk.Frame(self.body, bg=th.BG)
        grid.pack(fill="x")
        defaults = app.cfg.get("defaults", {})

        f, self.e_date = th.labelled_entry(grid, "Date",
                                           dt.date.today().strftime("%Y-%m-%d"))
        f.pack(anchor="w", pady=3)
        f, self.e_start = th.labelled_entry(grid, "Start",
                                            defaults.get("start", "09:00"))
        f.pack(anchor="w", pady=3)
        f, self.e_end = th.labelled_entry(grid, "Finish",
                                          defaults.get("finish", "17:30"))
        f.pack(anchor="w", pady=3)
        f, self.e_break = th.labelled_entry(grid, "Break (min)",
                                            str(defaults.get("break_min", "30")))
        f.pack(anchor="w", pady=3)
        f, self.e_ot = th.labelled_entry(grid, "Overtime (hrs)", "0")
        f.pack(anchor="w", pady=3)

        tf = tk.Frame(grid, bg=th.BG)
        tk.Label(tf, text="Type", bg=th.BG, fg=th.TXT, font=th.FONT,
                 width=12, anchor="w").pack(side="left")
        self.v_type = tk.StringVar(value=defaults.get("type", TYPES[0]))
        cb = ttk.Combobox(tf, textvariable=self.v_type, values=TYPES,
                          state="readonly", width=22, style="D.TCombobox")
        cb.pack(side="left", ipady=2)
        cb.bind("<<ComboboxSelected>>", self.on_type)
        tf.pack(anchor="w", pady=3)

        self.preview = tk.Label(self.body, text="", bg=th.BG, fg=th.MINT,
                                font=th.FONT_B)
        self.preview.pack(anchor="w", pady=(8, 0))

        tk.Label(self.body, text="What did you do today? (rough notes)",
                 bg=th.BG, fg=th.TXT, font=th.FONT_B).pack(anchor="w", pady=(10, 4))
        self.t_raw = tk.Text(self.body, height=5, bg=th.FIELD, fg=th.TXT,
                             insertbackground=th.MINT, relief="flat",
                             font=th.FONT, wrap="word")
        self.t_raw.pack(fill="x")

        self.btn_gen = th.button(self.body, "✨  Generate bullets", self.generate)
        self.btn_gen.pack(anchor="w", pady=8)
        tk.Label(self.body, text="Optional AI: sends these rough notes to Anthropic. "
                 "You can write the summary yourself.", bg=th.BG, fg=th.MUTED,
                 font=th.FONT_S, wraplength=650, justify="left").pack(anchor="w")

        tk.Label(self.body, text="Bullet summary (editable)", bg=th.BG, fg=th.TXT,
                 font=th.FONT_B).pack(anchor="w", pady=(2, 4))
        self.t_bullets = tk.Text(self.body, height=5, bg=th.FIELD, fg=th.TXT,
                                 insertbackground=th.MINT, relief="flat",
                                 font=th.FONT, wrap="word")
        self.t_bullets.pack(fill="x")

        self.status = tk.Label(self.body, text="", bg=th.BG, fg=th.MUTED,
                               font=th.FONT_S)
        self.status.pack(anchor="w", pady=(8, 4))

        bar = tk.Frame(self.body, bg=th.BG)
        bar.pack(fill="x", pady=(4, 0))
        self.btn_save = th.button(bar, "Save to timesheet", self.save, primary=True)
        self.btn_save.pack(side="left")
        th.button(bar, "Clear", self.clear_form).pack(side="left", padx=8)

        for w in (self.e_date, self.e_start, self.e_end, self.e_break, self.e_ot):
            w.bind("<KeyRelease>", lambda _e: self.update_preview())
        self.v_type.trace_add("write", lambda *_: self.update_preview())
        self.update_preview()
        self.after(150, self.pump)

    # ---------------- live preview ----------------
    def update_preview(self):
        try:
            d = dt.datetime.strptime(self.e_date.get().strip(), "%Y-%m-%d").date()
            start = parse_time(self.e_start.get())
            end = parse_time(self.e_end.get())
            brk_raw = self.e_break.get().strip()
            brk = int(brk_raw) if brk_raw else None
            ot = float(self.e_ot.get().strip() or 0)
        except (ValueError, TypeError):
            self.preview.config(text="—", fg=th.MUTED)
            return
        hours = hours_between(start, end, brk)
        total = round(hours + ot, 2)
        try:
            rate = cfgmod.rate_for_date(self.app.cfg, d)
            pay = round(total * rate, 2)
            self.preview.config(
                text=f"Hours: {hours:.1f}  +  OT {ot:.1f}  =  {total:.1f} h    "
                     f"@ £{rate:.2f}/hr   →   £{pay:,.2f}", fg=th.MINT)
        except ValueError:
            self.preview.config(text=f"Total {total:.1f} h — no rate configured "
                                     f"for this date", fg=th.RED)

    def on_type(self, _=None):
        if "Weekend" in self.v_type.get():
            for w in (self.e_start, self.e_end, self.e_break):
                w.delete(0, "end")
            self.set_status("Weekend: leave start/finish blank, put hours in Overtime.")
        self.update_preview()

    def set_status(self, msg, ok=True):
        self.status.config(text=msg, fg=(th.MINT if ok else th.RED))

    # ---------------- bullets (threaded) ----------------
    def generate(self):
        raw = self.t_raw.get("1.0", "end").strip()
        if not raw:
            self.set_status("Type some notes first.", ok=False)
            return
        if not messagebox.askyesno(
                "Send notes to Anthropic?",
                "Generate bullets sends the rough notes above to Anthropic's API. "
                "API usage may be billed to your account. Only send notes you are "
                "allowed to share. Continue?", parent=self):
            return
        key = ai.get_api_key()
        if not key:
            self.app.prompt_for_key()
            key = ai.get_api_key()
            if not key:
                return
        self.btn_gen.config(state="disabled", text="Generating…")
        self.set_status("Asking Claude to summarise…")
        threading.Thread(target=self._gen_worker, args=(key, raw),
                         daemon=True).start()

    def _gen_worker(self, key, raw):
        try:
            self.q.put(("bullets", ai.claude_bullets(key, raw)))
        except Exception as e:
            self.q.put(("error", str(e)))

    def pump(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "bullets":
                    self.t_bullets.delete("1.0", "end")
                    self.t_bullets.insert("1.0", payload)
                    self.set_status("Bullets generated — edit if needed, then save.")
                elif kind == "error":
                    self.set_status("API error: " + payload[:90], ok=False)
                elif kind == "saved":
                    self.set_status(payload)
                    self.app.on_data_changed()
                elif kind == "save_error":
                    self.set_status(payload, ok=False)
                self.btn_gen.config(state="normal", text="✨  Generate bullets")
        except queue.Empty:
            pass
        self.after(150, self.pump)

    # ---------------- save ----------------
    def save(self):
        try:
            d = dt.datetime.strptime(self.e_date.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            self.set_status("Date must be YYYY-MM-DD.", ok=False)
            return
        try:
            start = parse_time(self.e_start.get())
            end = parse_time(self.e_end.get())
        except (ValueError, TypeError):
            self.set_status("Couldn't read the times (use HH:MM).", ok=False)
            return
        brk_raw = self.e_break.get().strip()
        try:
            brk = int(brk_raw) if brk_raw else None
            ot = float(self.e_ot.get().strip() or 0)
        except ValueError:
            self.set_status("Break must be whole minutes; overtime a number.", ok=False)
            return
        if (brk is not None and not 0 <= brk <= 1440) or not math.isfinite(ot) or not 0 <= ot <= 24:
            self.set_status("Break must be 0–1440 minutes; overtime 0–24 hours.", ok=False)
            return
        if (start is None) != (end is None):
            self.set_status("Enter both start and finish, or leave both blank.", ok=False)
            return
        if start and end and (end <= start or hours_between(start, end, brk) < 0):
            self.set_status("Finish must be after start, and break within the shift.", ok=False)
            return
        bullets = self.t_bullets.get("1.0", "end").strip() or "• No tasks recorded"

        existing = self.app.store.entry_for_date(d)
        if existing and d != self._edit_original_date:
            if not messagebox.askyesno(
                    "Already logged",
                    f"{d:%d %b} is already in the sheet. Overwrite it?",
                    parent=self):
                return
        if (self._edit_original_date is not None
                and self._edit_original_date != d
                and self.app.store.entry_for_date(self._edit_original_date)):
            # date changed during an edit: remove the entry it replaces
            self.app.store.entries = [e for e in self.app.store.entries
                                      if e.date != self._edit_original_date]

        entry = Entry(date=d, start=start, finish=end, break_min=brk,
                      overtime=ot, type=self.v_type.get(), summary=bullets)
        self.set_status("Saving…")
        threading.Thread(target=self._save_worker, args=(entry,),
                         daemon=True).start()

    def _save_worker(self, entry):
        try:
            self.app.store.upsert(entry)
        except PermissionError:
            self.q.put(("save_error",
                        "Close the workbook in Excel, then save again."))
            return
        except Exception as e:
            self.q.put(("save_error", f"Save failed: {e}"))
            return
        msg = f"Saved {entry.date:%a %d %b} ✓"
        if self.app.store.last_mirror_error:
            msg += "  (OneDrive copy failed — will retry on next save)"
        self.q.put(("saved", msg))
        self._edit_original_date = None

    # ---------------- edit prefill / reset ----------------
    def load_entry(self, e):
        self._edit_original_date = e.date
        self.e_date.delete(0, "end")
        self.e_date.insert(0, e.date.strftime("%Y-%m-%d"))
        for widget, val in ((self.e_start, e.start), (self.e_end, e.finish)):
            widget.delete(0, "end")
            if val:
                widget.insert(0, val.strftime("%H:%M"))
        self.e_break.delete(0, "end")
        if e.break_min is not None:
            self.e_break.insert(0, str(e.break_min))
        self.e_ot.delete(0, "end")
        self.e_ot.insert(0, f"{e.overtime:g}")
        self.v_type.set(e.type)
        self.t_bullets.delete("1.0", "end")
        self.t_bullets.insert("1.0", e.summary)
        self.t_raw.delete("1.0", "end")
        self.set_status(f"Editing {e.date:%a %d %b} — press Save to update.")
        self.update_preview()

    def clear_form(self):
        self._edit_original_date = None
        defaults = self.app.cfg.get("defaults", {})
        self.e_date.delete(0, "end")
        self.e_date.insert(0, dt.date.today().strftime("%Y-%m-%d"))
        self.e_start.delete(0, "end")
        self.e_start.insert(0, defaults.get("start", "09:00"))
        self.e_end.delete(0, "end")
        self.e_end.insert(0, defaults.get("finish", "17:30"))
        self.e_break.delete(0, "end")
        self.e_break.insert(0, str(defaults.get("break_min", "30")))
        self.e_ot.delete(0, "end")
        self.e_ot.insert(0, "0")
        self.v_type.set(defaults.get("type", TYPES[0]))
        self.t_raw.delete("1.0", "end")
        self.t_bullets.delete("1.0", "end")
        self.set_status("")
        self.update_preview()

    def refresh(self):
        self.update_preview()
