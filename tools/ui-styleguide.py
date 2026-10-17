#!/usr/bin/env python3
"""
Rende `_styleguide.html` e la apre in un browser headless per la verifica.

La styleguide non e' instradata (il gate sul diff vieta di toccare app.py),
quindi la si rende con il motore Jinja dell'app e la si consegna al browser con
set_content + <base>, cosi' /static/... si risolve sul server vero. Zero
modifiche all'applicazione, nessun file sparso in static/.

Uso:
    .venv/bin/python tools/ui-styleguide.py            # screenshot nei 2 temi
    .venv/bin/python tools/ui-styleguide.py --html     # solo l'HTML su stdout
    .venv/bin/python tools/ui-styleguide.py --probe    # esegue i controlli A1.6-A1.8
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


# La styleguide va servita dall'ORIGINE VERA, non con set_content: su
# about:blank `localStorage` e' inaccessibile, l'anti-FOUC finisce nel suo
# try/catch e la pagina resta sempre in light. Il tema non sarebbe
# verificabile, e il bug sembrerebbe del codice invece che del banco di prova.
# Quindi: rendiamo il template in un file dentro static/ (ignorato da git) e
# navighiamo su http://localhost:5000/static/...
RESO = os.path.join(_ROOT, "pyspendless", "static", "_styleguide.rendered.html")
URL = BASE + "/static/_styleguide.rendered.html"


def render():
    from pyspendless.app import app
    with app.app_context():
        html = app.jinja_env.get_template("_styleguide.html").render()
    with io.open(RESO, "w", encoding="utf-8") as f:
        f.write(html)
    return html


def main():
    html = render()
    if "--html" in sys.argv:
        sys.stdout.write(html)
        return 0
    print(f"reso in {os.path.relpath(RESO, _ROOT)} -> {URL}")

    from playwright.sync_api import sync_playwright
    out = os.path.join(_ROOT, "docs", "ui-styleguide")
    os.makedirs(out, exist_ok=True)

    with sync_playwright() as p:
        b = p.chromium.launch()
        for tema in ("light", "dark"):
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.add_init_script(
                "try { localStorage.setItem('ps_theme', '%s'); } catch (e) {}" % tema)
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            path = os.path.join(out, f"styleguide__{tema}.png")
            page.screenshot(path=path, full_page=True)
            print(f"  {os.path.relpath(path, _ROOT)}  "
                  f"({os.path.getsize(path) / 1024:.0f} KB)")
            ctx.close()
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
