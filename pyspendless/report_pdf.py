"""
report_pdf.py – Generazione del report annuale PDF con fpdf2.

Usa fpdf2 per costruire il documento programmaticamente e incorpora
i grafici matplotlib (PNG bytes) prodotti da report_charts.py.
"""

import io
from typing import Dict, Any, List

from fpdf import FPDF, XPos, YPos

MONTHS_IT = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
             "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

# Colori brand (r, g, b)
COLOR_PRIMARY  = (13, 110, 253)    # Bootstrap primary blue
COLOR_EXPENSE  = (220, 53, 69)     # Bootstrap danger red
COLOR_INCOME   = (25, 135, 84)     # Bootstrap success green
COLOR_HEADER   = (33, 37, 41)      # dark
COLOR_SUBHEAD  = (73, 80, 87)      # secondary
COLOR_LIGHT_BG = (248, 249, 250)   # Bootstrap light
COLOR_BORDER   = (222, 226, 230)   # Bootstrap border
COLOR_WHITE    = (255, 255, 255)


class ReportPDF(FPDF):

    def __init__(self, account_name: str, year: int):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.account_name = account_name
        self.year = year
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=15, top=15, right=15)

    @staticmethod
    def _safe(text: str) -> str:
        """Sostituisce caratteri non-latin1 con equivalenti ASCII/leggibili."""
        return (text
                .replace("\u20ac", "EUR")   # €
                .replace("\u0394", "D")     # Δ (Delta)
                .replace("\u2026", "...")   # …
                .replace("\u2013", "-").replace("\u2014", "-")
                .replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2265", ">=").replace("\u2264", "<=")
                .replace("\u00e0", "a").replace("\u00e8", "e")
                .replace("\u00e9", "e").replace("\u00ec", "i")
                .replace("\u00f2", "o").replace("\u00f9", "u")
                .replace("\u00e3", "a").replace("\u00f5", "o")
                .replace("\u00fc", "u").replace("\u00e4", "a")
                .replace("\u00f6", "o").replace("\u00df", "ss"))

    def _cell(self, *args, **kwargs):
        """cell() con testo reso ASCII-safe."""
        if args:
            args = list(args)
            args[1] = self._safe(str(args[1])) if len(args) > 1 else args[1]
            args = tuple(args)
        if "text" in kwargs:
            kwargs["text"] = self._safe(str(kwargs["text"]))
        return self.cell(*args, **kwargs)

    def normalize_text(self, text: str) -> str:
        """Override fpdf2: applica _safe prima della codifica latin-1."""
        return super().normalize_text(self._safe(text))

    # ── Header e Footer ──────────────────────────────────────────────────────

    def header(self):
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 12, "F")
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 10)
        self.set_xy(15, 2)
        self.cell(0, 8, f"PySpendless – Report Annuale {self.year}  |  {self.account_name}",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*COLOR_HEADER)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_SUBHEAD)
        self.cell(0, 10, f"Pagina {self.page_no()} / {{nb}}  –  PySpendless", align="C")
        self.set_text_color(*COLOR_HEADER)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def section_title(self, title: str):
        """Titolo di sezione con sfondo colorato."""
        self.ln(4)
        self.set_fill_color(*COLOR_PRIMARY)
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.set_text_color(*COLOR_HEADER)
        self.ln(2)

    def sub_title(self, title: str):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*COLOR_SUBHEAD)
        self.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*COLOR_HEADER)

    def kpi_row(self, items: List[tuple]):
        """
        Riga di KPI box: items = [(label, value, color), ...]
        """
        col_w = (self.epw) / len(items)
        for label, value, color in items:
            x = self.get_x()
            y = self.get_y()
            self.set_fill_color(*COLOR_LIGHT_BG)
            self.rect(x, y, col_w - 2, 18, "F")
            self.set_draw_color(*COLOR_BORDER)
            self.rect(x, y, col_w - 2, 18)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*COLOR_SUBHEAD)
            self.set_xy(x + 2, y + 2)
            self.cell(col_w - 4, 5, label)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*color)
            self.set_xy(x + 2, y + 8)
            self.cell(col_w - 4, 7, value)
            self.set_xy(x + col_w, y)
        self.ln(20)
        self.set_text_color(*COLOR_HEADER)
        self.set_draw_color(0, 0, 0)

    def table_header(self, cols: List[tuple]):
        """cols = [(label, width, align), ...]"""
        self.set_fill_color(*COLOR_HEADER)
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 8)
        for label, w, align in cols:
            self.cell(w, 6, label, border=0, align=align, fill=True)
        self.ln()
        self.set_text_color(*COLOR_HEADER)

    def table_row(self, cols: List[tuple], fill: bool = False):
        """cols = [(value, width, align, color?), ...]"""
        if fill:
            self.set_fill_color(*COLOR_LIGHT_BG)
        self.set_font("Helvetica", "", 8)
        for item in cols:
            value = item[0]
            w     = item[1]
            align = item[2]
            color = item[3] if len(item) > 3 else COLOR_HEADER
            self.set_text_color(*color)
            self.cell(w, 5.5, str(value), border=0, align=align, fill=fill)
        self.set_text_color(*COLOR_HEADER)
        self.ln()

    def add_chart(self, img_bytes: bytes, w: float = 180, caption: str = ""):
        """Incorpora un'immagine PNG (bytes) nel documento."""
        buf = io.BytesIO(img_bytes)
        x = self.get_x()
        h = w * 0.4   # aspect ratio approssimativo
        # Evita page-break a metà immagine
        if self.get_y() + h + 8 > self.h - self.b_margin:
            self.add_page()
        self.image(buf, x=x, w=w)
        if caption:
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(*COLOR_SUBHEAD)
            self.cell(0, 4, caption, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            self.set_text_color(*COLOR_HEADER)
        self.ln(2)


# ── Builder principale ────────────────────────────────────────────────────────

def build_annual_report(data: Dict[str, Any], charts: Dict[str, bytes],
                        account_name: str) -> bytes:
    """
    Costruisce il PDF del report annuale.

    Args:
        data:         Output di ReportRepository.get_annual_report_data()
        charts:       Output di report_charts.generate_all_charts()
        account_name: Nome dell'account

    Returns:
        bytes del PDF generato
    """
    year = data["summary"]["year"]
    pdf = ReportPDF(account_name=account_name, year=year)
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── 1. Sommario anno ──────────────────────────────────────────────────
    pdf.section_title(f"1. Sommario {year}")
    s = data["summary"]
    saldo_color = COLOR_INCOME if s["saldo"] >= 0 else COLOR_EXPENSE

    pdf.kpi_row([
        ("Entrate totali",    f"€ {s['tot_income']:,.2f}",   COLOR_INCOME),
        ("Uscite totali",     f"€ {s['tot_expense']:,.2f}",  COLOR_EXPENSE),
        ("Saldo",             f"€ {s['saldo']:,.2f}",        saldo_color),
        ("N° movimenti",      str(s["n_movimenti"]),          COLOR_SUBHEAD),
    ])

    # ── 2. Confronto storico anni ──────────────────────────────────────────
    pdf.section_title("2. Confronto storico – Tutti gli anni")
    pdf.add_chart(charts["yearly_history"], w=178, caption="Entrate vs Uscite per anno")

    cols = [("Anno", 22, "C"), ("Entrate €", 35, "R"), ("Uscite €", 35, "R"),
            ("Saldo €", 35, "R"), ("Δ Uscite", 28, "R"), ("N° Mov.", 23, "C")]
    pdf.table_header(cols)
    for i, r in enumerate(data["yearly_history"]):
        sal_color = COLOR_INCOME if r["saldo"] >= 0 else COLOR_EXPENSE
        delta_str = f"{r['delta_expense_pct']:+.1f}%" if r["delta_expense_pct"] is not None else "–"
        delta_col = COLOR_EXPENSE if (r["delta_expense_pct"] or 0) > 0 else COLOR_INCOME
        year_color = COLOR_PRIMARY if r["year"] == year else COLOR_HEADER
        pdf.table_row([
            (str(r["year"]),                  22, "C", year_color),
            (f"€ {r['tot_income']:,.2f}",     35, "R", COLOR_INCOME),
            (f"€ {r['tot_expense']:,.2f}",    35, "R", COLOR_EXPENSE),
            (f"€ {r['saldo']:,.2f}",          35, "R", sal_color),
            (delta_str,                        28, "R", delta_col),
            (str(r["n_movimenti"]),            23, "C"),
        ], fill=(i % 2 == 0))
    pdf.ln(4)

    # ── 3. Trend mensile ───────────────────────────────────────────────────
    pdf.section_title(f"3. Trend mensile {year}")
    pdf.add_chart(charts["monthly_trend"], w=178, caption=f"Entrate e uscite mese per mese – {year}")

    cols = [("Mese", 35, "L"), ("Entrate €", 45, "R"), ("Uscite €", 45, "R"), ("Saldo mese €", 47, "R")]
    pdf.table_header(cols)
    for i, m in enumerate(data["monthly_trend"]):
        saldo_m = m["income"] - m["expense"]
        sc = COLOR_INCOME if saldo_m >= 0 else COLOR_EXPENSE
        pdf.table_row([
            (MONTHS_IT[m["month"]],           35, "L"),
            (f"€ {m['income']:,.2f}",          45, "R", COLOR_INCOME),
            (f"€ {m['expense']:,.2f}",         45, "R", COLOR_EXPENSE),
            (f"€ {saldo_m:,.2f}",              47, "R", sc),
        ], fill=(i % 2 == 0))
    pdf.ln(4)

    # ── 4. Top 10 spese singole ────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title(f"4. Top 10 spese singole {year}")
    cols = [("Data", 22, "C"), ("Categoria", 35, "L"), ("Wallet", 30, "L"),
            ("Nota", 62, "L"), ("Importo €", 29, "R")]
    pdf.table_header(cols)
    for i, t in enumerate(data["top_expenses"]):
        note = (t["note"][:42] + "...") if len(t["note"]) > 42 else t["note"]
        pdf.table_row([
            (t["date"],                22, "C"),
            (t["category"],            35, "L"),
            (t["wallet"],              30, "L"),
            (note,                     62, "L"),
            (f"€ {t['amount']:,.2f}", 29, "R", COLOR_EXPENSE),
        ], fill=(i % 2 == 0))
    pdf.ln(4)

    # ── 5. Spese per categoria ─────────────────────────────────────────────
    pdf.section_title(f"5. Spese per categoria – Incidenza sul budget {year}")
    pdf.add_chart(charts["category_pie"], w=140, caption="Incidenza % per categoria")

    cols = [("Categoria", 42, "L"), ("Totale €", 30, "R"), ("% Budget", 22, "R"),
            ("N° Mov.", 18, "C"), (f"vs {year-1} €", 32, "R"), ("Δ %", 22, "R")]
    pdf.table_header(cols)
    for i, c in enumerate(data["expense_by_category"]):
        delta_str = f"{c['delta_pct']:+.1f}%" if c["delta_pct"] is not None else "–"
        delta_col = COLOR_EXPENSE if (c["delta_pct"] or 0) > 0 else COLOR_INCOME
        prev_str  = f"€ {c['prev_year_expense']:,.2f}" if c["prev_year_expense"] else "–"
        pdf.table_row([
            (c["category"],                  42, "L"),
            (f"€ {c['tot_expense']:,.2f}",   30, "R", COLOR_EXPENSE),
            (f"{c['pct_budget']:.1f}%",      22, "R"),
            (str(c["n_movimenti"]),           18, "C"),
            (prev_str,                        32, "R"),
            (delta_str,                       22, "R", delta_col),
        ], fill=(i % 2 == 0))
    pdf.ln(4)

    # ── 6. Top 5 categorie per peso ────────────────────────────────────────
    if data["top5_categories"]:
        pdf.section_title("6. Categorie con maggiore incidenza sul budget (≥ 5%)")
        pdf.set_font("Helvetica", "", 8)
        col_w = (pdf.epw - 4) / min(len(data["top5_categories"]), 5)
        for cat in data["top5_categories"][:5]:
            x, y = pdf.get_x(), pdf.get_y()
            pdf.set_fill_color(*COLOR_EXPENSE)
            pdf.rect(x, y, col_w - 3, 20, "F")
            pdf.set_text_color(*COLOR_WHITE)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_xy(x + 2, y + 2)
            pdf.cell(col_w - 5, 6, cat["category"][:18])
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_xy(x + 2, y + 9)
            pdf.cell(col_w - 5, 7, f"{cat['pct_budget']:.1f}%")
            pdf.set_font("Helvetica", "", 7)
            pdf.set_xy(x + 2, y + 14)
            pdf.cell(col_w - 5, 5, f"€ {cat['tot_expense']:,.2f}")
            pdf.set_xy(x + col_w, y)
        pdf.set_text_color(*COLOR_HEADER)
        pdf.ln(24)

    # ── 7. Distribuzione per wallet ────────────────────────────────────────
    pdf.section_title(f"7. Distribuzione spese per wallet {year}")
    pdf.add_chart(charts["wallet_bars"], w=140, caption="Uscite totali per wallet")

    cols = [("Wallet", 50, "L"), ("Totale uscite €", 45, "R"), ("% sul totale", 35, "R"), ("N° Mov.", 25, "C")]
    pdf.table_header(cols)
    for i, w in enumerate(data["expense_by_wallet"]):
        pdf.table_row([
            (w["wallet"],                    50, "L"),
            (f"€ {w['tot_expense']:,.2f}",   45, "R", COLOR_EXPENSE),
            (f"{w['pct']:.1f}%",             35, "R"),
            (str(w["n_movimenti"]),           25, "C"),
        ], fill=(i % 2 == 0))
    pdf.ln(4)

    # ── 8. Mesi anomali ────────────────────────────────────────────────────
    if data["anomalous_months"]:
        pdf.section_title(f"8. Mesi anomali {year}  (uscite > media mensile + 20%)")
        cols = [("Mese", 40, "L"), ("Uscite €", 40, "R"), ("Media mensile €", 45, "R"), ("Eccedenza €", 35, "R")]
        pdf.table_header(cols)
        for i, m in enumerate(data["anomalous_months"]):
            pdf.table_row([
                (m["month_name"],              40, "L"),
                (f"€ {m['tot_expense']:,.2f}", 40, "R", COLOR_EXPENSE),
                (f"€ {m['media']:,.2f}",       45, "R"),
                (f"€ {m['delta']:,.2f}",       35, "R", COLOR_EXPENSE),
            ], fill=(i % 2 == 0))
        pdf.ln(4)

    return bytes(pdf.output())
