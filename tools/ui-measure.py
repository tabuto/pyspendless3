#!/usr/bin/env python3
"""
Misura il peso degli asset di una pagina, con cache fredda.

Serve alla Fase 0 del task19-0 (attivita' 0.5) per sostituire le stime del
piano con numeri veri, e va rieseguito a fine lavoro per quantificare il
guadagno. Raggruppa per origine (CDN per CDN, piu' il server locale) perche'
e' quella la ripartizione che il restyling cambia.

Uso:
    .venv/bin/python tools/ui-measure.py                      # /movements
    .venv/bin/python tools/ui-measure.py /dashboard/monthly   # altra rotta
"""
import os
import sys
from collections import defaultdict
from urllib.parse import urlparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import logging  # noqa: E402
logging.disable(logging.INFO)

from tools.ps_session_cookie import build_cookie  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://localhost:5000"
ROUTE = sys.argv[1] if len(sys.argv) > 1 else "/movements"
KB = 1024.0


def main():
    name, value, _ = build_cookie()
    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # contesto nuovo = cache vuota: misuriamo una prima visita
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_cookies([{"name": name, "value": value,
                          "domain": "localhost", "path": "/"}])
        page = ctx.new_page()

        def on_response(resp):
            try:
                sizes = resp.request.sizes()
                body = sizes.get("responseBodySize") or 0
                head = sizes.get("responseHeadersSize") or 0
            except Exception:
                body = head = 0
            records.append({
                "url": resp.url,
                "status": resp.status,
                "type": resp.request.resource_type,
                "bytes": body + head,
            })

        page.on("response", on_response)
        page.goto(BASE + ROUTE, wait_until="networkidle")
        page.wait_for_timeout(2500)   # DataTables, Chart.js, i18n, Tom Select
        browser.close()

    per_origin = defaultdict(lambda: {"n": 0, "bytes": 0})
    per_type = defaultdict(lambda: {"n": 0, "bytes": 0})
    for r in records:
        host = urlparse(r["url"]).netloc or "(inline)"
        per_origin[host]["n"] += 1
        per_origin[host]["bytes"] += r["bytes"]
        per_type[r["type"]]["n"] += 1
        per_type[r["type"]]["bytes"] += r["bytes"]

    tot_n = len(records)
    tot_b = sum(r["bytes"] for r in records)

    print(f"\nROTTA: {ROUTE}   (cache fredda, viewport 1440x900)")
    print(f"TOTALE: {tot_n} richieste, {tot_b / KB:.1f} KB\n")

    print(f"{'origine':<42} {'richieste':>9} {'KB':>9} {'%':>6}")
    print("-" * 70)
    for host, d in sorted(per_origin.items(), key=lambda kv: -kv[1]["bytes"]):
        pct = 100.0 * d["bytes"] / tot_b if tot_b else 0
        print(f"{host:<42} {d['n']:>9} {d['bytes'] / KB:>9.1f} {pct:>5.1f}%")

    print(f"\n{'tipo di risorsa':<42} {'richieste':>9} {'KB':>9} {'%':>6}")
    print("-" * 70)
    for t, d in sorted(per_type.items(), key=lambda kv: -kv[1]["bytes"]):
        pct = 100.0 * d["bytes"] / tot_b if tot_b else 0
        print(f"{t:<42} {d['n']:>9} {d['bytes'] / KB:>9.1f} {pct:>5.1f}%")

    print(f"\n{'le 12 risorse piu' + chr(39) + ' pesanti':<60} {'KB':>8}")
    print("-" * 70)
    for r in sorted(records, key=lambda r: -r["bytes"])[:12]:
        u = r["url"]
        if len(u) > 58:
            u = u[:28] + "…" + u[-29:]
        print(f"{u:<60} {r['bytes'] / KB:>8.1f}")

    errori = [r for r in records if r["status"] >= 400]
    if errori:
        print(f"\nRISPOSTE >= 400 ({len(errori)}):")
        for r in errori:
            print(f"  {r['status']}  {r['url']}")


if __name__ == "__main__":
    main()
