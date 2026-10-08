"""Work Hours Tracker - single-window Tkinter app.

Entry point. Handles the single-instance guard, --reminder mode,
first-run setup, and the sidebar navigation between views.
"""

import ctypes
import datetime as dt
import hashlib
import os
import sys
import tkinter as tk
from tkinter import messagebox

from core import ai, config as cfgmod
from core.excel_store import ExcelStore
from ui import theme as th

MUTEX_NAME = "WorkHoursTracker_" + hashlib.sha256(
    os.path.normcase(cfgmod.DATA_DIR).encode("utf-8")).hexdigest()[:16]
ERROR_ALREADY_EXISTS = 183
_mutex_handle = None


def acquire_single_instance():
    """Windows guard per data directory; source launches work on other systems."""
    global _mutex_handle
    if sys.platform != "win32":
        return True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    _mutex_handle = kernel.CreateMutexW(None, False, MUTEX_NAME)
    if not _mutex_handle:
        raise OSError(ctypes.get_last_error(), "Could not acquire the app instance lock.")
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def apply_dark_titlebar(root):
    """Ask DWM to draw a dark title bar (Windows 10 1809+/11) so the native
    chrome matches the app's dark theme instead of a clashing white bar.
    Harmless no-op on systems without the attribute."""
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (19 pre-20H1)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value),
                    ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass


def window_geometry(root):
    """Fit the available desktop, including smaller displays and scaled Windows."""
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    left, top = 0, 0
    if sys.platform == "win32":
        class Rect(ctypes.Structure):
            _fields_ = [(field, ctypes.c_long) for field in ("left", "top", "right", "bottom")]
        work_area = Rect()
        try:
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(work_area), 0):
                left, top = work_area.left, work_area.top
                width = work_area.right - left
                height = work_area.bottom - top
        except (AttributeError, OSError):
            pass
    available_width = max(320, width - 32)
    available_height = max(240, height - 80)  # window chrome and desktop margin
    initial_width = min(1100, available_width)
    initial_height = min(820, available_height)
    x = left + max(0, (width - initial_width) // 2)
    y = top + max(0, (height - initial_height - 40) // 2)
    minimum = (min(720, available_width), min(480, available_height))
    return f"{initial_width}x{initial_height}+{x}+{y}", minimum


class MainApp:
    def __init__(self, root, cfg, store, start_view="log"):
        self.root = root
        self.cfg = cfg
        self.store = store
        self.views = {}

        root.title("Work Hours Tracker")
        root.configure(bg=th.BG)
        geometry, minimum = window_geometry(root)
        root.geometry(geometry)
        root.minsize(*minimum)
        th.setup_style(root)
        apply_dark_titlebar(root)

        sidebar = tk.Frame(root, bg=th.PANEL, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="⏱  Work Hours", bg=th.PANEL, fg=th.MINT,
                 font=th.FONT_H2).pack(anchor="w", padx=16, pady=(20, 16))

        self.content = tk.Frame(root, bg=th.BG)
        self.content.pack(side="left", fill="both", expand=True,
                          padx=24, pady=20)

        from ui.log_view import LogView
        from ui.timesheet_view import TimesheetView
        from ui.invoice_view import InvoiceView
        from ui.dashboard_view import DashboardView
        from ui.settings_view import SettingsView
        specs = [("log", "Log Today", LogView),
                 ("timesheet", "Timesheet", TimesheetView),
                 ("invoice", "Invoice", InvoiceView),
                 ("dashboard", "Dashboard", DashboardView),
                 ("settings", "Settings", SettingsView)]
        self.nav_buttons = {}
        for key, label, cls in specs:
            self.views[key] = cls(self.content, self)
            btn = tk.Button(sidebar, text=label, anchor="w",
                            command=lambda k=key: self.show_view(k),
                            bg=th.PANEL, fg=th.TXT, activebackground=th.FIELD,
                            activeforeground=th.MINT, relief="flat",
                            font=th.FONT, cursor="hand2", padx=18, pady=9,
                            bd=0)
            btn.pack(fill="x")
            self.nav_buttons[key] = btn

        self.footer = tk.Label(sidebar, text="", bg=th.PANEL, fg=th.MUTED,
                               font=("Segoe UI", 8), justify="left")
        self.footer.pack(side="bottom", anchor="w", padx=16, pady=12)

        self.show_view(start_view)

    def show_view(self, key):
        for k, v in self.views.items():
            v.pack_forget()
            self.nav_buttons[k].config(fg=th.TXT, bg=th.PANEL)
        self.views[key].pack(fill="both", expand=True)
        self.nav_buttons[key].config(fg=th.MINT, bg=th.FIELD)
        self.views[key].refresh()

    def on_data_changed(self):
        n = len(self.store.entries)
        self.footer.config(text=f"{n} days logged\n{cfgmod.DATA_DIR}")
        for v in self.views.values():
            if v.winfo_ismapped():
                v.refresh()

    def prompt_for_key(self):
        top = tk.Toplevel(self.root, bg=th.BG)
        top.title("Anthropic API key")
        top.geometry("430x150")
        tk.Label(top, text="Optional AI key (requires an OS credential store):",
                 bg=th.BG, fg=th.TXT, font=th.FONT).pack(anchor="w",
                                                         padx=16, pady=(16, 6))
        e = th.entry(top, "", width=44, show="*")
        e.pack(padx=16, ipady=4)

        def ok():
            k = e.get().strip()
            if k:
                try:
                    ai.save_api_key(k)
                except (ValueError, RuntimeError) as error:
                    messagebox.showerror("Could not save key", str(error), parent=top)
                    return
            top.destroy()
        th.button(top, "Save", ok, primary=True).pack(pady=14)
        top.transient(self.root)
        top.grab_set()
        self.root.wait_window(top)


def main():
    reminder_mode = "--reminder" in sys.argv

    if not acquire_single_instance():
        return  # another instance is already open

    root = tk.Tk()
    root.withdraw()
    try:
        cfg = cfgmod.load_config()
    except (ValueError, OSError) as error:
        messagebox.showerror("Could not read settings",
                             f"{error}\n\nSettings were not overwritten.", parent=root)
        root.destroy()
        return
    store = ExcelStore(cfg=cfg)

    try:
        store.load()
    except PermissionError:
        messagebox.showerror("Workbook locked",
                             "Close the workbook in Excel and reopen the app.")
        root.destroy()
        return
    except Exception as error:
        messagebox.showerror("Could not open workbook",
                             f"{error}\n\nYour workbook was not changed.", parent=root)
        root.destroy()
        return

    # catch-up sync: heal the OneDrive copies if an earlier save was offline
    try:
        store.reconcile_mirror()
    except Exception:
        pass

    if reminder_mode and store.entry_for_date(dt.date.today()):
        root.destroy()
        return  # today already logged - exit silently

    from ui.setup_view import run_setup
    if not cfg.get("onboarding_complete") and not reminder_mode:
        run_setup(root, cfg)

    root.deiconify()
    app = MainApp(root, cfg, store, start_view="log")
    app.on_data_changed()

    root.mainloop()


if __name__ == "__main__":
    main()
