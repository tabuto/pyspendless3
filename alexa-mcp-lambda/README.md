# alexa-mcp-lambda

Funzione Lambda che fa da backend per una Alexa Custom Skill (invocation name
`spendless`) e inoltra le richieste al server MCP di PySpendless esposto su
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
   L'invocation name è `spendless`, quindi la frase di attivazione è «Alexa,
   apri spendless». Era `spese di famiglia`, cambiato il 20/10/2026: nel
   simulatore funzionava, ma sul dispositivo e nell'app no — «spese» è la parola
   della lista della spesa, e nell'arbitraggio vocale (che il simulatore salta,
   perché punta diritto allo stage Development) le funzionalità native di Alexa
   vincono sulle skill.

   Due regole Amazon da tenere a mente se lo si cambia di nuovo: le **launch
   phrase** (`apri`, `chiedi a`, `avvia`…) non possono starci dentro — sono il
   verbo, non il nome — e i nomi di **una sola parola** sono ammessi solo per
   marchi propri. La seconda regola la verifica la *certificazione*, non il
   build: per una skill che resta in Development o Beta per uso familiare
   `spendless` passa, ma se un giorno la si pubblicasse servirebbe un nome di
   due parole (`spendless famiglia`, `il mio spendless`).
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
- La direttiva **pretende un dialog model** nell'interaction model, e i sample a
  livello di slot sono rifiutati senza di esso:

  ```
  Slot "note" in intent "AddMovementIntent" includes samples,
  which is not supported in a skill without a dialog model
  ```

  Attenzione a come lo si scrive: un dialog model con **tutti** gli slot a
  `elicitationRequired: false` è formalmente valido secondo lo schema, ma la
  console lo pota — non chiede niente, quindi per lei non esiste — e il build
  torna a lamentare i sample. Perciò `note` ha `elicitationRequired: true` con un
  prompt vero (`Elicit.Slot.Note` nell'array `prompts`), che tiene in vita il
  dialog model. Non cambia il comportamento: con `delegationStrategy:
  SKILL_RESPONSE` il controllo resta alla skill a ogni turno, e `Dialog.ElicitSlot`
  usa comunque la frase che gli passiamo noi, non i prompt del modello (lo dice
  la documentazione della direttiva).
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

## Categorie per utente: entità dinamiche, non valori nel modello

I valori di `CategoryName` e `WalletName` nel JSON sono un **segnaposto
strutturale**, un elenco generico di categorie italiane. Non sono i dati veri e
non devono diventarlo: l'interaction model è **globale per la skill**, mentre
categorie e wallet appartengono a ogni singolo account PySpendless — scolpire
quelle di un utente nel modello romperebbe il riconoscimento per tutti gli
altri familiari.

Il meccanismo giusto è `Dialog.UpdateDynamicEntities`: a ogni apertura della
skill la Lambda chiama `list_categories`, legge il campo `structuredContent`
della risposta MCP (che il server già produce: `categories[].name`,
`wallets[].name/.code`) e sostituisce i valori dei due slot type per la durata
della sessione, con `updateBehavior: REPLACE`. Vedi `load_dynamic_entities()`.

Perché serve davvero: in teoria gli slot type custom non sono una whitelist
chiusa — Alexa restituisce anche valori fuori elenco, e il server fa poi un
confronto normalizzato con fuzzy match in
`resolve_category`/`resolve_wallet` — ma in pratica, se il valore detto non
somiglia a nessuno di quelli noti, l'NLU **non associa affatto la frase
all'intent**: arriva `FallbackIntent` e la skill risponde «non ho capito». È
successo con `registra 85 su baby`, dove `baby` non era fra i valori statici.

Limiti e comportamenti da conoscere:

- Le entità dinamiche valgono **per la sessione** (o 30 minuti), e vengono
  caricate sulla `LaunchRequest`: il flusso normale («Alexa, apri spendless»,
  poi la frase) è sempre coperto.
- Un'invocazione **in un colpo solo** («Alexa, chiedi a spendless di registrare
  85 su baby») arriva prima che le entità esistano, quindi può non essere
  riconosciuta. Per quello `FallbackIntentHandler`, la prima volta in una
  sessione, le carica e chiede di ripetere: al secondo tentativo la categoria è
  nota. Il flag `entities_loaded` in sessione evita di richiamare il server a
  ogni fallback.
- Se l'account non è collegato o il server non risponde, il caricamento viene
  salvato: la skill si apre comunque e si degrada ai valori statici.
- L'apertura costa una chiamata HTTP in più (~0,4-0,6 s verso PythonAnywhere),
  una sola per sessione.

Quando si cambiano categorie in PySpendless **non serve toccare la skill né
rifare il Build Model**: la prossima apertura le rilegge da sola.

Le utterance di `AddMovementIntent` coprono le preposizioni `per`/`di`/`su`/`in`
e l'importo sia con sia senza la parola «euro» (`registra 85 su baby` e
`registra 85 euro per baby` vanno entrambe). Una nota sull'ambiguità: `su` è
riservato alla **categoria**, il wallet si indica solo nominandolo
(`sul wallet contanti`, `con il wallet contanti`) — con entrambe le forme
`su {category}` e `su {wallet}` l'NLU non avrebbe modo di distinguerle.

Altri limiti noti del modello:

- `AMAZON.NUMBER` non cattura i centesimi: «venti euro e cinquanta» arriva come
  `20`. Per ora gli importi si dettano interi.
- `AddMovementIntent` pretende importo e categoria **nello stesso turno**:
  l'unico slot elicitato è `note`, se mancano gli altri la skill chiede di
  ripetere la frase per intero.

## Test

1. Nel developer console, tab **Test** → abilita test in stage "Development"
   (su una skill appena creata parte da *Off*).
2. Simulatore: `apri spendless`, poi `registra 20 euro per spesa alimentare`,
   poi `sì` e la nota a voce.
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
