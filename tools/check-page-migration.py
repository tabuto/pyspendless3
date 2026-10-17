#!/usr/bin/env python3
"""
Verifica che la conversione di UN template sia isofunzionale.

Confronta il file nel working tree con la sua versione in git (HEAD di default)
e controlla i criteri meccanici delle fasi di conversione (A3.2-A3.7 della
Fase 3, e gli equivalenti delle Fasi 4, 5, 7):

  - estende una shell `-tw`
  - nessun residuo Bootstrap/AdminLTE
  - stessi `id=`, stessi `name=`, stessi `url_for`
  - stesso numero di costrutti Jinja
  - stesso testo visibile

Uso:
    .venv/bin/python tools/check-page-migration.py ps-login.html
    .venv/bin/python tools/check-page-migration.py ps-login.html --base HEAD~1
    .venv/bin/python tools/check-page-migration.py ps-login.html -v

Exit code 0 = conversione isofunzionale secondo i controlli statici.
Quello che NON copre: resa visiva, comportamento del JS, overflow. Quelli li
verifica l'agente principale nel browser.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
TPL = os.path.join("pyspendless", "templates")

# Residui che non devono sopravvivere alla conversione. `col-` e `d-` da soli
# darebbero falsi positivi su attributi non-classe, quindi si ancora il match
# all'interno di un attributo class.
# ATTENZIONE al confine di parola. `\bcard-body\b` combacia ANCHE dentro
# `ps-card-body`, perche' il trattino e' un carattere non-di-parola e `\b`
# cade fra "ps-" e "card-body". E' lo stesso difetto che aveva `\bid=` nel
# test di contratto, dove catturava i `data-*-id`. Serve un lookbehind che
# escluda trattino e caratteri di parola.
_P = r"(?<![-\w])"

RESIDUI = [
    ("bootstrap",      re.compile(r"bootstrap", re.I)),
    ("adminlte",       re.compile(r"adminlte", re.I)),
    ("btn btn-",       re.compile(_P + r"btn btn-")),
    ("card-body",      re.compile(_P + r"card-body\b")),
    ("card-header",    re.compile(_P + r"card-header\b")),
    ("card-title",     re.compile(_P + r"card-title\b")),
    ("col-*-N",        re.compile(_P + r"col-(sm|md|lg|xl)-\d")),
    ("d-* Bootstrap",  re.compile(_P + r"d-(none|flex|grid|block|inline)\b|" + _P + r"d-(sm|md|lg)-")),
    ("form-control",   re.compile(_P + r"form-control\b")),
    ("form-label",     re.compile(_P + r"form-label\b")),
    ("form-text",      re.compile(_P + r"form-text\b")),
    ("text-muted",     re.compile(_P + r"text-muted\b")),
    ("me-/ms- logici", re.compile(_P + r"m[es]-\d\b")),
    ("icone FontAwesome", re.compile(_P + r"fa[sbr]?\b|" + _P + r"fa-[a-z0-9-]+")),
]

ID = re.compile(r'(?<![-\w])id=["\']([^"\']+)["\']')
NAME = re.compile(r'(?<![-\w])name=["\']([^"\']+)["\']')
URLFOR = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")
JINJA_IF = re.compile(r"\{%-?\s*if\b")
JINJA_FOR = re.compile(r"\{%-?\s*for\b")
JINJA_VAR = re.compile(r"\{\{")
# I commenti Jinja `{# ... #}` vanno rimossi come gli altri costrutti:
# altrimenti le parole di un commento contano come testo visibile e un
# commento aggiunto durante la conversione fa fallire il confronto.
TAG = re.compile(r"<[^>]+>|\{#.*?#\}|\{%[^%]*%\}|\{\{[^}]*\}\}|<!--.*?-->", re.S)


def da_git(ref, percorso):
    try:
        return subprocess.check_output(
            ["git", "show", f"{ref}:{percorso}"], cwd=_ROOT,
            stderr=subprocess.DEVNULL).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def testo_visibile(html):
    senza = TAG.sub(" ", html)
    return [p for p in senza.split() if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    nome = os.path.basename(a.template)
    rel = os.path.join(TPL, nome)
    assoluto = os.path.join(_ROOT, rel)
    if not os.path.exists(assoluto):
        print(f"File non trovato: {rel}")
        return 2

    prima = da_git(a.base, rel)
    if prima is None:
        print(f"Non trovo {rel} in {a.base}: e' un file nuovo?")
        return 2
    dopo = open(assoluto, encoding="utf-8").read()

    ok = fail = 0

    def check(desc, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            if a.verbose:
                print(f"  OK   {desc}" + (f"  [{extra}]" if extra else ""))
        else:
            fail += 1
            print(f"  FAIL {desc}" + (f"\n         {extra}" if extra else ""))

    print(f"\n{nome}  ({a.base} -> working tree)")

    # --- estende la shell nuova ---
    m = re.search(r"\{%\s*extends\s+['\"]([^'\"]+)['\"]", dopo)
    estende = m.group(1) if m else None
    check("estende una shell -tw", bool(estende and estende.endswith("-tw.html")),
          f"estende: {estende}")

    # --- nessun residuo ---
    for etichetta, pat in RESIDUI:
        trovati = pat.findall(dopo)
        check(f"nessun residuo '{etichetta}'", not trovati,
              f"{len(trovati)} occorrenze: {sorted(set(map(str, trovati)))[:6]}")

    # --- ancoraggi ---
    for etichetta, pat in (("id", ID), ("name", NAME), ("url_for", URLFOR)):
        p1, p2 = Counter(pat.findall(prima)), Counter(pat.findall(dopo))
        persi = sorted((p1 - p2).elements())
        nuovi = sorted((p2 - p1).elements())
        check(f"tutti gli '{etichetta}' preservati", not persi, f"spariti: {persi}")
        if nuovi and a.verbose:
            print(f"       (aggiunti, lecito: {nuovi})")

    # --- struttura Jinja ---
    for etichetta, pat in (("{% if %}", JINJA_IF), ("{% for %}", JINJA_FOR),
                           ("{{ }}", JINJA_VAR)):
        n1, n2 = len(pat.findall(prima)), len(pat.findall(dopo))
        check(f"stesso numero di {etichetta}", n1 == n2, f"prima {n1}, dopo {n2}")

    # --- testo visibile ---
    t1, t2 = testo_visibile(prima), testo_visibile(dopo)
    c1, c2 = Counter(t1), Counter(t2)
    persi = sorted((c1 - c2).elements())
    aggiunti = sorted((c2 - c1).elements())
    check("testo visibile invariato", not persi and not aggiunti,
          f"spariti: {persi[:12]}\n         comparsi: {aggiunti[:12]}")

    print(f"\n  {ok} OK, {fail} FAIL")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
