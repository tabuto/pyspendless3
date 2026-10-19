# Task 24.0: Auth assessment — isolamento tra account e fiducia nell'input

**Stato**: **assessment completato**, nessuna correzione implementata (volutamente:
il piano di implementazione segue da questo documento).
**Repo**: `tabuto/pyspendless3`, branch `feature/task-19-FE-refactoring` al momento
dell'analisi (`HEAD` = `e233557`).
**Dipende da**: nessuno. Tocca trasversalmente task20-0 (MCP), task22-0 (wallet
preferito), task23-0 (OAuth).
**Data analisi**: 2026-10-19.

## Obiettivo

Verificare che **ogni API che agisce sui dati dell'utente controlli che le entità
coinvolte nella richiesta appartengano all'utente loggato** (e al suo account), senza
mai fidarsi dell'input. Criterio di successo:

> Un utente non deve poter **leggere né scrivere** dati di un account a cui non
> appartiene.

Questo task produce solo: inventario, findings con severità, direzione di rimedio,
domande aperte. **Nessuna modifica al codice** è inclusa.

## Perimetro e metodo

- **Lettura integrale** di `pyspendless/app.py` (tutte le rotte e le pagine),
  `repository.py`, `mcp_server.py`, `oauth_server.py`, `conf.py`, `models.py`.
- **Conferma empirica** dei findings principali con PoC usa-e-getta (SQLite
  in-memory, Flask test client con `session_transaction`, due account A = attaccante
  e B = vittima). I PoC non sono versionati; la riproduzione è descritta in ogni
  finding contrassegnato **[CONFERMATO]**. `[DA CODICE]` = dedotto dalla lettura
  ma non eseguito. `[CONDIZIONALE]` = dipende da configurazione di produzione che il
  repo non permette di vedere.
- **Fuori perimetro** (non esaminato in questo task): XSS/escaping nei template Jinja,
  dipendenze/CVE, rate limiting, correttezza di PKCE/redirect_uri in
  `oauth_server.py` (coperti dai controlli di `test_task23_0.py`), infrastruttura
  PythonAnywhere (HTTPS, permessi file, accesso ai log).

## Modello di minaccia e decisioni di tenancy

1. **Il confine di sicurezza è `account_id`**, non `user_id`. Tutti i membri di un
   account condividono movimenti, wallet, categorie, ricorrenti, inviti pendenti e
   statistiche. Un membro può quindi modificare/eliminare dati inseriti da un altro
   membro: è **by design** e **non** è un finding (vedi domanda aperta Q1 se si
   volesse cambiarlo).
2. Attaccante considerato: **utente autenticato legittimo di un altro account**
   (A), che conosce o indovina identificatori (gli id sono interi sequenziali, quindi
   enumerabili) e controlla il proprio client HTTP. Secondo attaccante: chi riesce a
   far visitare un link a un utente loggato (CSRF di navigazione).
3. Non c'è un'autorizzazione centralizzata: **ogni rotta ripete a mano**
   `if not session.get('user_id')` e poi confronta a mano. Non esistono decorator
   `login_required` né `before_request` di autenticazione (solo `admin_required` e il
   check di manutenzione). Di conseguenza la correttezza dipende dalla disciplina
   rotta per rotta: è il motivo strutturale della maggior parte dei findings.
4. Il layer repository **non è account-scoped** per costruzione: molti metodi
   accettano solo un id (`get_wallet`, `get_category`, `update_*`, `delete_*`,
   `get_movement`, `get_group`). Oggi le rotte compensano con un pre-check, ma ogni
   rotta nuova o dimenticata è potenzialmente un IDOR.

## Riepilogo findings

| ID | Severità | Stato | Titolo |
|---|---|---|---|
| AUTH-01 | **Alta** | CONFERMATO | Mass assignment: `PUT /api/wallets/<id>` e `PUT /api/categories/<id>` permettono di riassegnare `account_id` (e `id`) |
| AUTH-02 | **Alta** | CONFERMATO | `GET /generate-link/callback` da loggato cambia account senza vincolo email né conferma (anche via CSRF di navigazione) |
| AUTH-03 | **Alta** | CONFERMATO | Spese ricorrenti: `category_id`/`wallet_id` non verificati → lettura nomi cross-account e scrittura di riferimenti esterni |
| AUTH-04 | **Alta** (se vero in prod) | CONDIZIONALE | `SECRET_KEY` con default `'changeme'`: sessioni falsificabili → presa di controllo di qualunque account |
| AUTH-05 | **Media** | CONFERMATO | Token MCP/OAuth non rivalidati: restano validi dopo cambio account o cancellazione utente; con id riusati diventano validi per un altro utente |
| AUTH-06 | **Media** | CONFERMATO | Sessione non rivalidata: `account_id`/`user_id` nel cookie per 7 giorni; stessa riusabilità degli id |
| AUTH-07 | Bassa | CONFERMATO | `POST /api/movements`: `recurrent_movement_id` non verificato |
| AUTH-08 | Bassa | CONFERMATO | `admin_required` è fail-open per l'anonimo se `ADMIN_USER_ID` non è impostata (difeso solo dal check interno) |
| AUTH-09 | Bassa | DA CODICE | Oracoli 403/404 su wallet, categorie, token: enumerazione di id altrui |
| AUTH-10 | Bassa | DA CODICE | Repository non account-scoped: nessuna difesa in profondità |
| AUTH-11 | Bassa | DA CODICE | `DELETE /api/pending-invites/<uuid>` non filtra per tipo di token |
| AUTH-12 | Bassa | DA CODICE | Segreti nei log (DEBUG), `str(e)` nelle risposte, `debug=True` |
| AUTH-13 | Bassa | DA CODICE | Cookie `Secure=False`, nessun token CSRF, GET con effetti collaterali |
| AUTH-14 | Info | DA CODICE | Nessun modello di ruoli: ogni membro può invitare, rinominare l'account, cancellare tutto |
| AUTH-15 | Info (non-auth) | CONFERMATO | Bug collaterale: `delete_user` fallisce se l'account ha ricorrenti e lascia token orfani |

Nessun finding **Critico** accertato: nessun difetto permette a un utente anonimo di
leggere dati altrui. AUTH-04 diventerebbe Critico se confermato in produzione.

**Superficie realmente compromessa oggi**: *scrittura* cross-account (AUTH-01,
AUTH-03, AUTH-07), *lettura* cross-account limitata ai nomi di wallet/categoria
(AUTH-03), *presa d'account* per spostamento forzato (AUTH-02), *accesso persistente
post-revoca* (AUTH-05/06). **I movimenti degli altri account non risultano leggibili
né modificabili da nessun percorso trovato**: tutte le rotte sui movimenti sono
correttamente scoped (vedi "Verificato conforme").

## Inventario endpoint

Legenda esito: **OK** = l'accesso è limitato ai dati dell'account di sessione;
**DIF** = difetto (vedi finding); **PUB** = pubblico per design. "Input-entità" =
identificatori che il client fornisce e che il server deve ricondurre all'account.
I numeri di riga sono quelli di `pyspendless/app.py` al commit `e233557`.

### Rotte pubbliche, di login e di infrastruttura

| Rotta | Metodo | Input-entità | Controllo | Esito |
|---|---|---|---|---|
| `/version` (143), `/` (151), `/login` (160), `/auth/login` (164) | GET | – | – | PUB |
| `/auth/callback` (174) | GET | email da Google; cookie `pending_invite_token` | per **nuovi** utenti l'email dell'invito deve coincidere con quella Google (riga ~246); utenti esistenti entrano nel proprio account | OK (log DEBUG: AUTH-12) |
| `/auth/logout` (618) | GET | – | – | PUB (GET con effetto: AUTH-13) |
| `/onboarding` (326, 345) | GET, POST | `oauth_user_info` in sessione firmata | richiede il passaggio da Google | OK |
| `/generate-link/callback` (2202) | GET | `token` (bearer di invito) | utente non loggato: salva cookie e rimanda al login; **utente loggato: nessun vincolo email** | **DIF** AUTH-02 |
| `/oauth/authorize`, `/oauth/authorize/confirm`, `/oauth/token`, metadata (`oauth_server.py` 129/165/324/341/355) | GET/POST | `client_id`, `redirect_uri`, code | consenso con CSRF token e `hmac.compare_digest`; il code lega `user_id`+`account_id` **di sessione** | OK al rilascio; snapshot poi non rivalidato: AUTH-05 |
| `/.well-known/*` (2932) | GET | – | solo 404 JSON | PUB |
| `/mcp` (2846), `/mcp-oauth2` (2890) | POST | Bearer token | vedi sezione MCP | AUTH-05 |

### Pagine HTML (richiedono sessione)

| Rotta | Input-entità | Controllo | Esito |
|---|---|---|---|
| `/home` (405) | – | controlla `user_email` invece di `user_id` (incoerente, innocuo) | OK |
| `/create` (419) | `movement_id`, `repeat_from` (query) | `get_movement_by_id(id, account_id)` per entrambi | OK |
| `/movements` (539), `/ps-search-mov` (1020) | filtri `wallet_id`, `category_id[]`, `keywords`, `search` | i filtri sono sempre in AND con `account_id` di sessione; un id altrui restituisce zero righe | OK |
| `/recurrent-movements` (1114), `/settings/categories`, `/settings/wallets`, `/settings/group`, `/settings/import-export`, `/settings/profile` (1259–1296, 2664) | – | dati letti con `account_id`/`user_id` di sessione | OK |
| `/dashboard/monthly`, `/dashboard/yearly`, `/reports` (2409, 2424, 2580) | – | solo render; i dati arrivano dalle API stats | OK |
| `/settings/admin` (1305) | – | `@admin_required` + check interno | OK/AUTH-08 |

### API movimenti e ricerca

| Rotta | Metodo | Input-entità | Controllo | Esito |
|---|---|---|---|---|
| `/api/movements` (656) | GET | filtri | `account_id` di sessione | OK |
| `/api/movements/export` (742) | GET | filtri | `account_id` di sessione | OK |
| `/api/movements/bulk-update` (799) | POST | `category_id`, filtri | categoria verificata (`category.account_id != account_id` → 404); update limitato a `get_movements_for_account(account_id, …)` | OK |
| `/api/movements` (863) | POST | `movement_id`, `category_id`, `wallet_id`, `recurrent_movement_id` | category/wallet e movimento (update) verificati su `account_id`; `account_id`/`user_id` del nuovo movimento da sessione; **`recurrent_movement_id` no** | OK / **DIF** AUTH-07 |
| `/api/movements/<id>` (981) | DELETE | `movement_id` | `get_movement_by_id(id, account_id)`; 404 uniforme | OK |
| `/api/search-movements` (1063) | GET | `search`, `page` | `account_id` di sessione | OK |
| `/api/export/movements` (1899) | POST | – | `account_id` di sessione | OK |
| `/api/import/movements` (1944) | POST | CSV (categoria per nome, wallet per `code`) | categoria e wallet risolti **solo** fra quelli dell'account; id movimento = md5 del contenuto, che include il `code` wallet (UNIQUE globale) → collisione fra account non sfruttabile | OK |

### API ricorrenti

| Rotta | Metodo | Input-entità | Controllo | Esito |
|---|---|---|---|---|
| `/api/recurrent-movements` (1142) | GET | – | `get_all_for_account` | OK (ma espone i nomi di ciò che AUTH-03 ha inserito) |
| `/api/recurrent-movements` (1171) | POST | `category_id`, `wallet_id` | **nessuna verifica** di appartenenza | **DIF** AUTH-03 |
| `/api/recurrent-movements/<id>` (1211) | PUT | `rm_id`, `category_id`, `wallet_id` | `rm_id` scoped (`get_by_id(rm_id, account_id)`); `category_id`/`wallet_id` **no** | **DIF** AUTH-03 |
| `/api/recurrent-movements/<id>` (1236) | DELETE | `rm_id` | `delete(rm_id, account_id)` | OK |

### API categorie e wallet

| Rotta | Metodo | Input-entità | Controllo | Esito |
|---|---|---|---|---|
| `/api/categories` (626) | GET | – | `account_id` di sessione | OK |
| `/api/accounts/<aid>/categories` (1411) | POST | `account_id` in URL | `session.account_id == aid`; account del record dall'URL già validato | OK |
| `/api/categories/<id>` (1443) | PUT | `category_id`, **corpo JSON intero** | `category.account_id == account_id`, ma poi `update_category(id, data)` fa `setattr` su **ogni** chiave | **DIF** AUTH-01 |
| `/api/categories/<id>` (1478) | DELETE | `category_id`, `target_category_id` | categoria scoped; il target è verificato **nel repository** (stesso account e stesso tipo) | OK (AUTH-10: la sicurezza sta nel repository, non nella rotta) |
| `/api/accounts/<aid>/wallets` (1543) | GET | `account_id` in URL | `session.account_id == aid` | OK |
| `/api/accounts/<aid>/wallets` (1586) | POST | `account_id` in URL | idem | OK |
| `/api/wallets/<id>` (1624) | PUT | `wallet_id`, **corpo JSON intero** | `wallet.account_id == account_id`, poi `update_wallet` fa `setattr` su ogni chiave | **DIF** AUTH-01 |
| `/api/wallets/<id>/preferred` (1661, 1701) | PUT, DELETE | `wallet_id` | `set_preferred_wallet(user_id, wallet_id, account_id)` verifica utente e wallet nell'account; `unset` confronta con il preferito dell'utente | OK |
| `/api/wallets/<id>` (1737) | DELETE | `wallet_id` | wallet scoped; rifiuta se ha movimenti | OK |

### API account, utenti, gruppi, inviti

| Rotta | Metodo | Input-entità | Controllo | Esito |
|---|---|---|---|---|
| `/api/accounts/<aid>` (1842, 1868) | GET, PUT | `account_id` in URL | `session.account_id == aid`; `update_account` riceve solo `{'name': …}` | OK |
| `/api/accounts/<aid>/users` (2306) | GET | `account_id` in URL | `session.account_id == aid` | OK |
| `/api/groups/<gid>/members` (1770) | GET | `group_id` | `group.account_id == session.account_id` → 404 | OK |
| `/api/groups/<gid>/invite` (1800) | POST | `group_id`, `email` | gruppo dell'account + solo owner; non esiste rotta di accettazione (`accept_invite` è codice morto) | OK (residuo: restituisce il `token`, AUTH-12) |
| `/api/generate-link` (2057) | POST | `email` | `account_id` del payload da sessione; solo `@gmail.com` | OK (AUTH-14: qualsiasi membro; AUTH-12: link nei log) |
| `/api/pending-invites` (2117) | GET | – | filtra per `account_id` nel payload | OK |
| `/api/pending-invites/<uuid>` (2154) | DELETE | `token_uuid` | `payload.account_id == account_id`, **senza filtro sul tipo** | **DIF** AUTH-11 |
| `/api/user/delete-account` (2357) | DELETE | – (usa `user_id` di sessione) | solo sé stesso | OK / AUTH-15 |

### API statistiche e report

| Rotta | Input-entità | Controllo | Esito |
|---|---|---|---|
| `/api/stats/monthly` (2443), `/api/stats/yearly` (2480), `/api/stats/category-trend` (2513), `/api/filters/years` (2550), `/api/reports/annual` (2593) | `year`, `month`, `category_name` | `StatsRepository`/`ReportRepository`: ogni query filtrata per `account_id` di sessione | OK |

### API amministrazione

| Rotta | Metodo | Controllo | Esito |
|---|---|---|---|
| `/admin/whitelist` (1325), `/admin/whitelist/<email>` (1351), `/admin/users` (1370), `/admin/users/<id>` (1386) | POST/DELETE/GET/DELETE | `@admin_required` + secondo check `session.user_id`; cross-account **per design** (è l'amministratore) | OK / AUTH-08 |

### API token personali e connessioni

| Rotta | Metodo | Input-entità | Controllo | Esito |
|---|---|---|---|---|
| `/api/mcp-tokens` (2691, 2713) | GET, POST | – | elenco filtrato per `user_id`; creazione lega `user_id`+`account_id` **di sessione** | OK (snapshot: AUTH-05) |
| `/api/mcp-tokens/<hash>` (2758) | DELETE | `token_hash` | `get_mcp_token_owner` (filtra `type='MCP'`) deve coincidere con `user_id` | OK |
| `/api/oauth-connections` (2793), `/<client_id>` (2818) | GET, DELETE | `client_id` | `revoke_oauth_connection(user_id, client_id)` scoped sull'utente | OK |

### Server MCP (`mcp_server.py`)

| Tool | Input-entità | Controllo | Esito |
|---|---|---|---|
| `list_categories` | – | `ctx['account_id']` dal **payload del token** | OK se il token è fresco; AUTH-05 |
| `add_movement` | categoria e wallet per nome | risolti fra quelli di `ctx['account_id']` + controllo esplicito anti cross-account (`mcp_server.py` ~652); utente cercato per id | OK; AUTH-05 |

## Findings

### AUTH-01 — Mass assignment su wallet e categorie [CONFERMATO] — Alta

**Dove**: `app.py:1624` (`api_update_wallet`), `app.py:1443` (`api_update_category`);
`repository.py:470-474` (`WalletRepository.update_wallet`) e
`repository.py:611-613` (`CategoryRepository.update_category`).

**Difetto**: la rotta verifica che il wallet/la categoria **di partenza** sia
dell'account, poi passa all'update l'intero JSON del client. Il repository applica
`for key, value in data.items(): if hasattr(obj, key): setattr(obj, key, value)`
(per le categorie, tutte le chiavi tranne `name`). Il client può quindi impostare
`account_id`, `id`, `code`, `created_at`, ecc. L'unico campo validato è `order_index`.

**Scenario**: l'utente A invia `PUT /api/wallets/<suo_wallet> {"account_id": <id_B>}`.
Il controllo passa (il wallet è di A al momento del check), poi il wallet **si
trasferisce nell'account di B**.

**PoC eseguito**: A e B con wallet/categorie; A manda il PUT con `account_id` di B su
un proprio wallet e una propria categoria → `200` entrambi; nel DB
`wallet.account_id == id_B`; `GET /api/accounts/<B>/wallets` e `GET /api/categories`
**di B** ora elencano anche il wallet e la categoria dell'attaccante.

**Impatto**: scrittura in un account altrui (iniezione di wallet e categorie scelti
dall'attaccante nelle liste di B; B può poi selezionarli in un movimento, perché ora
risultano suoi). Con `id` si possono anche provocare collisioni di chiave primaria.
Gli id di account sono interi piccoli e sequenziali. Non rende leggibili i dati di B.

**Direzione di rimedio** (non implementata): lista bianca esplicita dei campi
modificabili (`name`, `currency`, `order_index` per i wallet; `name`, `type`,
`order_index` per le categorie) e mai `setattr` generico su dati del client.
Stesso criterio da applicare a `MovementRepository.update_movement`
(`repository.py:752`) e `AccountRepository.update_account` (`repository.py:383`),
oggi sicuri solo perché la rotta costruisce il dizionario a mano.

### AUTH-02 — Accettazione invito da GET senza vincolo email né conferma [CONFERMATO] — Alta

**Dove**: `app.py:2202-2266` (`generate_link_callback`, scenario A, righe 2241-2266).

**Difetto**: se l'utente è loggato, il codice nota che l'email dell'invito non
coincide con la sua, mostra un `flash` di warning e **procede comunque**
(commento: "Per ora permettiamo l'aggiunta"). Poi esegue
`user.account_id = target_account_id; user.role = 'member'; db.commit();
session['account_id'] = target_account_id`. Il tutto avviene su una **GET** e senza
alcuna conferma. Il percorso per i *nuovi* utenti (`auth_callback`) invece impone il
match dell'email: le due vie sono incoerenti.

**Scenario**: l'attaccante crea un invito (basta un qualunque `@gmail.com`) e fa
arrivare il link alla vittima (messaggio, `<a href>`, redirect). SameSite=Lax invia il
cookie di sessione alle navigazioni top-level in GET, quindi la vittima, già loggata,
viene **spostata nell'account dell'attaccante**. Da quel momento tutto ciò che la
vittima registra finisce in un account che l'attaccante legge, e perde la visibilità
dei propri dati (restano nel vecchio account, orfani se era l'unica). Se la vittima
era `owner` di un account con altri membri, quell'account resta senza proprietario.

**PoC eseguito**: B loggato (email `u2@gmail.com`) apre il link con
`payload.email = qualcun.altro@gmail.com` → `302`; B risulta in `account_id` di A.

**Impatto**: presa di controllo dei dati futuri della vittima e perdita di accesso a
quelli passati; violazione del criterio "non accedere/scrivere dati di un account a
cui non si appartiene" nella direzione inversa (è l'attaccante che ottiene accesso
ai dati della vittima).

**Direzione di rimedio**: rifiutare (non solo avvisare) se l'email di sessione
differisce da quella dell'invito, come già fa `auth_callback`; spostare
l'accettazione su una **POST con conferma esplicita** e token CSRF; decidere cosa
succede ai dati dell'account di provenienza (vedi Q3).

### AUTH-03 — Spese ricorrenti: `category_id`/`wallet_id` non verificati [CONFERMATO] — Alta

**Dove**: `app.py:1171` (POST), `app.py:1211` (PUT);
`repository.py:1974` (`create`) e `repository.py:1991` (`update`).

**Difetto**: il record ricorrente viene creato/aggiornato con l'`account_id` giusto
(sessione), ma `category_id` e `wallet_id` arrivano dal corpo e sono salvati senza
controllare che appartengano all'account. Il `GET /api/recurrent-movements` li
risolve poi a nome (`category_obj.name`, `wallet_obj.name`) tramite relationship.

**Scenario**: A crea una ricorrente con `category_id`/`wallet_id` di B (id
sequenziali) e legge la propria lista.

**PoC eseguito**: `POST` → `201`; `GET` → `category_name: "CAT-SECRET-B"`,
`wallet_name: "WALLET-SECRET-B"`. Enumerando gli id si ottengono tutti i nomi di
categorie e wallet di tutti gli account.

**Impatto**: **lettura** cross-account (nomi di categorie e wallet: dati modesti ma
reali, e in una app di finanza personale i nomi dei wallet possono essere
descrittivi) e creazione di riferimenti incrociati fra account. Il successivo
`POST /api/movements` basato su quella ricorrente viene fermato dal controllo
esistente (403), quindi non c'è scrittura dei movimenti, ma l'integrità
referenziale è violata.

**Direzione di rimedio**: validare entrambi gli id contro l'account in rotta (o,
meglio, in un metodo di repository che li risolva già scoped) sia in POST sia in
PUT, e rispondere 404 uniforme.

### AUTH-04 — `SECRET_KEY` con default debole [CONDIZIONALE] — Alta se vero in produzione

**Dove**: `conf.py:82` (`os.getenv('SECRET_KEY', 'changeme')`), `app.py:39`.

**Difetto**: se la variabile non è impostata sul server l'app parte comunque con la
chiave pubblica `changeme`. Le sessioni sono cookie firmati con quella chiave e
contengono `user_id`/`account_id`: chi conosce la chiave può **fabbricarsi un cookie
per qualunque utente/account** senza passare da Google. Nessun controllo all'avvio.

**Stato**: non verificabile dal repo (`.env` non versionato). **Azione di verifica
richiesta al proprietario**: controllare su PythonAnywhere che `SECRET_KEY` sia
impostata, lunga e casuale. In ogni caso conviene far fallire l'avvio se manca
(fuori da `FLASK_ENV=development`).

### AUTH-05 — Token MCP/OAuth: snapshot mai rivalidato [CONFERMATO] — Media

**Dove**: `mcp_server.py:225-258` (`authenticate`) e `271-312`
(`authenticate_oauth`); `repository.py:295-352` (`delete_user`);
`oauth_server.py:191` (account congelato nel code).

**Difetto**: il token contiene `user_id` e `account_id` al momento dell'emissione
(MCP: 365 giorni; OAuth: access 1 h, refresh 60 giorni con rotazione) e il server li
usa **senza confrontarli con lo stato attuale** dell'utente. Inoltre `delete_user`
non revoca alcun token.

**Scenari confermati col PoC**:
1. *Cambio account* (anche tramite AUTH-02): U ha un token MCP con snapshot
   `account=2`, poi passa all'account 1. Il token continua a leggere (e scrivere)
   l'account 2, cui non appartiene più.
2. *Cancellazione + riuso id*: B (ultimo utente creato, account 2) ha un token MCP e
   cancella il proprio account → il token resta `PENDING`. Il successivo utente C
   riceve gli stessi id (SQLite riusa il rowid massimo + 1: user 2 / account 2).
   **Il vecchio token di B legge le categorie di C e vi registra movimenti**
   (`add_movement` → "Registrata spesa", movimento presente nell'account di C).

**Impatto**: accesso persistente dopo la perdita di appartenenza (fino a 365 giorni
per MCP). Lo scenario 2 richiede che l'ultimo utente si cancelli e ne arrivi uno
nuovo, quindi poco probabile oggi ma reale, e il suo effetto è un accesso totale ai
dati del nuovo utente.

**Direzione di rimedio**: in `authenticate*` ricaricare l'utente e confrontare
`user.account_id` con quello del token (rifiutare se diverso o se l'utente non
esiste); revocare i token alla cancellazione e al cambio account; valutare id non
riusabili (`AUTOINCREMENT`) per `User` e `Account` (vedi Q5).

### AUTH-06 — Sessione non rivalidata contro il DB [CONFERMATO] — Media

**Dove**: tutte le rotte; la sessione è scritta in `auth_callback` (~211-216),
`onboarding_submit`, `generate_link_callback` (2266).

**Difetto**: `user_id` e `account_id` vivono nel cookie firmato per 7 giorni e non
vengono mai ricontrollati. Quindi: (a) un utente eliminato dall'amministratore
(`DELETE /admin/users/<id>`) o che ha cambiato account da un altro dispositivo
mantiene l'accesso, in lettura e scrittura, all'account vecchio fino a scadenza del
cookie; (b) come sopra, con id riusati la sessione "orfana" punta all'account di un
altro utente.

**PoC eseguito**: utente 3 / account 3 cancellati; con il cookie vecchio
`GET /api/categories` → `200`; creato un nuovo account (riceve id 3) con la categoria
`CAT-NUOVO-UTENTE`: **il cookie vecchio la legge**.

**Direzione di rimedio**: una funzione unica di "utente corrente" (caricata per
richiesta, con `account_id` letto dal DB e non dal cookie) usata da un decorator
`login_required` che sostituisca i controlli a mano.

### AUTH-07 — `recurrent_movement_id` non verificato nei movimenti [CONFERMATO] — Bassa

**Dove**: `app.py:940-942`.

**Difetto**: `int(recurrent_movement_id)` finisce nel movimento senza controllare che
la ricorrente sia dell'account. **PoC**: movimento di A con `recurrent_movement_id`
di una ricorrente di B → `201`, riferimento salvato.

**Impatto**: solo integrità referenziale. Non c'è lettura: il riepilogo delle
ricorrenti filtra anche `Movement.account_id`, quindi B non vede nulla di A, e A non
legge la ricorrente di B. Rimedio: `get_by_id(rm_id, account_id)` prima del salvataggio.

### AUTH-08 — `admin_required` fail-open per l'anonimo [CONFERMATO] — Bassa

**Dove**: `app.py:67-80`, `conf.py:92`.

**Difetto**: `str(session.get('user_id')) != str(ADMIN_USER_ID)`; senza
`ADMIN_USER_ID` (nessun default) e senza sessione, entrambi i lati valgono `'None'`
e il decorator **lascia passare**. Lo stesso vale per `is_admin()`, che quindi
risulta vero per un anonimo e potrebbe far mostrare voci di menu admin.

**PoC** (`ADMIN_USER_ID=None`): `GET /admin/users` anonimo → `401` dal check interno
della rotta; `/settings/admin` → redirect al login. Quindi oggi **non è sfruttabile**
solo perché ogni rotta admin ripete il controllo di sessione; un utente loggato non
admin viene respinto con 403. Rimedio: negare esplicitamente se `ADMIN_USER_ID` è
vuota o se la sessione non ha `user_id`.

### AUTH-09 — Oracoli di esistenza e id enumerabili [DA CODICE] — Bassa

`PUT/DELETE /api/categories/<id>`, `PUT/DELETE /api/wallets/<id>` rispondono **404**
se l'id non esiste e **403** se esiste ma è di un altro account, a differenza dei
movimenti e delle ricorrenti che rispondono 404 in entrambi i casi. Combinato con id
sequenziali permette di mappare quanti wallet/categorie esistono e di chi sono
(a livello di range di id). Rimedio: 404 uniforme.

### AUTH-10 — Repository non account-scoped [DA CODICE] — Bassa (difesa in profondità)

Metodi che ricevono solo un id: `WalletRepository.get_wallet/update_wallet/delete_wallet`,
`CategoryRepository.get_category/update_category/delete_category`,
`MovementRepository.get_movement/update_movement/delete_movement`,
`GroupRepository.get_group`, `UserRepository.get_preferred_wallet`,
`AccountRepository.update_account`. La correttezza dipende dal pre-check in rotta:
AUTH-01 e AUTH-03 sono esattamente il caso in cui il pre-check c'è ma non basta, o
manca. Il metodo `delete_category` verifica da solo il target (stesso account/tipo),
ed è l'esempio da generalizzare. Direzione: firme del tipo
`get_wallet(wallet_id, account_id)` che non permettano di dimenticare l'account.

### AUTH-11 — `delete_pending_invite` senza filtro di tipo [DA CODICE] — Bassa

**Dove**: `app.py:2154`, `repository.py` (`get_token`, `delete_token`).

`get_token(uuid)` non filtra per `type`; il controllo è solo `payload.account_id ==
account_id`. I token MCP e OAuth contengono lo stesso campo, quindi un membro che
conosca l'hash di un token MCP/OAuth di un altro membro **dello stesso account** può
**cancellarlo fisicamente** attraverso questa rotta. Mitigante forte: gli hash sono
SHA-256 di segreti casuali e non sono mai mostrati ad altri utenti, quindi non sono
indovinabili. Rimedio: limitare la rotta a `type == 'SHARE'`.

### AUTH-12 — Segreti nei log, `str(e)` in risposta, `debug=True` [DA CODICE] — Bassa

- Il logging è a `DEBUG` (`app.py:28`) e scrive: token OAuth di Google
  (`app.py:202`), `dict(session)` (`app.py:237`), UUID dei token di invito e link
  completi (`app.py:186`, `2104`, `2291`). Chi legge i log (o un file di log
  esposto) ottiene bearer utilizzabili: il link di invito è equivalente a un
  accesso all'account (vedi AUTH-02).
- Molte rotte restituiscono `f'...{str(e)}'` al client e fanno `flash(... str(e))`
  (es. `app.py:979`, `1018`, `1206`, `1473`, `1698`, `2050`), con rischio di
  fuga di dettagli SQL/percorsi.
- `app.run(debug=True)` (`app.py:2951`): su PythonAnywhere si usa WSGI e non conta,
  ma lanciare il file a mano su un host raggiungibile abilita il debugger Werkzeug.
- `api_invite_to_group` restituisce nel JSON il `token` del gruppo.

### AUTH-13 — Cookie e CSRF [DA CODICE] — Bassa

`SESSION_COOKIE_SECURE = False` (`app.py:45`) anche in produzione HTTPS: il cookie
viaggia anche su HTTP. Non esiste alcun token CSRF sulle API JSON: ci si appoggia a
`SameSite=Lax` più `request.get_json()` che pretende `application/json`. È una
difesa accettabile ma unica; le eccezioni sono le **GET con effetti collaterali**
(`/auth/logout`, `/generate-link/callback` → AUTH-02) che Lax non protegge.

### AUTH-14 — Nessun modello di ruoli [DA CODICE] — Info

`User.role` (`owner`/`member`) non è usato per autorizzare nulla tranne la
funzione, oggi non raggiungibile da UI, dei gruppi. Di fatto ogni membro può:
invitare chiunque (`@gmail.com`) con accesso completo, rinominare l'account,
eliminare wallet/categorie/ricorrenti e qualsiasi movimento, cancellare i movimenti
altrui (anche con `delete-account`, che rimuove i movimenti inseriti dall'utente).
Non esiste una rotta per **rimuovere un membro**. È coerente col modello
"famiglia" ma va deciso in modo esplicito (Q1, Q2).

### AUTH-15 — Bug collaterale (non di sicurezza): `delete_user` [CONFERMATO] — Info

`UserRepository.delete_user` (`repository.py:295`) per l'ultimo utente di un account
elimina movimenti, categorie, wallet, gruppi e account ma **non le ricorrenti**: la
rimozione dell'account fa tentare all'ORM un `UPDATE "RecurrentMovement" SET
account_id=NULL`, che viola il `NOT NULL` → `IntegrityError` e `500`
("Errore durante l'eliminazione"). L'utente con ricorrenti non riesce quindi a
eliminare il proprio account. Lascia anche i token (AUTH-05). Da trattare insieme ad
AUTH-05 nel piano di implementazione.

## Verificato conforme

- **Tutte le rotte sui movimenti** (`GET/POST/DELETE`, export, ricerca, bulk-update,
  import, `/create` con `movement_id` e `repeat_from`): account da sessione, id
  risolti con `get_movement_by_id(id, account_id)`, 404 uniforme. `account_id` e
  `user_id` di un nuovo movimento non sono mai presi dal corpo.
- **Rotte con `account_id` nell'URL** (`/api/accounts/<aid>/…`): confrontato con
  l'account di sessione (403 se diverso).
- **Statistiche e report**: nessun parametro del client entra nella clausola di
  tenancy, solo `year`/`month`/`category_name` come filtri.
- **Wallet preferito** (task22-0): `set_preferred_wallet` verifica utente e wallet
  nello stesso account; la delete di un wallet libera i preferiti.
- **Token MCP personali**: elenco e revoca limitati al proprietario
  (`get_mcp_token_owner` con filtro di tipo); segreto restituito una sola volta, nel
  DB c'è solo l'hash.
- **Connessioni OAuth**: elenco e revoca per `user_id`; il consenso OAuth ha CSRF e
  legge `account_id` dalla sessione dell'utente che acconsente.
- **Tool MCP `add_movement`**: ha già un controllo esplicito anti cross-account su
  categoria e wallet.
- **Gruppi**: verificano `group.account_id == account_id` e restituiscono 404
  uniforme.
- **Import CSV**: l'id del movimento è un hash che include il `code` del wallet
  (UNIQUE globale), quindi un attaccante non può far "saltare" l'import di un altro
  account con righe pre-inserite. *Verificato dal PoC (IntegrityError su
  `Wallet.code` duplicato) e dal codice.*
- **Onboarding**: richiede `oauth_user_info` in sessione firmata, quindi un login
  Google completato.

## Domande aperte per il piano di implementazione

- **Q1** — Si conferma il modello "tutti i membri sono pari" (nessuna distinzione
  fra `owner` e `member`) o si vogliono almeno i permessi di *invitare*, *rimuovere
  membri* e *eliminare l'account* riservati all'owner?
- **Q2** — Serve una rotta per **rimuovere un membro** (oggi non esiste e il membro
  rimosso manterrebbe sessioni e token: AUTH-05/06)?
- **Q3** — All'accettazione di un invito da parte di un utente che ha già un proprio
  account con dati: i dati restano orfani (oggi), si migrano, o l'invito è consentito
  solo a chi non ha dati / non ha altri membri?
- **Q4** — Gli inviti devono restare *bearer link* (basta il link) o devono essere
  legati all'identità (email verificata)? Comporta anche cosa fare con il caso
  "utente loggato con altra email".
- **Q5** — Si accetta una migrazione per rendere gli id di `User` e `Account` non
  riusabili (`sqlite_autoincrement`) o si preferisce risolvere solo con rivalidazione
  (AUTH-05/06)? La rivalidazione è comunque necessaria.
- **Q6** — In produzione `SECRET_KEY` e `ADMIN_USER_ID` sono impostate (AUTH-04,
  AUTH-08)? Da controllare a mano sul server prima di decidere la priorità.
- **Q7** — La sessione deve restare valida 7 giorni, o si accorcia/si lega a una
  versione per-utente (`session_version`) invalidabile a cambio account/cancellazione?
- **Q8** — Si vuole centralizzare l'autenticazione (decorator `login_required` +
  "utente corrente" per richiesta) come refactor unico, o intervenire rotta per rotta?
  Raccomandato il primo: risolve AUTH-06 e riduce la superficie dei futuri difetti.

## Ordine di intervento suggerito (da validare in fase di piano)

1. **Subito, bassa invasività, alto valore**: AUTH-01 (lista bianca campi), AUTH-03
   (validazione id), AUTH-02 (rifiuto se email diversa + POST di conferma), verifica
   AUTH-04.
2. **Poi**: rivalidazione utente/account in sessione e nei token (AUTH-05/06),
   revoca alla cancellazione, fix AUTH-15.
3. **Infine, hardening**: AUTH-07/08/09/11/12/13, repository account-scoped
   (AUTH-10), eventuale modello di ruoli (AUTH-14).

## Strategia di test per la fase di implementazione (traccia)

- Un unico file `pyspendless/test/test_task24_x.py` sullo schema di
  `test_task23_0.py` (SQLite in-memory, `get_db_session` sostituito in `app`,
  `mcp_server`, `oauth_server`, Flask test client con `session_transaction`).
- Fixture a **due account** (A attaccante, B vittima) con wallet, categorie,
  movimenti, ricorrenti, token MCP.
- Ogni PoC di questo documento diventa un test di regressione che oggi **fallisce**
  e deve passare dopo il fix: AUTH-01 (PUT con `account_id` → ignorato o 400),
  AUTH-02 (email diversa → nessun cambio account), AUTH-03 (id altrui → 404),
  AUTH-05 (token con snapshot obsoleto → rifiutato; token orfano dopo delete),
  AUTH-06 (sessione di utente cancellato → 401), AUTH-07.
- Test di **sistema** (guardia contro le future rotte): iterare su
  `app.url_map`, chiamare ogni rotta `/api/...` con la sessione di A passando gli id
  di B, e asserire che nessuna risposta sia `2xx` né contenga dati di B. Una rotta
  nuova non classificata fa fallire il test.
- Test del layer repository: i metodi che accettano un id devono richiedere anche
  `account_id`.

## File toccati

Nessuno oltre a questo documento e a `backlog/features.md` (registrazione del task).
