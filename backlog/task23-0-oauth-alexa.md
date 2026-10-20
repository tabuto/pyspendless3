# Task 23.0: OAuth 2.x per il server MCP (endpoint `/mcp-oauth2`) — integrazione con Alexa+ (retrocompatibile con Claude)

**Stato**: server implementato, **rilasciato in produzione** (v0.3.0, metadata e
401 verificati dal vivo) e Lambda del bridge Alexa già creata su AWS. Resta da
creare la skill sulla console Amazon, impostare le variabili `OAUTH_ALEXA_*` sul
server e rilasciare la patch «`resource` facoltativa» (vedi "Stato
dell'integrazione Alexa"). La strada scelta **non** è l'add-on MCP di Alexa+ ma
una **Custom Skill con Lambda bridge** (`alexa-mcp-lambda/`): Alexa+ non è
disponibile in italiano, mentre una Custom Skill con Account Linking funziona su
qualunque Echo e si distribuisce ai familiari via Beta Testing.
**Repo**: `tabuto/pyspendless3`, branch `main`.
**Dipende da**: task20-0 (server MCP), task22-0 (wallet preferito per utente).

## Stato implementazione (aggiornato da questa sessione)
- `pyspendless/mcp_server.py`: `auth_mode` (`static`|`oauth`) su
  `handle_http_request`/`_dispatch`/`_handle_tools_call`; `/mcp` invariato,
  `authenticate_oauth` + 401/403 con `WWW-Authenticate` solo in modalità `oauth`.
- `pyspendless/repository.py`: `TokenRepository` generalizzata con helper
  privati condivisi (`_create_hashed_secret_token`/`_validate_hashed_secret_token`)
  e nuovi metodi `create_oauth_code`/`redeem_oauth_code`/`create_oauth_access_token`/
  `validate_oauth_access_token`/`create_oauth_refresh_token`/`redeem_oauth_refresh_token`/
  `get_oauth_connections_for_user`/`revoke_oauth_connection`. Nessuna migrazione
  di schema (riuso dello status `EXPIRED` per le revoche).
- `pyspendless/oauth_server.py` (nuovo): blueprint `oauth` con
  `/oauth/authorize`, `/oauth/authorize/confirm`, `/oauth/token`
  (authorization_code+PKCE, client_credentials, refresh_token), metadata di
  discovery dedicati. Scritto a mano, nessuna dipendenza nuova.
- `pyspendless/app.py`: rotte `/mcp-oauth2`, blueprint registrato, eccezioni di
  manutenzione, redirect post-login verso `/oauth/authorize` pendente,
  API `/api/oauth-connections` (elenco/revoca).
- `pyspendless/conf.py`: `OAUTH_ALEXA_CLIENT_ID/SECRET/REDIRECT_URIS`,
  `OAUTH_MAX_MOVEMENT_AMOUNT` (solo lettura, nessuna logica di blocco ancora).
- `pyspendless/templates/ps-oauth-consent.html` (nuovo) + sezione
  "Connessioni" in `ps-setting-profile.html`.
- Test: `pyspendless/test/test_task23_0.py` (56 controlli, SQLite in-memory:
  `TokenRepository` OAuth, `mcp_server` nei due `auth_mode`, flusso end-to-end
  via Flask test client) e `pyspendless/dev_mcp_check.py` esteso con i
  controlli su `/mcp-oauth2` e i metadata dedicati (richiede server locale
  reale + DB `.env`: **non eseguito in questa sessione** per un problema
  preesistente e indipendente dal task — il DB locale di sviluppo non ha
  ancora la colonna `preferred_wallet_id` del task22-0, da migrare a parte).
- Variabili d'ambiente OAuth (`OAUTH_ALEXA_*`): impostate in locale il
  19/10/2026, ancora da riportare sul server (vedi "Stato dell'integrazione
  Alexa").

## Obiettivo
Rendere il server MCP di PySpendless collegabile ad **Alexa+** (add-on MCP), che richiede
OAuth 2.x con PKCE, **senza alterare in alcun modo** il funzionamento attuale con il
connettore claude.ai (token statico personale in header, errori di autenticazione come
`200 + isError`, mai 401).

Il nuovo endpoint OAuth2 si chiama **`/mcp-oauth2`** (non `/mcp-alexa`): il nome non lo lega
ad Alexa in modo esplicito, così in futuro può essere riusato da altri client MCP che
richiedono OAuth2 standard, senza dover introdurre un terzo endpoint (vedi "Punti aperti" §7).
Alexa+ resta però il motivo per cui il task nasce ora e l'unico client pre-registrato al
momento del rilascio.

## Vincoli di Alexa+ (da documentazione Amazon, da riverificare prima di implementare)
Fonti: [QuickStart](https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-quickstart.html),
[Authentication](https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-authentication.html).

- Transport Streamable HTTP, spec MCP **2025-11-25**; URL pubblico HTTPS; risposta < 500 ms.
- Due livelli di autenticazione:
  - **service-level**: `client_credentials` (M2M), per registrazione del servizio, health check,
    sincronizzazione; nessun dato utente;
  - **user-level**: `authorization_code` + **PKCE (S256)**, per l'esecuzione dei tool.
- Authorization server: `client_credentials` in `grant_types_supported`, client auth via HTTP
  Basic, access token con validità **max 3600 s**, **nessun refresh token** per
  `client_credentials`, validazione del parametro `resource` contro l'URI del server MCP
  registrato.
- **Non supportati**: API key, Dynamic Client Registration, OpenID Connect, Step-Up Authorization.

## Stato attuale (verificato sul codice, branch master)
- `/mcp` (POST) in `app.py`; logica in `mcp_server.py`. JSON-RPC stateless, protocollo
  dichiarato `2025-06-18` (accettati anche `2024-11-05`, `2025-03-26`).
- Token personale statico: `Authorization: Bearer <segreto>` (fallback `x-api-token`,
  `x-api-key`, `x-auth-token`), hash SHA-256 nella tabella `Token` con `type='MCP'`
  (`TokenRepository.validate_mcp_secret`). Il payload contiene `user_id`, `account_id`.
- `AUTH_REQUIRED_METHODS = ('tools/call',)`: `initialize`, `tools/list`, `ping` sono
  pubblici. Token assente/non valido → **200 con `isError: true`**, **mai 401**.
- `/.well-known/oauth-protected-resource[/...]` (`app.py` ~2818) risponde con un **404 JSON
  pulito** (`not_found_body`): è voluto, vedi sotto.
- GET/DELETE su `/mcp` → 405 JSON (server stateless, niente stream).
- Login utenti: **Google OAuth** + sessione Flask (`/login`, `/auth/login`, `/auth/callback`).
- Modalità manutenzione: `/mcp` → 503; `/.well-known/*` gestito in `check_maintenance_mode`.
- Tabella `Token`: `uuid` (PK), `type`, `create_date`, `expire_date`, `status`
  (`PENDING|USED|EXPIRED`), `payload` (JSON).

## Perché è un task delicato (rischio di regressione con Claude)
Dal commento in `mcp_server.py` (task20-0 §3.bis): un **401** (o dei metadata OAuth trovati
dalla sonda) sul percorso usato da Claude fa partire il suo flusso OAuth/Dynamic Client
Registration e il connettore fallisce con «impossibile registrarsi con il servizio di accesso».
Quindi **nessuna modifica deve essere osservabile da Claude** sull'origine e su `/mcp`.

## Soluzione proposta: risorsa separata `/mcp-oauth2`, `/mcp` invariato

### Principio
Due porte d'ingresso allo **stesso codice dei tool** (`TOOL_DEFINITIONS`, `_dispatch`,
`_tool_*`), con autenticazione diversa:

| | `/mcp` (Claude, invariato) | `/mcp-oauth2` (nuovo) |
|---|---|---|
| Credenziale | token statico (invariato) | access token OAuth |
| Auth mancante/errata | `200 + isError`, mai 401 | **`401` + `WWW-Authenticate`** (`resource_metadata=...`) |
| Metadata discovery | nessuno (404 JSON invariato) | `/.well-known/oauth-protected-resource/mcp-oauth2` |
| Metodi pubblici | `initialize`, `tools/list`, `ping` | `initialize`, `tools/list`, `ping` (come oggi) |

### Metadata OAuth senza toccare l'origine
- Il **path root** `/.well-known/oauth-protected-resource` e
  `/.well-known/oauth-authorization-server` **restano 404 JSON** (comportamento attuale,
  quello che la sonda di Claude si aspetta).
- Il Protected Resource Metadata va **solo** sul path della nuova risorsa:
  `/.well-known/oauth-protected-resource/mcp-oauth2`.
- L'authorization server usa un **issuer con path** (RFC 8414, path insertion):
  `issuer = {BASE_URL}/oauth` → metadata in
  `/.well-known/oauth-authorization-server/oauth`. Non occupa il path root.
- Va controllato che la sonda di Claude non cerchi anche i path con suffisso `/oauth`
  (da verificare con test, vedi sotto).

### Endpoint OAuth (nuovo modulo `oauth_server.py`, blueprint Flask)
- `GET /oauth/authorize` — authorization code + PKCE S256. Usa la **sessione Flask esistente**:
  se l'utente non è loggato, redirect a `/login` (Google) e ritorno all'authorize. Schermata di
  consenso minimale ("Alexa vuole registrare spese per il tuo account"). Valida `client_id`,
  `redirect_uri` (whitelist esatta), `code_challenge`, `code_challenge_method=S256`,
  `resource`, `state`.
- `POST /oauth/token` — `grant_type=authorization_code` (con `code_verifier`) e
  `grant_type=client_credentials`; client auth via HTTP Basic (accettare anche
  `client_secret_post` solo se Alexa lo richiede). Access token max 3600 s. Validazione
  `resource` == URI di `/mcp-oauth2`.
- `GET /.well-known/oauth-authorization-server/oauth` — metadata (`issuer`,
  `authorization_endpoint`, `token_endpoint`, `grant_types_supported` con
  `authorization_code` e `client_credentials`, `code_challenge_methods_supported=["S256"]`,
  `token_endpoint_auth_methods_supported`, `response_types_supported=["code"]`).
- **Nessun** endpoint di Dynamic Client Registration: il client Alexa è pre-registrato.

### Modello dati e sicurezza
- Riuso della tabella `Token` con nuovi `type`: `OAUTH_CODE` (monouso, scadenza ~60 s),
  `OAUTH_ACCESS` (max 3600 s). Segreti **hashati SHA-256** come per `MCP`. Nessuna migrazione
  dello schema (la colonna `type` è `Text`); verificare che nessun codice assuma i soli tipi
  esistenti (es. `INVITE`, `MCP`).
- `payload` dell'access token: `user_id`, `account_id`, `client_id`, `scope`, `resource`.
  Il token `client_credentials` ha `user_id = None`: **non autorizza `tools/call`**.
- Client Alexa **pre-registrato via variabili d'ambiente** (`OAUTH_ALEXA_CLIENT_ID`,
  `OAUTH_ALEXA_CLIENT_SECRET`, `OAUTH_ALEXA_REDIRECT_URIS`), mai nel repo. Confronto del secret
  a tempo costante.
- Codice monouso: marcarlo `USED` alla prima redenzione; una seconda redenzione fallisce.
- PKCE obbligatorio; nessun flusso implicito; nessun refresh token per `client_credentials`
  (per `authorization_code` vedi "Punti aperti").
- Limite di importo opzionale su `add_movement` per le chiamate via Alexa (riduce l'impatto di
  un riconoscimento vocale errato) — da decidere.
- Il flusso Alexa **non tocca** i token personali esistenti: revocare un token MCP personale non
  invalida i token OAuth e viceversa. Aggiungere in Impostazioni > Profilo l'elenco delle
  connessioni Alexa con possibilità di revoca.

### Refactor minimo di `mcp_server.py`
- Estrarre da `handle_http_request` la logica comune e aggiungere un parametro di modalità di
  autenticazione (`static` | `oauth`). In modalità `oauth`, `tools/call` senza token valido
  restituisce **401 con `WWW-Authenticate: Bearer resource_metadata="..."`**; in modalità `static`
  il comportamento resta **identico byte per byte**.
- Aggiungere `2025-11-25` a `SUPPORTED_PROTOCOL_VERSIONS` (per `/mcp` la versione
  dichiarata di default non cambia, per non alterare la negoziazione di Claude).
- Rotte in `app.py`: `POST /mcp-oauth2` (stessa gestione manutenzione/405 di `/mcp`).
- Verificare che il parser accetti `Accept: application/json, text/event-stream` e risponda in
  JSON semplice (Streamable HTTP consente la risposta JSON singola).

## Test di non regressione per Claude (bloccanti)
Estendere `dev_mcp_check.py` e aggiungere `pyspendless/test/test_task23_0.py` (DB SQLite isolato,
come task22-0):
1. `POST /mcp` senza token su `tools/call` → **200 + `isError`**, nessun header
   `WWW-Authenticate` (identico a prima).
2. `POST /mcp` con token statico valido → `add_movement` e `list_categories` invariati.
3. `initialize`, `tools/list`, `ping` su `/mcp` senza token → invariati.
4. `GET /.well-known/oauth-protected-resource` e `/.well-known/oauth-authorization-server`
   (path root) → **404 JSON** come oggi; idem `/.well-known/openid-configuration`.
5. `GET/DELETE /mcp` → 405 JSON invariato; modalità manutenzione → 503 su `/mcp`.
6. Confronto di una batteria di risposte `/mcp` salvate prima della modifica (golden file)
   con quelle dopo: devono coincidere.
7. Nuovi test OAuth: authorize/token con PKCE corretto e errato, codice riusato, `redirect_uri`
   non in whitelist, `resource` errato, token scaduto (→ 401 su `/mcp-oauth2`),
   `client_credentials` che non può chiamare `tools/call`, token Alexa **rifiutato** su `/mcp` e
   token statico **rifiutato** su `/mcp-oauth2`.
8. Prima del tag: provare dal vivo che il connettore claude.ai esistente continua a funzionare
   (chiamata a `list_categories`) **e** che l'aggiunta di un connettore nuovo con la stessa URL
   `/mcp` non apra alcun flusso OAuth.

## Stato dell'integrazione Alexa (sessione del 19/10/2026)

Scelta di architettura: **Custom Skill it-IT + Lambda bridge**, non l'add-on MCP
di Alexa+ (non disponibile in italiano). La Lambda parla JSON-RPC a
`/mcp-oauth2` usando l'access token che Alexa le passa nella envelope
(`context.System.user.accessToken`), ottenuto via Account Linking.

Fatto e verificato:
- **Server in produzione**: `/version` = 0.3.0, `/mcp-oauth2` senza token → 401
  con `WWW-Authenticate: Bearer resource_metadata="..."`, metadata su
  `/.well-known/oauth-protected-resource/mcp-oauth2` e
  `/.well-known/oauth-authorization-server/oauth` → 200. Radice `.well-known`
  invariata (404 JSON), Claude non coinvolto.
- **Lambda `alexa-mcp-bridge`** (eu-west-1, `arn:aws:lambda:eu-west-1:662578989604:function:alexa-mcp-bridge`,
  python3.13, timeout 10s): esiste, è Active, il codice caricato coincide con
  `lambda_function.py` in repo. Aggiunta la variabile d'ambiente
  `MCP_SERVER_URL=https://tabuto.pythonanywhere.com/mcp-oauth2` (prima assente:
  funzionava per il default nel codice).
- **Invocazioni di prova** con envelope Alexa sintetiche (`aws lambda invoke`):
  `LaunchRequest` → frase di benvenuto; `AddMovementIntent` senza accessToken →
  `LinkAccountCard`; con accessToken finto → la Lambda raggiunge il server di
  produzione, riceve 401 e risponde `LinkAccountCard`. Il percorso di rete
  AWS → PythonAnywhere funziona.
- **Patch «`resource` facoltativa»** (questa sessione, da rilasciare): l'Account
  Linking di una Custom Skill è OAuth2 puro e **non manda `resource`** (RFC 8707
  è cosa da client MCP), quindi `/oauth/authorize` lo rifiutava con
  `invalid_target`: era il blocco certo del flusso. Ora se manca si assume
  `{BASE_URL}/mcp-oauth2`; se c'è deve coincidere come prima. In più
  `redirect_uri` nella richiesta di token è diventato facoltativo (RFC 6749
  §4.1.3 lo impone solo se era nell'authorize, e non è documentato cosa manda
  Alexa): se c'è viene confrontato, se manca il codice resta legato al client
  autenticato e al PKCE. File: `oauth_server.py`, `repository.py`
  (`redeem_oauth_code`), `test/test_task23_0.py` (62 controlli, verde).
- **Variabili OAuth**: aggiunte a `pyspendless/.env` e `pyspendless/.env_pa`
  locali — `OAUTH_ALEXA_CLIENT_ID=alexa-pyspendless`,
  `OAUTH_ALEXA_CLIENT_SECRET` (64 hex generati con `openssl rand -hex 32`,
  stesso valore nei due file), `OAUTH_ALEXA_REDIRECT_URIS` vuota in attesa dei
  redirect URI della console. Attenzione: `conf.py` carica **solo `.env`**, non
  `.env_pa`, quindi sul server la copia che conta è `pyspendless/.env`.
- **Produzione verificata dal vivo** dopo il Reload con le variabili caricate:
  authorize con i parametri esatti di Alexa (senza `resource`) → `302 /login`;
  vendor id diverso → `400 redirect_uri non registrato`; senza PKCE → redirect
  ad Alexa con `error=invalid_request` e `state` preservato.
- **Modello di interazione rifatto**: il primo build sulla console è fallito con
  «cannot include both a phrase slot and another intent slot» su tutte e sei le
  utterance di `AddMovementIntent`. `AMAZON.SearchQuery` è un *phrase slot* e
  non può stare in una frase insieme a un altro slot, mentre `category`,
  `wallet` e `note` erano tutti `SearchQuery` e convivevano con `{amount}`. Ora
  `category`/`wallet` sono slot type custom (`CategoryName`, `WalletName`, seme
  generico da sostituire con i valori veri dell'account) e `note` è fuori dal
  modello; `lambda_function.py` non cambia (legge `note` solo se presente).
  Dettagli e limiti residui in `alexa-mcp-lambda/README.md`.

Fatto il 20/10/2026 (punti 1-6 della lista originale, tutti chiusi):
1. Patch «`resource` facoltativa» rilasciata: `v0.3.1` in produzione, mergiata
   in `origin/main` (PR #2).
2. Skill creata, **Skill ID `amzn1.ask.skill.cc3d1431-701a-4f36-acf0-af88083e400a`**,
   locale it-IT, modello Custom, hosting *Provision your own*, endpoint
   `arn:aws:lambda:eu-west-1:662578989604:function:alexa-mcp-bridge` nel campo
   *Default Region*. Un primo tentativo era stato creato **Alexa-hosted**: in
   quel caso l'endpoint è bloccato sul reflector di Amazon
   (`arn:aws:lambda:us-east-1:318883658404:function:ReflectorTemplateSkill`), la
   Lambda nostra non viene mai invocata e l'hosting non si cambia — la skill va
   ricreata. Il vendor id non cambia, quindi i redirect URI e il `.env` del
   server restano validi; cambia solo lo Skill ID.
3. Account Linking configurato con PKCE S256.
4. `OAUTH_ALEXA_*` impostate nel `.env` sul server + Reload. Redirect URI del
   vendor `MMFCHA6BHYFHR`.
5. Trigger: `statement-id alexa-skills-kit-trigger-v2` vincolato allo Skill ID
   nuovo, quello della skill ricreata rimosso. Nota: la console **valida la
   resource policy della Lambda** quando salvi l'endpoint, quindi il permesso va
   aggiunto prima, altrimenti risponde `SkillManifestError`.
6. Provato dal vivo: la skill si apre e gli intent arrivano alla Lambda
   (CloudWatch: nove invocazioni, 330-760 ms per quelle che interrogano il
   server, nessuna eccezione).

Da fare:
- Sostituire il seme generico di `CategoryName`/`WalletName` con le categorie e
  i wallet veri dell'account, e rifare il Build Model.
- Prova sull'Echo fisico, poi Beta Testing per i familiari (richiede prima i
  metadati di distribuzione: descrizioni, frasi di esempio, icone, URL di
  privacy e termini).

Rischi noti ancora aperti:
- Il login di PySpendless passa da Google OAuth: se l'app Alexa aprisse il
  collegamento in una webview incorporata, Google può rifiutare con
  `disallowed_useragent`. Le versioni recenti dell'app usano il browser di
  sistema; se succede, si collega l'account da `alexa.amazon.it` in un browser.
- Latenza di PythonAnywhere gratuito: la Lambda ha timeout 10s, Alexa ~8s. Se le
  risposte arrivano lente la skill risponde con la frase di errore generica.

## Rilascio e rollback
- Nuova versione (`_APP_VERSION`) + tag, deploy con il workflow esistente; verificare
  `GET /version`.
- Variabili d'ambiente OAuth da impostare **prima** del deploy sul server PythonAnywhere.
- Rollback: tornare al tag precedente. Poiché `/mcp` non cambia, Claude non è coinvolto; i token
  `OAUTH_*` nella tabella `Token` possono restare inerti o essere eliminati.

## File toccati (previsti)
- `pyspendless/oauth_server.py` — nuovo (authorize, token, metadata).
- `pyspendless/mcp_server.py` — modalità di autenticazione, 401 solo in modalità `oauth`,
  versione di protocollo.
- `pyspendless/app.py` — rotte `/mcp-oauth2`, blueprint OAuth, metadata sotto path dedicati,
  eccezioni per la modalità manutenzione.
- `pyspendless/repository.py` — `TokenRepository`: creazione e validazione di codici e access
  token OAuth.
- `pyspendless/conf.py` — variabili d'ambiente OAuth.
- `pyspendless/templates/` — pagina di consenso, sezione "Connessioni" nel profilo.
- `pyspendless/dev_mcp_check.py`, `pyspendless/test/test_task23_0.py` — test.
- `CLAUDE.md` / `backlog/` — documentazione.

## Punti aperti (da chiarire prima di scrivere codice)
1. **Redirect URI di Alexa** e se serve `client_secret_post` oltre a HTTP Basic.
2. **Refresh token** per `authorization_code`: la documentazione dice solo che non vanno emessi
   per `client_credentials`. Senza refresh l'utente dovrebbe riautorizzare ogni ora: verificare
   cosa si aspetta Alexa e quale durata/rotazione adottare.
3. Se la sonda di Claude richiede anche i path con suffisso (`/oauth`) e come reagisce (test 8).
4. Se il piano gratuito di PythonAnywhere accetta il traffico e la latenza richiesti da Alexa
   (< 500 ms) e se il dominio `pythonanywhere.com` è accettato da Amazon.
5. Se `it-IT` è supportato per gli add-on sull'account.
6. Se serve un tetto di importo e una conferma vocale per `add_movement` via Alexa.
7. Se mantenere un solo client OAuth (Alexa) o prevedere altri client in futuro.

## Criteri di accettazione
- [ ] Tutti i test di non regressione su `/mcp` passano con risposte identiche a prima.
- [ ] Il connettore claude.ai esistente funziona dopo il deploy senza essere rimosso e riaggiunto.
- [ ] Flusso `authorization_code` + PKCE completo da web simulator Alexa.
- [ ] `client_credentials` funzionante e limitato a metodi senza dati utente.
- [ ] `add_movement` da Echo registra la spesa nell'account e wallet corretti (preferito
  dell'utente).
- [ ] Revoca della connessione Alexa dal profilo invalida i token emessi.
- [ ] Nessun segreto nel repo.
