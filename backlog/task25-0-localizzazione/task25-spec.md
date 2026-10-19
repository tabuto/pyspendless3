# Task 25.0 — Localizzazione dell'interfaccia e preferenza di lingua per utente

**Stato**: **SPECIFICA** — sola analisi. Nessun file applicativo modificato da
questo documento. Serve come base per la pianificazione delle attività di
implementazione (che andranno in `fasi/fase-N.md` in questa stessa cartella,
come per il task19-0).
**Data**: 2026-10-19
**Versione app analizzata**: `_APP_VERSION = "0.3.1"` (`pyspendless/app.py:35`)
**Repo**: `tabuto/pyspendless3`, branch `main`
**Dipende da**: niente. Tocca però **tutti** i template usciti dal task19-0 e
gran parte dei messaggi di `app.py`, quindi va fatto a task19-0 chiuso (lo è).
**Piano di dettaglio**: `piano-localizzazione.md` + `fasi/fase-0.md` … `fase-9.md`
in questa cartella. I punti aperti P1, P2 e P3 di §10 sono stati **chiusi** il
2026-10-19; le decisioni sono riportate qui e sviluppate nel piano.

---

## 1. Obiettivo

Due obiettivi, in quest'ordine di priorità:

1. **Rendere traducibili i testi dell'interfaccia**, estraendoli dal codice in
   cataloghi di traduzione — senza cambiare una virgola di comportamento
   (vincolo di **isofunzionalità**, come nel task19-0: cambia solo da dove
   arriva il testo, non cosa fa l'app).
2. **Salvare la preferenza di lingua dell'utente**, in modo che sopravviva al
   logout e sia la stessa su tutti i dispositivi (quindi: sul database, non
   solo in `localStorage` come il tema).

Lingue del primo rilascio: **italiano** (lingua di default e sorgente) e
**inglese britannico** — `en_GB`, non `en` (decisione P2, chiusa il 2026-10-19:
tiene le date nell'ordine `19/10/2026` a cui gli utenti attuali sono abituati,
invece del `10/19/2026` americano). L'infrastruttura deve rendere l'aggiunta di
una terza lingua un lavoro di sola traduzione, senza toccare codice.

### Criteri di accettazione

| # | Criterio |
|---|---|
| A1 | Con preferenza `it` l'app è **identica** a oggi: stesse stringhe, stessi formati, nessuna regressione visiva (confronto con gli screenshot di `docs/ui-after/`). |
| A2 | Con preferenza `en_GB` ogni pagina autenticata, i messaggi flash e le risposte di errore delle API sono in inglese. |
| A3 | La preferenza è persistita per utente e sopravvive a logout/login e a un browser diverso. |
| A4 | Le pagine **non** autenticate (login, onboarding, manutenzione, consenso OAuth) rendono in una lingua sensata anche senza utente in sessione. |
| A5 | `pybabel extract` non trova stringhe hardcoded residue nelle pagine dichiarate "fatte" (verifica automatizzabile, vedi §8). |
| A6 | Nessuna modifica ai formati **macchina**: CSV di export/import, `data-order` di DataTables, `value` degli `<input type="date">`, payload JSON delle API. |
| A7 | Il deploy resta un `git pull` + Reload: nessuna fase di build sul server. |

---

## 2. Stato attuale (verificato sul codice)

### 2.1 La lingua è italiana e hardcoded in tre strati

| Strato | Dove | Esempio |
|---|---|---|
| Markup | 22 template in `pyspendless/templates/` | `templates/ps-base.html:35` → `<html lang="it">` |
| JS inline nei template | blocchi `{% block scripts %}` | `templates/ps-dashboard-monthly.html:251` → `['Entrate', 'Uscite']` |
| Python | `app.py`, `repository.py`, `report_pdf.py` | `app.py:1526` → `f'Categoria eliminata e {movements_count} movimenti spostati'` |

Non esiste oggi alcuna infrastruttura di i18n: nessuna dipendenza, nessun
catalogo, nessun `lang` dinamico. `Babel`/`Flask-Babel` **non sono installati**
(verificato in `.venv/lib/python3.9/site-packages/`).

### 2.2 Inventario delle stringhe (misura, non stima)

Conteggio euristico sui 22 template (testo fra tag, attributi
`placeholder|title|aria-label|alt`, stringhe-frase nei blocchi `<script>`
inline). Da raffinare con `pybabel extract` nella Fase 0, ma dà l'ordine di
grandezza del lavoro:

| Template | testo | attributi | stringhe JS |
|---|---:|---:|---:|
| `ps-setting-profile.html` | 55 | 2 | 17 |
| `ps-show-mov.html` | 48 | 7 | 14 |
| `ps-setting-group.html` | 47 | 5 | 40 |
| `ps-setting-categories.html` | 36 | 3 | 20 |
| `ps-recurrent-mov.html` | 29 | 2 | 10 |
| `ps-reports.html` | 27 | 0 | 1 |
| `ps-setting-import-export.html` | 27 | 0 | 6 |
| `ps-dashboard-monthly.html` | 22 | 0 | 6 |
| `ps-setting-admin.html` | 22 | 1 | 9 |
| `ps-nav.html` | 21 | 10 | 0 |
| `ps-setting-wallet.html` | 21 | 2 | 26 |
| `ps-search-mov.html` | 19 | 5 | 9 |
| `ps-add-mov.html` | 15 | 0 | 8 |
| `ps-home.html` | 12 | 0 | 0 |
| `ps-dashboard-yearly.html` | 11 | 0 | 7 |
| `ps-onboarding.html` | 8 | 3 | 0 |
| `ps-maintenance.html` | 5 | 0 | 0 |
| `ps-oauth-consent.html` | 4 | 0 | 0 |
| `ps-base.html`, `ps-login.html` | 4 | 0 | 0 |
| `ps-auth.html` | 0 | 0 | 0 |
| **Totale pagine utente** | **~433** | **~40** | **~173** |
| `_styleguide.html` (pagina di sviluppo) | 127 | 9 | 6 |

Lato Python, stringhe-frase candidate (euristica: almeno due parole):

| File | candidate | di cui `flash()` |
|---|---:|---:|
| `app.py` | ~200 (include i log, da escludere) | 33 |
| `repository.py` | ~73 | 0 |
| `mcp_server.py` | ~93 | 0 |
| `report_pdf.py` | ~22 | 0 |
| `oauth_server.py` | ~7 | 0 |
| `report_charts.py` | ~6 | 0 |

In `app.py` ci sono **172 occorrenze** di chiavi `'error'|'message'|'success'`
nelle risposte `jsonify`: sono messaggi che il JS delle pagine mostra
all'utente, quindi **sono stringhe di interfaccia**, non dettagli interni.

Ordine di grandezza complessivo del catalogo: **700–900 msgid**.

### 2.3 Formati data/numero già presenti

- `strftime('%d/%m/%Y')` per la visualizzazione: `app.py:722`, `app.py:1093`,
  `templates/ps-search-mov.html:77`, `templates/ps-show-mov.html:215`,
  `templates/ps-recurrent-mov.html:99`, `templates/ps-add-mov.html:19`,
  `templates/ps-setting-group.html:28`, `mcp_server.py:685,727`.
- `strftime('%d/%m/%Y %H:%M')` per le date dei token: `repository.py:1166,1253,1358,1619`.
- `strftime('%Y-%m-%d')` / `isoformat()` dove il formato è **macchina**:
  export CSV (`app.py:779`, `app.py:1925`), `data-order` di DataTables
  (`ps-show-mov.html:215`), `value` degli input date (`ps-add-mov.html:57`).
- Nomi dei mesi in italiano, duplicati in tre punti: `repository.py:2212`,
  `report_pdf.py:13` (`MONTHS_IT`), e come 12 `<option>` hardcoded in
  `templates/ps-dashboard-monthly.html:25` e seguenti.
- Importi: `'%.2f'|format(...)` nei template e `'%.2f' %` in Python. In
  italiano e in inglese il separatore decimale **è diverso** (`1.234,56` vs
  `1,234.56`): oggi l'app stampa sempre il punto, cioè è già "inglese" nei
  numeri e italiana nelle date.

### 2.4 Quello su cui si può costruire

- **Pattern della preferenza per utente**: `User.preferred_wallet_id`
  (`models.py:46`) + API `PUT/DELETE /api/wallets/<id>/preferred`
  (`app.py:1661`, `app.py:1701`) + DDL in
  `sql/sqllite/NEXT_RELEASE/alter_user_add_preferred_wallet.sql`. Il task22-0
  ha già tracciato la strada che `User.locale` deve ripercorrere.
- **Pattern del selettore in testata**: il toggle del tema in
  `templates/ps-nav.html:186` (gruppo di tre bottoni con `aria-label`), con
  `static/js/ps-theme.js` e persistenza in `localStorage`. Il selettore di
  lingua gli somiglia come UI ma **non** come persistenza (vedi D5).
- **Context processor** già presente (`app.py:93`) dove esporre `current_locale`
  ai template senza toccare 77 rotte.
- `static/js/ps-ui.js` e `ps-theme.js` **non contengono stringhe utente**
  (verificato: nessun `textContent`/`innerHTML`/`alert` con testo; l'italiano
  che contengono è tutto nei commenti). Due file in meno da toccare.

---

## 3. Decisioni

| # | Decisione | In sintesi |
|---|---|---|
| D1 | **Flask-Babel** (Babel + `gettext`, cataloghi `.po`/`.mo`) | È lo standard de facto per Flask/Jinja2: niente di artigianale. |
| D2 | **msgid in italiano** | I letterali attuali diventano i msgid; si traduce `it → en`. Diff minimo, rischio minimo. |
| D3 | Lingue: `it` (default + fallback), `en_GB` | Catalogo `en_GB` completo. Nessun catalogo `it`: senza catalogo `gettext` restituisce il msgid, che *è* l'italiano. |
| D4 | I `.mo` compilati sono **versionati**, build con `tools/build-i18n.sh` | Stessa logica del CSS Tailwind: sul server non c'è una fase di build. |
| D5 | Preferenza su `User.locale` (nullable) + cache in `session['locale']` | Deve seguire l'utente fra dispositivi; `localStorage` (come il tema) non basta. |
| D6 | Ordine di risoluzione: `?lang=` → sessione → `User.locale` → `Accept-Language` → `it` | Vedi §4.2. |
| D7 | Stringhe JS: `{{ _('...') }}` **dentro** i blocchi `<script>` dei template | Quei blocchi sono già resi da Jinja. Zero catalogo JS, zero runtime nuovo. |
| D8 | Date/numeri/valuta con `format_date`/`format_decimal`/`format_currency` di Babel, **solo in visualizzazione** | I formati macchina restano invariati (criterio A6). |
| D9 | Selettore nel profilo (`ps-setting-profile.html`) **+** nella testata accanto al tema | Il profilo è la sede naturale; la testata serve alle pagine non autenticate. |
| D10 | Fuori scope: `mcp_server.py`, header CSV, categorie di default, fuso orario | Vedi §9, con la motivazione per ciascuno. |

### Motivazioni delle decisioni non ovvie

**D1 — perché Flask-Babel e non una soluzione fatta in casa.**
`gettext` è lo standard: strumenti di estrazione (`pybabel extract`), formato
`.po` editabile con strumenti esistenti (Poedit, Weblate), plurali dichiarati
nel catalogo, fallback automatico. Flask-Babel aggiunge l'integrazione con il
ciclo di richiesta Flask (locale per richiesta), registra l'estensione i18n di
Jinja2 e espone `_`, `gettext`, `ngettext` nei template senza boilerplate; e
porta Babel, cioè i dati CLDR per date, numeri e valute (D8), che altrimenti
andrebbero riscritti a mano lingua per lingua. Un dizionario JSON fatto in casa
costerebbe meno all'inizio e più a ogni lingua aggiunta.

> **Alternativa valutata e scartata**: `gettext` della standard library +
> estensione i18n di Jinja2 configurata a mano, con `pybabel` usato solo come
> strumento di sviluppo locale. Vantaggio reale: **zero dipendenze nuove sul
> server** (vedi §6.2, il `pip install` manuale su PythonAnywhere). Svantaggio:
> ci si scrive e si mantiene il pezzo che Flask-Babel regala, e si perdono i
> formati CLDR. **Da tenere come piano B** se l'installazione delle dipendenze
> sul server si rivelasse un problema.

**D2 — perché i msgid restano in italiano.**
La prassi gettext vorrebbe msgid in inglese. Qui costerebbe la riscrittura di
~900 letterali in due passaggi (italiano → inglese nel codice, poi catalogo
`it` da zero) su file molto grandi (`app.py` è 105 KB), con un diff enorme in
cui un errore di battitura in una stringa italiana non si vedrebbe più. Con
msgid italiani il lavoro per stringa è `"Testo"` → `_("Testo")` — meccanico,
rivedibile, e con l'italiano che funziona **anche a catalogo mancante o
corrotto** (fallback = msgid). Il costo accettato: cambiare una parola nella
copy italiana cambia il msgid e invalida la traduzione inglese corrispondente,
che torna in italiano fino al successivo `pybabel update`. Accettabile perché
`tools/check-i18n.py` (§8) rende visibile il buco; e perché la copy italiana è
stabile.

**D5 — perché sul database e non in `localStorage` come il tema.**
Il tema è una preferenza del dispositivo (dipende dallo schermo, dall'ora, dal
sistema): è giusto che sia locale. La lingua è una proprietà della persona: chi
usa l'app in inglese la vuole in inglese anche dal telefono. Serve quindi una
colonna su `User`, con lo stesso trattamento di `preferred_wallet_id`:
`nullable`, e **`NULL` è uno stato legittimo** che significa "decidi tu dal
browser" (`Accept-Language`). La sessione fa da cache per non interrogare il DB
a ogni richiesta e per coprire le pagine senza utente.

---

## 4. Architettura

### 4.1 Wiring

```
pyspendless/
├── babel.cfg                      # NUOVO: mappa di estrazione (Python + Jinja2)
├── translations/                  # NUOVO
│   ├── messages.pot               #   catalogo sorgente (versionato)
│   └── en_GB/LC_MESSAGES/
│       ├── messages.po            #   traduzione inglese (versionata, editabile)
│       └── messages.mo            #   COMPILATO, VERSIONATO (vedi §6)
├── i18n.py                        # NUOVO: init Babel, resolver, costanti
├── app.py                         #   init + context processor + API locale
├── conf.py                        #   SUPPORTED_LOCALES, DEFAULT_LOCALE
└── models.py                      #   User.locale

sql/sqllite/NEXT_RELEASE/alter_user_add_locale.sql   # NUOVO (DDL + nessun backfill)
tools/build-i18n.sh                                  # NUOVO (extract+update+compile)
tools/check-i18n.py                                  # NUOVO (sonda di coerenza)
```

`babel.cfg` minimo:

```ini
[python: **.py]
[jinja2: **/templates/**.html]
```

> **Attenzione** (è il tranello che ha fatto sfuggire `ps-oauth-consent.html`
> nella pianificazione del task19-0, cfr. CLAUDE.md): `oauth_server.py` è un
> blueprint registrato in `app.py:64` e rende un template per conto proprio. Il
> pattern `**.py` + `**/templates/**.html` lo include; un elenco di file
> scritto a mano lo dimenticherebbe. **Niente elenchi a mano in `babel.cfg`.**

### 4.2 Risoluzione della lingua

Un solo `locale_selector` in `i18n.py`, con quest'ordine:

1. **`?lang=xx` in query string** — se valido, *scrive* in sessione e vale da
   quel momento. Serve al selettore nelle pagine senza utente e ai link
   condivisibili. Qualsiasi valore non in `SUPPORTED_LOCALES` viene ignorato in
   silenzio (nessun errore, nessun eco in pagina: è input non fidato).
2. **`session['locale']`** — cache per richiesta/sessione.
3. **`User.locale`** dell'utente in sessione — letto una volta sola al login e
   messo in `session['locale']` (come già si fa con `user_name` e
   `account_id`, `app.py:223-226`); riletto se la sessione non lo ha.
4. **`Accept-Language`** del browser, filtrato su `SUPPORTED_LOCALES`
   (`request.accept_languages.best_match(...)`).
5. **`it`** come default finale.

Il selettore nel profilo scrive *sia* su `User.locale` *sia* in sessione, così
l'effetto è immediato senza rileggere il DB.

### 4.3 Modello dati e DDL

```sql
-- sql/sqllite/NEXT_RELEASE/alter_user_add_locale.sql
ALTER TABLE User ADD COLUMN locale TEXT;
```

Nessun backfill: `NULL` = "lingua dal browser", che per gli utenti attuali
(tutti italiani) dà esattamente il comportamento di oggi. È la differenza
rispetto al task22-0, che invece aveva una preferenza preesistente da
preservare.

`models.py`, in `User`, accanto a `preferred_wallet_id`:

```python
# Lingua preferita dell'utente (task25-0). None è uno stato legittimo
# ("decidi dal browser"): nessun backfill alla migrazione.
locale = Column(Text, nullable=True)
```

### 4.4 API

Una sola rotta nuova, modellata su `api_set_preferred_wallet` (`app.py:1662`):

```
PUT /api/user/locale      body {"locale": "en"}   -> 200 {"locale": "en"}
                                                  -> 400 se non in SUPPORTED_LOCALES
                                                  -> 401 se non autenticato
```

Validazione **a whitelist** (`locale in SUPPORTED_LOCALES`), non a regex: è il
valore che finirà in `<html lang="...">` e nel path dei cataloghi. Coerente con
i finding del task24-0 sul mass assignment: si accetta solo la chiave `locale`,
e si scrive solo sull'utente in sessione — mai su un `user_id` che arriva dal
client.

### 4.5 UI

- **Profilo** (`ps-setting-profile.html`): nuova card "Lingua" con un `<select>`
  (Italiano / English / "Come il browser" per `NULL`), che chiama l'API e
  ricarica la pagina.
- **Testata** (`ps-nav.html`, accanto al toggle del tema a riga 186): selettore
  compatto a due voci. Nelle pagine non autenticate (`ps-auth.html` e
  discendenti) agisce via `?lang=`.
- `ps-base.html:35`: `<html lang="it">` → `<html lang="{{ current_locale }}">`,
  con `current_locale` iniettato dal context processor di `app.py:93`.

---

## 5. Punti tecnici che decidono la riuscita

### 5.1 Le f-string non sono traducibili

`pybabel extract` non vede le f-string, e `_(f"...")` è un bug a runtime (si
cercherebbe nel catalogo la stringa *già interpolata*). Ogni messaggio con
interpolazione va riscritto con **placeholder nominali**:

```python
# prima  (app.py:1526)
flash(f'Categoria eliminata e {movements_count} movimenti spostati')

# dopo
flash(ngettext(
    'Categoria eliminata e %(num)d movimento spostato',
    'Categoria eliminata e %(num)d movimenti spostati',
    movements_count) % {'num': movements_count})
```

Placeholder **nominali** e non posizionali: il traduttore può riordinarli, e un
catalogo con un placeholder sbagliato si becca in verifica invece che in
produzione. Casi noti già censiti: `app.py:1526`, `app.py:1997`, `app.py:2004`.
Vanno escluse le f-string nei **log** (`logger.*`): restano in italiano e non
si traducono, non sono interfaccia (`app.py:2741`, `2783`, `2834`).

### 5.2 Plurali

L'italiano e l'inglese hanno la stessa regola (una forma singolare, una
plurale), ma la forma va dichiarata con `ngettext` ovunque ci sia un conteggio,
altrimenti una terza lingua con regole diverse richiederebbe di riaprire il
codice. Punti noti: messaggi di import ("N movimenti importati"), "Nessun
movimento trovato" (`ps-search-mov.html:47,160`), risultati dei filtri.

### 5.3 Stringhe fuori dal ciclo di richiesta

Le costanti a livello di modulo vengono valutate all'import, quando non esiste
una richiesta e quindi nemmeno una lingua. Per `MONTHS_IT` (`report_pdf.py:13`),
`month_names` (`repository.py:2212`) e simili: o `lazy_gettext`, o — meglio per
i nomi dei mesi — `babel.dates.get_month_names(locale=...)`, che li prende dal
CLDR e **cancella la duplicazione** oggi presente in tre punti (compresi i 12
`<option>` di `ps-dashboard-monthly.html:25`, che diventano un ciclo Jinja).

### 5.4 DataTables

`templates/ps-show-mov.html:337` carica la localizzazione da un URL fisso:

```js
language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/it-IT.json' }
```

**Decisione P3, chiusa il 2026-10-19: si self-hostano i due JSON** in
`pyspendless/static/js/i18n/datatables-it-IT.json` e `datatables-en-GB.json`,
come si è fatto per le icone nel task19-0 (decisione D9 di
`task19-0/fasi/fase-1.md`). Sono ~2 KB l'uno, versionati, e la riga diventa:

```js
language: { url: '{{ url_for("static", filename="js/i18n/datatables-" ~ dt_locale ~ ".json") }}?v={{ app_version }}' }
```

dove `dt_locale` è `it-IT` o `en-GB`, iniettato dal context processor. Si
guadagna una dipendenza da CDN in meno su una pagina che ne ha già troppe, e il
cache-busting già in uso nel progetto.

### 5.5 Pagine senza utente, e la manutenzione

`check_maintenance_mode` (`app.py:99`) intercetta **ogni** richiesta e rende
`ps-maintenance.html`. In manutenzione il DB può essere indisponibile: il
resolver della lingua su quel percorso **non deve toccare il database**, solo
sessione, `?lang=` e `Accept-Language`. Vale anche per `ps-login.html`,
`ps-auth.html`, `ps-onboarding.html` e `ps-oauth-consent.html` (quest'ultima è
la pagina di consenso del flusso Alexa del task23-0: la vede l'utente, va
tradotta, e arriva da un redirect esterno senza sessione).

### 5.7 `en_GB`: tre conseguenze tecniche da non sbagliare

La scelta di `en_GB` invece di `en` (P2) porta tre dettagli che, se sbagliati,
danno un bug silenzioso:

1. **Due grafie dello stesso codice.** Babel e i path dei cataloghi usano
   l'underscore (`en_GB`, `translations/en_GB/LC_MESSAGES/`); l'attributo
   `lang` dell'HTML vuole il BCP-47 con il trattino (`en-GB`); DataTables
   nomina il suo file `en-GB.json`. Servono entrambe le forme, prodotte da un
   solo punto (`i18n.py`), mai scritte a mano nei template.
2. **`Accept-Language` non manda mai `en_GB`.** I browser mandano `en-GB`,
   `en-US`, `en`, con pesi. La lista passata a `best_match` va scritta nella
   grafia dei browser, e tutto ciò che è inglese — `en`, `en-US`, `en-AU`, … —
   va **normalizzato** su `en_GB`: è l'unica variante inglese che abbiamo, e
   dare l'italiano a chi chiede `en-US` sarebbe il peggiore dei due esiti.
3. **Il `<select>` del profilo salva `en_GB`**, che è il valore che finisce in
   `User.locale` e nella whitelist di validazione (§4.4). Un `en` scritto a
   mano nel markup passerebbe la validazione solo se la whitelist lo
   contenesse — e allora `gettext` cercherebbe `translations/en/`, che non
   esiste, e tornerebbe all'italiano senza un solo errore in log. **Una sola
   fonte di verità: `SUPPORTED_LOCALES` in `conf.py`**, e il `<select>` reso
   da un ciclo su quella.

### 5.6 Cosa non si traduce mai

I **dati dell'utente**: nomi di categorie e wallet, note dei movimenti, nomi dei
gruppi. Sono contenuto, non interfaccia. Nessun `_()` attorno a un valore che
arriva dal DB.

---

## 6. Build e rilascio

### 6.1 I `.mo`: il passo che si dimentica (di nuovo)

Identico al caso del CSS Tailwind descritto in CLAUDE.md, e con la stessa
trappola: **l'output compilato è versionato**, perché sul server non c'è
nessuna fase di build e il deploy è un `git pull`. `gettext` legge i `.mo`
binari, non i `.po`.

```bash
./tools/build-i18n.sh      # pybabel extract -> update -> compile
```

Lo script deve, sul modello di `tools/build-css.sh`:

- fallire se `pybabel` non è nel virtualenv;
- fallire se un `.mo` non viene prodotto o è più vecchio del `.po`;
- fallire se git **ignora** i `.mo` (vedi §6.3);
- stampare le statistiche di traduzione (quante msgid non tradotte), così un
  catalogo incompleto si vede prima del commit.

**Se ci si dimentica**: in produzione resta il catalogo vecchio, cioè alcune
stringhe tornano in italiano per gli utenti in inglese. Fallimento degradato,
non rotto — e per questo insidioso. Il modo di accorgersene prima è lo stesso
del CSS: se dopo una build `git status` non è pulito, il commit era incompleto.

### 6.2 Nuove dipendenze: un passo manuale sul server

`Flask-Babel` e `Babel` vanno aggiunti a `pyspendless/requirements.txt`. Il
`git pull` **non installa niente**: serve un `pip install -r requirements.txt`
nel virtualenv di PythonAnywhere prima del Reload, una volta sola. Va scritto
nella procedura di rilascio di CLAUDE.md, altrimenti il primo deploy del task
porta l'app a un `ImportError` su tutte le pagine — questa volta un fallimento
**rotto**, non degradato.

Da verificare in Fase 0 (vedi §10, P1): la versione di Python della web app su
PythonAnywhere, per fissare i pin giusti. Il virtualenv locale è su
**Python 3.9**; `Flask-Babel 4.x` e `Babel 2.x` lo supportano, ma i pin vanno
scelti e scritti, non lasciati aperti.

### 6.3 `.gitignore`

Verificare che nessuna regola ignori `*.mo` (oggi non c'è: controllato). Per
simmetria con il blocco del task19-0, aggiungere un commento che spieghi
**perché** i `.mo` sono versionati, così nessuno li "ripulisca" in futuro
pensando siano artefatti di build.

---

## 7. File toccati (previsione)

| File | Intervento |
|---|---|
| `pyspendless/requirements.txt` | + `Flask-Babel`, `Babel` (pin) |
| `pyspendless/babel.cfg` | **nuovo** — mappa di estrazione |
| `pyspendless/i18n.py` | **nuovo** — init, `locale_selector`, helper di formato |
| `pyspendless/translations/**` | **nuovo** — `.pot`, `en_GB/*.po`, `en_GB/*.mo` (compilato, versionato) |
| `pyspendless/conf.py` | + `SUPPORTED_LOCALES`, `DEFAULT_LOCALE` (da env, default `it`) |
| `pyspendless/models.py` | + `User.locale` (riga ~47, accanto a `preferred_wallet_id`) |
| `pyspendless/repository.py` | + `UserRepository.set_locale/get_locale`; `_()` sui messaggi; mesi dal CLDR (riga 2212) |
| `pyspendless/app.py` | init Babel; `current_locale` nel context processor (riga 93); `PUT /api/user/locale`; `locale` in sessione al login (righe 223-226, 274-277, 385-388); `_()`/`ngettext()` su 33 `flash()` e sui messaggi `jsonify` |
| `pyspendless/oauth_server.py` | `_()` sui ~7 messaggi utente |
| `pyspendless/report_pdf.py`, `report_charts.py` | etichette traducibili; `MONTHS_IT` dal CLDR (riga 13) |
| `pyspendless/templates/ps-base.html` | `lang` dinamico (riga 35) |
| `pyspendless/templates/ps-nav.html` | selettore lingua accanto al tema (riga 186); `_()` su 21 testi + 10 attributi |
| `pyspendless/templates/ps-setting-profile.html` | card "Lingua" + `_()` |
| altri 18 template | `_()` su testi, attributi e stringhe nei blocchi `<script>` |
| `pyspendless/templates/ps-show-mov.html` | localizzazione DataTables (riga 337) |
| `pyspendless/templates/ps-dashboard-monthly.html` | mesi da ciclo invece dei 12 `<option>` (riga 25) |
| `sql/sqllite/NEXT_RELEASE/alter_user_add_locale.sql` | **nuovo** — DDL |
| `tools/build-i18n.sh`, `tools/check-i18n.py` | **nuovi** |
| `pyspendless/test/test_task25_0.py` | **nuovo** |
| `CLAUDE.md`, `pyspendless/README.md` | procedura di rilascio (`build-i18n.sh`, `pip install` sul server) |
| `backlog/features.md` | riga del task |
| `.gitignore` | commento sui `.mo` versionati |

`static/js/ps-ui.js` e `static/js/ps-theme.js`: **non toccati** (nessuna
stringa utente, §2.4). `_styleguide.html`: non tradotto (pagina di sviluppo).

---

## 8. Test e verifiche

**Test automatici** — `pyspendless/test/test_task25_0.py`, SQLite in-memory +
Flask test client, come `test_task22_0.py` / `test_task23_0.py`:

- `locale_selector`: i cinque livelli di §4.2, nell'ordine, compreso
  `?lang=xx` non valido che non deve cambiare nulla;
- `PUT /api/user/locale`: 200 sul valore valido, 400 fuori whitelist, 401 senza
  sessione, e **nessuna scrittura su un utente diverso** da quello in sessione;
- persistenza: scrittura → nuovo client (sessione nuova) → login → lingua
  ritrovata;
- resa: `/home` con `en_GB` contiene una stringa inglese attesa e non la sua
  controparte italiana; con `it` è identica a prima;
- `<html lang>` segue la lingua;
- **formati macchina invariati**: l'export CSV ha sempre l'header italiano e le
  date ISO anche con `en_GB` attivo (criterio A6);
- `ps-maintenance.html` rende con `MAINTENANCE_MODE=1` e **zero query** al DB.

**Sonda di coerenza** — `tools/check-i18n.py` (nello spirito di
`tools/check-nav-parity.py`):

- `pybabel extract` e confronto col `.pot` versionato: se differiscono, qualcuno
  ha aggiunto una stringa senza rigenerare;
- elenco delle msgid non tradotte per lingua, con soglia che fa fallire la
  sonda;
- `.mo` presente e non più vecchio del `.po`;
- placeholder coerenti fra msgid e msgstr (un `%(num)d` perso in traduzione è un
  `KeyError` in produzione);
- per i template dichiarati "fatti", nessun testo residuo fuori da `_()`
  (criterio A5).

**Verifica visiva**: `tools/ui-shots.py` sulle pagine principali in `it` e in
`en_GB`, confronto del set `it` con `docs/ui-after/` (criterio A1) e controllo che
in `en_GB` non ci siano troncamenti o layout rotti — l'inglese è più corto
dell'italiano quasi sempre, ma non nelle etichette dei bottoni.

---

## 9. Fuori scope (con motivo)

| Escluso | Perché |
|---|---|
| **`mcp_server.py`**: descrizioni dei tool e risposte a Claude/Alexa | Sono il contratto verso un client LLM, non interfaccia umana; la lingua lì la determina la conversazione, non una preferenza salvata. Richiedono un ragionamento proprio (e in `/mcp-oauth2` la lingua dell'utente sarebbe deducibile dal token, in `/mcp` no). Task separato. |
| **Header del CSV di export** (`Data, Categoria, Wallet, Entrata, Spesa, Note`) | È un **formato di scambio**: l'import li rilegge per nome (`app.py:1983`). Tradurli romperebbe la re-importazione dei file già esportati. Se mai, si tradurranno insieme a un import che accetta entrambi gli insiemi di intestazioni. |
| **Categorie di default** (tabella `CategoryTemplate`, copiate all'onboarding da `repository.py:144`) | Sono **dati**, e dopo la copia diventano dati dell'utente, rinominabili. Tradurle significa decidere cosa fare degli account esistenti. Vale un suo MB/task. |
| **Fuso orario** delle date-ora | Oggi `datetime.utcnow()` viene stampato come ora locale presunta (`repository.py:1166` e simili): è un difetto **preesistente** e indipendente dalla lingua. Flask-Babel offrirebbe un `timezone_selector`: da valutare a parte, per non mescolare un bugfix a un refactoring di 900 stringhe. |
| **`_styleguide.html`** | Pagina di sviluppo, non instradata per gli utenti. |
| **Messaggi di log** | Non sono interfaccia. Restano in italiano. |

---

## 10. Punti aperti e punti chiusi

### Chiusi il 2026-10-19

| # | Decisione |
|---|---|
| **P2** | L'inglese è **`en_GB`**, non `en`: date `19/10/2026`, importi `1,234.56`, valuta `€1,234.56`. Le date restano nell'ordine a cui gli utenti attuali sono abituati. Conseguenze tecniche in §5.7. |
| **P3** | I due JSON di localizzazione di DataTables si **self-hostano** in `static/js/i18n/` (§5.4). |
| **P1** | Promosso da punto aperto a **gate bloccante**: prima di scrivere una riga di codice va verificato sul server PythonAnywhere che `Flask-Babel` e `Babel` si possano installare, e che ci stiano nella quota disco dell'account gratuito. È la **Fase 0** del piano (`fasi/fase-0.md`): se il gate è rosso si passa al piano B di §3 (D1), e il resto del piano non cambia di una virgola. |

### Ancora aperti

| # | Punto |
|---|---|
| P4 | Il selettore in testata su **tutte** le pagine, o solo in quelle non autenticate (dove il profilo non è raggiungibile)? Due controlli nuovi accanto al tema affollano la barra su mobile. Da decidere alla Fase 2, guardando la testata a 375 px. |
| P5 | Granularità dei commit: un commit per fase (10 commit grossi) o uno per pagina (22 commit piccoli)? Il task19-0 ha usato le fasi, con successo. **Qui le fasi sono vincolate**: vedi `piano-localizzazione.md` §6, i worktree dei subagent vedono solo file committati. |
| P6 | Serve un catalogo `it` esplicito (oggi non necessario, D3) per poter correggere la copy italiana senza toccare il codice? Rimandabile. |
| P7 | Glossario terminologico `it → en_GB`: la bozza è in `piano-localizzazione.md` §8. Va confermata **prima** della Fase 9, perché una volta tradotte 900 stringhe cambiare "transaction" in "movement" è un trova-e-sostituisci su un catalogo, ma su 900 stringhe gli errori ci scappano. |

## 11. Fasi

Dieci fasi, ciascuna con un checkpoint verificabile e **l'app funzionante alla
fine di ognuna** — lo schema che ha funzionato nel task19-0. Il dettaglio di
ciascuna, con i criteri di accettazione e il brief per i subagent, è in
`fasi/fase-N.md`; l'orchestrazione in `piano-localizzazione.md`.

| Fase | Contenuto | Chi | Checkpoint |
|---|---|---|---|
| 0 | **Gate**: installabilità di Flask-Babel/Babel su PythonAnywhere, quota disco, versione di Python del server; inventario esatto delle stringhe | principale + `ps-i18n-audit` | Gate verde (o piano B deciso) + inventario reale |
| 1 | Infrastruttura: dipendenze, `babel.cfg`, `i18n.py`, resolver, `build-i18n.sh`, `check-i18n.py`, `test_task25_0.py`, `lang` dinamico. **Nessuna stringa estratta** | principale | App identica a oggi; catalogo vuoto che compila; gate automatici in piedi |
| 2 | Preferenza utente: `User.locale`, DDL, API, selettore nel profilo e in testata | 1 subagent | La preferenza si salva e si rilegge |
| 3 | Shell e pagine di accesso (8 template) | 4 × `ps-i18n-template` | Navigazione e login traducibili; manutenzione senza DB |
| 4 | Messaggi Python: `flash()` + `jsonify`, conversione delle f-string | 6 × `ps-i18n-python` | Nessuna f-string in un messaggio utente |
| 5 | Movimenti (3 template) + DataTables self-hostato | 3 × `ps-i18n-template` + principale | Il percorso principale è traducibile |
| 6 | Dashboard e report (3 template); mesi dal CLDR | 3 × `ps-i18n-template` | Nomi dei mesi da un'unica fonte |
| 7 | Impostazioni e ricorrenti (7 template, ~220 stringhe) | 7 × `ps-i18n-template` | Tutte le pagine coperte |
| 8 | Date, numeri, valuta con Babel; report PDF | 1 subagent | Formati localizzati in vista, macchina invariati (A6) |
| 9 | Traduzione `en_GB`, QA incrociato, documentazione | `ps-i18n-translate` + principale | `check-i18n.py` verde, 0 msgid non tradotte |

## 12. Impatto su rilascio e documentazione

La procedura di rilascio di CLAUDE.md acquista due passi:

- **passo 0-bis**: `./tools/build-i18n.sh` e verifica che i `.mo` siano
  aggiornati e **staged** (accanto a `./tools/build-css.sh`);
- **nel passo 5** (manuale sul server, una volta sola al primo deploy del
  task): `pip install -r requirements.txt` nel virtualenv **prima** del Reload.

La sezione "CSS: il passo che si dimentica" guadagna una gemella sui cataloghi.
Il bump di `_APP_VERSION` è anche quello che invalida la cache dei
`?v={{ app_version }}` sui file statici: se la Fase 5 self-hosta i JSON di
DataTables (P3), ne beneficiano anche quelli.
