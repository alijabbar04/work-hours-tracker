"""A short, skippable local-first welcome screen."""

import datetime as dt
import math
import tkinter as tk
from tkinter import messagebox

from core import config as cfgmod
from . import theme as th


def initial_rate(rate_text, effective_text):
    """Validate an optional initial rate; a blank field means hours-only mode."""
    if not rate_text.strip():
        return None
    rate = float(rate_text.strip())
    if not math.isfinite(rate) or rate < 0:
        raise ValueError("Use a finite hourly rate of zero or more.")
    date = dt.date.fromisoformat(effective_text.strip())
    return {"effective_date": date.isoformat(), "rate": rate}


def run_setup(root, cfg):
    top = tk.Toplevel(root, bg=th.BG)
    top.title("Welcome to Work Hours Tracker")
    top.geometry("560x440")
    top.resizable(False, False)
    tk.Label(top, text="Start tracking your hours", bg=th.BG, fg=th.MINT,
             font=th.FONT_H).pack(anchor="w", padx=24, pady=(24, 12))
    tk.Label(top, text="Your records stay on this computer. No account is required.\n"
                      "Add an hourly rate for pay estimates, or skip to log hours only.",
             bg=th.BG, fg=th.TXT, font=th.FONT, justify="left",
             wraplength=510).pack(anchor="w", padx=24)
    form = tk.Frame(top, bg=th.BG)
    form.pack(anchor="w", padx=24, pady=16)
    frame, rate_entry = th.labelled_entry(form, "Hourly rate (£)", "", width=14,
                                         label_width=17)
    frame.pack(anchor="w", pady=4)
    frame, date_entry = th.labelled_entry(form, "Effective from", dt.date.today().isoformat(),
                                         width=14, label_width=17)
    frame.pack(anchor="w", pady=4)
    tk.Label(top, text="Use YYYY-MM-DD. For older entries, set a rate effective on or\n"
                      "before their dates. You can add rate changes in Settings.",
             bg=th.BG, fg=th.MUTED, font=th.FONT_S, justify="left").pack(anchor="w", padx=24)
    tk.Label(top, text="Optional later in Settings: invoice details, workbook import,\n"
                      "folder sync and a mobile companion. Sync and AI start switched off.",
             bg=th.BG, fg=th.TXT, font=th.FONT, justify="left").pack(
                 anchor="w", padx=24, pady=(18, 8))
    error_label = tk.Label(top, text="", bg=th.BG, fg=th.RED, font=th.FONT_S)
    error_label.pack(anchor="w", padx=24)

    def finish(skip=False):
        try:
            rate = None if skip else initial_rate(rate_entry.get(), date_entry.get())
        except ValueError as error:
            error_label.config(text=str(error))
            return
        previous_rates = cfg.get("rates", [])
        if rate:
            cfg["rates"] = [item for item in previous_rates
                            if item.get("effective_date") != rate["effective_date"]] + [rate]
        cfg["onboarding_complete"] = True
        try:
            cfgmod.save_config(cfg)
        except OSError as error:
            cfg["rates"] = previous_rates
            cfg["onboarding_complete"] = False
            messagebox.showerror("Could not save setup", str(error), parent=top)
            return
        top.destroy()

    buttons = tk.Frame(top, bg=th.BG)
    buttons.pack(anchor="w", padx=24, pady=10)
    th.button(buttons, "Start tracking", finish, primary=True).pack(side="left")
    th.button(buttons, "Skip for now", lambda: finish(True)).pack(side="left", padx=10)
    top.protocol("WM_DELETE_WINDOW", lambda: finish(True))
    # The main window is withdrawn, so keep this first-run window independent.
    top.lift()
    top.focus_force()
    top.grab_set()
    root.wait_window(top)
