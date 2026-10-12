# Task 23.0: OAuth 2.x per il server MCP — integrazione con Alexa+ (retrocompatibile con Claude)

**Stato**: da pianificare — nessun file di codice toccato.
**Repo**: `tabuto/pyspendless3`, branch `master` (file da creare: `backlog/task23-0.md`).
**Dipende da**: task20-0 (server MCP), task22-0 (wallet preferito per utente).

## Obiettivo
Rendere il server MCP di PySpendless collegabile ad **Alexa+** (add-on MCP), che richiede
OAuth 2.x con PKCE, **senza alterare in alcun modo** il funzionamento attuale con il
connettore claude.ai (token statico personale in header, errori di autenticazione come
`200 + isError`, mai 401).

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

## Soluzione proposta: risorsa separata `/mcp-alexa`, `/mcp` invariato

### Principio
Due porte d'ingresso allo **stesso codice dei tool** (`TOOL_DEFINITIONS`, `_dispatch`,
`_tool_*`), con autenticazione diversa:

| | `/mcp` (Claude, invariato) | `/mcp-alexa` (nuovo) |
|---|---|---|
| Credenziale | token statico (invariato) | access token OAuth |
| Auth mancante/errata | `200 + isError`, mai 401 | **`401` + `WWW-Authenticate`** (`resource_metadata=...`) |
| Metadata discovery | nessuno (404 JSON invariato) | `/.well-known/oauth-protected-resource/mcp-alexa` |
| Metodi pubblici | `initialize`, `tools/list`, `ping` | `initialize`, `tools/list`, `ping` (come oggi) |

### Metadata OAuth senza toccare l'origine
- Il **path root** `/.well-known/oauth-protected-resource` e
  `/.well-known/oauth-authorization-server` **restano 404 JSON** (comportamento attuale,
  quello che la sonda di Claude si aspetta).
- Il Protected Resource Metadata va **solo** sul path della nuova risorsa:
  `/.well-known/oauth-protected-resource/mcp-alexa`.
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
  `resource` == URI di `/mcp-alexa`.
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
- Rotte in `app.py`: `POST /mcp-alexa` (stessa gestione manutenzione/405 di `/mcp`).
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
   non in whitelist, `resource` errato, token scaduto (→ 401 su `/mcp-alexa`),
   `client_credentials` che non può chiamare `tools/call`, token Alexa **rifiutato** su `/mcp` e
   token statico **rifiutato** su `/mcp-alexa`.
8. Prima del tag: provare dal vivo che il connettore claude.ai esistente continua a funzionare
   (chiamata a `list_categories`) **e** che l'aggiunta di un connettore nuovo con la stessa URL
   `/mcp` non apra alcun flusso OAuth.

## Lato Alexa (dopo il rilascio del server)
1. Account sviluppatore Amazon, installazione `alexa-ai` CLI, `alexa-ai configure` (Login with
   Amazon).
2. `alexa-ai new mcp --name "PySpendless" --locale it-IT --mcp-server-url
   https://tabuto.pythonanywhere.com/mcp-alexa`.
3. Compilare `addon-package/addon.json`: descrizioni, 3-4 frasi di esempio, URL privacy/termini
   (pagina statica HTTPS), 6 icone, 1 carousel 600x900, configurazione OAuth (endpoint,
   client id/secret).
4. Registrare in `OAUTH_ALEXA_REDIRECT_URIS` i redirect URI forniti da Amazon.
5. `alexa-ai deploy` (stage di sviluppo) → test nel web simulator, poi sull'Echo.
6. Restare in stage di sviluppo (uso personale); `alexa-ai submit` solo se serve la distribuzione.

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
- `pyspendless/app.py` — rotte `/mcp-alexa`, blueprint OAuth, metadata sotto path dedicati,
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
