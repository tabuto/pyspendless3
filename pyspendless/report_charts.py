"""
report_charts.py – Generazione grafici matplotlib per il report annuale PDF.

Ogni funzione produce un'immagine PNG in-memory e la restituisce come bytes.
Usa il backend non-interattivo 'Agg' per funzionare in ambiente server.
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from typing import List, Dict, Any

# Palette colori coerente con Bootstrap/AdminLTE
COLOR_EXPENSE = "#dc3545"   # rosso Bootstrap
COLOR_INCOME  = "#198754"   # verde Bootstrap
COLOR_SALDO   = "#0d6efd"   # blu Bootstrap
COLOR_BAR_BG  = "#f8f9fa"
MONTHS_IT = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
              "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

# Palette per grafico a torta
PIE_COLORS = [
    "#4e73df", "#1cc88a", "#36b9cc", "#f6c23e", "#e74a3b",
    "#858796", "#5a5c69", "#2e59d9", "#17a673", "#2c9faf",
]


def _save_fig(fig) -> bytes:
    """Salva la figura corrente in un buffer PNG e la restituisce come bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_yearly_history(yearly_history: List[Dict[str, Any]]) -> bytes:
    """
    Grafico a barre doppie: entrate vs uscite per anno.
    Restituisce PNG come bytes.
    """
    years = [str(r["year"]) for r in yearly_history]
    incomes  = [r["tot_income"]  for r in yearly_history]
    expenses = [r["tot_expense"] for r in yearly_history]

    x = range(len(years))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar([i - width / 2 for i in x], incomes,  width, label="Entrate", color=COLOR_INCOME,  alpha=0.85)
    ax.bar([i + width / 2 for i in x], expenses, width, label="Uscite",  color=COLOR_EXPENSE, alpha=0.85)

    ax.set_xticks(list(x))
    ax.set_xticklabels(years, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.set_ylabel("€")
    ax.set_title("Entrate vs Uscite – Serie storica")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _save_fig(fig)


def chart_monthly_trend(monthly_trend: List[Dict[str, Any]], year: int) -> bytes:
    """
    Grafico a linee: entrate e uscite mensili per l'anno selezionato.
    Restituisce PNG come bytes.
    """
    incomes  = [m["income"]  for m in monthly_trend]
    expenses = [m["expense"] for m in monthly_trend]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(MONTHS_IT, incomes,  marker="o", color=COLOR_INCOME,  linewidth=2, label="Entrate")
    ax.plot(MONTHS_IT, expenses, marker="o", color=COLOR_EXPENSE, linewidth=2, label="Uscite")
    ax.fill_between(MONTHS_IT, incomes,  alpha=0.08, color=COLOR_INCOME)
    ax.fill_between(MONTHS_IT, expenses, alpha=0.08, color=COLOR_EXPENSE)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.set_ylabel("€")
    ax.set_title(f"Trend mensile {year}")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return _save_fig(fig)


def chart_category_pie(expense_by_category: List[Dict[str, Any]]) -> bytes:
    """
    Grafico a torta: incidenza % delle categorie di spesa.
    Raggruppa le categorie < 3% in "Altro".
    Restituisce PNG come bytes.
    """
    items = [(c["category"], c["tot_expense"]) for c in expense_by_category]
    total = sum(v for _, v in items)

    # Raggruppa categorie < 3%
    main  = [(label, val) for label, val in items if val / total >= 0.03]
    other = sum(val for _, val in items if val / total < 0.03)
    if other > 0:
        main.append(("Altro", other))

    labels = [label for label, _ in main]
    values = [val   for _, val   in main]
    colors = [PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.82,
    )
    for at in autotexts:
        at.set_fontsize(8)

    ax.legend(wedges, labels, loc="lower center", ncol=3,
              bbox_to_anchor=(0.5, -0.18), fontsize=8, frameon=False)
    ax.set_title("Incidenza spese per categoria")
    fig.tight_layout()
    return _save_fig(fig)


def chart_wallet_bars(expense_by_wallet: List[Dict[str, Any]]) -> bytes:
    """
    Grafico a barre orizzontali: uscite per wallet.
    Restituisce PNG come bytes.
    """
    wallets  = [w["wallet"]      for w in expense_by_wallet]
    amounts  = [w["tot_expense"] for w in expense_by_wallet]
    colors   = [PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(wallets))]

    fig, ax = plt.subplots(figsize=(8, max(3, len(wallets) * 0.7)))
    bars = ax.barh(wallets, amounts, color=colors, alpha=0.85)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.set_xlabel("€")
    ax.set_title("Spese per wallet")
    ax.invert_yaxis()

    # Etichette importo sulle barre
    for bar, val in zip(bars, amounts):
        ax.text(bar.get_width() + max(amounts) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"€{val:,.0f}", va="center", fontsize=8)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    return _save_fig(fig)


def generate_all_charts(data: Dict[str, Any]) -> Dict[str, bytes]:
    """
    Genera tutti i grafici per il report annuale.

    Returns:
        Dizionario {nome_grafico: bytes_png}
    """
    return {
        "yearly_history":    chart_yearly_history(data["yearly_history"]),
        "monthly_trend":     chart_monthly_trend(data["monthly_trend"], data["summary"]["year"]),
        "category_pie":      chart_category_pie(data["expense_by_category"]),
        "wallet_bars":       chart_wallet_bars(data["expense_by_wallet"]),
    }
