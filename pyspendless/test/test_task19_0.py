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
    from pyspendless.conf import get_db_session, ADMIN_USER_ID
    from pyspendless.models import User
except ImportError:  # esecuzione da dentro pyspendless/
    from app import app
    from conf import get_db_session, ADMIN_USER_ID
    from models import User


# ===========================================================================
# CONTRATTO
# ===========================================================================
# Per ogni rotta:
#   ids          -> id che DEVONO esistere, esattamente una volta
#   form_fields  -> attributi name= che devono esistere
#   links        -> href che devono comparire almeno una volta
#   contains     -> stringhe letterali che devono comparire nell'HTML. Serve a
#                   coprire cio' che non e' un id: i `data-*` letti dal JS e
#                   gli id costruiti dal server e ricomposti dal JS (`row-<n>`).
#   solo_admin   -> la rotta risponde 200 solo se l'utente della sessione finta
#                   e' ADMIN_USER_ID; altrimenti viene saltata, non fallita.
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
        # I due submenu sono aperti/chiusi da toggleDashboardMenu() e
        # toggleSettingsMenu() in ps-nav.html: vivono nel layout, quindi sono
        # presenti su TUTTE le pagine autenticate. Li dichiariamo solo qui,
        # dove la shell viene verificata, per non ripeterli 15 volte.
        "ids": ["navigation", "dashboardSubmenu", "settingsSubmenu"],
        "links": [
            "/create", "/movements",
            "/settings/categories", "/settings/wallets",
            "/settings/group", "/settings/import-export",
        ],
    },
    # Copribile dalla Fase 3 in poi: vedi la nota in _fake_login sul perche'
    # questa rotta sembrava irraggiungibile.
    "/onboarding": {
        "fase": 3,
        "ids": ["account_name", "wallet_name"],
        "form_fields": ["account_name", "wallet_name"],
    },
    "/create": {
        "fase": 4,
        "ids": [
            "movement-form", "movement_id", "is_repeat", "recurrent_movement_id",
            "move_date", "movement_type", "category", "wallet", "amount", "note",
            "submit-btn", "alert-container",
            # select dei template ricorrenti: il change handler (ps-add-mov.html:189)
            # precompila il form leggendo i data-* delle sue <option>.
            "recurrent_template",
        ],
        # Letti da JS come dataset.*: ps-add-mov.html:194-198 sulle option di
        # `recurrent_template`, e :170 (`data-type`) sulle option di `category`.
        "contains": [
            "data-movement-type=", "data-category-id=", "data-wallet-id=",
            "data-amount=", "data-note=", "data-type=",
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
            "recurrent-table",
        ],
        # `id="row-<id>"` sulle <tr>: il JS lo ricompone per rimuovere la riga
        # cancellata (ps-recurrent-mov.html:262, getElementById(`row-${...}`)).
        # Richiede almeno una ricorrente nel DB di sviluppo.
        "contains": ['id="row-'],
    },
    "/settings/wallets": {
        "fase": 5,
        "ids": [
            "walletsContainer", "addWalletModal", "editWalletModal",
            "walletName", "walletCurrency", "editWalletId", "editWalletName",
            "editWalletCurrency", "editWalletOrder", "alertContainer",
            # il submit handler e' agganciato al form, non al bottone
            # (ps-setting-wallet.html:251)
            "addWalletForm", "editWalletForm",
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
            # submit handler sul form (ps-setting-categories.html:349)
            "addCategoryForm", "editCategoryForm",
            # struttura dei tab: i bottoni puntano a #expense / #income con
            # data-bs-target. In Fase 1 il comportamento passa a ps-ui.js, ma
            # gli id devono restare.
            "categoryTabs", "categoryTabContent", "expense-tab", "income-tab",
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
            # submit handler sui form (ps-setting-group.html:232, :240)
            "editAccountForm", "inviteForm",
        ],
    },
    "/movements": {
        "fase": 6,
        "ids": [
            "filters-collapse", "movementsTable", "category_id",
            "cat-select-all", "cat-deselect-all", "export-csv-btn",
            "movements-card-list", "cards-container", "load-more-trigger",
            "cards-spinner", "no-more-msg", "expensesChart",
            # i campi dei filtri sono sia id sia name: le <label for=...> e il
            # codice di reset li raggiungono per id.
            "date_from", "date_to", "wallet_id", "category_type", "keywords",
            # correzione massiva (ps-show-mov.html:229-280). `bulk-category`
            # NON e' qui: e' condizionale, vedi la voce con query string.
            "bulk-edit-btn", "bulkEditModal", "bulk-note", "bulk-edit-apply-btn",
        ],
        "form_fields": [
            "date_from", "date_to", "wallet_id",
            "category_type", "category_id", "keywords",
        ],
    },
    # Stessa pagina, stato diverso: il select della correzione massiva esiste
    # SOLO con un filtro per tipo attivo ({% if filters.category_type %},
    # ps-show-mov.html:242). Sulla rotta nuda non c'e', e il JS lo gestisce
    # (getElementById -> null, :440). Senza questa voce il ramo non e' coperto
    # e la Fase 6 potrebbe perderlo senza che nulla se ne accorga.
    "/movements?category_type=expense": {
        "fase": 6,
        "ids": ["bulk-category", "bulkEditModal", "bulk-edit-apply-btn"],
    },
    "/ps-search-mov": {
        "fase": 7,
        "ids": [
            "cards-container", "load-more-trigger", "cards-spinner",
            "no-more-msg", "no-results-msg", "alert-container",
            "movements-card-list",
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
        "ids": [
            "filterYear", "btnUpdate",
            # quattro canvas uguali a quelli di /dashboard/monthly, piu' il
            # trend per categoria, che monthly non ha
            "chartIncomeExpense", "chartExpenseByCategory",
            "chartExpenseByWallet", "chartIncomeByWallet",
            # select + canvas del trend (ps-dashboard-yearly.html:170, :399, :415)
            "filterCategory", "chartCategoryTrend",
        ],
    },
    # Non era nel CONTRACT: pagina dei token MCP e delle connessioni OAuth.
    # Rifatta in Fase 5 insieme alle altre pagine di impostazioni.
    "/settings/profile": {
        "fase": 5,
        "ids": [
            "alertContainer", "mcpUrl", "tokensContainer",
            "oauthConnectionsContainer", "addTokenModal", "addTokenForm",
            "tokenLabel", "showTokenModal", "newTokenValue",
        ],
    },
    # Non era nel CONTRACT perche' risponde 200 solo all'admin. Con
    # `solo_admin` la rotta viene saltata quando la sessione finta non e'
    # ADMIN_USER_ID, invece di produrre un falso fallimento su un altro DB.
    "/settings/admin": {
        "fase": 5,
        "solo_admin": True,
        "ids": [
            "alertContainer", "whitelistTable", "whitelistTableBody",
            "usersTable", "usersTableBody", "addWhitelistModal",
            "addWhitelistForm", "whitelistEmail", "whitelistNote",
        ],
        # il JS raggiunge la riga utente con
        # querySelector(`#usersTable tr[data-user-id="${userId}"]`) (:232)
        "contains": ['data-user-id="'],
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
    # Stesso rischio, lato Jinja: `class="alert alert-{{ category }}"` assembla
    # il nome della classe a pezzi, e il frammento `alert-` non e' una stringa
    # letterale completa. Il carattere prima di `{{` dev'essere alfanumerico o
    # un trattino: cosi' `class="{% if x %}a{% else %}b{% endif %}"`, che
    # produce classi INTERE, non viene segnalato.
    re.compile(r"""class=["'][^"']*[A-Za-z0-9_-]\{\{"""),  # class="x-{{ var }}
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
        # /onboarding NON redirige perche' l'utente ha gia' un account, come si
        # era supposto in Fase 0: redirige perche' manca `oauth_user_info`
        # (app.py:338). E' l'unica rotta che legge questa chiave, quindi
        # aggiungerla qui non cambia il comportamento di nessun'altra.
        sess["oauth_user_info"] = {
            "name": user["name"], "email": user["email"],
        }
    return user


# `\b` non basta: in `data-category-id="27"` il confine di parola cade dopo
# il trattino, quindi `\bid=` combacia e l'estrattore cattura il VALORE del
# data-attribute ("27") come se fosse un id. Stesso problema per `name` con
# `data-*-name=`. Il lookbehind esclude trattino e caratteri di parola, cosi'
# combaciano solo gli attributi `id=` / `name=` veri. Senza questa precisione
# il controllo "esattamente una volta" puo' segnalare duplicati inesistenti.
def _ids_in(html):
    return re.findall(r'(?<![-\w])id=["\']([^"\']+)["\']', html)


def _names_in(html):
    return re.findall(r'(?<![-\w])name=["\']([^"\']+)["\']', html)


def _hrefs_in(html):
    return re.findall(r'\bhref=["\']([^"\']+)["\']', html)


class ContrattoDOM(unittest.TestCase):
    """Un test per rotta: la pagina risponde 200 e espone tutti gli ancoraggi."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.user = _fake_login(cls.client)
        # Le rotte marcate `solo_admin` rispondono 200 solo se l'utente della
        # sessione finta e' ADMIN_USER_ID. Sul DB di sviluppo attuale lo e'
        # (il primo utente e' l'admin), ma il legame e' fragile: dipende
        # dall'ordine di inserimento. Meglio saltare che fallire a vuoto.
        cls.is_admin = str(cls.user["id"]) == str(ADMIN_USER_ID)
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
        saltate = []
        for route, spec in CONTRACT.items():
            if self.only_fase is not None and spec.get("fase") != self.only_fase:
                continue
            if spec.get("solo_admin") and not self.is_admin:
                saltate.append(route)
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

                for wanted in spec.get("contains", []):
                    if wanted not in html:
                        errori.append(f"{route}: stringa '{wanted}' MANCANTE")

        if saltate:
            print(f"\n[info] rotte saltate (sessione non admin): {saltate}")

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
