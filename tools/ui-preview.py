#!/usr/bin/env python3
"""
Rende un template NON instradato e lo serve dall'origine vera dell'app.

Serve a vedere nel browser i template che non hanno una route — `_styleguide.html`,
`_shell-probe.html` — senza toccare `app.py` (il gate sul diff del task19-0 lo
vieta).

Perche' non basta `set_content`: una pagina consegnata cosi' vive su
`about:blank`, dove `localStorage` e' inaccessibile. Lo script anti-FOUC finisce
nel suo try/catch, la pagina resta sempre in light, e il tema sembra rotto
quando invece e' il banco di prova a esserlo. Qui il file viene scritto dentro
`static/` (ignorato da git) e servito da http://localhost:5000, cioe'
dall'origine vera, con localStorage funzionante e /static che risolve da solo.

Uso:
    .venv/bin/python tools/ui-preview.py _shell-probe.html
    .venv/bin/python tools/ui-preview.py _styleguide.html --url   # stampa solo l'URL
"""
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import logging  # noqa: E402
logging.disable(logging.INFO)

BASE = "http://localhost:5000"


def rendi(nome_template, contesto=None, user_id="admin"):
    """Rende il template e lo scrive in static/. Ritorna (percorso, url)."""
    uscita = "_preview." + nome_template.lstrip("_")
    percorso = os.path.join(_ROOT, "pyspendless", "static", uscita)
    from tools.ui_preview_helper import rendi_html
    html = rendi_html(nome_template, contesto, user_id=user_id)
    with io.open(percorso, "w", encoding="utf-8") as f:
        f.write(html)
    return percorso, f"{BASE}/static/{uscita}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    utente = "utente" if "--non-admin" in sys.argv else "admin"
    percorso, url = rendi(args[0], user_id=utente)
    if "--url" in sys.argv:
        print(url)
    else:
        print(f"reso:  {os.path.relpath(percorso, _ROOT)}  "
              f"({os.path.getsize(percorso) / 1024:.1f} KB)")
        print(f"url:   {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
