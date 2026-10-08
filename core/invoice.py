"""Invoice PDF generation with reportlab:

page 1 - FROM block + INVOICE meta, BILL TO block, "Summary of charges"
grouped by rate, "Timesheet detail" per-day table, conditional footnote.
page 2 - Payment details block + self-employed/no-VAT line.

All names, addresses, bank details and note text come from config.
"""

import datetime as dt
import os
import re
from dataclasses import dataclass
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle,
                                PageBreak)

from . import config as cfgmod
from .timeutil import month_display, month_last_day

NAVY = colors.HexColor("#1F2A50")       # table header bars
BLUE = colors.HexColor("#2F4B9E")       # total bars
ALT = colors.HexColor("#EEF1F8")        # alternating rows
WEEKEND = colors.HexColor("#E7F5EE")    # weekend rows (mint-soft)
GREY = colors.HexColor("#6b7280")
DARK = colors.HexColor("#111827")
RULE = colors.HexColor("#c9d2e8")

F = "Helvetica"
FB = "Helvetica-Bold"
FI = "Helvetica-Oblique"


@dataclass
class InvoiceData:
    year: int
    month: int
    number: int
    invoice_date: dt.date
    lines: list          # [(date, day, description, hours, rate, amount)]
    groups: list         # [(rate, hours, amount)] ascending by first use
    total_hours: float
    total_amount: float


def build_invoice_data(entries, cfg, year, month, number, invoice_date=None):
    """Group a month's entries by the rate in force on each date."""
    month_entries = sorted((e for e in entries
                            if (e.date.year, e.date.month) == (year, month)),
                           key=lambda e: e.date)
    lines, groups, order = [], {}, []
    for e in month_entries:
        rate = cfgmod.rate_for_date(cfg, e.date)
        hours = e.total_hours()
        amount = e.pay(rate)
        lines.append((e.date, e.date.strftime("%A"), e.type, hours, rate, amount))
        if rate not in groups:
            groups[rate] = [0.0, 0.0]
            order.append(rate)
        groups[rate][0] = round(groups[rate][0] + hours, 4)
        groups[rate][1] = round(groups[rate][1] + amount, 2)
    group_list = [(r, groups[r][0], groups[r][1]) for r in order]
    return InvoiceData(
        year=year, month=month, number=number,
        invoice_date=invoice_date or dt.date.today(),
        lines=lines, groups=group_list,
        total_hours=round(sum(g[1] for g in group_list), 2),
        total_amount=round(sum(g[2] for g in group_list), 2),
    )


def default_filename(cfg, year, month):
    # Personal names must never become directory paths or Windows filenames
    # with control characters, reserved punctuation, or trailing dots/spaces.
    name = str(cfg.get("personal", {}).get("name", ""))
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", "_", name).strip("._ ")[:80] or "Worker"
    mon = dt.date(year, month, 1).strftime("%B_%Y")
    return f"Invoice_{name}_{mon}.pdf"


def footnotes(data):
    notes = []
    if any("Weekend" in ln[2] for ln in data.lines):
        notes.append("Weekend entries were worked remotely.")
    if len(data.groups) > 1:
        rates = [g[0] for g in data.groups]
        # the date the later rate first applied
        switch = min(ln[0] for ln in data.lines if ln[4] == rates[-1])
        notes.append(f"The contract rate changed from £{rates[0]:.2f} to "
                     f"£{rates[-1]:.2f} per hour from "
                     f"{switch.day} {switch:%B %Y} onwards.")
    return " ".join(notes)


def generate_pdf(path, data, cfg):
    personal = cfg["personal"]
    bill_to = cfg["bill_to"]
    payment = cfg["payment"]
    inv_cfg = cfg["invoice"]

    doc = BaseDocTemplate(path, pagesize=A4,
                          leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=16 * mm, bottomMargin=16 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame])])

    label = ParagraphStyle("label", fontName=FB, fontSize=7, textColor=GREY,
                           spaceAfter=1)
    name_st = ParagraphStyle("name", fontName=FB, fontSize=11, textColor=DARK,
                             spaceAfter=2)
    body = ParagraphStyle("body", fontName=F, fontSize=9.5, textColor=DARK,
                          leading=13)
    h2 = ParagraphStyle("h2", fontName=FB, fontSize=11.5, textColor=DARK,
                        spaceBefore=8, spaceAfter=4)
    foot = ParagraphStyle("foot", fontName=FI, fontSize=8, textColor=GREY,
                          leading=11)
    big = ParagraphStyle("big", fontName=FB, fontSize=22, leading=26,
                         textColor=DARK, alignment=2)
    meta = ParagraphStyle("meta", fontName=F, fontSize=9.5, textColor=GREY,
                          alignment=2, leading=14)

    period = (f"1–{month_last_day(data.year, data.month).day} "
              f"{month_display(data.year, data.month)}")

    from_lines = "<br/>".join(_text(x) for x in [*personal.get("address_lines", []),
                               personal.get("email", ""),
                               personal.get("phone", "")])
    left = [Paragraph("FROM", label),
            Paragraph(_text(personal.get("name", "")), name_st),
            Paragraph(from_lines, body)]
    right = [Paragraph("INVOICE", big),
             Spacer(1, 4),
             Paragraph(
                 f'Invoice no.  <font color="#111827"><b>{data.number}</b></font><br/>'
                 f'Invoice date  <font color="#111827">{data.invoice_date.day} '
                 f'{data.invoice_date:%B %Y}</font><br/>'
                 f'Period  <font color="#111827">{period}</font>', meta)]
    header = Table([[left, right]], colWidths=[doc.width * 0.55, doc.width * 0.45])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    bill_lines = list(bill_to.get("lines", []))
    bill_flow = [Paragraph("BILL TO", label)]
    if bill_lines:
        bill_flow.append(Paragraph(_text(bill_lines[0]), name_st))
        if bill_lines[1:]:
            bill_flow.append(Paragraph("<br/>".join(_text(x) for x in bill_lines[1:]), body))
    bill_tbl = Table([[bill_flow]], colWidths=[doc.width])
    bill_tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))

    # ---- summary of charges ----
    sum_rows = [["Charge", "Hours", "Rate (£/hr)", "Amount (£)"]]
    for rate, hours, amount in data.groups:
        sum_rows.append([f"Contract hours worked @ £{rate:.2f}/hour",
                         f"{hours:.1f}", f"{rate:.2f}", f"{amount:,.2f}"])
    sum_rows.append(["Total due", "", "", f"£{data.total_amount:,.2f}"])
    sum_tbl = Table(sum_rows, colWidths=[doc.width - 60 * mm, 20 * mm, 20 * mm, 20 * mm])
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FB),
        ("BACKGROUND", (0, -1), (-1, -1), BLUE),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), FB),
        ("FONTNAME", (0, 1), (-1, -2), F),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, RULE),
    ]
    sum_tbl.setStyle(TableStyle(st))

    # ---- timesheet detail ----
    det_rows = [["Date", "Day", "Description", "Hours", "Rate (£/hr)", "Amount (£)"]]
    for d, day, desc, hours, rate, amount in data.lines:
        det_rows.append([f"{d.day} {d:%b}", day, Paragraph(_text(desc), body), f"{hours:.1f}",
                         f"{rate:.2f}", f"{amount:,.2f}"])
    det_rows.append(["TOTAL", "", "", f"{data.total_hours:.1f}", "",
                     f"{data.total_amount:,.2f}"])
    det_tbl = Table(det_rows, repeatRows=1,
                    colWidths=[20 * mm, 26 * mm, doc.width - 116 * mm,
                               20 * mm, 25 * mm, 25 * mm])
    dt_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FB),
        ("BACKGROUND", (0, -1), (-1, -1), BLUE),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), FB),
        ("FONTNAME", (0, 1), (-1, -2), F),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for i, ln in enumerate(data.lines, start=1):
        if "Weekend" in ln[2]:
            dt_style.append(("BACKGROUND", (0, i), (-1, i), WEEKEND))
        elif i % 2 == 0:
            dt_style.append(("BACKGROUND", (0, i), (-1, i), ALT))
    det_tbl.setStyle(TableStyle(dt_style))

    story = [header, Spacer(1, 8), bill_tbl, Spacer(1, 4),
             Paragraph("Summary of charges", h2), sum_tbl,
             Paragraph("Timesheet detail", h2), det_tbl]
    notes = footnotes(data)
    if notes:
        story += [Spacer(1, 5), Paragraph(notes, foot)]

    # ---- page 2: payment ----
    pay_body = ParagraphStyle("pay", fontName=F, fontSize=9.5, textColor=DARK,
                              leading=15)
    thanks = str(inv_cfg.get("thanks_template", "")).replace("{number}", str(data.number))
    story += [
        PageBreak(),
        Paragraph("Payment", h2),
        Table([[[
            Paragraph("PAYMENT DETAILS", label),
            Paragraph(
                f'Account name:  <b>{_text(payment.get("account_name", ""))}</b><br/>'
                f'Sort code:  <b>{_text(payment.get("sort_code", ""))}</b>'
                f'&nbsp;&nbsp;&nbsp;&nbsp;Account no.:  '
                f'<b>{_text(payment.get("account_no", ""))}</b>', pay_body),
        ]]], colWidths=[doc.width], style=TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.75, RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ])),
        Spacer(1, 8),
        Paragraph(_text(thanks), body),
        Spacer(1, 2),
        Paragraph(_text(inv_cfg.get("self_employed_note", "")), foot),
    ]

    doc.build(story)
    return path


def _text(value):
    """Treat every config/user value as literal text, never ReportLab markup."""
    return escape(str(value or "")).replace("\n", "<br/>")


def generate(entries, cfg, year, month, number, out_dir=None, invoice_date=None):
    """Build data + PDF; returns (path, data). Caller handles mirroring/opening."""
    out_dir = out_dir or cfgmod.INVOICE_DIR
    os.makedirs(out_dir, exist_ok=True)
    data = build_invoice_data(entries, cfg, year, month, number, invoice_date)
    path = os.path.join(out_dir, default_filename(cfg, year, month))
    generate_pdf(path, data, cfg)
    return path, data
