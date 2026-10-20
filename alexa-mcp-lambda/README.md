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

## Modello di interazione: il vincolo dei phrase slot

La prima versione usava `AMAZON.SearchQuery` per `category`, `wallet` e `note`.
**Non compila**: `SearchQuery` è un *phrase slot*, e Alexa rifiuta ogni
utterance che contenga un phrase slot insieme a un altro slot — quindi
«registra {amount} euro per {category}» è illegale. Errore del build:

```
Sample utterance "..." cannot include both a phrase slot and another intent slot.
```

Perciò `category` e `wallet` sono **slot type custom** (`CategoryName`,
`WalletName`), che possono convivere con `{amount}`.

Lo slot `note` resta `AMAZON.SearchQuery` — una nota libera non può essere
altro — ma non appare in nessuna utterance dell'intent: viene raccolto in un
**turno dedicato**, dove è l'unico slot in gioco e il vincolo non si applica.
La documentazione Amazon lo dice esplicitamente: la carrier phrase è
obbligatoria nelle sample utterance dell'intent, con l'unica eccezione dei
**sample a livello di slot**, dove `{note}` da solo è legale.

## Il dialogo sulla nota

```
U: registra 20 euro per spesa alimentare
A: Ho una spesa di 20 euro per spesa alimentare. Vuoi aggiungere una nota?
U: sì
A: Dimmi la nota.                        <- direttiva Dialog.ElicitSlot su `note`
U: cena fuori con i nonni
A: Registrata spesa di 20,00 € ...       <- risposta di add_movement
```

Come è fatto:

- Il primo turno **non registra niente**: mette il movimento negli *attributi di
  sessione* (`pending_movement`), che Alexa rimanda indietro a ogni turno. La
  Lambda resta senza stato proprio, nessun database di appoggio.
- «Sì» risponde con `Dialog.ElicitSlot` su `note`, con `updatedIntent` che
  riporta importo, categoria, wallet e tipo già riempiti: Alexa non li richiede.
  La direttiva **pretende un dialog model** nell'interaction model — c'è,
  con `delegationStrategy: SKILL_RESPONSE` e tutti gli slot a
  `elicitationRequired: false`, perché i prompt li diciamo noi dal codice.
- «No» registra subito senza nota.
- Mentre Alexa elicita uno `AMAZON.SearchQuery`, *qualunque* frase finisce nello
  slot: un «no» detto in quel turno arriverebbe come nota con testo «no». Per
  questo `NOTE_DECLINED` e `NOTE_CANCELLED` in `lambda_function.py`
  intercettano i rifiuti e gli annullamenti detti al posto della nota.
- Se la sessione finisce con un movimento ancora in attesa (l'utente si
  allontana, scadono i reprompt), `SessionEndedRequestHandler` lo registra
  comunque **senza nota**: l'intenzione dichiarata era registrarlo, e perderlo
  in silenzio sarebbe peggio. Un doppione è escluso dal controllo
  anti-duplicato del server.
- `AMAZON.YesIntent`/`AMAZON.NoIntent` hanno anche un handler per quando non c'è
  nulla in sospeso: senza di quello il dispatcher solleva un'eccezione e
  l'utente si sente dire «si è verificato un errore».

La nota finisce in `Movement.note`, cioè il campo **Nota** del form di
PySpendless: il server non è stato toccato, `add_movement` accettava già
quell'argomento.

Il flusso è coperto da `test_dialog.py` (36 controlli): fa girare
`lambda_function.handler` su envelope costruite a mano, con `requests.post`
sostituito da un finto server MCP, riportando gli attributi di sessione da un
turno al successivo come fa Alexa.

```bash
cd alexa-mcp-lambda && .venv/bin/python test_dialog.py
```

I valori dei due slot type custom in repo sono un **seme generico** di categorie
e wallet italiani: gli slot type custom non sono una whitelist chiusa (Alexa
restituisce anche valori fuori elenco, e il server fa poi un confronto
normalizzato con fuzzy match in `resolve_category`/`resolve_wallet`), ma il
riconoscimento vocale è molto più preciso sui valori elencati. Conviene quindi
sostituirli con le categorie e i wallet veri dell'account — si leggono con
`elenca le categorie` dalla skill stessa, o dalle pagine Impostazioni di
PySpendless — e rifare il **Build Model**.

Altri limiti noti del modello:

- `AMAZON.NUMBER` non cattura i centesimi: «venti euro e cinquanta» arriva come
  `20`. Per ora gli importi si dettano interi.
- `AddMovementIntent` pretende importo e categoria **nello stesso turno**:
  l'unico slot elicitato è `note`, se mancano gli altri la skill chiede di
  ripetere la frase per intero.

## Test

1. Nel developer console, tab **Test** → abilita test in stage "Development"
   (su una skill appena creata parte da *Off*).
2. Simulatore: `apri spese di famiglia`, poi `registra 20 euro per spesa
   alimentare`, poi `sì` e la nota a voce.
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
- `AddMovementIntent` richiede amount e category nello stesso turno vocale: se
  mancano, la skill chiede di ripetere la frase per intero. L'unico slot
  elicitato in un turno a parte è `note` (vedi "Il dialogo sulla nota").
- La Lambda logga a livello INFO l'intent servito, gli argomenti passati al
  server e l'esito (`isError` + prima riga della risposta): le prove si leggono
  dal log group `/aws/lambda/alexa-mcp-bridge` senza dover riferire a mano cosa
  ha detto Alexa. Nessun token viene mai scritto nel log.
