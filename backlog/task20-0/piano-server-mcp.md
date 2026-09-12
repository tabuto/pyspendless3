# Task 20-0 — Server MCP integrato nella webapp (aggiunta spesa vocale da Claude)

**Stato**: piano approvato nelle decisioni di progetto (D1-D11 chiuse il 2026-09-12) — **nessun file
del repo ancora modificato**, nessun `git add`/`commit`
**Data**: 2026-09-12 (rev. 2 — incorpora le decisioni dell'utente)
**Versione app analizzata**: `_APP_VERSION = "0.1.8"` (`pyspendless/app.py:32`)
**Obiettivo**: esporre un server MCP dentro la stessa app WSGI Flask, con un **tool di scrittura**
(`add_movement`) e uno **di lettura** (`list_categories`), autenticati con token personali
dell'utente, così che da Claude mobile si possa dire "ho speso 23 euro di spesa al supermercato" e il
movimento finisca nel DB di PySpendless.

---

## 0. Sintesi esecutiva

| Voce | Decisione proposta |
|---|---|
| Framework | Flask 3 (WSGI puro), tutte le rotte in `pyspendless/app.py` — nessun blueprint oggi |
| Trasporto MCP | **Streamable HTTP stateless**: un solo endpoint `POST /mcp`, risposta `application/json`, nessun SSE, nessuna sessione |
| Metodi implementati | `initialize`, `notifications/initialized`, `tools/list`, `tools/call` (+ `ping`) |
| Tool esposti | **due**: `add_movement` (scrittura) e `list_categories` (lettura) — D2 |
| Auth | `Authorization: Bearer <segreto>`, **fallback `x-api-token` / `x-api-key` / `x-auth-token`**; segreto **hashato SHA-256** nella tabella `Token` esistente con `type='MCP'` — D1, D3 |
| Errori di auth | **200 con `isError: true`, mai 401 né `WWW-Authenticate`** (innescherebbero OAuth lato client) — vedi §3.bis |
| Anti-duplicazione | confronto dell'hash `importo-categoria-descrizione` con l'**ultimo** movimento inserito dall'utente; bypass esplicito con `force: true` — D7 |
| **Prerequisito bloccante** | **Il sistema di "custom auth token nel profilo utente" NON esiste ancora nel repo** → va costruito (Fase 0, dentro questo task — D11) |
| Nuovi file Python | `pyspendless/mcp_server.py` (logica MCP), registrato in `app.py` |
| Nuove tabelle | **Nessuna** — si riusa `Token` (`models.py:205`) |
| Impatto deploy | **Nullo** sul workflow: nessuna nuova dipendenza, nessun file WSGI da toccare |
| Test | solo locali (`dev_mcp_check.py`); **nessun end-to-end con Claude prima del tag** — D10 |
| Fasi | 0 → 7, ciascuna con checkpoint verificabile |
| Fuori scope (task futuri) | rate limiting sull'endpoint (D9) |
| Da registrare | riga in `backlog/features.md` |

---

## 0.1 Finding critico — il sistema di auth token non esiste

La consegna dava per esistente un "sistema di custom auth token già presente nel profilo utente,
da riutilizzare così com'è". **Nel repo non c'è.** Verifiche fatte:

- Nessuna pagina/rotta di profilo utente: le uniche `/settings/*` sono `categories`, `wallets`,
  `group`, `import-export`, `admin` (`pyspendless/app.py:1158-1219`).
- Nessun `api_token` / `auth_token` / `X-API-Key` / header `Authorization` in tutto il codice
  applicativo (grep su `pyspendless/**`, esclusa `.venv`): unico risultato è l'API token di
  PythonAnywhere usato dal deploy (`backlog/task18-0.md:100`), che è un'altra cosa.
- L'unico modello token è `Token` (`pyspendless/models.py:205-218`), usato **solo** per gli inviti /
  link di condivisione (`type='SHARE'`, `pyspendless/app.py:1866-2113`).
- Tutta l'autenticazione applicativa passa da Google OAuth + cookie di sessione Flask
  (`session['user_id']`, `session['account_id']` — `pyspendless/app.py:141-291`).

**Conseguenza**: la Fase 0 non è opzionale. La buona notizia è che il modello `Token` e
`TokenRepository` sono già abbastanza generici da ospitare un token personale **senza modifiche allo
schema DB** (vedi Fase 0), quindi lo spirito della richiesta ("non creare un sistema di auth nuovo")
resta rispettato: si estende quello esistente, non se ne inventa un secondo.

---

## 1. Inventario del progetto (ciò che il piano assume)

### 1.1 Framework e struttura

| Aspetto | Realtà nel repo |
|---|---|
| Framework | Flask (`pyspendless/app.py:6,34`), WSGI classico — compatibile con PythonAnywhere |
| Organizzazione rotte | **monolite**: ~60 rotte tutte in `pyspendless/app.py`, nessun Blueprint |
| Dipendenze | `pyspendless/requirements.txt`: Flask, SQLAlchemy, Authlib, python-dotenv, marshmallow, alembic, requests, fpdf2, matplotlib — **nessun SDK MCP** (e non serve) |
| Accesso dati | `pyspendless/repository.py`, classi `*Repository` su sessione SQLAlchemy da `conf.get_db_session()` |
| Config | `pyspendless/conf.py`, variabili da `.env` (non versionato) |
| Logging | `logging.basicConfig(level=DEBUG)` + `logger` modulo (`app.py:22-27`) |
| Versione | `_APP_VERSION` in `app.py:32`, esposta da `GET /version` |

### 1.2 Convenzioni delle API esistenti (da imitare)

Dal blocco `@app.route("/api/...")` di `app.py`:

- Prefisso `/api/`, `methods=['GET'|'POST'|'PUT'|'DELETE']`, risposta `jsonify(...)`.
- Auth: controllo inline, non un decoratore:
  ```python
  if not session.get('user_id'):
      return jsonify({'error': 'Non autenticato'}), 401
  ```
- Scoping multi-tenant: `account_id = session.get('account_id')` e verifica esplicita che
  categoria/wallet appartengano all'account (`app.py:812-814`) → **403** altrimenti.
- Pattern risorse: `db = get_db_session()` → `try: ... finally: db.close()`.
- Errori: `try/except ValueError → 400`, `except Exception → 500` con `logger.error` +
  `logger.debug(traceback.format_exc())`.
- Successo scrittura: `{'success': True, 'message': '...', 'movement_id': ...}` con `201`.
- Unico decoratore esistente: `admin_required` (`app.py:59-68`).
- **Nessuna protezione CSRF** (niente Flask-WTF) → un endpoint `POST /mcp` senza cookie non
  introduce regressioni di CSRF.

### 1.3 Modello dati delle spese

`Movement` (`pyspendless/models.py:114-143`) — schema ibrido legacy + FK:

| Campo | Tipo | Note |
|---|---|---|
| `id` | Text PK | UUID4 generato applicativamente (`app.py:856`) |
| `move_date` | Date | obbligatorio |
| `move_year`, `move_month` | Integer | **denormalizzati**, calcolati da `move_date` (`app.py:820-822`) |
| `category` | Text | **legacy**: nome categoria come stringa |
| `wallet` | Text | **legacy**: `wallet.code` come stringa |
| `income` / `expense` | Numeric(10,2) | nullable; almeno uno valorizzato |
| `note` | Text | nullable |
| `user` | Text | **legacy**: email utente |
| `account_id` | FK `Account.id` | obbligatorio — chiave del multi-tenant |
| `user_id`, `category_id`, `wallet_id` | FK nullable | campi nuovi |
| `recurrent_movement_id` | FK nullable | da task17-0 |

Entità collegate:

- `Category` (`models.py:83-101`): `id`, `name`, `account_id`, `type ∈ {expense, income, transfer}`,
  `order_index`. **Le categorie sono per-account**, non globali.
- `Wallet` (`models.py:49-63`): `id`, `code` (unique globale), `name`, `currency` (default `EUR`),
  `account_id`, `order_index`.
- `User` (`models.py:31-46`): `id`, `email`, `name`, `account_id`, `role`.
- Condivisione famiglia: `UserGroup` / `GroupMembership` (`models.py:146-182`); in pratica la
  condivisione avviene assegnando allo stesso `account_id` più utenti (`app.py:235-251`).

**Riferimento comportamentale**: `POST /api/movements` (`app.py:762-878`) — è la logica che il tool
MCP deve replicare, incluse le conversioni legacy `category.name` / `wallet.code` / `user.email`.

### 1.4 Token esistenti

`Token` (`models.py:205-218`) / `sql/sqllite/create_token.sql`:

- `uuid` TEXT PK, `type` TEXT (**nessun CHECK constraint** → si può aggiungere `'MCP'` liberamente),
  `create_date`, `expire_date` NOT NULL, `status ∈ {PENDING, USED, EXPIRED}` (**questo sì** ha un
  CHECK), `payload` TEXT (JSON).
- Indici già presenti su `status`, `expire_date`, `type`.
- `TokenRepository` (`repository.py:873-1015`): `create_token(type, payload, expire_days)`,
  `get_token`, `validate_token` (esiste + `PENDING` + non scaduto, altrimenti auto-`EXPIRED`),
  `get_payload`, `mark_as_used`, `mark_as_expired`, `delete_token`,
  `get_pending_invites_for_account`.

**Mappatura semantica proposta per i token MCP** (zero modifiche a schema e repository):

| Concetto MCP | Campo `Token` |
|---|---|
| token attivo | `status = 'PENDING'` |
| token revocato | `status = 'USED'` (via `mark_as_used`) oppure record eliminato (`delete_token`) |
| tipo | `type = 'MCP'` |
| segreto | **SHA-256 esadecimale** del segreto mostrato all'utente, salvato nella colonna `uuid` (D3) |
| identità | `payload = {"user_id":…, "account_id":…, "label":…, "prefix":…}` |
| scadenza | `expire_date` = creazione + **365 giorni** (D4) |

Il segreto vero e proprio (un UUID4, 122 bit di entropia) **non viene mai salvato**: esiste solo nella
risposta HTTP che lo mostra una volta sola. In DB resta il suo hash, quindi una copia del file `.db`
non contiene credenziali utilizzabili. `payload['prefix']` conserva i primi 8 caratteri del segreto,
in chiaro, al solo scopo di far riconoscere il token nell'elenco e nei log.

---

## Fase 0 — Token personali nel profilo utente (**prerequisito**)

### Cosa va fatto

1. **Repository**: aggiungere in `TokenRepository` tre soli metodi di supporto (il resto è già
   riusabile così com'è):
   - `create_mcp_token(user_id, account_id, label, expire_days=365) -> (Token, secret)` — genera il
     segreto `uuid4()`, ne calcola lo SHA-256 e lo passa a `create_token('MCP', payload, 365)` come
     chiave; **restituisce il segreto in chiaro al chiamante una sola volta** (D3, D4).
   - `validate_mcp_secret(secret) -> Optional[Token]` — `validate_token(sha256(secret))` con verifica
     aggiuntiva `type == 'MCP'`. Il confronto sul valore letto va fatto con `hmac.compare_digest`.
   - `get_mcp_tokens_for_user(user_id) -> List[dict]` — filtro `type='MCP'` + `status='PENDING'`,
     poi match su `payload['user_id']` (stesso pattern di `get_pending_invites_for_account`,
     `repository.py:974-1005`).

   Nota: poiché la colonna `uuid` è la PK e contiene l'hash, il lookup resta una singola query su
   indice primario — nessun costo rispetto alla variante in chiaro.
2. **Pagina profilo**: nuova rotta `GET /settings/profile` in `app.py` (stesso stile di
   `settings_wallets`, `app.py:1167-1173`) + template `pyspendless/templates/ps-setting-profile.html`
   che estende `ps-nav.html`.
3. **API di gestione** (stile identico alle API esistenti):
   - `POST /api/mcp-tokens` → crea, e **restituisce il segreto in chiaro una sola volta** (dopo di
     che è irrecuperabile: in DB c'è solo l'hash).
   - `GET /api/mcp-tokens` → elenco (label, data creazione, scadenza, **mai il segreto**:
     si mostra `payload['prefix']` + `…`).
   - `DELETE /api/mcp-tokens/<token_hash>` → revoca (`mark_as_used`), previa verifica che il
     `payload['user_id']` coincida con `session['user_id']` (stesso controllo di
     `delete_pending_invite`, `app.py:1986-1996`). L'identificatore in URL è l'hash, non il segreto.
4. **Voce di menu**: link "Profilo" nel submenu impostazioni di
   `pyspendless/templates/ps-nav.html:116-145`.
5. **Testo della UI**: la pagina deve dire esplicitamente che (a) il segreto è mostrato una sola
   volta, (b) il token vale 365 giorni, (c) chi lo possiede può **scrivere movimenti sull'account di
   famiglia**, (d) per cambiarlo va rimosso e riaggiunto anche il connettore lato Claude.

### File coinvolti

- `pyspendless/repository.py` (classe `TokenRepository`, dopo la riga 1005)
- `pyspendless/app.py` (nuova sezione rotte, vicino a `# ===== INVITE & TOKEN ENDPOINTS =====`, riga 1864)
- `pyspendless/templates/ps-setting-profile.html` (**nuovo**)
- `pyspendless/templates/ps-nav.html` (una voce di menu)

### Rischi residui

- Un token porta con sé `account_id` → chi lo possiede può scrivere sull'account di famiglia. È il
  comportamento voluto, ma va detto esplicitamente nella UI (punto 5).
- Con l'hashing (D3) il segreto perso è **irrecuperabile**: l'unica strada è revocare e rigenerare,
  il che impone di rifare anche il connettore lato Claude (che non consente di modificare le
  impostazioni di auth dopo la creazione).
- Alla scadenza dei 365 giorni (D4) il connettore smette di funzionare **senza preavviso**: Claude
  riceverà un 401 e l'utente vedrà solo un errore generico. Vale la pena mostrare la data di
  scadenza nell'elenco della pagina profilo.

---

## Fase 1 — Schema del tool e formato input/output

### Cosa va fatto

Definire il contratto del tool, che è ciò che Claude "vede" e su cui basa l'interpretazione del
parlato. Proposta:

**Nome**: `add_movement` (non `add_expense`: il modello `Movement` copre anche le entrate).

**`inputSchema`** (JSON Schema draft 2020-12):

| Campo | Tipo | Obbl. | Semantica |
|---|---|---|---|
| `amount` | number > 0 | sì | importo sempre **positivo**; il segno lo determina `kind` |
| `kind` | enum `expense` \| `income` | no (default `expense`) | mappa su colonna `expense`/`income` |
| `category` | string | sì | **nome** categoria; risoluzione fuzzy lato server |
| `wallet` | string | no | nome o `code` del wallet; default = primo per `order_index` |
| `date` | string `YYYY-MM-DD` | no (default: oggi in `Europe/Rome`) | il client **deve** inviarla esplicita (D5) |
| `note` | string | no | testo libero (es. la frase originale) |
| `force` | boolean | no (default `false`) | bypassa il controllo anti-duplicato (D7) |

**Risoluzione dei nomi** (server-side, `account_id` dal token):
1. match esatto case-insensitive su `Category.name` filtrando `type = kind`;
2. match normalizzato (trim, lowercase, accenti rimossi);
3. match per sottostringa **se unico**;
4. altrimenti → errore di tool con l'elenco delle categorie disponibili, così Claude può richiedere
   conferma all'utente invece di indovinare.

Le categorie con `type = 'transfer'` sono **escluse a monte** da ogni ricerca e da `list_categories`
(D6): non sono raggiungibili dal tool e non compaiono negli elenchi di errore. Di conseguenza `kind`
resta un enum a due valori.

**Secondo tool — `list_categories`** (sola lettura, D2): nessun parametro obbligatorio, parametro
opzionale `kind` per filtrare. Restituisce nome e tipo delle categorie dell'account più l'elenco dei
wallet (nome, `code`, valuta, quale è il default). Serve a Claude per non indovinare la categoria al
primo tentativo — senza, l'unico modo di scoprire la tassonomia è sbagliare una chiamata di
scrittura. `annotations`: `readOnlyHint: true`, `openWorldHint: false`.

**Output**: `content: [{type: "text", text: "Registrata spesa di 23,00 € — Supermercato / Conto principale — 12/09/2026"}]`
più `structuredContent` con `movement_id`, `move_date`, `category`, `wallet`, `amount`, `kind`.
Frase di conferma in italiano e formattata come l'app, così l'utente la sente/legge e può correggere.

**`annotations`**: `readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: false`,
`openWorldHint: false`. La `description` del tool va scritta con cura (è prompt a tutti gli effetti):
deve dire che gli importi sono in EUR, che le categorie sono quelle dell'account, e che in caso di
ambiguità va chiesta conferma.

### 1.bis — Gestione della data (D5)

> **Confermato dall'utente il 2026-09-12**: il campo `date` **resta nel contratto del tool** (il
> client lo valorizza con la data locale dell'utente, ed è ciò che permette di registrare "la spesa
> di ieri"); se il campo **manca**, il server assume *oggi* calcolato con ora locale `Europe/Rome`,
> non UTC.

Conseguenze implementative:

- La `description` del tool dichiara che `date` va sempre valorizzata con la data locale dell'utente
  in formato `YYYY-MM-DD`.
- Se `date` è assente: `datetime.now(ZoneInfo("Europe/Rome")).date()`. `zoneinfo` è in stdlib da
  Python 3.9 (la versione del venv del repo), quindi **nessuna dipendenza nuova**; se il sistema PA
  non avesse il database tzdata si ricade su UTC+1/+2 calcolato a mano — da verificare in Fase 5.
- Il resto del codice continua a usare `datetime.utcnow()` come già fa ovunque: la scelta riguarda
  **solo** il default di `move_date`, non i timestamp di audit.
- `move_year` / `move_month` restano derivati da `move_date`, come in `app.py:820-822`.

### 1.ter — Anti-duplicazione (D7)

Versione semplificata richiesta: **si confronta solo con l'ultimo movimento inserito dall'utente**,
non con una finestra temporale.

**Fingerprint**: `sha256("{importo}|{category_id}|{note_normalizzata}")` dove

- `importo` = `Decimal` quantizzato a 2 decimali, con il segno determinato da `kind` (così una spesa
  di 23,00 e un'entrata di 23,00 non collidono);
- `category_id` = id risolto (non il nome grezzo passato dal client, altrimenti "spesa" e "Spesa"
  darebbero hash diversi);
- `note_normalizzata` = `note` con `strip()`, lowercase e spazi interni collassati; stringa vuota se
  `note` è assente o `None`.

**Confronto**: si legge l'**ultimo** `Movement` dell'utente corrente (`user_id` dal token, filtrato
per `account_id`) e si ricalcola su di esso lo stesso fingerprint. Se coincide e `force` è `false` →
il movimento **non** viene inserito.

**Nodo tecnico da risolvere in implementazione**: `Movement` (`models.py:114-143`) **non ha una
colonna di data/ora di inserimento** — `move_date` è la data *della spesa*, non della scrittura, e la
PK è un UUID testuale, quindi non è ordinabile cronologicamente. Le opzioni per identificare
"l'ultimo inserito":

1. `ORDER BY rowid DESC LIMIT 1` — SQLite assegna un `rowid` implicito crescente anche con PK TEXT.
   Zero modifiche allo schema. Limite: il `rowid` può essere riusato dopo cancellazioni, ed è
   SQLite-specifico (non sopravvivrebbe a un'eventuale migrazione a Postgres).
2. Aggiungere `created_at` a `Movement` — soluzione corretta, ma comporta un `ALTER TABLE` in
   `sql/sqllite/NEXT_RELEASE/` e un passo manuale sul server PA, cioè **rompe la premessa "nessun
   cambio di schema"** di questo task.

**Scelta confermata: opzione 1** (`ORDER BY rowid DESC`), con il caveat documentato. È coerente con
la richiesta di una verifica "semplificata" e non tocca lo schema.

**Cosa viene restituito al client quando scatta il blocco**: risposta di **successo HTTP**, con
`isError: true` e un testo in italiano esplicito, del tipo:

> «Non ho registrato nulla: sembra identico all'ultimo movimento inserito (23,00 € — Supermercato —
> "spesa settimanale", del 12/09/2026). Se è davvero una seconda spesa, richiamami con `force: true`.»

più `structuredContent: {duplicate: true, existing_movement_id: "…", existing: {...}}`. In questo modo
Claude può chiedere conferma a voce all'utente e ripetere la chiamata con `force: true`, invece di
fallire in modo opaco o inserire due volte.

**Casi limite e limiti accettati**:

| Caso | Comportamento |
|---|---|
| Due spese legittimamente identiche e ravvicinate (due caffè da 1,20 €) | **Bloccate al secondo tentativo**; si sbloccano con `force: true`. È il costo consapevole della semplificazione |
| Sequenza A → B → A | Il secondo A **non** viene bloccato (si confronta solo con l'ultimo) — falso negativo accettato |
| Nessun movimento precedente per l'utente | Nessun controllo, si inserisce |
| Ultimo movimento inserito dalla UI web pochi secondi prima | Viene comunque confrontato: è desiderato (protegge anche dal doppio inserimento misto app/voce) |
| Importi uguali ma categorie o note diverse | Nessun blocco |
| `date` diversa, tutto il resto uguale | **Bloccato**: la data non entra nel fingerprint (come richiesto: importo-categoria-descrizione). Se si volesse distinguere, basta aggiungere `move_date` all'hash — modifica di una riga, da valutare in implementazione |
| Retry di Claude dopo timeout di rete | Il secondo tentativo viene bloccato → **è esattamente il caso che si vuole coprire** |

Il controllo vive **solo** nel percorso MCP: `POST /api/movements` (`app.py:762`) e la UI web non
cambiano comportamento.

### File coinvolti

- `pyspendless/mcp_server.py` (**nuovo**) — `TOOL_DEFINITIONS` (2 tool), `_resolve_category()`,
  `_resolve_wallet()`, `_resolve_date()`, `_movement_fingerprint()`, `_tool_add_movement()`,
  `_tool_list_categories()`.
- `pyspendless/repository.py` — un metodo nuovo in `MovementRepository`:
  `get_last_inserted_for_user(user_id, account_id) -> Optional[Movement]` (la query `ORDER BY rowid
  DESC LIMIT 1` va isolata lì, non sparsa nel modulo MCP).
- Riuso in lettura: `CategoryRepository.get_categories_for_account` (`repository.py:390`),
  `WalletRepository.get_wallets_for_account` (`repository.py:333`),
  `MovementRepository.create_movement` (`repository.py:621`).

---

## Fase 2 — Endpoint `/mcp` e routing dei tre metodi JSON-RPC

### Cosa va fatto

1. **Rotta unica** `@app.route("/mcp", methods=['POST'])` in `app.py`, che delega tutta la logica a
   `mcp_server.handle_request(...)`. La rotta resta di 10-15 righe, in linea con lo stile del file.
2. **Dispatch JSON-RPC 2.0**:
   - `initialize` → `{protocolVersion, capabilities: {tools: {}}, serverInfo: {name: "pyspendless", version: _APP_VERSION}}`.
     Fare eco della `protocolVersion` richiesta se supportata, altrimenti rispondere con la propria.
   - `notifications/initialized` (notifica: **senza `id`**) → HTTP **202** con body vuoto.
   - `tools/list` → `{tools: [...]}` da `TOOL_DEFINITIONS` (**due** tool: `add_movement` e
     `list_categories`, D2).
   - `tools/call` → esecuzione + `{content: [...], structuredContent: {...}, isError: false}`.
   - `ping` → `{}` (una riga, evita fallimenti di health-check del client).
   - qualsiasi altro metodo → errore JSON-RPC `-32601`.
3. **Stateless**: nessun `Mcp-Session-Id` emesso, nessuno stato tra richieste. È legittimo e
   sufficiente per un tool di scrittura; evita del tutto il problema che PythonAnywhere non ha ASGI
   né worker long-lived.
4. **Metodi non-POST**: `GET /mcp` (stream SSE server→client) e `DELETE /mcp` (chiusura sessione)
   devono rispondere **405** in modo pulito, non 500 e non la pagina HTML di errore di Flask.
5. **Header**: rispondere `Content-Type: application/json`. Accettare la richiesta anche quando il
   client manda `Accept: application/json, text/event-stream` (è il caso di Claude).
6. **Modalità manutenzione**: `check_maintenance_mode` (`app.py:81-108`) intercetta *ogni* richiesta e
   restituisce HTML 503 → va aggiunto `/mcp` alla lista di esclusione, oppure gestito restituendo un
   errore JSON-RPC. *Proposta: non escluderlo (in manutenzione è giusto rifiutare) ma restituire JSON,
   non HTML.*

### File coinvolti

- `pyspendless/mcp_server.py` (**nuovo**) — dispatcher, costruzione risposte, costanti di protocollo.
- `pyspendless/app.py` — import in cima (riga 9-14, mantenendo il doppio `try/except` relativo/assoluto),
  rotta `/mcp` in una nuova sezione `# ===== MCP SERVER =====`, ritocco a `check_maintenance_mode`.

### Rischi / note

- **Path**: `/mcp` (D8). La sicurezza la fa il token, non l'oscurità del path.
- **Versione di protocollo**: la stringa `protocolVersion` esatta da dichiarare va verificata sulla
  spec MCP **al momento dell'implementazione** (cambia con le revisioni della spec); il codice deve
  accettare una lista di versioni note e non fallire su una sconosciuta.
- **PythonAnywhere**: il dominio `tabuto.pythonanywhere.com` serve già HTTPS valido → requisito
  "MCP server URL deve essere HTTPS" soddisfatto senza lavoro aggiuntivo.
- **Timeout**: la webapp PA su piano free va in sleep e la prima richiesta può essere lenta. Claude ha
  timeout stretti sulle chiamate. *Mitigazione: tenere `tools/call` sotto il secondo (è una singola
  INSERT SQLite) e non fare lavoro pesante in `initialize`.*

---

## Fase 3 — Validazione del custom auth token

### Cosa va fatto

1. **Estrazione** (D1), in quest'ordine:
   1. `Authorization: Bearer <segreto>` — modalità primaria; il parsing tollera spazi multipli ed è
      case-insensitive sullo schema (`bearer`/`Bearer`);
   2. **fallback**, nell'ordine: `x-api-token`, `x-api-key`, `x-auth-token` — valore **nudo**, senza
      prefisso `Bearer`.
   Se sono presenti più header vince `Authorization`. Nessun token in query string (è esplicitamente
   sconsigliato e vietato dalla spec di autorizzazione MCP: le URL finiscono nei log, nei proxy e
   nella cronologia). Supportare quattro nomi costa poche righe ed evita di restare bloccati se nella
   UI dei connettori il nome header desiderato non fosse selezionabile: la scelta si fa lato Claude,
   senza toccare il server.
2. **Validazione**: `TokenRepository.validate_mcp_secret(secret)` → calcola SHA-256 del segreto
   presentato, cerca la PK corrispondente e verifica `type='MCP'`, `status='PENDING'`, non scaduto
   (D3). Confronto finale con `hmac.compare_digest` per evitare timing attack.
3. **Contesto**: da `get_payload()` si ricavano `user_id` e `account_id`, che **sostituiscono**
   `session['user_id']` / `session['account_id']` nella logica di scrittura. Il resto dei controlli di
   appartenenza (categoria e wallet dello stesso `account_id`, `app.py:812-814`) resta identico.
4. **Fallimento**: HTTP **200** con un errore di *tool* (`isError: true`) e un testo in italiano che
   spiega come configurare il token. **Mai 401, mai `WWW-Authenticate`** — vedi §3.bis: sono il
   segnale che avvia il flusso OAuth lato client.
5. **Decoratore** `@mcp_token_required` in `mcp_server.py`, per non spargere la logica nelle rotte
   (stesso pattern di `admin_required`, `app.py:59-68`).
6. **Nessun cookie di sessione** viene letto o scritto su `/mcp`: il flusso è completamente
   indipendente dal login browser.

### 3.bis — Perché il fallimento di autenticazione NON è un 401 (correzione del 2026-09-12)

**Sintomo.** Al primo tentativo di collegare il connettore, Claude rispondeva:
*«Impossibile registrarsi con il servizio di accesso di mcp-pyspendless. Puoi riprovare oppure
aggiungere un OAuth Client ID nelle impostazioni del connettore.»*

**Causa.** La prima stesura restituiva `401` + `WWW-Authenticate: Bearer` quando il token mancava.
Nella specifica MCP quello **è** il segnale di lazy authentication: un 401 a livello di trasporto fa
sospendere la chiamata al client, che cerca i metadata di discovery e avvia OAuth. La documentazione
Anthropic è esplicita: *«Only a transport-level 401 causes Claude to pause the call, run the OAuth
flow, and retry»*, mentre un 200 con `isError: true` *«Claude passes the error text to the model as
the tool result and moves on — there is no auth prompt»*.

Era quindi implementato il protocollo di challenge OAuth su un server che OAuth non ha. La catena
completa osservata in produzione:

1. `tools/call` senza token → `401` + `WWW-Authenticate: Bearer`;
2. l'header non porta il parametro `resource_metadata`, quindi Claude sonda i well-known
   sull'origine: `/.well-known/oauth-protected-resource/mcp` e varianti → 404 HTML di Flask;
3. senza metadata, il client assume che l'authorization server sia l'origine stessa e tenta la
   **Dynamic Client Registration** su `POST /register` → 404;
4. errore mostrato all'utente.

Verificato in analisi che il resto dell'ipotesi *non* era in causa: l'app **non** ha rotte catch-all
(`<path:...>` non compare), l'unico `before_request` è `check_maintenance_mode`, e i path di
discovery non producevano alcun redirect verso il login Google — solo un 404.

**Correzione applicata.**

- L'endpoint `/mcp` non emette più **né 401 né `WWW-Authenticate`**, in nessun caso.
- Token assente, errato, revocato o scaduto → risposta **200** con `isError: true`,
  `structuredContent: {"auth_error": true}` e il testo di `AUTH_ERROR_TEXT`, che spiega all'utente
  come generare il token dal profilo e come configurarlo nel connettore.
- Rotte difensive per `/.well-known/oauth-protected-resource`,
  `/.well-known/oauth-authorization-server`, `/.well-known/openid-configuration` (e le varianti con
  path suffisso): rispondono **404 in JSON**, escluse dalla modalità manutenzione, così non possono
  mai degenerare in HTML o in un redirect che suggerisca l'esistenza di un authorization server.

**Conseguenza operativa**: le impostazioni di autenticazione di un connettore non sono modificabili
dopo la creazione → il connettore va **rimosso e riaggiunto**. Inoltre Claude tiene in cache i
documenti di discovery **globalmente per URL, per circa 5 minuti**: conviene attendere qualche minuto
fra un tentativo e il successivo.

**Se un domani servisse davvero OAuth** (scenario D1 sfavorevole), il 401 va reintrodotto *insieme* a
tutta la catena di discovery — PRM, metadata dell'authorization server, `/authorize`, `/token` — mai
da solo.

### File coinvolti

- `pyspendless/mcp_server.py` (**nuovo**)
- `pyspendless/repository.py` (`validate_mcp_secret` per il lookup su hash)
- `pyspendless/app.py` (rotte `.well-known` di discovery → 404 JSON)

### Rischi residui

- **Il rischio principale del progetto resta la configurazione lato Claude, non il codice.** I bearer
  token statici sui connettori custom passano dalla sezione **Request headers**, che è **in beta e
  disponibile solo a una parte degli account**: nella UI può semplicemente non comparire. Le modalità
  supportate ovunque sono OAuth (DCR o Client ID Metadata Document) oppure nessuna auth.
  Il piano supporta bearer + header alternativo (D1) proprio per coprire le varianti a costo quasi
  nullo, ma **se la sezione Request headers non è disponibile affatto**, nessuna delle due strade
  funziona e l'unica alternativa è un OAuth 2.0 minimale lato Flask (metadata `.well-known`,
  authorize, token, PKCE): 300-500 righe, cioè un task autonomo. **Verifica da fare per prima cosa**,
  aprendo il dialog "Add custom connector" — prima di scrivere la Fase 3.
- **Rate limiting: fuori scope (D9)**, sarà oggetto di un task dedicato. Va messo agli atti che nel
  frattempo `/mcp` è un endpoint pubblico non limitato: con 122 bit di entropia il brute-force sul
  token è irrilevante, ma nulla impedisce a un terzo di generare traffico verso l'endpoint e
  consumare le CPU-seconds del piano PythonAnywhere. Mitigazione a costo zero nel frattempo:
  rispondere ai 401 senza toccare il DB più dello stretto necessario (una sola query su PK).

---

## Fase 4 — Gestione errori e logging

### Cosa va fatto

1. **Due livelli di errore, da non confondere**:
   - **Errori di protocollo** → oggetto JSON-RPC `error`: `-32700` parse error, `-32600` invalid
     request, `-32601` method not found, `-32602` invalid params.
   - **Errori applicativi del tool** (categoria inesistente, importo ≤ 0, data non parsabile) →
     risposta **di successo** con `isError: true` e un `content` testuale in italiano, così Claude
     può spiegarlo all'utente e riprovare. Questo è il caso più frequente e va curato.
2. **Errori inattesi**: `try/except Exception` attorno all'esecuzione del tool → `isError: true` con
   messaggio generico, **mai** lo stack trace nel body (finirebbe nel contesto del modello).
   `logger.error` + `logger.debug(traceback.format_exc())`, come già fa `app.py:875-878`.
3. **Logging**: prefisso `[MCP]` su ogni riga. Loggare metodo, nome tool, `account_id`, esito, durata.
   **Mai** loggare il token: al massimo i primi 8 caratteri dell'uuid come correlatore.
   Nota: `logging.basicConfig(level=DEBUG)` (`app.py:23-26`) è globale — su PythonAnywhere i log
   finiscono nel server log della webapp, e SQLAlchemy in `FLASK_ENV=development` logga tutte le
   query (`conf.py:103`). Verificare che in produzione `FLASK_ENV` non sia `development`.
4. **Rollback**: in caso di eccezione dopo `db.add`, chiudere la sessione nel `finally` come da
   pattern esistente.

### File coinvolti

- `pyspendless/mcp_server.py`
- `pyspendless/app.py` (nessuna modifica al logging globale, salvo verifica `FLASK_ENV`)

---

## Fase 5 — Test locali

### Cosa va fatto

Non esiste una suite di test nel repo (nessuna cartella `tests/`), quindi la proposta è pragmatica e
in linea col progetto: uno **script di verifica manuale** riproducibile, non l'introduzione di pytest
(che sarebbe un task a sé).

> **D10 — nessun test end-to-end con Claude prima del rilascio.** Di conseguenza lo script locale
> diventa l'**unica** rete di sicurezza prima del tag, e va quindi preso più sul serio di quanto
> sarebbe necessario in presenza di una prova end-to-end: la prima volta che un client MCP reale
> parlerà con il server sarà **in produzione**. Due conseguenze pratiche: (a) lo script deve coprire
> anche gli scenari "di protocollo" che normalmente si scoprono solo collegando Claude (header
> `Accept` combinato, notifica senza `id`, `GET`/`DELETE`, versione di protocollo sconosciuta);
> (b) la verifica post-deploy della Fase 7 non è una formalità.

1. **Script** `pyspendless/dev_mcp_check.py` (**nuovo**, sullo stile di `dev_setup.py`) che, contro
   `http://localhost:5000`, esegue in sequenza:
   - `initialize` → verifica `serverInfo.version == _APP_VERSION`;
   - `notifications/initialized` → verifica 202 e body vuoto;
   - `tools/list` → verifica che **entrambi** i tool (`add_movement`, `list_categories`) siano
     presenti e che gli `inputSchema` siano JSON Schema validi;
   - `tools/call` `add_movement` con dati validi → verifica 200, `isError: false`, e che il movimento
     compaia in `GET /api/movements`;
   - `tools/call` `list_categories` → nessuna categoria `transfer` nell'output (D6);
   - `tools/call` con categoria inesistente → `isError: true` + elenco categorie;
   - `tools/call` con categoria `transfer` per nome esatto → `isError: true`, non risolta (D6);
   - **anti-duplicazione (D7)**: stessa chiamata ripetuta → il secondo tentativo restituisce
     `duplicate: true` e **non** crea il movimento; ripetuta con `force: true` → creata;
     cambiando solo la `note` → creata; cambiando solo la `date` → **bloccata** (comportamento atteso,
     la data non è nel fingerprint); dopo un movimento diverso in mezzo (A→B→A) → creata;
   - **data (D5)**: chiamata senza `date` → `move_date` = oggi in `Europe/Rome` (da verificare
     esplicitamente a cavallo di mezzanotte simulando l'ora, o almeno controllando che `zoneinfo`
     risolva `Europe/Rome` senza eccezioni);
   - `tools/call` senza alcun header di auth → **200 con `isError: true`** e
     `structuredContent.auth_error`, **senza** header `WWW-Authenticate` (vedi §3.bis);
   - `tools/call` con `x-api-token` valido → **200** (verifica del fallback, D1);
   - `tools/call` con segreto errato → **200 con `isError`** (e verifica che in DB ci sia solo
     l'hash, D3);
   - `tools/call` con token revocato (`status='USED'`) → **200 con `isError`**;
   - i cinque path `.well-known` di discovery OAuth → **404 con `Content-Type: application/json`**,
     senza redirect (§3.bis);
   - `tools/call` con token di un altro account → il movimento **non** deve finire sull'account sbagliato;
   - `GET /mcp` e `DELETE /mcp` → **405** con body JSON, non HTML;
   - body non-JSON → `-32700`; metodo sconosciuto → `-32601`;
   - `initialize` con `protocolVersion` sconosciuta → risposta valida, non eccezione;
   - richiesta con `MAINTENANCE_MODE=1` → 503 **in JSON**, non la pagina HTML.
2. **Checklist manuale**: creare token dalla pagina profilo, verificare che il segreto sia mostrato
   una sola volta e **mai più** (né in elenco né in DB), che la revoca funzioni, che il token revocato
   sparisca dall'elenco, che sia visibile la data di scadenza a 365 giorni.
3. **Nessun test end-to-end con Claude prima del tag** (D10): la prima verifica con un client reale
   avviene dopo il deploy, seguendo la checklist della Fase 7.

### File coinvolti

- `pyspendless/dev_mcp_check.py` (**nuovo**)
- Nessuna modifica a `requirements.txt` (`requests` è già presente, riga 8)

---

## Fase 6 — Registrazione del connettore su Claude

### Cosa va fatto

1. Su Claude (web o desktop): **Customize → Connectors → Add custom connector**.
2. **Name**: `PySpendless`. **MCP server URL**: `https://tabuto.pythonanywhere.com/mcp`.
3. **Authentication**: `No sign-in`, e il token va sotto **Request headers** (D1):
   - opzione primaria → nome `authorization`, valore `Bearer <token-generato-dal-profilo>`. Il
     prefisso `Bearer ` **con lo spazio** è obbligatorio: Claude invia il valore esattamente come
     inserito, senza aggiungere lo schema.
   - fallback → uno tra `x-api-token`, `x-api-key`, `x-auth-token`, valore = solo il token,
     **senza** prefisso.
   Il server accetta tutte queste forme, quindi la scelta si fa qui senza toccare il codice.
4. **Advanced → Transport**: si imposta da solo in base alla URL; poiché l'URL **non** finisce in
   `/sse`, viene scelto Streamable HTTP — che è ciò che vogliamo. Non toccare.
5. Verifica: in una conversazione, abilitare il connettore dal menu "+", chiedere l'elenco dei tool
   (devono comparirne **due**), provare `list_categories`, poi la frase vocale completa da telefono.
6. Impostare il permesso di `add_movement` su "chiedi conferma" (non "Always allow") almeno nella fase
   iniziale: è un tool di scrittura sul DB di famiglia. `list_categories` può stare su "Always allow".

Poiché non c'è stato alcun test end-to-end prima del rilascio (D10), **questa fase è il primo
contatto reale fra Claude e il server**: va eseguita subito dopo il deploy, con i log della webapp PA
aperti, e con la prima spesa di prova di importo riconoscibile (es. 0,01 €) da cancellare poi
dall'app.

### Rischi / decisioni

- I connettori custom **non sono modificabili** dopo la creazione per quanto riguarda le
  impostazioni di autenticazione: per cambiare il token bisogna rimuovere e riaggiungere il
  connettore. Da tenere presente quando il token scade (D4).
- La configurazione del connettore si fa **da web/desktop**; l'uso dal telefono avviene poi
  normalmente. Da verificare che il connettore risulti attivo anche sull'app mobile.
- **Prompt injection**: le `note` dei movimenti e i nomi delle categorie tornano nelle risposte del
  tool e quindi nel contesto del modello. Con dati propri il rischio è teorico, ma conviene comunque
  troncare i testi restituiti e non restituire mai elenchi enormi.

---

## Fase 7 — Deploy

### Cosa va fatto

Il flusso esistente copre tutto senza modifiche, **a patto** che valgano queste condizioni (tutte
verificate in analisi):

- Nessuna nuova dipendenza Python → nessun `pip install` sul server, nessuno step nuovo in
  `.github/workflows/deploy.yml`.
- Nessuna modifica allo schema DB → nessun file in `sql/sqllite/NEXT_RELEASE/` e nessuna migrazione
  manuale sul server (a differenza, ad es., di `alter_movement_add_recurrent_id.sql`). Le decisioni
  prese lo confermano: l'hashing del token (D3) usa la colonna `uuid` esistente, la durata (D4) sta
  in `expire_date`, e l'anti-duplicazione (D7) si appoggia al `rowid` implicito di SQLite proprio per
  **non** aggiungere un `created_at` a `Movement`.
- **Nessuna nuova variabile in `.env` / `.env_pa`**: con D4 fissa a 365 giorni e D9 fuori scope, non
  resta nulla da configurare. Quindi **nessun passo manuale sul server**, il deploy è interamente
  coperto dal workflow.
- Il file WSGI su PythonAnywhere importa `app` da `pyspendless/app.py`: una rotta in più non richiede
  di toccarlo.

Procedura (da eseguire **solo su richiesta esplicita**, come da `CLAUDE.md`):

1. Bump di `_APP_VERSION` in `pyspendless/app.py:32` → `0.2.0` (feature nuova, non patch).
   **Eseguito il 2026-09-12** su via libera esplicita dell'utente.
2. `git commit` delle modifiche.
3. `git tag v0.2.0`.
4. `git push && git push --tags` → parte la GitHub Action (`deploy.yml`: `git pull` via console PA +
   reload webapp).
5. Verifica post-deploy (**non formale**, vista D10): `GET https://tabuto.pythonanywhere.com/version`
   → `0.2.0`; `GET /mcp` → 405; `POST /mcp` senza auth → 401; `POST /mcp` con `initialize` e token
   valido → 200 con `serverInfo.version = 0.2.0`. Solo dopo si procede con la Fase 6.
6. Piano di rollback: se qualcosa non torna, il ripristino è un `git checkout` del tag precedente
   sulla console PA + reload. Nessun dato da migrare all'indietro, perché non cambia lo schema; gli
   eventuali token già generati restano nel DB inerti (nessuna rotta li legge più).

### Rischi

- **Il workflow dipende da una console PA "già avviata"** (`PA_CONSOLE_ID: 45331030`,
  `deploy.yml:8-13`): se la console è stata chiusa, il deploy fallisce con "not yet started". Da
  controllare **prima** di taggare.
- Il deploy fa `git pull` sulla working copy del server: se lì ci sono modifiche locali non
  committate, il pull fallisce.
- Esporre un endpoint di scrittura pubblico è un cambio di superficie d'attacco: conviene rilasciare
  prima con `MAINTENANCE_MODE` non attivo ma tenendo il connettore non condiviso, e verificare i log
  PA nelle prime ore. Senza rate limiting (D9, rimandato), questo monitoraggio manuale delle prime
  ore è l'unica forma di controllo disponibile.
- **Conseguenza diretta di D10**: un difetto di protocollo che lo script locale non avesse
  intercettato si manifesta solo in produzione, e la correzione richiede un nuovo tag (`v0.2.1`) con
  tutto il giro di deploy. Da mettere in conto uno o due tag di aggiustamento ravvicinati, e da
  preferire quindi una finestra di rilascio in cui si ha tempo di seguirli.

---

## Riepilogo dei file toccati

| File | Tipo | Fase |
|---|---|---|
| `pyspendless/mcp_server.py` | **nuovo** — tutta la logica MCP (dispatcher, auth bearer + `x-api-token`, 2 tool, fingerprint anti-duplicato) | 1, 2, 3, 4 |
| `pyspendless/app.py` | modifica — import, rotta `/mcp`, rotte `/settings/profile` e `/api/mcp-tokens*`, esclusione/JSON in manutenzione, bump versione | 0, 2, 7 |
| `pyspendless/repository.py` | modifica — 3 metodi in `TokenRepository` (dopo riga 1005) + `get_last_inserted_for_user` in `MovementRepository` | 0, 1 |
| `pyspendless/templates/ps-setting-profile.html` | **nuovo** — UI generazione/revoca token | 0 |
| `pyspendless/templates/ps-nav.html` | modifica — voce di menu (righe 116-145) | 0 |
| `pyspendless/dev_mcp_check.py` | **nuovo** — script di verifica (unica rete di sicurezza, D10) | 5 |
| `backlog/features.md` | modifica — riga di registrazione del task | — |
| `pyspendless/requirements.txt` | **nessuna modifica** (`zoneinfo` è stdlib da 3.9) | — |
| `.github/workflows/deploy.yml` | **nessuna modifica** | — |
| `sql/sqllite/**` | **nessuna modifica** (nessun cambio di schema) | — |
| `.env` / `.env_pa` | **nessuna modifica** | — |

**Stima aggiornata**: ~600-700 righe nuove (era 450-550 nella rev. 1), così ripartite:

| Blocco | Righe | Variazione vs rev. 1 |
|---|---|---|
| `mcp_server.py` — dispatcher, auth, errori | ~180 | +~20 (secondo header di auth, D1) |
| `mcp_server.py` — `add_movement` + risoluzione nomi + data | ~110 | +~20 (`Europe/Rome`, esclusione `transfer`) |
| `mcp_server.py` — `list_categories` | ~40 | **+40** (D2) |
| `mcp_server.py` — fingerprint e anti-duplicazione | ~50 | **+50** (D7) |
| `repository.py` — token + ultimo movimento | ~70 | +~25 (hashing D3, `get_last_inserted_for_user`) |
| `app.py` — rotte MCP e gestione token | ~110 | invariato |
| Template profilo + menu | ~130 | invariato |
| `dev_mcp_check.py` | ~120 | +~50 (copertura estesa per compensare D10) |

Le voci fuori scope (D9 rate limiting) non pesano su questa stima.

---

## Decisioni prese (chiuse il 2026-09-12)

| # | Decisione | Scelta | Dove impatta |
|---|---|---|---|
| **D1** | Canale del token | **Confermato**: `Authorization: Bearer <segreto>` primario; fallback su header alternativi, tutti accettati dal server: **`x-api-token`, `x-api-key`, `x-auth-token`** (valore nudo, senza prefisso) | Fasi 3, 6 |
| **D2** | Tool esposti | **Due**: `add_movement` + `list_categories` | Fasi 1, 2, 5 |
| **D3** | Segreto del token | **Hashato SHA-256** nella colonna `uuid`; il valore in chiaro esiste solo nella risposta di creazione | Fasi 0, 3 |
| **D4** | Durata del token | **365 giorni** | Fase 0 |
| **D5** | Data del movimento | **Confermato**: il campo `date` **resta nel contratto** del tool; se assente, il server assume *oggi* con ora locale **`Europe/Rome`** | Fase 1 |
| **D6** | Categorie `transfer` | **Escluse** da risoluzione e da `list_categories` | Fase 1 |
| **D7** | Anti-duplicazione | Fingerprint `sha256(importo\|categoria\|descrizione)` confrontato con l'**ultimo movimento inserito dall'utente**, individuato con **`ORDER BY rowid DESC`** (confermato); bypass con `force: true` — vedi §1.ter | Fasi 1, 5 |
| **D8** | Path endpoint | **`/mcp`** | Fase 2 |
| **D9** | Rate limiting | **Nessuno** in questo task → **task dedicato successivo** | rischio documentato in Fase 3 |
| **D10** | Test end-to-end pre-rilascio | **Nessuno**: si va in produzione con i soli test locali | Fasi 5, 6, 7 |
| **D11** | Collocazione della Fase 0 | **Dentro task20-0** | Fase 0 |

### Chiarimenti chiusi in fase di conferma (2026-09-12)

1. **D5** — il campo `date` resta nel contratto del tool (si possono quindi registrare spese di
   giorni passati); l'assenza del campo significa "oggi in `Europe/Rome`". §1.bis allineata.
2. **D7** — l'individuazione dell'ultimo movimento avviene con `ORDER BY rowid DESC`: accettata la
   dipendenza implicita da SQLite, in cambio di zero modifiche allo schema.
3. **D1** — il server accetta `Authorization: Bearer` e, in alternativa, `x-api-token`, `x-api-key`,
   `x-auth-token`: qualunque nome header risulti selezionabile nella UI dei connettori va bene senza
   toccare il codice.

### Unico punto ancora aperto (non bloccante)

- **Stringa `protocolVersion`**: il server dichiara `2025-06-18` e comunque **fa eco** alla versione
  richiesta dal client se la riconosce, senza fallire su versioni sconosciute. Da riallineare se la
  spec MCP avanza.

---

## Registrazioni di backlog previste (a implementazione conclusa)

- Riga in `backlog/features.md`:
  `| Server MCP | Endpoint /mcp (JSON-RPC stateless) con tool add_movement e list_categories, autenticati via token personale generato dal profilo utente, per aggiungere spese parlando a Claude (task20-0) | TODO |`
- Seconda riga in `backlog/features.md` per lo scorporo deciso in D9:
  `| Rate limiting endpoint MCP | Limite di richieste/401 sull'endpoint /mcp, scorporato da task20-0 (decisione D9) | TODO |`
  → alla sua apertura diventerà un `task21-0.md` autonomo.
- Nessuna voce `MB-NNN`: l'intervento tocca più di 2-3 file e introduce una superficie nuova, quindi
  è correttamente un `taskN-0` (cfr. `backlog/00-task-minor-bugfix.md:8-10`).
