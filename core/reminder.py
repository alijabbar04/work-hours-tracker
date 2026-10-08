"""Windows Task Scheduler integration for the 17:30 weekday reminder.

Enabling registers a task that launches the app with --reminder Mon-Fri at
17:30; with that flag the app opens Log Today only if today has no entry,
otherwise it exits silently. Disabling deletes the task.
"""

import os
import hashlib
import subprocess
import sys
from . import config as cfgmod

TASK_NAME = "WorkHoursTracker_Reminder_" + hashlib.sha256(
    os.path.normcase(cfgmod.DATA_DIR).encode("utf-8")).hexdigest()[:12]
_HIDE = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


def launch_command():
    """Command line for the scheduled task, frozen exe or source."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --reminder'
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "app.py")
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    py = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{py}" "{script}" --reminder'


def enable():
    if sys.platform != "win32":
        raise RuntimeError("Scheduled reminders are currently available on Windows only.")
    if os.environ.get("WORK_HOURS_TRACKER_DATA_DIR"):
        raise RuntimeError("Reminders are disabled while using a custom data directory. Launch normally to enable them.")
    cmd = ["schtasks", "/Create", "/F", "/TN", TASK_NAME,
           "/TR", launch_command(), "/SC", "WEEKLY",
           "/D", "MON,TUE,WED,THU,FRI", "/ST", "17:30"]
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=_HIDE)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "schtasks failed")


def disable():
    if sys.platform != "win32":
        return
    r = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
                       capture_output=True, text=True, creationflags=_HIDE)
    # "cannot find the file" (task absent) is fine
    if r.returncode != 0 and "ERROR: The system cannot find" not in (r.stderr or ""):
        stderr = (r.stderr or "").strip()
        if stderr and "cannot find" not in stderr.lower():
            raise RuntimeError(stderr)


def is_enabled():
    if sys.platform != "win32":
        return False
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME],
                       capture_output=True, text=True, creationflags=_HIDE)
    return r.returncode == 0
