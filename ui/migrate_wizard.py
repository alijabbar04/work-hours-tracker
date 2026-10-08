"""User-requested workbook import wizard.

Dateless rows are shown to the user with a suggested date pre-filled -
migration cannot proceed until each one is confirmed. Verification results
are shown before the app switches to the new workbook.
"""

import datetime as dt
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from core import config as cfgmod, migrate
from . import theme as th


def run_wizard(root, cfg, original_path=None):
    """Import an explicitly selected workbook. Returns whether it succeeded."""
    old_path = original_path or filedialog.askopenfilename(
        parent=root, title="Choose a tracker workbook to import",
        filetypes=[("Excel tracker workbook", "*.xlsx")])
    if not old_path:
        return False
    try:
        plan = migrate.read_original(old_path)
    except Exception as error:
        messagebox.showerror("Cannot import workbook", str(error), parent=root)
        return False
    replacement = ("This replaces the existing local timesheet; a backup will be kept.\n"
                   if os.path.exists(cfgmod.WORKBOOK_PATH) else "")
    if not messagebox.askyesno(
            "Confirm workbook import",
            f"Import {len(plan.entries)} dated entries and {len(plan.dateless)} rows needing dates?\n\n"
            + replacement + "The source workbook will be backed up and left unchanged.\n"
            "Pay is recalculated using the rates in Settings. This does not import invoice details.",
            parent=root):
        return False
    resolved = {}
    for dr in plan.dateless:
        d = _ask_date(root, dr)
        if d is None:
            messagebox.showinfo(
                "Migration cancelled",
                "Migration needs a confirmed date for every row.\n"
                "Nothing was changed — your original workbook is untouched.",
                parent=root)
            return False
        resolved[dr.row] = d

    try:
        ok, report = migrate.run(cfg, resolved, original_path=old_path)
    except Exception as error:
        messagebox.showerror("Import failed",
                             f"{error}\n\nYour source and existing local workbook were not replaced.",
                             parent=root)
        return False
    text = "\n".join(report)
    if ok:
        messagebox.showinfo("Import complete",
                            "All checks passed:\n\n" + text, parent=root)
        return True
    messagebox.showerror("Import failed",
                         "Checks failed — original workbook untouched:\n\n" + text,
                         parent=root)
    return False


def _ask_date(root, dr):
    """Modal asking the user to confirm/enter the date for a dateless row."""
    result = {"date": None}
    top = tk.Toplevel(root, bg=th.BG)
    top.title("Missing date")
    top.geometry("470x260")
    top.resizable(False, False)

    tk.Label(top, text="A row in your old timesheet has no date",
             bg=th.BG, fg=th.MINT, font=th.FONT_H2).pack(anchor="w",
                                                         padx=18, pady=(16, 6))
    detail = (f"Row {dr.row}:  {dr.day_name}"
              f"   {dr.start.strftime('%H:%M') if dr.start else '—'}"
              f"–{dr.finish.strftime('%H:%M') if dr.finish else '—'}"
              f"   break {dr.break_min if dr.break_min is not None else '—'} min"
              f"   {dr.type}")
    tk.Label(top, text=detail, bg=th.BG, fg=th.TXT, font=th.FONT).pack(
        anchor="w", padx=18)
    tk.Label(top, text=(dr.summary or "")[:90], bg=th.BG, fg=th.MUTED,
             font=th.FONT_S, wraplength=430, justify="left").pack(
        anchor="w", padx=18, pady=(2, 8))

    f = tk.Frame(top, bg=th.BG)
    f.pack(anchor="w", padx=18)
    tk.Label(f, text="Date (YYYY-MM-DD)", bg=th.BG, fg=th.TXT,
             font=th.FONT).pack(side="left")
    e = th.entry(f, dr.suggested.isoformat() if dr.suggested else "", width=14)
    e.pack(side="left", padx=8, ipady=4)
    err = tk.Label(top, text="", bg=th.BG, fg=th.RED, font=th.FONT_S)
    err.pack(anchor="w", padx=18, pady=(4, 0))

    def confirm():
        try:
            d = dt.date.fromisoformat(e.get().strip())
        except ValueError:
            err.config(text="Enter a valid date in YYYY-MM-DD format.")
            return
        if d.strftime("%A") != dr.day_name:
            if not messagebox.askyesno(
                    "Day mismatch",
                    f"{d:%d %b %Y} is a {d:%A}, but the row says "
                    f"{dr.day_name}. Use it anyway?", parent=top):
                return
        result["date"] = d
        top.destroy()

    bar = tk.Frame(top, bg=th.BG)
    bar.pack(anchor="w", padx=18, pady=12)
    th.button(bar, "Confirm date", confirm, primary=True).pack(side="left")
    th.button(bar, "Cancel migration", top.destroy).pack(side="left", padx=8)

    # NOTE: root is withdrawn at this point (migration runs before the main
    # window is shown). Do NOT call top.transient(root) here - Windows ties
    # an owned/transient window's visibility to its owner's, so a transient
    # child of a withdrawn window never actually gets mapped to screen (it
    # exists at the Tcl level but has no visible HWND, so wait_window hangs
    # forever with nothing on screen). Show it as an independent window and
    # force it to the foreground instead.
    top.lift()
    top.focus_force()
    top.grab_set()
    root.wait_window(top)
    return result["date"]
