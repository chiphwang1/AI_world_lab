#!/usr/bin/env python3
"""Render the student Markdown completion sheet as a printable two-page PDF.

Requires reportlab. Run from any directory:
  python3 scripts/build-completion-sheet.py
  python3 scripts/build-completion-sheet.py --output docs/completion-sheet.pdf
"""

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
INK = colors.HexColor("#172C3B")
TEAL = colors.HexColor("#126D75")
RULE = colors.HexColor("#BDC9CE")
PALE = colors.HexColor("#EDF4F5")
WIDTH, HEIGHT = 612, 792
LEFT, RIGHT = 42, 570
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=13,
                      textColor=INK)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=9, leading=12)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10)


def plain(text):
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    return text.translate(str.maketrans({"→": "->", "–": "-", "—": "-",
                                        "’": "'", "“": '"', "”": '"'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "output/pdf/completion-sheet.pdf")
    args = parser.parse_args()
    source = (ROOT / "docs/completion-sheet.md").read_text()
    lines = source.splitlines()

    def one(prefix):
        matches = [line for line in lines if line.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one line starting {prefix!r}")
        return plain(matches[0])

    checks = [plain(line[6:]) for line in lines if line.startswith("- [ ] ")]
    questions = [plain(line) for line in lines if re.match(r"^[1-5]\. ", line)]
    rows = [line for line in lines if line.startswith("| ")]
    if len(checks) != 6 or len(questions) != 5 or len(rows) != 4:
        raise ValueError("Completion-sheet structure changed; review PDF layout")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(args.output), pagesize=(WIDTH, HEIGHT), invariant=1)
    pdf.setTitle("OKE lab completion sheet")
    pdf.setAuthor("OKE Bootcamp")
    pdf.setSubject("Student checkpoints, observations, and debrief")

    def paragraph(text, y, style=BODY, x=LEFT, width=RIGHT-LEFT):
        p = Paragraph(escape(text), style)
        _, height = p.wrap(width, HEIGHT)
        if y-height < 48:
            raise ValueError(f"Content exceeds printable page: {text[:50]}")
        p.drawOn(pdf, x, y-height)
        return y-height

    def rule(y, x=LEFT, width=RIGHT-LEFT):
        pdf.setStrokeColor(RULE)
        pdf.setLineWidth(0.6)
        pdf.line(x, y, x+width, y)

    def heading(text, y):
        pdf.setFillColor(TEAL)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(LEFT, y-12, text)
        return y-25

    def page(number, subtitle):
        pdf.setFillColor(TEAL)
        pdf.rect(LEFT, 751, 32, 4, fill=1, stroke=0)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 21)
        pdf.drawString(LEFT, 720, "OKE lab completion sheet")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(LEFT, 700, subtitle)
        rule(687)
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(INK)
        pdf.drawString(LEFT, 27, "OKE Bootcamp  |  60-minute hands-on lab")
        pdf.drawRightString(RIGHT, 27, f"{number} / 2")
        return 673

    y = page(1, "Record evidence at the existing checkpoints - no extra exercise.")
    y = paragraph("Keep credentials, kubeconfig contents, and tokens out of this sheet.", y, SMALL)-15
    y = paragraph(one("Name:"), y)-18
    y = heading("Checkpoints", y)
    for check in checks:
        pdf.setStrokeColor(TEAL)
        pdf.rect(LEFT, y-10, 8, 8, fill=0, stroke=1)
        y = paragraph(check, y, x=LEFT+17, width=RIGHT-LEFT-17)-8
    y = paragraph("My customized response message:", y-3)-14
    rule(y)
    y = heading("Observations", y-17)
    y = paragraph(one("Use Grafana"), y, SMALL)-10

    table_rows = []
    for row in rows:
        cells = [plain(value.strip()) for value in row.strip("|").split("|")]
        table_rows.append([Paragraph(escape(value), CELL) for value in cells])
    table = Table(table_rows, colWidths=[104, 122, 65, 66, 88, 83],
                  rowHeights=[34, 33, 33, 33])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    _, height = table.wrap(RIGHT-LEFT, HEIGHT)
    table.drawOn(pdf, LEFT, y-height)
    y -= height+14
    y = paragraph(one("Peak HPA"), y, SMALL)-8
    paragraph(one("Six replicas"), y, SMALL)
    pdf.showPage()

    y = page(2, "Five-minute debrief - explain what you observed.")
    y = paragraph("Name: ______________________________    Date: __________________", y)-19
    for question in questions:
        y = paragraph(question, y)-18
        rule(y)
        y -= 18
        rule(y)
        y -= 17
    y = paragraph(one("Prediction from"), y, SMALL)-14
    y = paragraph(one("Optional pod recovery:"), y, SMALL)-14
    y = paragraph(one("Result:"), y, SMALL)-13
    y = paragraph("If blocked, record the step, symptom, and last observed state:", y, SMALL)-17
    rule(y)
    y -= 18
    rule(y)
    y -= 17
    paragraph(one("Leave releases"), y, SMALL)
    pdf.save()
    print(args.output)


if __name__ == "__main__":
    main()
