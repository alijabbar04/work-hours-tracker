"""Consistent dark theme shared by every view."""

import tkinter as tk
from tkinter import ttk

BG = "#0d0d0d"
PANEL = "#161616"
FIELD = "#1f1f1f"
MINT = "#3ddc97"
TXT = "#e8e8e8"
MUTED = "#8a8a8a"
RED = "#ff6b6b"
MINT_DARK = "#062019"

FONT = ("Segoe UI", 10)
FONT_S = ("Segoe UI", 9)
FONT_B = ("Segoe UI", 10, "bold")
FONT_H = ("Segoe UI", 15, "bold")
FONT_H2 = ("Segoe UI", 12, "bold")


def setup_style(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("D.TCombobox", fieldbackground=FIELD, background=FIELD,
                    foreground=TXT, arrowcolor=MINT, bordercolor=FIELD,
                    lightcolor=FIELD, darkcolor=FIELD, relief="flat",
                    selectbackground=FIELD, selectforeground=TXT)
    style.map("D.TCombobox",
              fieldbackground=[("readonly", FIELD)],
              foreground=[("readonly", TXT)])
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TXT)
    root.option_add("*TCombobox*Listbox.selectBackground", MINT)
    root.option_add("*TCombobox*Listbox.selectForeground", MINT_DARK)

    style.configure("D.Treeview", background=FIELD, fieldbackground=FIELD,
                    foreground=TXT, bordercolor=PANEL, rowheight=26,
                    font=FONT_S)
    style.configure("D.Treeview.Heading", background=PANEL, foreground=MINT,
                    font=FONT_B, relief="flat")
    style.map("D.Treeview",
              background=[("selected", MINT)],
              foreground=[("selected", MINT_DARK)])
    style.map("D.Treeview.Heading", background=[("active", PANEL)])

    style.configure("D.Vertical.TScrollbar", background=PANEL,
                    troughcolor=BG, arrowcolor=MINT, bordercolor=BG)
    style.configure("D.TCheckbutton", background=BG, foreground=TXT,
                    font=FONT, focuscolor=BG)
    style.map("D.TCheckbutton", background=[("active", BG)],
              foreground=[("active", MINT)])
    return style


def button(parent, text, command, primary=False, **kw):
    if primary:
        return tk.Button(parent, text=text, command=command, bg=MINT,
                         fg=MINT_DARK, activebackground=MINT,
                         activeforeground=MINT_DARK, relief="flat",
                         font=FONT_B, cursor="hand2", padx=14, pady=7, **kw)
    return tk.Button(parent, text=text, command=command, bg=PANEL, fg=MINT,
                     activebackground=PANEL, activeforeground=MINT,
                     relief="flat", font=FONT_B, cursor="hand2",
                     padx=12, pady=6, **kw)


def entry(parent, default="", width=14, **kw):
    e = tk.Entry(parent, bg=FIELD, fg=TXT, insertbackground=MINT,
                 relief="flat", font=FONT, width=width, **kw)
    if default:
        e.insert(0, default)
    return e


def labelled_entry(parent, label, default="", width=14, label_width=12):
    f = tk.Frame(parent, bg=BG)
    tk.Label(f, text=label, bg=BG, fg=TXT, font=FONT,
             width=label_width, anchor="w").pack(side="left")
    e = entry(f, default, width)
    e.pack(side="left", ipady=4)
    return f, e
