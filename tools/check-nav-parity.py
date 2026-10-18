#!/usr/bin/env python3
"""
Confronta le destinazioni della nav VECCHIA con quelle della nav NUOVA.

Criterio A2.3 / definition of done della Fase 2: "il confronto fra le
destinazioni estratte dalla nav vecchia e dalla nuova da' differenza vuota".

La nav vecchia si legge dall'app viva (`/home`, che estende `ps-nav.html`).
La nuova si legge rendendo un template che estende `ps-nav.html` — di norma
`_shell-probe.html`, che non e' instradato.

L'estrazione e' delimitata a `<ul id="navigation">`, **la stessa delimitazione
che usa `test_nav_destinazioni`**: fuori da li' ci sono la voce Account
dell'header e i link delle card di /home, che falserebbero l'ordine.

Uso:
    .venv/bin/python tools/check-nav-parity.py                     # usa _shell-probe.html
    .venv/bin/python tools/check-nav-parity.py _altro-template.html

Exit code 0 = stesse destinazioni, stesso ordine.
"""
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import logging  # noqa: E402
logging.disable(logging.INFO)

NUOVO_DEFAULT = "ps-home.html"   # era _shell-probe.html, cancellata a fine Fase 3


def _blocco_navigation(html):
    m = re.search(
        r'<ul[^>]*\bid=["\']navigation["\'][^>]*>(.*?)</ul>\s*(?:<!--[^>]*-->\s*)*</nav>',
        html, re.S)
    if m is None:
        m = re.search(r'\bid=["\']navigation["\'].*?(?=</nav>)', html, re.S)
    return m.group(0) if m else None


def _destinazioni(html, attese):
    blocco = _blocco_navigation(html)
    if blocco is None:
        return None
    hrefs = re.findall(r'\bhref=["\']([^"\']+)["\']', blocco)
    visti, ordine = set(), []
    for h in hrefs:
        if h in attese and h not in visti:
            visti.add(h)
            ordine.append(h)
    return ordine


def main():
    nuovo_tpl = next((a for a in sys.argv[1:] if not a.startswith("-")), NUOVO_DEFAULT)

    import io as _io
    import contextlib
    with contextlib.redirect_stdout(_io.StringIO()), \
            contextlib.redirect_stderr(_io.StringIO()):
        from pyspendless.test import test_task19_0 as T
    attese = T.NAV_LINKS_ORDER

    # --- nav vecchia: dall'app viva ---
    with contextlib.redirect_stdout(_io.StringIO()), \
            contextlib.redirect_stderr(_io.StringIO()):
        T.app.config["TESTING"] = True
        client = T.app.test_client()
        T._fake_login(client)
        html_vecchio = client.get("/home").get_data(as_text=True)
    vecchia = _destinazioni(html_vecchio, attese)

    # --- nav nuova: dal template non instradato ---
    percorso = os.path.join(_ROOT, "pyspendless", "templates", nuovo_tpl)
    if not os.path.exists(percorso):
        print(f"Template non trovato: {nuovo_tpl}")
        print("La Fase 2 non l'ha ancora prodotto.")
        return 2
    from tools.ui_preview_helper import rendi_html
    html_nuovo = rendi_html(nuovo_tpl)
    nuova = _destinazioni(html_nuovo, attese)

    print(f"nav vecchia (/home, ps-nav.html):        "
          f"{len(vecchia) if vecchia else 'id=navigation NON TROVATO'}")
    print(f"nav nuova   ({nuovo_tpl}): "
          f"{len(nuova) if nuova else 'id=navigation NON TROVATO'}")

    if vecchia is None or nuova is None:
        print("\nFALLITO: manca l'elemento id='navigation' (e' parte del contratto).")
        return 1

    mancanti = [d for d in vecchia if d not in nuova]
    aggiunte = [d for d in nuova if d not in vecchia]
    fuori_dal_contratto = [d for d in attese if d not in nuova]

    print(f"\n{'#':>3}  {'vecchia':<26} {'nuova':<26}")
    print("-" * 60)
    for i in range(max(len(vecchia), len(nuova))):
        v = vecchia[i] if i < len(vecchia) else "—"
        n = nuova[i] if i < len(nuova) else "—"
        print(f"{i+1:>3}  {v:<26} {n:<26}{'' if v == n else '   <<< DIVERSO'}")

    esito = 0
    if mancanti:
        print(f"\nSPARITE dalla nav nuova: {mancanti}"); esito = 1
    if aggiunte:
        print(f"\nAGGIUNTE nella nav nuova: {aggiunte}"); esito = 1
    if fuori_dal_contratto:
        print(f"\nMancano rispetto a NAV_LINKS_ORDER: {fuori_dal_contratto}"); esito = 1
    if vecchia != nuova and not (mancanti or aggiunte):
        print("\nSTESSE destinazioni ma ORDINE DIVERSO."); esito = 1

    if esito == 0:
        print("\nDifferenza vuota: stesse destinazioni, stesso ordine.")
    return esito


if __name__ == "__main__":
    sys.exit(main())
