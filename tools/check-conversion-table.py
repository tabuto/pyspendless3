#!/usr/bin/env python3
"""
Verifica che la tabella di conversione copra tutte le classi dei template.

Criterio A1.4 della Fase 1 del task19-0: `ps-markup` si ferma se incontra un
pattern Bootstrap che non e' in tabella, quindi una lacuna qui diventa un
blocco piu' avanti. Questo script la trova prima.

Confronta:
  - le classi estratte dagli `class="..."` dei template renderizzati
  - le classi nominate in `backlog/task19-0/fasi/fase-1.md`, sezione 1.3

Uso:
    .venv/bin/python tools/check-conversion-table.py
    .venv/bin/python tools/check-conversion-table.py -v   # elenca anche i coperti

Exit code 0 = copertura completa.
"""
import os
import re
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
TPL = os.path.join(_ROOT, "pyspendless", "templates")
FASE1 = os.path.join(_ROOT, "backlog", "task19-0", "fasi", "fase-1.md")

# I 18 template renderizzati + i 3 layout. I template morti non contano.
RENDERIZZATI = """ps-login ps-home ps-onboarding ps-maintenance ps-add-mov ps-show-mov
ps-search-mov ps-recurrent-mov ps-setting-wallet ps-setting-categories ps-setting-group
ps-setting-import-export ps-setting-admin ps-setting-profile ps-dashboard-monthly
ps-dashboard-yearly ps-reports ps-oauth-consent ps-base ps-nav ps-auth""".split()

# Token che finiscono dentro `class="..."` ma non sono classi: frammenti di
# espressioni Jinja (`{% if x %}`), e nomi di variabili JS.
NON_CLASSI = re.compile(
    r"^(if|else|elif|endif|for|endfor|and|or|not|in|is|==|!=|<=|>=|<|>|\+|'|\"|\d+)$"
    r"|^[a-z_]+\.[a-z_]+$"          # filters.active_count, stats.balance
    r"|^'[^']*'$"                   # 'owner', 'primary'
    r"|^(colorClass|current_page|pages|category|badgeColor|balanceClass)$"
)

# Famiglie coperte da una riga sola in tabella, con un pattern invece che
# elencando ogni variante.
COPERTE_DA_PATTERN = [
    (re.compile(r"^bi(-|$)"),            "icone Bootstrap (D9: invariate)"),
    (re.compile(r"^(fas|far|fab)$|^fa-"), "icone FontAwesome (P1 / D10)"),
    (re.compile(r"^(app-|layout-|lte-)"), "shell AdminLTE (riscritta in Fase 2)"),
    (re.compile(r"^(sidebar|brand|navbar)(-|$)"), "shell AdminLTE (riscritta in Fase 2)"),
    (re.compile(r"^(nav-icon|nav-arrow|nav-treeview)$"), "shell AdminLTE (riscritta in Fase 2)"),
    (re.compile(r"^login-(box|page|card-body|box-msg)$"), "layout auth (riscritto in Fase 2)"),
    (re.compile(r"^(main-|content$|close$|skip-)"), "shell AdminLTE (riscritta in Fase 2)"),
    (re.compile(r"^[mp][tbsexy]?-(auto|\d)$"), "spaziature"),
    (re.compile(r"^col(-|$)|^row(-|$)|^g[xy]?-\d$|^container(-|$)"), "griglia"),
    (re.compile(r"^(fade|show|collapse|active|disabled)$"), "stato, non stile"),
]


# Le tre shell dell'app. Fino alla Fase 9 si chiamavano ps-*-tw.html e il
# discriminante era il suffisso; ora che la vecchia gerarchia e' cancellata il
# suffisso non distingue piu' nulla ed e' stato tolto (attivita' 9.3). Il
# discriminante e' l'appartenenza a questo insieme: un endswith("-tw.html")
# qui darebbe sempre falso, e ogni pagina risulterebbe non migrata.
SHELL = {"ps-base.html", "ps-nav.html", "ps-auth.html"}


def _gia_migrato(nome, testo):
    """Un template gia' convertito ha classi che sono la DESTINAZIONE, non la
    sorgente: cercarle in tabella produrrebbe falsi 'non coperte' su ogni
    utility Tailwind.

    Due casi, e il secondo e' nato in Fase 9. Un template di contenuto si
    riconosce dall'extends. Una shell no: ps-base.html e' radice e non estende
    nulla, e fino alla Fase 9 il nome ps-base.html apparteneva alla VECCHIA
    shell, che era legittimamente sorgente. Dopo il rename lo stesso nome
    indica la shell Tailwind, quindi va riconosciuta per nome."""
    if nome in SHELL:
        return True
    m = re.search(r"\{%\s*extends\s+['\"]([^'\"]+)['\"]", testo)
    return bool(m and m.group(1) in SHELL)


def classi_nei_template():
    cnt = Counter()
    dove = {}
    saltati = []
    for nome in RENDERIZZATI:
        p = os.path.join(TPL, nome + ".html")
        if not os.path.exists(p):
            print(f"[attenzione] template assente: {nome}.html", file=sys.stderr)
            continue
        testo = open(p, encoding="utf-8").read()
        if _gia_migrato(nome + ".html", testo):
            saltati.append(nome + ".html")
            continue
        for m in re.finditer(r'class="([^"]*)"', testo):
            for c in m.group(1).split():
                if "{" in c or "}" in c or NON_CLASSI.match(c):
                    continue
                cnt[c] += 1
                dove.setdefault(c, nome + ".html")
    if saltati:
        print(f"gia' migrati, esclusi dal confronto: {len(saltati)} -> {saltati}")
    return cnt, dove


def classi_in_tabella():
    testo = open(FASE1, encoding="utf-8").read()
    i = testo.index("### 1.3")
    j = testo.index("### 1.4")
    sezione = testo[i:j]
    # tutto cio' che e' fra backtick nella sezione
    return {t.strip() for t in re.findall(r"`([^`]+)`", sezione)}


def main():
    verboso = "-v" in sys.argv
    cnt, dove = classi_nei_template()
    tabella = classi_in_tabella()

    scoperte, coperte = [], []
    for c, n in cnt.most_common():
        if c in tabella:
            coperte.append((c, n, "riga esplicita"))
            continue
        pattern = next((d for r, d in COPERTE_DA_PATTERN if r.match(c)), None)
        if pattern:
            coperte.append((c, n, pattern))
            continue
        scoperte.append((c, n))

    print(f"classi distinte nei template: {len(cnt)}  "
          f"(occorrenze: {sum(cnt.values())})")
    print(f"coperte dalla tabella:        {len(coperte)}")
    print(f"NON coperte:                  {len(scoperte)}")

    if verboso:
        print("\n--- coperte ---")
        for c, n, via in coperte:
            print(f"  {n:>4}  {c:<28} {via}")

    if scoperte:
        print("\n--- NON COPERTE: aggiungere una riga alla tabella 1.3 ---")
        for c, n in scoperte:
            print(f"  {n:>4}  {c:<28} (prima occorrenza: {dove[c]})")
        return 1

    print("\nCopertura completa: ogni classe dei template ha una destinazione.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
