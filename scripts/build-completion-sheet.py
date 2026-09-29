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

    def section(title):
        return source.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0].splitlines()

    def checks(title):
        return [plain(line[6:]) for line in section(title) if line.startswith("- [ ] ")]

    def rows(title):
        return [line for line in section(title) if line.startswith("| ")]

    core_checks = checks("Core checkpoints")
    hpa_checks = checks("Optional HPA observations")
    core_rows = rows("Core observations")
    hpa_rows = rows("Optional HPA observations")
    questions = [plain(line) for line in section("Core debrief") if re.match(r"^[1-4]\. ", line)]
    if (len(core_checks), len(hpa_checks), len(questions), len(core_rows), len(hpa_rows)) != (4, 3, 4, 4, 4):
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
            raise ValueError(f"Content exceeds printable page (bottom={y-height}): {text[:50]}")
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

    def checklist(items, y):
        for check in items:
            pdf.setStrokeColor(TEAL)
            pdf.rect(LEFT, y-10, 8, 8, fill=0, stroke=1)
            y = paragraph(check, y, SMALL, x=LEFT+17, width=RIGHT-LEFT-17)-8
        return y

    def observations(table_source, y):
        table_rows = []
        for row in table_source:
            cells = [plain(value.strip()) for value in row.strip("|").split("|")]
            table_rows.append([Paragraph(escape(value), CELL) for value in cells])
        table = Table(table_rows, colWidths=[104, 122, 65, 66, 88, 83],
                      rowHeights=[34, 28, 28, 28])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALE),
            ("GRID", (0, 0), (-1, -1), 0.5, RULE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        _, height = table.wrap(RIGHT-LEFT, HEIGHT)
        if y-height < 48:
            raise ValueError("Observation table exceeds printable page")
        table.drawOn(pdf, LEFT, y-height)
        return y-height

    y = page(1, "Record core observations; leave optional HPA sections blank if skipped.")
    y = paragraph("Keep credentials, kubeconfig contents, and tokens out of this sheet.", y, SMALL)-10
    y = paragraph(one("Name:"), y)-12
    y = heading("Core checkpoints", y)
    y = checklist(core_checks, y)
    y = paragraph("My customized response message:", y-3)-12
    rule(y)
    y = heading("Core observations", y-12)
    y = paragraph(one("Use Grafana"), y, SMALL)-8
    y = observations(core_rows, y)-10
    y = paragraph(one("The baseline generator"), y, SMALL)-12
    y = heading("Optional HPA observations - not required", y)
    y = paragraph(one("HPA extension:"), y, SMALL)-8
    observations(hpa_rows, y)
    pdf.showPage()

    y = page(2, "Core debrief and optional extension notes.")
    y = paragraph("Name: ______________________________    Date: __________________", y)-12
    y = heading("Core debrief", y)
    for number, question in enumerate(questions, start=1):
        y = paragraph(question, y)-14
        rule(y)
        y -= 9
        if number in (2, 3):
            y = paragraph(one(f"My evidence (question {number}):"), y, SMALL)-4
        if number == 3:
            y = paragraph(one("Worker names:"), y, SMALL)-4
        y -= 6
    y = heading("Optional HPA checklist and debrief", y)
    y = checklist(hpa_checks, y)
    for prefix in ("Peak HPA", "Six replicas", "HPA metrics:", "HPA scale-in:", "CPU prediction:"):
        y = paragraph(one(prefix), y, SMALL)-5
    y = heading("Optional pod recovery", y)
    y = paragraph(one("Pod recovery:"), y, SMALL)-7
    y = paragraph(one("Recovery evidence:"), y, SMALL)-12
    y = paragraph(one("Core result:"), y, SMALL)-9
    y = paragraph("If blocked, record the step, symptom, and last observed state:", y, SMALL)-14
    rule(y)
    y -= 12
    paragraph(one("Leave releases"), y, SMALL)
    pdf.save()
    print(args.output)


if __name__ == "__main__":
    main()
