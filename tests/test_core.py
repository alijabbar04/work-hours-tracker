"""Unit tests: rate resolution, time parsing, month sheets, invoice grouping."""

import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config as cfgmod, invoice as inv
from core.excel_store import Entry, build_workbook, read_data_rows
from core.timeutil import (parse_time, hours_between, month_sheet_name,
                           tax_year_of, tax_year_label)

CFG = {
    "rates": [
        {"effective_date": "2024-01-01", "rate": 20.0},
        {"effective_date": "2024-03-15", "rate": 25.0},
    ],
    "personal": {"name": "Example Worker", "address_lines": ["Example address"],
                 "email": "worker@example.invalid", "phone": ""},
    "bill_to": {"lines": ["Example Client"]},
    "payment": {"account_name": "", "sort_code": "", "account_no": ""},
    "invoice": {"next_number": 1, "self_employed_note": "note",
                "thanks_template": "Ref {number}."},
}


# ----------------------------- rate resolution -----------------------------
class TestRates:
    def test_day_before_change_uses_old_rate(self):
        assert cfgmod.rate_for_date(CFG, dt.date(2024, 3, 14)) == 20.0

    def test_change_date_uses_new_rate(self):
        assert cfgmod.rate_for_date(CFG, dt.date(2024, 3, 15)) == 25.0

    def test_later_dates_use_latest(self):
        assert cfgmod.rate_for_date(CFG, dt.date(2025, 1, 1)) == 25.0

    def test_date_before_table_raises(self):
        with pytest.raises(ValueError):
            cfgmod.rate_for_date(CFG, dt.date(2023, 12, 31))

    def test_empty_table_raises(self):
        with pytest.raises(ValueError):
            cfgmod.rate_for_date({"rates": []}, dt.date(2024, 3, 1))

    def test_format_rate_trims(self):
        assert cfgmod.format_rate(20.0) == "20"
        assert cfgmod.format_rate(25.5) == "25.5"


# ----------------------------- time parsing -----------------------------
class TestParseTime:
    @pytest.mark.parametrize("raw,expected", [
        ("9", dt.time(9, 0)),
        ("9:00", dt.time(9, 0)),
        ("09:00", dt.time(9, 0)),
        ("17.30", dt.time(17, 30)),
        ("5:30pm", dt.time(17, 30)),
        ("12am", dt.time(0, 0)),
        ("12pm", dt.time(12, 0)),
        ("", None),
        ("  ", None),
    ])
    def test_parse(self, raw, expected):
        assert parse_time(raw) == expected

    def test_hours_between(self):
        assert hours_between(dt.time(9), dt.time(18), 30) == 8.5
        assert hours_between(dt.time(9), dt.time(17, 30), 0) == 8.5
        assert hours_between(None, dt.time(17), 30) == 0.0

    def test_entry_totals(self):
        e = Entry(date=dt.date(2024, 3, 9), start=dt.time(9),
                  finish=dt.time(18, 30), break_min=0, overtime=1.5)
        assert e.hours_worked() == 9.5
        assert e.total_hours() == 11.0
        assert e.pay(20.0) == 220.0


# ----------------------------- month sheets -----------------------------
class TestMonthSheets:
    def entries(self):
        return [
            Entry(dt.date(2024, 3, 13), dt.time(9), dt.time(17, 30), 30,
                  0, "Office", "• a"),
            Entry(dt.date(2024, 3, 15), dt.time(9), dt.time(17, 30), 30,
                  0, "Office", "• b"),
            Entry(dt.date(2024, 4, 4), None, None, None, 5,
                  "Weekend (home)", "• c"),
        ]

    def test_sheet_per_month_and_summary_first(self):
        wb = build_workbook(self.entries(), CFG)
        assert wb.sheetnames == ["Summary", "Mar 2024", "Apr 2024"]

    def test_pay_formula_uses_rate_in_force(self):
        wb = build_workbook(self.entries(), CFG)
        ws = wb["Mar 2024"]
        assert ws.cell(row=2, column=10).value == "=I2*20"
        assert ws.cell(row=3, column=10).value == "=I3*25"

    def test_footer_after_blank_row(self):
        wb = build_workbook(self.entries(), CFG)
        ws = wb["Mar 2024"]
        assert ws.cell(row=4, column=1).value is None          # blank spacer
        assert ws.cell(row=5, column=1).value == "Totals"
        assert ws.cell(row=5, column=10).value == '=IF(COUNT(J2:J3)=ROWS(J2:J3),SUM(J2:J3),"")'

    def test_roundtrip_preserves_values(self):
        wb = build_workbook(self.entries(), CFG)
        back = read_data_rows(wb["Mar 2024"]) + read_data_rows(wb["Apr 2024"])
        orig = sorted(self.entries(), key=lambda e: e.date)
        back = sorted(back, key=lambda e: e.date)
        assert [(e.date, e.start, e.finish, e.break_min, e.overtime, e.type,
                 e.summary) for e in orig] == \
               [(e.date, e.start, e.finish, e.break_min, e.overtime, e.type,
                 e.summary) for e in back]

    def test_sheet_name_format(self):
        assert month_sheet_name(2024, 3) == "Mar 2024"

    def test_tax_year(self):
        assert tax_year_of(dt.date(2024, 4, 5)) == 2023
        assert tax_year_of(dt.date(2024, 4, 6)) == 2024
        assert tax_year_label(2024) == "2024/25"


# ----------------------------- invoice grouping -----------------------------
class TestInvoiceGrouping:
    def entries(self):
        return [
            Entry(dt.date(2024, 3, 13), dt.time(9), dt.time(17, 30), 30, 0, "Office"),
            Entry(dt.date(2024, 3, 14), None, None, None, 2.0, "Weekend (home)"),
            Entry(dt.date(2024, 3, 15), dt.time(9), dt.time(18), 60, 0, "Office"),
            Entry(dt.date(2024, 4, 1), dt.time(9), dt.time(17), 0, 0, "Office"),
        ]

    def test_groups_split_at_rate_change(self):
        data = inv.build_invoice_data(self.entries(), CFG, 2024, 3, 1)
        assert data.groups == [(20.0, 10.0, 200.0), (25.0, 8.0, 200.0)]
        assert data.total_hours == 18.0
        assert data.total_amount == 400.0
        assert len(data.lines) == 3

    def test_footnotes_conditional(self):
        data = inv.build_invoice_data(self.entries(), CFG, 2024, 3, 1)
        notes = inv.footnotes(data)
        assert "Weekend entries were worked remotely." in notes
        assert "changed from £20.00 to £25.00" in notes
        assert "from 15 March 2024" in notes

        april = inv.build_invoice_data(self.entries(), CFG, 2024, 4, 2)
        assert inv.footnotes(april) == ""

    def test_single_rate_month_one_group(self):
        data = inv.build_invoice_data(self.entries(), CFG, 2024, 4, 2)
        assert len(data.groups) == 1
        assert data.groups[0][0] == 25.0

    def test_filename(self):
        assert inv.default_filename(CFG, 2024, 3) == "Invoice_Example_Worker_March_2024.pdf"

    def test_pdf_renders(self, tmp_path):
        data = inv.build_invoice_data(self.entries(), CFG, 2024, 3, 1,
                                      invoice_date=dt.date(2024, 4, 1))
        out = str(tmp_path / "inv.pdf")
        inv.generate_pdf(out, data, CFG)
        assert os.path.getsize(out) > 1000
