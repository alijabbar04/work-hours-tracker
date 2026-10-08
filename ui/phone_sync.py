"""Import phone-logged entries from the OneDrive inbox (shared by the
startup check and the Timesheet view button)."""

from tkinter import messagebox

from core import inbox


def import_phone_entries(parent, app, silent_if_empty=False):
    """Scan the inbox; confirm with the user; upsert + archive.

    Returns the number of entries imported (0 if none / declined).
    """
    pending, errors = inbox.scan(app.cfg)

    if not pending and not errors:
        if not silent_if_empty:
            messagebox.showinfo("Phone entries",
                                "No phone entries waiting in the OneDrive inbox.",
                                parent=parent)
        return 0

    lines = []
    for _path, e in pending:
        span = (f"{e.start:%H:%M}–{e.finish:%H:%M}" if e.start and e.finish
                else "no times")
        dup = "  (replaces existing!)" if app.store.entry_for_date(e.date) else ""
        lines.append(f"• {e.date:%a %d %b %Y}  {span}  OT {e.overtime:g}  "
                     f"{e.type}{dup}")
    msg = "Entries logged on your phone:\n\n" + "\n".join(lines)
    if errors:
        msg += "\n\nSkipped (couldn't read):\n" + "\n".join(
            f"• {p}: {m}" for p, m in errors)
    if not pending:
        messagebox.showwarning("Phone entries", msg, parent=parent)
        return 0
    msg += "\n\nImport into the timesheet?"
    if not messagebox.askyesno("Phone entries", msg, parent=parent):
        return 0

    dates = [e.date for _path, e in pending]
    if len(set(dates)) != len(dates):
        messagebox.showwarning("Phone entries",
                               "Multiple inbox files describe the same date. "
                               "Keep the correct file for each date in the inbox, "
                               "then import again. No entries were changed.", parent=parent)
        return 0

    previous = list(app.store.entries)
    for _path, e in pending:
        app.store.entries = [x for x in app.store.entries if x.date != e.date]
        app.store.entries.append(e)
    app.store.entries.sort(key=lambda x: x.date)
    try:
        app.store.save()
    except PermissionError:
        app.store.entries = previous
        messagebox.showerror("Workbook locked",
                             "Close the workbook in Excel and try the import "
                             "again — nothing was archived.", parent=parent)
        return 0
    except Exception:
        app.store.entries = previous
        messagebox.showerror("Phone import failed",
                             "The timesheet could not be saved. No files were "
                             "archived; please try again.", parent=parent)
        return 0
    archive_failures = 0
    for path, _e in pending:
        if not inbox.archive(path):
            archive_failures += 1
    app.on_data_changed()
    messagebox.showinfo("Phone entries",
                        f"Imported {len(pending)} entr"
                        f"{'y' if len(pending) == 1 else 'ies'}. ✓"
                        + (f"\n{archive_failures} source files could not be archived; "
                           "remove them from the inbox to avoid importing them again."
                           if archive_failures else ""),
                        parent=parent)
    return len(pending)
