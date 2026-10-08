"""Dashboard - dark/mint matplotlib charts + headline stats."""

import datetime as dt
import tkinter as tk

import matplotlib
matplotlib.use("Agg")  # embedded via FigureCanvasTkAgg below
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core import config as cfgmod
from core.timeutil import month_key, month_sheet_name, tax_year_of, tax_year_label
from . import theme as th


class DashboardView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=th.BG)
        self.app = app
        tk.Label(self, text="Dashboard", bg=th.BG, fg=th.MINT,
                 font=th.FONT_H).pack(anchor="w")
        self.stats = tk.Label(self, text="", bg=th.BG, fg=th.TXT,
                              font=th.FONT, justify="left")
        self.stats.pack(anchor="w", pady=(4, 8))

        self.fig = Figure(figsize=(7.4, 4.6), dpi=100, facecolor=th.BG)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().configure(bg=th.BG, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh(self):
        entries = self.app.store.entries
        cfg = self.app.cfg
        self.fig.clear()
        if not entries:
            self.stats.config(text="No data yet — log your first day.")
            self.canvas.draw()
            return

        missing_rates = False

        def pay(e):
            nonlocal missing_rates
            try:
                return e.pay(cfgmod.rate_for_date(cfg, e.date))
            except ValueError:
                missing_rates = True
                return 0.0

        months = sorted({month_key(e.date) for e in entries})
        labels = [month_sheet_name(y, m) for (y, m) in months]
        hours = [sum(e.total_hours() for e in entries
                     if month_key(e.date) == k) for k in months]
        pays = [sum(pay(e) for e in entries if month_key(e.date) == k)
                for k in months]

        today = dt.date.today()
        cur_key = (today.year, today.month)
        prev_key = (today.year - 1, 12) if today.month == 1 \
            else (today.year, today.month - 1)
        cur_h = sum(e.total_hours() for e in entries
                    if month_key(e.date) == cur_key)
        prev_h = sum(e.total_hours() for e in entries
                     if month_key(e.date) == prev_key)
        ty = tax_year_of(today)
        ty_pay = sum(pay(e) for e in entries if tax_year_of(e.date) == ty)
        pay_text = ("Set rates in Settings to calculate pay" if missing_rates else
                    f"Tax year {tax_year_label(ty)} gross estimate: £{ty_pay:,.2f}")
        self.stats.config(text=(
            f"This month: {cur_h:.1f} h   (last month {prev_h:.1f} h)      "
            f"\n{pay_text}"))

        ax1 = self.fig.add_subplot(1, 2, 1)
        ax2 = self.fig.add_subplot(1, 2, 2)
        for ax, vals, title, fmt in ((ax1, hours, "Total hours / month", "{:.0f}"),
                                     (ax2, pays, "Pay £ / month", "£{:,.0f}")):
            ax.set_facecolor(th.PANEL)
            ax.set_title(title, color=th.TXT, fontsize=10)
            ax.tick_params(colors=th.MUTED, labelsize=8)
            for s in ax.spines.values():
                s.set_color(th.PANEL)
            if ax is ax2 and missing_rates:
                ax.text(0.5, 0.5, "Add the missing hourly rates\nin Settings to see pay totals.",
                        color=th.MUTED, ha="center", va="center", transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
                continue
            bars = ax.bar(labels, vals, color=th.MINT, width=0.55)
            ax.bar_label(bars, fmt=fmt.format, color=th.MINT, fontsize=8, padding=2)
            if len(labels) > 5:
                ax.tick_params(axis="x", rotation=45)
            ax.margins(y=0.15)
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()
