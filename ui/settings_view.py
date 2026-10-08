"""Settings - rate table, invoice details, mirror path, API key, reminder."""

import datetime as dt
import math
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core import ai, config as cfgmod, reminder
from . import theme as th
from .scroll_frame import ScrollableFrame


class SettingsView(ScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=th.BG)
        self.app = app
        self._wrapping_widgets = []
        self.body.bind("<Configure>", self._form_resized, add="+")

        tk.Label(self.body, text="Settings", bg=th.BG, fg=th.MINT,
                 font=th.FONT_H).pack(anchor="w")

        # ---------------- rate table ----------------
        self._section("Pay rates (effective date → £/hr)")
        rf = tk.Frame(self.body, bg=th.BG)
        rf.pack(fill="x")
        self.rate_tree = ttk.Treeview(rf, columns=("date", "rate"),
                                      show="headings", height=4,
                                      style="D.Treeview")
        self.rate_tree.heading("date", text="Effective from")
        self.rate_tree.heading("rate", text="Rate £/hr")
        self.rate_tree.column("date", width=140, anchor="center")
        self.rate_tree.column("rate", width=100, anchor="center")
        self.rate_tree.pack(side="left")
        rb = tk.Frame(rf, bg=th.BG)
        rb.pack(side="left", padx=10, anchor="n")
        self._rate_group, self._rate_buttons = rf, rb
        self._rates_stacked = False
        self.e_rate_date = th.entry(rb, "", width=12)
        self.e_rate_date.pack(pady=2)
        self.e_rate_val = th.entry(rb, "", width=12)
        self.e_rate_val.pack(pady=2)
        th.button(rb, "Add / update", self.add_rate).pack(pady=2)
        th.button(rb, "Remove selected", self.remove_rate).pack(pady=2)
        self._help("Date YYYY-MM-DD; hourly rate, zero or more.")

        # ---------------- personal / FROM ----------------
        self._section("Your details (FROM block on invoices)")
        self.e_name = self._row("Name")
        self.t_addr = self._text_row("Address lines")
        self.e_email = self._row("Email")
        self.e_phone = self._row("Phone")

        # ---------------- bill to ----------------
        self._section("BILL TO defaults")
        self.t_billto = self._text_row("Bill-to lines")

        # ---------------- payment ----------------
        self._section("Payment details (invoice page 2)")
        self.e_acct_name = self._row("Account name")
        self.e_sort = self._row("Sort code")
        self.e_acct_no = self._row("Account no.")

        # ---------------- invoice / mirror ----------------
        self._section("Invoice & storage")
        self.e_next_no = self._row("Next invoice no.")
        self.t_invoice_note = self._text_row("Invoice note")
        self.e_mirror = self._row("Mirror folder", width=44)
        th.button(self.body, "Choose mirror folder", self.choose_mirror).pack(anchor="w", pady=4)
        self._help("Leave blank for local-only storage. A mirror copies your workbook\n"
                                "and work notes into that folder as unencrypted files. If the folder\n"
                                "is cloud-synced, its provider receives those files. Disabling exports\n"
                   "does not remove files already copied; remove those separately.")
        self.v_mobile = tk.BooleanVar()
        self.v_mobile_details = tk.BooleanVar()
        self.v_invoice_mirror = tk.BooleanVar()
        for label, variable in [
                ("Export mobile companion (requires a mirror folder)", self.v_mobile),
                ("Include invoice and payment details in mobile companion", self.v_mobile_details),
                ("Copy generated invoice PDFs to mirror folder", self.v_invoice_mirror)]:
            self._checkbutton(label, variable)
        th.button(self.body, "Import tracker workbook…", self.import_workbook).pack(
            anchor="w", pady=10)

        # ---------------- API key ----------------
        self._section("Optional AI — Anthropic API key (OS credential store)")
        self._help("Logging hours and writing notes need no API key. Generating AI\n"
                                "summaries sends the selected notes to Anthropic after consent.\n"
                   "Invoices and bank details are not part of the AI request.")
        kf = tk.Frame(self.body, bg=th.BG)
        kf.pack(fill="x")
        self.e_key = th.entry(kf, "", width=44, show="*")
        th.button(kf, "Save key", self.save_key).pack(side="right", padx=(8, 0))
        self.e_key.pack(side="left", fill="x", expand=True, ipady=4)
        self.key_status = tk.Label(self.body, text="", bg=th.BG, fg=th.MUTED,
                                   font=th.FONT_S)
        self.key_status.pack(anchor="w")
        self._wrapping_widgets.append(self.key_status)

        # ---------------- reminder ----------------
        self._section("Reminder")
        self.v_reminder = tk.BooleanVar()
        self._checkbutton("Remind me at 17:30 on weekdays", self.v_reminder,
                          command=self.toggle_reminder)

        self.status = tk.Label(self.body, text="", bg=th.BG, fg=th.MUTED,
                               font=th.FONT_S)
        self.status.pack(anchor="w", pady=(10, 4))
        self._wrapping_widgets.append(self.status)
        th.button(self.body, "Save settings", self.save, primary=True).pack(
            anchor="w", pady=(4, 20))

    # ---------------- helpers ----------------
    def _section(self, text):
        label = tk.Label(self.body, text=text, bg=th.BG, fg=th.TXT,
                         font=th.FONT_H2, justify="left", anchor="w")
        label.pack(fill="x", pady=(16, 4))
        self._wrapping_widgets.append(label)

    def _help(self, text):
        label = tk.Label(self.body, text=text, bg=th.BG, fg=th.MUTED,
                         font=th.FONT_S, justify="left", anchor="w")
        label.pack(fill="x")
        self._wrapping_widgets.append(label)

    def _checkbutton(self, text, variable, **kwargs):
        check = tk.Checkbutton(self.body, text=text, variable=variable,
                               bg=th.BG, fg=th.TXT, activebackground=th.BG,
                               activeforeground=th.MINT, selectcolor=th.FIELD,
                               font=th.FONT, anchor="w", justify="left",
                               highlightthickness=0, **kwargs)
        check.pack(fill="x", pady=2)
        self._wrapping_widgets.append(check)

    def _form_resized(self, event):
        for widget in self._wrapping_widgets:
            widget.configure(wraplength=max(160, event.width - 32))
        if not hasattr(self, "_rate_group"):
            return
        needed = self.rate_tree.winfo_reqwidth() + self._rate_buttons.winfo_reqwidth() + 24
        stacked = event.width < needed
        if stacked != self._rates_stacked:
            self._rates_stacked = stacked
            self.rate_tree.pack_configure(side="top" if stacked else "left",
                                          fill="x" if stacked else "none")
            self._rate_buttons.pack_configure(side="top" if stacked else "left",
                                              anchor="w" if stacked else "n",
                                              padx=0 if stacked else 10,
                                              pady=8 if stacked else 0)

    def _row(self, label, width=30):
        f, e = th.labelled_entry(self.body, label, "", width, label_width=16)
        f.pack(fill="x", pady=2)
        e.pack_configure(fill="x", expand=True)
        return e

    def _text_row(self, label):
        f = tk.Frame(self.body, bg=th.BG)
        tk.Label(f, text=label, bg=th.BG, fg=th.TXT, font=th.FONT,
                 width=16, anchor="nw").pack(side="left", anchor="n")
        t = tk.Text(f, height=4, width=42, bg=th.FIELD, fg=th.TXT,
                    insertbackground=th.MINT, relief="flat", font=th.FONT)
        t.pack(side="left", fill="x", expand=True)
        f.pack(fill="x", pady=2)
        return t

    def _set(self, widget, value):
        widget.delete(0, "end")
        widget.insert(0, str(value))

    # ---------------- load / save ----------------
    def refresh(self):
        cfg = self.app.cfg
        self.rate_tree.delete(*self.rate_tree.get_children())
        for d, r in cfgmod.sorted_rates(cfg):
            self.rate_tree.insert("", "end", iid=d.isoformat(),
                                  values=(d.isoformat(), f"{r:.2f}"))
        p = cfg["personal"]
        self._set(self.e_name, p.get("name", ""))
        self.t_addr.delete("1.0", "end")
        self.t_addr.insert("1.0", "\n".join(p.get("address_lines", [])))
        self._set(self.e_email, p.get("email", ""))
        self._set(self.e_phone, p.get("phone", ""))
        self.t_billto.delete("1.0", "end")
        self.t_billto.insert("1.0", "\n".join(cfg["bill_to"].get("lines", [])))
        pay = cfg["payment"]
        self._set(self.e_acct_name, pay.get("account_name", ""))
        self._set(self.e_sort, pay.get("sort_code", ""))
        self._set(self.e_acct_no, pay.get("account_no", ""))
        self._set(self.e_next_no, cfg["invoice"].get("next_number", 1))
        self.t_invoice_note.delete("1.0", "end")
        self.t_invoice_note.insert("1.0", cfg["invoice"].get("self_employed_note", ""))
        self._set(self.e_mirror, cfg.get("onedrive_mirror_dir", ""))
        self.v_mobile.set(cfg.get("mobile_export_enabled", False))
        self.v_mobile_details.set(cfg.get("mobile_include_invoice_details", False))
        self.v_invoice_mirror.set(cfg.get("mirror_invoices", False))
        self.v_reminder.set(reminder.is_enabled())
        self.key_status.config(text="Enter a key only if you want optional AI summaries.")

    def add_rate(self):
        try:
            d = dt.date.fromisoformat(self.e_rate_date.get().strip())
            r = float(self.e_rate_val.get().strip())
            if not math.isfinite(r) or r < 0:
                raise ValueError("Rate must be finite and non-negative.")
        except ValueError:
            self.status.config(text="Rate row: date YYYY-MM-DD + numeric rate.",
                               fg=th.RED)
            return
        rates = [x for x in self.app.cfg.get("rates", [])
                 if x.get("effective_date") != d.isoformat()]
        rates.append({"effective_date": d.isoformat(), "rate": r})
        self.app.cfg["rates"] = sorted(rates, key=lambda x: x["effective_date"])
        self.refresh_rates()
        self.status.config(text="Rate added — press Save settings.", fg=th.MINT)

    def remove_rate(self):
        sel = self.rate_tree.selection()
        if not sel:
            return
        if len(self.app.cfg.get("rates", [])) <= 1:
            if not messagebox.askyesno("Switch to hours-only tracking?",
                                       "Removing the last rate leaves pay blank. You can still log hours,\n"
                                       "but invoices need a rate. Continue?", parent=self):
                return
        self.app.cfg["rates"] = [x for x in self.app.cfg["rates"]
                                 if x.get("effective_date") != sel[0]]
        self.refresh_rates()
        self.status.config(text="Rate removed — press Save settings.", fg=th.MINT)

    def save_key(self):
        k = self.e_key.get().strip()
        if not k:
            return
        try:
            ai.save_api_key(k)
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("Could not save key", str(error), parent=self)
            return
        self.e_key.delete(0, "end")
        self.key_status.config(text="A key is stored. ✓")

    def toggle_reminder(self):
        try:
            if self.v_reminder.get():
                reminder.enable()
                self.status.config(text="Reminder task registered. ✓", fg=th.MINT)
            else:
                reminder.disable()
                self.status.config(text="Reminder task removed.", fg=th.MINT)
            self.app.cfg["reminder_enabled"] = self.v_reminder.get()
            cfgmod.save_config(self.app.cfg)
        except RuntimeError as e:
            self.v_reminder.set(not self.v_reminder.get())
            messagebox.showerror("Task Scheduler", str(e), parent=self)

    def save(self):
        cfg = self.app.cfg
        try:
            next_number = int(self.e_next_no.get().strip())
            if next_number < 1:
                raise ValueError()
        except ValueError:
            self.status.config(text="Next invoice number must be a positive whole number.", fg=th.RED)
            return
        mirror = self.e_mirror.get().strip()
        if mirror:
            mirror = os.path.abspath(os.path.expanduser(mirror))
        if self.v_mobile.get() and not mirror:
            self.status.config(text="Choose a mirror folder before exporting the mobile companion.", fg=th.RED)
            return
        exposures = []
        if mirror and mirror != cfg.get("onedrive_mirror_dir", ""):
            exposures.append("workbook and work notes copied to the selected folder")
        if self.v_mobile.get() and not cfg.get("mobile_export_enabled"):
            exposures.append("mobile companion containing your work entries exported as plain files")
        if self.v_mobile_details.get() and not cfg.get("mobile_include_invoice_details"):
            exposures.append("invoice identity, client and payment details included in mobile files")
        if self.v_invoice_mirror.get() and not cfg.get("mirror_invoices"):
            exposures.append("invoice PDFs, including entered payment details, copied to the mirror folder")
        if exposures and not messagebox.askyesno(
                "Enable optional file exports?",
                "The following will be enabled:\n\n" + "\n".join("• " + item for item in exposures)
                + "\n\nThese files are not encrypted. A cloud-synced folder shares them with its provider. Continue?",
                parent=self):
            return
        cfg["personal"]["name"] = self.e_name.get().strip()
        cfg["personal"]["address_lines"] = [
            ln.strip() for ln in self.t_addr.get("1.0", "end").splitlines()
            if ln.strip()]
        cfg["personal"]["email"] = self.e_email.get().strip()
        cfg["personal"]["phone"] = self.e_phone.get().strip()
        cfg["bill_to"]["lines"] = [
            ln.strip() for ln in self.t_billto.get("1.0", "end").splitlines()
            if ln.strip()]
        cfg["payment"]["account_name"] = self.e_acct_name.get().strip()
        cfg["payment"]["sort_code"] = self.e_sort.get().strip()
        cfg["payment"]["account_no"] = self.e_acct_no.get().strip()
        cfg["invoice"]["next_number"] = next_number
        cfg["invoice"]["self_employed_note"] = self.t_invoice_note.get("1.0", "end").strip()
        cfg["onedrive_mirror_dir"] = mirror
        cfg["mobile_export_enabled"] = self.v_mobile.get()
        cfg["mobile_include_invoice_details"] = self.v_mobile_details.get()
        cfg["mirror_invoices"] = self.v_invoice_mirror.get()
        try:
            cfgmod.save_config(cfg)
            if self.app.store.entries:
                self.app.store.save()  # update pay formulas for effective-rate changes
            else:
                self.app.store.export_mobile()  # remove excluded details from current enabled export
        except OSError as error:
            self.status.config(text=f"Could not save fully: {error}. Close Excel and try again.", fg=th.RED)
            return
        self.status.config(text="Settings saved. ✓", fg=th.MINT)
        self.app.on_data_changed()

    def refresh_rates(self):
        self.rate_tree.delete(*self.rate_tree.get_children())
        for date, rate in cfgmod.sorted_rates(self.app.cfg):
            self.rate_tree.insert("", "end", iid=date.isoformat(),
                                  values=(date.isoformat(), f"{rate:.2f}"))

    def choose_mirror(self):
        folder = filedialog.askdirectory(parent=self, title="Choose optional mirror folder")
        if folder:
            self._set(self.e_mirror, folder)

    def import_workbook(self):
        from .migrate_wizard import run_wizard
        if run_wizard(self, self.app.cfg):
            self.app.store.load()
            self.app.on_data_changed()
            self.status.config(text="Workbook imported. Invoice details stay in Settings.", fg=th.MINT)
