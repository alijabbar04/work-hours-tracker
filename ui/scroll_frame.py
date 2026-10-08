"""A vertically scrollable form with wheel input scoped to its own descendants."""

import tkinter as tk
from tkinter import ttk

from . import theme as th


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", th.BG)
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, bg=self.cget("bg"), highlightthickness=0,
                                yscrollincrement=24)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                       command=self.canvas.yview,
                                       style="D.Vertical.TScrollbar")
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.body = tk.Frame(self.canvas, bg=self.cget("bg"))
        self._body_window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._body_resized)
        self.canvas.bind("<Configure>", self._canvas_resized)

        # Child widget bindtags include their toplevel. Unlike bind_all, these
        # handlers never affect other app windows, hidden views or siblings.
        self._toplevel = self.winfo_toplevel()
        self._wheel_bindings = {
            event: self._toplevel.bind(event, self._on_wheel, add="+")
            for event in ("<MouseWheel>", "<Button-4>", "<Button-5>")
        }
        self.bind("<Destroy>", self._clean_bindings, add="+")

    def _body_resized(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _canvas_resized(self, event):
        self.canvas.itemconfigure(self._body_window, width=event.width)

    def _contains(self, widget):
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_wheel(self, event):
        if not self.winfo_ismapped() or not self._contains(event.widget):
            return None
        # Text areas and tables have their own wheel bindings. Avoid scrolling
        # both their contents and the surrounding form for the same gesture.
        if event.widget.winfo_class() in ("Text", "Treeview", "TCombobox", "Listbox"):
            return None
        if getattr(event, "num", None) in (4, 5):
            units = -1 if event.num == 4 else 1
        else:
            delta = getattr(event, "delta", 0)
            if not delta:
                return None
            units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        before = self.canvas.yview()
        self.canvas.yview_scroll(units, "units")
        return "break" if self.canvas.yview() != before else None

    def _clean_bindings(self, event):
        if event.widget is not self:
            return
        for sequence, binding in self._wheel_bindings.items():
            try:
                self._toplevel.unbind(sequence, binding)
            except tk.TclError:
                pass
