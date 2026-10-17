#!/usr/bin/env python3
"""
Baseline visiva di PySpendless: matrice pagine x viewport, piu' gli stati
interattivi che un semplice `goto` non mostra.

Perche' uno script e non un agente: fra il "before" di oggi e l'"after" di tre
settimane dopo serve la **stessa inquadratura**, altrimenti il confronto non
dimostra niente. Qui l'inquadratura e' codice.

Autenticazione: cookie di sessione firmato (vedi tools/ps_session_cookie.py).
Nessun login, nessuna credenziale, nessuna chiamata a Google.

Uso:
    .venv/bin/python tools/ui-shots.py                 # matrice + stati
    .venv/bin/python tools/ui-shots.py --pages         # solo la matrice
    .venv/bin/python tools/ui-shots.py --states        # solo gli stati
    .venv/bin/python tools/ui-shots.py --out docs/ui-after   # per il confronto
"""
import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import logging  # noqa: E402
logging.disable(logging.INFO)

from tools.ps_session_cookie import build_cookie  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://localhost:5000"
VIEWPORTS = [375, 768, 1440]
THEME = "light"          # oggi esiste un solo tema; da Fase 2 anche "dark"
SETTLE_MS = 2200         # Chart.js anima ~1s, DataTables + Tom Select meno

# --- la matrice ------------------------------------------------------------
# slug -> percorso. `auth=False` significa "cattura senza cookie di sessione".
PAGES = [
    ("login",                  "/login",                   False),
    ("home",                   "/home",                    True),
    ("create",                 "/create",                  True),
    ("movements",              "/movements",               True),
    ("search-mov",             "/ps-search-mov",           True),
    ("recurrent-movements",    "/recurrent-movements",     True),
    ("dashboard-monthly",      "/dashboard/monthly",       True),
    ("dashboard-yearly",       "/dashboard/yearly",        True),
    ("reports",                "/reports",                 True),
    ("settings-categories",    "/settings/categories",     True),
    ("settings-wallets",       "/settings/wallets",         True),
    ("settings-group",         "/settings/group",          True),
    ("settings-import-export", "/settings/import-export",  True),
    ("settings-profile",       "/settings/profile",        True),
    ("settings-admin",         "/settings/admin",          True),
]

# --- i modal ---------------------------------------------------------------
# (slug, rotta, id del modal). Dove esiste un trigger `data-bs-target` lo
# clicchiamo, cosi' il modal si apre come lo apre l'utente; altrimenti lo
# mostriamo via API Bootstrap.
MODALS = [
    ("recurrent-movements", "/recurrent-movements",    "deleteModal"),
    ("settings-wallets",    "/settings/wallets",       "addWalletModal"),
    ("settings-wallets",    "/settings/wallets",       "editWalletModal"),
    ("settings-categories", "/settings/categories",    "addCategoryModal"),
    ("settings-categories", "/settings/categories",    "editCategoryModal"),
    ("settings-categories", "/settings/categories",    "deleteCategoryModal"),
    ("settings-group",      "/settings/group",         "editAccountModal"),
    ("settings-group",      "/settings/group",         "inviteModal"),
    ("settings-group",      "/settings/group",         "deleteAccountModal"),
    ("settings-admin",      "/settings/admin",         "addWhitelistModal"),
    ("settings-profile",    "/settings/profile",       "addTokenModal"),
    ("settings-profile",    "/settings/profile",       "showTokenModal"),
    ("movements",           "/movements?category_type=expense", "bulkEditModal"),
]

OPEN_MODAL_JS = """(id) => {
    const el = document.getElementById(id);
    if (!el) return 'assente';
    const trigger = document.querySelector('[data-bs-target="#' + id + '"]');
    if (trigger) { trigger.click(); return 'trigger'; }
    if (window.bootstrap && bootstrap.Modal) {
        bootstrap.Modal.getOrCreateInstance(el).show(); return 'api';
    }
    return 'niente-bootstrap';
}"""


def settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    try:
        page.evaluate("document.fonts && document.fonts.ready")
    except Exception:
        pass
    page.wait_for_timeout(SETTLE_MS)


def shot(page, outdir, nome):
    path = os.path.join(outdir, nome + ".png")
    page.screenshot(path=path, full_page=True)
    kb = os.path.getsize(path) / 1024.0
    print(f"  {nome}.png  ({kb:.0f} KB)")
    return path


def maintenance_html():
    """
    La pagina di manutenzione non e' raggiungibile dal server in esecuzione:
    il gate legge MAINTENANCE_MODE a ogni richiesta. La rendiamo qui dentro,
    con il test client e la variabile attiva, poi la diamo al browser con
    set_content + <base>, cosi' /static si risolve sul server vero.
    """
    os.environ["MAINTENANCE_MODE"] = "1"
    try:
        from pyspendless.app import app
        app.config["TESTING"] = True
        html = app.test_client().get("/home").get_data(as_text=True)
    finally:
        os.environ["MAINTENANCE_MODE"] = "0"
    return html.replace("<head>", f'<head><base href="{BASE}/">', 1)


def cattura_pagine(browser, cookie, outdir):
    name, value = cookie
    fatti = 0
    for w in VIEWPORTS:
        print(f"\n[viewport {w}px]")
        for slug, path, auth in PAGES:
            ctx = browser.new_context(viewport={"width": w, "height": 900})
            if auth:
                ctx.add_cookies([{"name": name, "value": value,
                                  "domain": "localhost", "path": "/"}])
            page = ctx.new_page()
            resp = page.goto(BASE + path, wait_until="domcontentloaded")
            if resp and resp.status != 200:
                print(f"  ! {slug}: HTTP {resp.status} su {path} — salto")
                ctx.close()
                continue
            if auth and page.url.rstrip("/").endswith("/login"):
                print(f"  ! {slug}: rimandato a /login — cookie non valido")
                ctx.close()
                continue
            settle(page)
            shot(page, outdir, f"{slug}__{w}__{THEME}")
            fatti += 1
            ctx.close()

        # manutenzione: HTML reso fuori banda, vedi maintenance_html()
        ctx = browser.new_context(viewport={"width": w, "height": 900})
        page = ctx.new_page()
        page.set_content(maintenance_html(), wait_until="domcontentloaded")
        settle(page)
        shot(page, outdir, f"maintenance__{w}__{THEME}")
        fatti += 1
        ctx.close()
    return fatti


def cattura_stati(browser, cookie, outdir):
    name, value = cookie

    def nuovo(w=1440):
        ctx = browser.new_context(viewport={"width": w, "height": 900})
        ctx.add_cookies([{"name": name, "value": value,
                          "domain": "localhost", "path": "/"}])
        return ctx, ctx.new_page()

    fatti = 0
    print("\n[modal aperti, 1440px]")
    for slug, path, modal_id in MODALS:
        ctx, page = nuovo()
        page.goto(BASE + path, wait_until="domcontentloaded")
        settle(page)
        esito = page.evaluate(OPEN_MODAL_JS, modal_id)
        if esito == "assente":
            print(f"  ! {slug}/{modal_id}: id non presente — salto")
            ctx.close()
            continue
        page.wait_for_timeout(900)
        visibile = page.evaluate(
            "(id) => { const e = document.getElementById(id);"
            " return !!e && e.classList.contains('show'); }", modal_id)
        if not visibile:
            print(f"  ! {slug}/{modal_id}: non si e' aperto ({esito}) — salto")
            ctx.close()
            continue
        shot(page, outdir, f"stato--modal-{modal_id}__1440__{THEME}")
        fatti += 1
        ctx.close()

    print("\n[altri stati]")

    # tab "Entrate" su /settings/categories
    ctx, page = nuovo()
    page.goto(BASE + "/settings/categories", wait_until="domcontentloaded")
    settle(page)
    page.click("#income-tab")
    page.wait_for_timeout(700)
    shot(page, outdir, f"stato--categories-tab-entrate__1440__{THEME}")
    fatti += 1
    ctx.close()

    # pannello filtri aperto con badge di conteggio su /movements
    ctx, page = nuovo()
    page.goto(BASE + "/movements?date_from=2026-08-01&date_to=2026-10-16"
                     "&category_type=expense&keywords=spesa",
              wait_until="domcontentloaded")
    settle(page)
    page.evaluate("""() => {
        const el = document.getElementById('filters-collapse');
        if (!el) return;
        if (window.bootstrap && bootstrap.Collapse)
            bootstrap.Collapse.getOrCreateInstance(el).show();
        else el.classList.add('show');
    }""")
    page.wait_for_timeout(900)
    shot(page, outdir, f"stato--movements-filtri-aperti__1440__{THEME}")
    fatti += 1
    ctx.close()

    # card-list mobile dopo lo scroll: deve caricarsi la seconda pagina
    ctx, page = nuovo(375)
    page.goto(BASE + "/movements", wait_until="domcontentloaded")
    settle(page)
    prima = page.evaluate(
        "() => document.querySelectorAll('#cards-container > *').length")
    for _ in range(6):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(900)
    dopo = page.evaluate(
        "() => document.querySelectorAll('#cards-container > *').length")
    print(f"  card nel contenitore: {prima} -> {dopo}")
    shot(page, outdir, f"stato--movements-cardlist-scroll__375__{THEME}")
    fatti += 1
    ctx.close()

    # alert di successo: mostrato con il codice di presentazione della pagina,
    # SENZA salvare niente (nessuna scrittura sul DB)
    ctx, page = nuovo()
    page.goto(BASE + "/create", wait_until="domcontentloaded")
    settle(page)
    esito = page.evaluate("""() => {
        if (typeof showAlert === 'function') {
            showAlert('success', 'Movimento salvato correttamente');
            return 'funzione-della-pagina';
        }
        const c = document.getElementById('alert-container');
        if (!c) return 'assente';
        c.innerHTML = '<div class="alert alert-success alert-dismissible fade show">'
            + 'Movimento salvato correttamente'
            + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
        return 'markup-equivalente';
    }""")
    page.wait_for_timeout(600)
    print(f"  alert ottenuto via: {esito}")
    shot(page, outdir, f"stato--create-alert-successo__1440__{THEME}")
    fatti += 1
    ctx.close()

    # progress bar dell'import, resa visibile senza importare nulla
    ctx, page = nuovo()
    page.goto(BASE + "/settings/import-export", wait_until="domcontentloaded")
    settle(page)
    page.evaluate("""() => {
        const p = document.getElementById('importProgress');
        if (!p) return;
        p.classList.remove('d-none');
        p.style.display = '';
        const bar = p.querySelector('.progress-bar');
        if (bar) { bar.style.width = '60%'; bar.textContent = '60%'; }
    }""")
    page.wait_for_timeout(500)
    shot(page, outdir, f"stato--import-progress__1440__{THEME}")
    fatti += 1
    ctx.close()

    # "Zona pericolosa": digitare ELIMINA abilita il bottone. Si scrive nel
    # campo e si fotografa; il bottone NON viene premuto.
    ctx, page = nuovo()
    page.goto(BASE + "/settings/group", wait_until="domcontentloaded")
    settle(page)
    page.evaluate(OPEN_MODAL_JS, "deleteAccountModal")
    page.wait_for_timeout(800)
    page.fill("#confirmDeleteText", "ELIMINA")
    page.dispatch_event("#confirmDeleteText", "input")
    page.wait_for_timeout(500)
    attivo = page.evaluate(
        "() => { const b = document.getElementById('confirmDeleteBtn');"
        " return b ? !b.disabled : null; }")
    print(f"  bottone di conferma abilitato: {attivo}")
    shot(page, outdir, f"stato--group-zona-pericolosa__1440__{THEME}")
    fatti += 1
    ctx.close()

    return fatti


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", action="store_true", help="solo la matrice")
    ap.add_argument("--states", action="store_true", help="solo gli stati")
    ap.add_argument("--out", default="docs/ui-baseline",
                    help="cartella di destinazione (default: docs/ui-baseline)")
    args = ap.parse_args()
    fai_pagine = args.pages or not args.states
    fai_stati = args.states or not args.pages

    outdir = args.out if os.path.isabs(args.out) else os.path.join(_ROOT, args.out)
    os.makedirs(outdir, exist_ok=True)

    name, value, user = build_cookie()
    print(f"destinazione: {outdir}")
    print(f"sessione finta: utente {user['id']} <{user['email']}>, "
          f"account {user['account_id']}")

    tot = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if fai_pagine:
            tot += cattura_pagine(browser, (name, value), outdir)
        if fai_stati:
            tot += cattura_stati(browser, (name, value), outdir)
        browser.close()

    print(f"\n{tot} immagini in {outdir}")


if __name__ == "__main__":
    main()
