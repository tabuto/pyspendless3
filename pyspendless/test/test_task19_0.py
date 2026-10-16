#!/usr/bin/env python3
"""
Task 19-0 — Test del CONTRATTO DOM (isofunzionalita' del restyling Tailwind).

Questo e' il test piu' importante del task: congela gli `id`, i `name` dei campi
form e le destinazioni dei link su cui il JS di pagina e il server fanno
affidamento. Il restyling riscrive il markup ma **non** il JS: se un id sparisce
o cambia, il JS smette di funzionare in silenzio. Questo file lo intercetta.

Va eseguito VERDE sul codice attuale (Fase 0) **prima** che una riga di markup
cambi, e deve restare verde a ogni fase.

Uso (dalla root del repo):
    .venv/bin/python -m pyspendless.test.test_task19_0            # tutto
    .venv/bin/python -m pyspendless.test.test_task19_0 FASE=3     # solo le rotte della fase 3

Nel repo ci sono DUE virtualenv: `.venv/` nella root e `pyspendless/.venv/`.
`test_task22_0.py` usa il secondo (`pyspendless/.venv/bin/python -m
pyspendless.test.test_task22_0`), `.claude/settings.local.json` registra il
primo. Usa quello in cui sono installate le dipendenze: se l'import di Flask
fallisce, prova l'altro.

Exit code 0 = contratto rispettato. Diverso da 0 = regressione.
I subagent usano l'exit code come criterio di rilascio del task.

Nota OAuth: l'app e' interamente dietro Google OAuth. Il test NON fa login:
inietta direttamente la sessione Flask con `session_transaction()`, che e' il
modo supportato per testare rotte autenticate senza toccare credenziali.
"""

import os
import re
import sys
import unittest

# --- import dell'app, tollerante al punto di partenza -----------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)            # .../pyspendless
_ROOT = os.path.dirname(_PKG)            # .../pyspendless3
for _p in (_ROOT, _PKG):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from pyspendless.app import app
    from pyspendless.conf import get_db_session
    from pyspendless.models import User
except ImportError:  # esecuzione da dentro pyspendless/
    from app import app
    from conf import get_db_session
    from models import User


# ===========================================================================
# CONTRATTO
# ===========================================================================
# Per ogni rotta:
#   ids          -> id che DEVONO esistere, esattamente una volta
#   form_fields  -> attributi name= che devono esistere
#   links        -> href che devono comparire almeno una volta
#   fase         -> in quale fase del task19-0 quella pagina viene rifatta
#
# Fonte: backlog/task19-0/ (sezione "Contratto DOM") — estratto dal codice
# attuale, non inventato. Aggiungere qui e' consentito; TOGLIERE no, se non
# con una riga di motivazione nel task.
# ===========================================================================

CONTRACT = {
    "/login": {
        "fase": 3,
        "ids": ["login-google-btn"],
        "links": ["/auth/login"],
    },
    "/home": {
        "fase": 3,
        # `navigation` e' l'id del <ul> della sidebar: serve a delimitare
        # l'estrazione in test_nav_destinazioni. Va conservato dalla nuova shell.
        "ids": ["navigation"],
        "links": [
            "/create", "/movements",
            "/settings/categories", "/settings/wallets",
            "/settings/group", "/settings/import-export",
        ],
    },
    "/create": {
        "fase": 4,
        "ids": [
            "movement-form", "movement_id", "is_repeat", "recurrent_movement_id",
            "move_date", "movement_type", "category", "wallet", "amount", "note",
            "submit-btn", "alert-container",
        ],
    },
    "/recurrent-movements": {
        "fase": 4,
        "ids": [
            "recurrent-form", "rm_id", "rm_name", "rm_movement_type",
            "rm_category", "rm_wallet", "rm_amount", "rm_note",
            "submit-btn", "cancel-btn", "form-title",
            "recurrent-tbody", "deleteModal", "delete-name",
            "confirm-delete-btn", "alertContainer",
        ],
    },
    "/settings/wallets": {
        "fase": 5,
        "ids": [
            "walletsContainer", "addWalletModal", "editWalletModal",
            "walletName", "walletCurrency", "editWalletId", "editWalletName",
            "editWalletCurrency", "editWalletOrder", "alertContainer",
        ],
    },
    "/settings/import-export": {
        "fase": 5,
        "ids": [
            "csvFile", "importProgress", "importResults", "importedCount",
            "errorsContainer", "errorsList", "alertContainer",
        ],
    },
    "/settings/categories": {
        "fase": 5,
        "ids": [
            "expenseCategoriesTableBody", "incomeCategoriesTableBody",
            "addCategoryModal", "editCategoryModal", "deleteCategoryModal",
            "categoryName", "categoryType", "categoryOrderIndex",
            "editCategoryId", "editCategoryOldName", "editCategoryName",
            "editCategoryOrderIndex", "deleteCategoryId", "deleteCategoryType",
            "deleteCategoryName", "deleteMovementsCount", "targetCategorySelect",
            "btnToggleSort", "alertContainer", "expense", "income",
        ],
    },
    "/settings/group": {
        "fase": 5,
        "ids": [
            "membersTable", "pendingInvitesTable", "noPendingMessage",
            "accountName", "accountNameInput", "editAccountModal",
            "inviteModal", "inviteEmail", "generatedLinkContainer",
            "generatedLink", "shareButton", "generateLinkBtn",
            "deleteAccountModal", "deletionDetails", "sharedAccountNote",
            "fullDeletionNote", "confirmDeleteText", "confirmDeleteBtn",
            "alertContainer",
        ],
    },
    "/movements": {
        "fase": 6,
        "ids": [
            "filters-collapse", "movementsTable", "category_id",
            "cat-select-all", "cat-deselect-all", "export-csv-btn",
            "movements-card-list", "cards-container", "load-more-trigger",
            "cards-spinner", "no-more-msg", "expensesChart",
        ],
        "form_fields": [
            "date_from", "date_to", "wallet_id",
            "category_type", "category_id", "keywords",
        ],
    },
    "/ps-search-mov": {
        "fase": 7,
        "ids": [
            "cards-container", "load-more-trigger", "cards-spinner",
            "no-more-msg", "no-results-msg", "alert-container",
        ],
        "form_fields": ["search"],
    },
    "/dashboard/monthly": {
        "fase": 8,
        "ids": [
            "filterYear", "filterMonth", "btnUpdate",
            "chartIncomeExpense", "chartExpenseByCategory",
            "chartExpenseByWallet", "chartIncomeByWallet",
        ],
    },
    "/dashboard/yearly": {
        "fase": 8,
        "ids": ["filterYear", "btnUpdate"],
    },
    "/reports": {
        "fase": 8,
        "ids": [
            "reportYear", "btnDownload", "statusArea",
            "loadingMsg", "successMsg", "errorMsg", "errorDetail",
        ],
    },
}

# Voci di menu della sidebar: destinazione + ordine. La nav viene ricostruita
# in Fase 2 e deve esporre le stesse destinazioni, nello stesso ordine.
NAV_LINKS_ORDER = [
    "/home",
    "/create",
    "/movements",
    "/ps-search-mov",
    "/recurrent-movements",
    "/dashboard/monthly",
    "/dashboard/yearly",
    "/reports",
    "/settings/categories",
    "/settings/wallets",
    "/settings/group",
    "/settings/import-export",
    "/auth/logout",
]

# Pattern vietati nel markup: classi CSS costruite per concatenazione di
# stringhe in JS. Lo scanner di Tailwind vede solo stringhe letterali complete,
# quindi una classe spezzata finisce ASSENTE dal CSS compilato (rischio R1).
DYNAMIC_CLASS_PATTERNS = [
    re.compile(r"""class=["'][^"']*["']\s*\+"""),      # class="..." + var
    re.compile(r"""\+\s*["'][^"']*\bclass=""" ),        # + "...class=
    re.compile(r"""class=["'][^"']*\$\{"""),            # class="...${var}
]


def _fake_login(client):
    """
    Inietta una sessione autenticata senza passare da Google OAuth.
    Usa il primo utente presente nel DB locale di sviluppo.
    """
    db = get_db_session()
    try:
        row = db.query(User).first()
        user = None if row is None else {
            "id": row.id,
            "account_id": row.account_id,
            "email": row.email,
            "name": row.name,
        }
    finally:
        db.close()

    if user is None:
        raise unittest.SkipTest(
            "Nessun utente nel DB locale: popola il DB di sviluppo prima di "
            "eseguire il contratto (vedi backlog/task19-0/fasi/fase-0.md)."
        )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["account_id"] = user["account_id"]
        sess["user_email"] = user["email"]
        sess["user_name"] = user["name"]
    return user


def _ids_in(html):
    return re.findall(r'\bid=["\']([^"\']+)["\']', html)


def _names_in(html):
    return re.findall(r'\bname=["\']([^"\']+)["\']', html)


def _hrefs_in(html):
    return re.findall(r'\bhref=["\']([^"\']+)["\']', html)


class ContrattoDOM(unittest.TestCase):
    """Un test per rotta: la pagina risponde 200 e espone tutti gli ancoraggi."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.user = _fake_login(cls.client)
        cls.only_fase = None
        for arg in sys.argv[1:]:
            if arg.startswith("FASE="):
                cls.only_fase = int(arg.split("=", 1)[1])

    def _get(self, route):
        resp = self.client.get(route, follow_redirects=False)
        self.assertEqual(
            resp.status_code, 200,
            f"{route} ha risposto {resp.status_code} invece di 200 "
            f"(redirect = sessione non valida?)"
        )
        return resp.get_data(as_text=True)

    def test_contratto(self):
        errori = []
        for route, spec in CONTRACT.items():
            if self.only_fase is not None and spec.get("fase") != self.only_fase:
                continue
            with self.subTest(route=route):
                html = self._get(route)
                ids = _ids_in(html)
                names = _names_in(html)
                hrefs = " ".join(_hrefs_in(html))

                for wanted in spec.get("ids", []):
                    n = ids.count(wanted)
                    if n == 0:
                        errori.append(f"{route}: id '{wanted}' MANCANTE")
                    elif n > 1:
                        errori.append(f"{route}: id '{wanted}' duplicato ({n}x)")

                for wanted in spec.get("form_fields", []):
                    if wanted not in names:
                        errori.append(f"{route}: campo name='{wanted}' MANCANTE")

                for wanted in spec.get("links", []):
                    if wanted not in hrefs:
                        errori.append(f"{route}: link '{wanted}' MANCANTE")

        if errori:
            self.fail("CONTRATTO VIOLATO:\n  - " + "\n  - ".join(errori))

    def test_nav_destinazioni(self):
        """
        La sidebar espone le stesse destinazioni, nello stesso ordine.

        L'estrazione e' limitata all'elemento `id="navigation"` (il <ul> della
        sidebar, oggi `ps-nav.html:48`): fuori da li' ci sono sia la voce
        Account nell'header, sia i link delle card di /home, che comparirebbero
        prima e falserebbero l'ordine. Quell'id e' quindi **parte del
        contratto**: la nuova shell deve mantenerlo.
        """
        html = self._get("/home")

        m = re.search(
            r'<ul[^>]*\bid=["\']navigation["\'][^>]*>(.*?)</ul>\s*(?:<!--[^>]*-->\s*)*</nav>',
            html, re.S,
        )
        if m is None:
            # fallback: dal tag con id="navigation" fino alla fine del <nav>
            m = re.search(
                r'\bid=["\']navigation["\'].*?(?=</nav>)', html, re.S)
        self.assertIsNotNone(
            m, "Elemento id='navigation' non trovato: la sidebar deve "
               "conservare quell'id (vedi ps-nav.html:48)."
        )
        blocco = m.group(0)

        hrefs = _hrefs_in(blocco)
        trovati = [h for h in hrefs if h in NAV_LINKS_ORDER]
        # dedup preservando l'ordine di comparsa
        visti, ordine = set(), []
        for h in trovati:
            if h not in visti:
                visti.add(h)
                ordine.append(h)

        mancanti = [l for l in NAV_LINKS_ORDER if l not in visti]
        self.assertEqual(
            mancanti, [],
            f"Destinazioni sparite dalla nav: {mancanti}"
        )

        atteso = [l for l in NAV_LINKS_ORDER if l in visti]
        self.assertEqual(
            ordine, atteso,
            f"Ordine della nav cambiato.\n  atteso: {atteso}\n  trovato: {ordine}"
        )

    def test_footer_versione(self):
        """Il footer mostra la versione su ogni pagina autenticata."""
        html = self._get("/home")
        self.assertRegex(
            html, r"v\d+\.\d+\.\d+",
            "Versione assente dal footer (context processor app_version)"
        )


class IgieneTemplate(unittest.TestCase):
    """Controlli statici sui sorgenti dei template, senza avviare l'app."""

    TEMPLATES = os.path.join(_PKG, "templates")

    def test_niente_classi_dinamiche(self):
        """
        Rischio R1: classi Tailwind costruite per concatenazione spariscono dal
        CSS compilato. Ogni ramo di un ternario deve produrre la classe INTERA,
        o meglio una classe .ps-* dichiarata in @layer components.
        """
        colpevoli = []
        for nome in sorted(os.listdir(self.TEMPLATES)):
            if not nome.endswith(".html"):
                continue
            path = os.path.join(self.TEMPLATES, nome)
            with open(path, encoding="utf-8") as f:
                for i, riga in enumerate(f, 1):
                    for pat in DYNAMIC_CLASS_PATTERNS:
                        if pat.search(riga):
                            colpevoli.append(f"{nome}:{i}")
                            break

        # NOTA Fase 0: sul codice ATTUALE questo test fallisce (Bootstrap non ha
        # il problema, quindi le concatenazioni esistono e vanno bene). Serve
        # da Fase 3 in poi, sui template gia' migrati. Finche' la migrazione e'
        # in corso, la whitelist elenca i file non ancora toccati.
        whitelist_non_migrati = {
            # <-- togliere il file da qui quando viene migrato a Tailwind
            "ps-show-mov.html", "ps-search-mov.html", "ps-setting-group.html",
            "ps-setting-categories.html", "ps-setting-wallet.html",
            "ps-setting-admin.html", "ps-setting-import-export.html",
            "ps-recurrent-mov.html", "ps-add-mov.html",
            "ps-dashboard-monthly.html", "ps-dashboard-yearly.html",
            "ps-reports.html",
            # template morti
            "cards.html", "forms.html", "tables.html", "base.html",
            "index.html", "login.html", "login_old.html", "loginv2.html",
            "ps-setting-categories-old.html",
        }
        residui = [c for c in colpevoli
                   if c.split(":")[0] not in whitelist_non_migrati]
        self.assertEqual(
            residui, [],
            "Classi CSS costruite per concatenazione in template GIA' migrati "
            f"(vedi §2.4 del piano): {residui}"
        )

    def test_nessun_bootstrap_nei_migrati(self):
        """
        Da Fase 9: nessun template deve piu' referenziare Bootstrap/AdminLTE.
        Finche' la migrazione e' in corso il test e' informativo: elenca
        quanti file li usano ancora, senza fallire.
        """
        residui = []
        for nome in sorted(os.listdir(self.TEMPLATES)):
            if not nome.endswith(".html"):
                continue
            with open(os.path.join(self.TEMPLATES, nome), encoding="utf-8") as f:
                testo = f.read()
            if "bootstrap" in testo.lower() or "adminlte" in testo.lower():
                residui.append(nome)

        if os.getenv("PS_FASE9") == "1":
            self.assertEqual(
                residui, [],
                f"Fase 9: Bootstrap/AdminLTE ancora referenziati in {residui}"
            )
        else:
            print(f"\n[info] template che usano ancora Bootstrap/AdminLTE: "
                  f"{len(residui)} -> {residui}")


def main():
    argv = [a for a in sys.argv if not a.startswith("FASE=")]
    print("=" * 70)
    print("TASK 19-0 — Contratto DOM (isofunzionalita' restyling)")
    print("=" * 70)
    unittest.main(argv=argv, verbosity=2, exit=True)


if __name__ == "__main__":
    main()
