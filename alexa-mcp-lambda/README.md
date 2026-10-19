# alexa-mcp-lambda

Funzione Lambda che fa da backend per una Alexa Custom Skill ("spese di
famiglia") e inoltra le richieste al server MCP di PySpendless esposto su
`https://tabuto.pythonanywhere.com/mcp-oauth2` (endpoint OAuth2, task23-0).

Sottoprogetto isolato: dipendenze e virtualenv propri, separati da quelli di
`pyspendless/` (vedi `.venv/` e `requirements.txt` in questa cartella).

Tool esposti dal server e usati qui: `add_movement` (scrittura), `list_categories`
(lettura). Protocollo: JSON-RPC 2.0 stateless — `tools/call` si invoca
direttamente, senza handshake `initialize` preventivo.

## Setup locale

```bash
cd alexa-mcp-lambda
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Build del pacchetto di deploy

Lambda richiede le dipendenze "vendored" insieme al codice in uno zip:

```bash
rm -rf build lambda-package.zip
mkdir build
.venv/bin/pip install -r requirements.txt -t build/
cp lambda_function.py build/
cd build && zip -r ../lambda-package.zip . -x "*.pyc" && cd ..
```

## Creazione della funzione (prima volta)

```bash
aws lambda create-function \
  --function-name alexa-mcp-bridge \
  --runtime python3.13 \
  --role arn:aws:iam::662578989604:role/alexa-mcp-lambda-role \
  --handler lambda_function.handler \
  --zip-file fileb://lambda-package.zip \
  --timeout 10 \
  --environment "Variables={MCP_SERVER_URL=https://tabuto.pythonanywhere.com/mcp-oauth2}"
```

## Aggiornamenti successivi del codice

```bash
aws lambda update-function-code \
  --function-name alexa-mcp-bridge \
  --zip-file fileb://lambda-package.zip
```

## Creazione della skill su developer.amazon.com

1. **Create Skill** → nome "PySpendless" (o simile), locale **Italian (IT)**,
   modello **Custom**, metodo di hosting **Provision your own**.
2. **Interaction Model** → **JSON Editor** → incolla il contenuto di
   `interaction-model.it-IT.json` di questa cartella → **Save** → **Build Model**.
   L'invocation name proposto è `spese di famiglia`: cambialo pure se preferisci
   altro, purché rispetti le regole Amazon (minuscolo, niente parole riservate
   tipo nomi di dispositivi Alexa).
3. **Endpoint** → scegli **AWS Lambda ARN**, regione **Europe (Ireland)**, e
   incolla l'ARN restituito da `aws lambda create-function` (sopra).
4. **Account Linking** (sezione nel menu Build), con i valori:
   - **Authorization Grant Type**: Auth Code Grant
   - **Authorization URI**: `https://tabuto.pythonanywhere.com/oauth/authorize`
   - **Access Token URI**: `https://tabuto.pythonanywhere.com/oauth/token`
   - **Client ID**: il valore di `OAUTH_ALEXA_CLIENT_ID` impostato in `.env_pa`
   - **Client Secret**: il valore di `OAUTH_ALEXA_CLIENT_SECRET`
   - **Client Authentication Scheme**: HTTP Basic (credentials in request body va bene come fallback)
   - **Scope**: `profile` (valore libero, il server non valida contro una lista fissa)
   - **Domain list**: lascia vuoto
   - **PKCE**: attiva "Proof Key for Code Exchange (PKCE)" con metodo **S256**
     (obbligatorio: il server rifiuta richieste senza `code_challenge`)
5. Salvando, Alexa mostra 3 **Redirect URI** (dominio `pitangui.amazon.com`,
   `layla.amazon.com`, `alexa.amazon.co.jp`). Copiali tutti e impostali,
   separati da virgola, in `OAUTH_ALEXA_REDIRECT_URIS` sul server, poi fai
   **Reload** della web app su PythonAnywhere.

   > Attenzione: `pyspendless/conf.py` carica **solo `pyspendless/.env`**.
   > `.env_pa` è la copia di riferimento dei valori di produzione, ma il file
   > che l'app legge davvero sul server è `.env`: le tre `OAUTH_ALEXA_*` vanno
   > scritte là (o copiate da `.env_pa` a `.env`), altrimenti il client resta
   > non registrato e `/oauth/authorize` risponde «client_id non riconosciuto».
6. **Permissions** → non serve nulla di speciale per questi 2 tool.

## Collegare il trigger Alexa Skills Kit alla Lambda

Dopo aver creato la skill, prendi lo **Skill ID** (visibile nell'URL della
console, `amzn1.ask.skill.xxxxxxxx`):

```bash
aws lambda add-permission \
  --function-name alexa-mcp-bridge \
  --statement-id alexa-skills-kit-trigger \
  --action lambda:InvokeFunction \
  --principal alexa-appkit.amazon.com \
  --event-source-token <amzn1.ask.skill.xxxxxxxx>
```

## Test

1. Nel developer console, tab **Test** → abilita test in stage "Development".
2. Simulatore: prova `apri spese di famiglia`, poi `registra 20 euro per spesa alimentare`.
3. Alla prima chiamata autenticata ti chiederà di collegare l'account (Account
   Linking): segui il link, fai login su PySpendless, autorizza.
4. Per i familiari: **Beta Testing** (tab Distribution) → invita via email,
   nessuna certificazione richiesta per uso personale/familiare.

## Note

- `call_mcp_tool` in `lambda_function.py` legge l'access token OAuth
  direttamente dalla request envelope di Alexa
  (`context.System.user.accessToken`), ottenuto automaticamente da Account
  Linking: la Lambda non gestisce né richiede token da sola.
- Gestione errori 401/403 dal server → risposta con `LinkAccountCard`, che in
  Alexa invita l'utente a ricollegare l'account (token scaduto/revocato).
- `AddMovementIntent` richiede amount e category nello stesso turno vocale
  (nessuna elicitazione multi-turno degli slot in questa prima versione): se
  mancano, la skill chiede di ripetere la frase per intero.
