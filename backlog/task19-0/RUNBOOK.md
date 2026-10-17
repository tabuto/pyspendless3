# RUNBOOK — Avvio del task 19-0

Come far partire il refactoring su questo Mac, con l'agente principale che
verifica in Chrome e i subagent che lavorano in parallelo su modelli più
piccoli.

---

## 1. Prerequisiti, una volta sola

### 1.1 Spostare le agent definition in `.claude/agents/`

Le tre definizioni sono state create in `backlog/task19-0/agents/` solo perché
`.claude/` è una posizione protetta in scrittura **per l'assistente**, non per
te. La loro casa definitiva è `.claude/agents/`.

Non è una copia da tenere allineata: `.claude/` **non è in `.gitignore`** (lì
dentro ci sono già `launch.json` e `settings.local.json`), quindi i file
restano versionati esattamente come prima. Quindi `mv`, non `cp`:

```bash
cd /Users/fradidio/Sviluppo/pyspendless3
mkdir -p .claude/agents
mv backlog/task19-0/agents/*.md .claude/agents/
rmdir backlog/task19-0/agents
```

Da quel momento Claude le trova da sola: i subagent definiti in
`.claude/agents/` del repo vengono rilevati automaticamente a inizio sessione.

**Verifica**: in una nuova sessione, i tipi `ps-markup`, `ps-contract` e
`ps-component` compaiono fra gli agent disponibili.

#### Perché non basta referenziarle da `backlog/`

`subagent_type` accetta un **nome** (`ps-markup`), non un percorso. La
registrazione avviene scansionando `.claude/agents/` del progetto e
`~/.claude/agents/` dell'utente: non c'è modo di puntare a una cartella
arbitraria.

Esiste un ripiego senza installare nulla — usare il tipo `general-purpose`
passando il file come istruzione ("leggi `…/ps-markup.md` e segui quelle
istruzioni") e forzando `model` sulla singola invocazione. L'allocazione dei
modelli funziona lo stesso, perché il parametro `model` della chiamata ha
precedenza su tutto.

Si perde però la cosa che conta: la riga `tools:` nel frontmatter smette di
essere una **restrizione** e diventa un suggerimento. `ps-contract` dichiara
`tools: Read, Grep, Glob` e come agent registrato *non può* scrivere file —
garanzia utile, visto che gira in Fase 0, quando nessuno deve toccare il
markup. Via prompt, quella garanzia non c'è.

### 1.2 Avviare l'applicazione

**L'agente non può avviarla da solo**, per due motivi che si sommano: la shell
dell'agente non è il Mac (è un sandbox o una VM isolata, e Chrome non ne
raggiunge il `localhost`), e computer use concede ai terminali solo il livello
"click" — digitare è bloccato.

Quindi la avvii tu, e la lasci girare:

```bash
cd /Users/fradidio/Sviluppo/pyspendless3
export OAUTHLIB_INSECURE_TRANSPORT=1
.venv/bin/python pyspendless/app.py
```

Verifica che `http://localhost:5000/version` risponda con il JSON della
versione. Se vuoi evitare di rifarlo ogni volta, un `launchd` plist al login
risolve.

### 1.3 Chrome

Claude in Chrome installato e impostato come **browser preferito**. Fai login
a PySpendless con Google una volta, nel tuo Chrome: da lì in poi l'agente
arriva su `/home` senza toccare credenziali — cosa che comunque non farebbe.

### 1.4 Mac sempre sveglio

La sessione gira in cloud, ma **file locali e browser passano dall'app Claude
Desktop**: se il Mac dorme o l'app è chiusa, l'agente perde l'accesso a
entrambi. Disattiva lo sleep per la durata del lavoro.

### 1.5 DB di sviluppo popolato

Requisiti in `fasi/fase-0.md` §0.1. Senza, metà delle verifiche non è
osservabile e il test di contratto va in `SkipTest`.

---

## 2. Come avviare la sessione

**Sul Mac, dall'app desktop.** È il punto che conta: una sessione in cloud
raggiunge i file locali e il browser **solo** se è stata avviata da desktop.
Se la fai partire dal telefono, non vede il repo.

Poi la controlli da dove vuoi — telefono, web — ed è la stessa sessione.

### Modello della sessione principale

Impostalo su **Opus** (o Sonnet) dal selettore. L'agente principale fa il
lavoro che non si può delegare: orchestrazione, verifica in Chrome, giudizio
sugli screenshot, decisioni sui punti aperti.

### Prompt di avvio

```
Leggi backlog/task19-0.md e backlog/task19-0/RUNBOOK.md.
Partiamo dalla Fase 0: backlog/task19-0/fasi/fase-0.md.
L'app gira su http://localhost:5000, sono già loggato in Chrome.
Non passare alla fase successiva senza avermi mostrato i criteri di
accettazione soddisfatti.
```

---

## 3. Allocazione dei modelli

| Chi | Modello | Perché |
|---|---|---|
| **Agente principale** | opus / sonnet | Orchestra, verifica in Chrome, giudica gli screenshot, decide sui punti aperti. È l'unico che vede il risultato visivo. |
| `ps-markup` | **haiku** | Conversione meccanica guidata da una tabella, con criteri di accettazione verificabili da un test. Molto lavoro, poca decisione. |
| `ps-contract` | **haiku** | Estrazione in sola lettura. Serve precisione e pazienza, non ragionamento. |
| `ps-component` | **sonnet** | `ps-ui.js`, ordine degli eventi, skin DataTables, tema Chart.js. Qui si replica comportamento sottile: haiku non basta. |

Il modello si cambia nel frontmatter della definizione, oppure caso per caso
all'invocazione. Se un `ps-markup` su haiku restituisce lavoro impreciso su una
pagina complessa, quella pagina si rilancia su sonnet — senza riscrivere la
definizione.

### Regola pratica

Haiku va bene quando **il criterio di "fatto" è un exit code**. Dove il
criterio è "sembra giusto", serve un modello più grande, o un umano.

---

## 4. Regole di orchestrazione

### 4.1 Worktree sì, ma solo per i subagent

⛔ **La sessione principale NON va avviata in un worktree.** Niente
`claude --worktree`, niente opzione equivalente nell'app.

Il motivo è concreto: Flask gira dal checkout principale
(`/Users/fradidio/Sviluppo/pyspendless3`) e Chrome punta a `localhost:5000`.
Se la sessione girasse in un worktree, l'agente modificherebbe file in
un'altra directory mentre il browser continua a mostrare il checkout
principale — verificherebbe codice che non ha scritto, e non se ne
accorgerebbe.

✅ **I subagent `ps-markup`, invece, sì.** `isolation: worktree` sta nel
frontmatter della loro definizione, quindi vale sempre e l'orchestratore non
se ne deve ricordare:

```yaml
---
name: ps-markup
model: haiku
isolation: worktree
---
```

Così quattro pagine indipendenti si convertono in parallelo senza conflitti, e
un agente su haiku non può toccare il checkout principale mentre l'agente
principale sta verificando qualcosa in Chrome.

`ps-component` e `ps-contract` **non** usano worktree: il primo lavora in
sequenza su fasi che vanno verificate subito nel browser, il secondo non scrive
niente.

Da cui la regola che genera le due tabelle di criteri in ogni file di fase:

- i subagent **non aprono mai il browser** — si fermano a ciò che si verifica
  con test e grep;
- la verifica visiva la fa **l'agente principale, dopo il merge**, sul checkout
  principale.

#### ⚠️ Un worktree non ha i file ignorati da git

Un `git worktree` contiene solo i file **tracciati**. Restano fuori proprio i
due che servono a far girare l'app:

- **`.venv/`** → dentro il worktree `.venv/bin/python` non esiste;
- **`pyspendless/.env`** → senza, `conf.py` non trova `DATABASE_URL` né
  `SECRET_KEY`, e l'import dell'app fallisce.

Quindi il criterio di rilascio dei subagent (`exit code 0` sul test di
contratto) in un worktree **non funzionerebbe affatto**.

La soluzione non è un passo manuale: **`tools/worktree-bootstrap.sh` è
versionato**, quindi esiste già dentro ogni worktree appena creato. Il subagent
lo esegue come primo comando:

```bash
./tools/worktree-bootstrap.sh          # prepara
./tools/worktree-bootstrap.sh --test   # prepara ed esegue il contratto
```

Cosa fa:

1. trova il checkout principale con `git rev-parse --git-common-dir`, che
   funziona anche da dentro un worktree secondario — niente percorsi scritti a
   mano;
2. collega `pyspendless/.env` al file del checkout principale, se manca;
3. sceglie fra i **due** virtualenv del repo (`.venv/` e `pyspendless/.venv/`)
   quello che ha davvero Flask installato, risolvendo l'ambiguità segnalata
   al §5;
4. avvisa se `DATABASE_URL` è ancora un percorso relativo (da un worktree
   punterebbe a un file inesistente);
5. stampa il comando esatto del test — interprete dal checkout principale,
   codice dal worktree, perché Python mette la cwd in `sys.path`.

Nel checkout principale è un **no-op**: non crea symlink e usa il proprio venv.
Si può quindi eseguire sempre, senza doversi chiedere dove si è. Eseguirlo due
volte non fa danni.

Perché valga davvero, va scritto nella definizione di `ps-markup` come primo
comando della sequenza di lavoro.

### 4.2 Un solo Chrome

Due agent che guidano lo stesso browser insieme fanno disastri. La verifica
nel browser è **sempre seriale** e **sempre dell'agente principale**.

### 4.3 Mai `isolation: "remote"`

Un subagent remoto gira su un'altra macchina: non vede il tuo `localhost`, non
vede il tuo Chrome, non vede il repo che stai modificando. Per questo task non
va usato mai.

### 4.4 Parallelismo per fase

| Fase | Subagent in parallelo |
|---|---|
| 0 | 1 `ps-contract` |
| 1, 2 | 1 `ps-component` (sequenziale) |
| 3 | fino a 4 `ps-markup` |
| 4 | 2 `ps-markup` |
| 5 | fino a 5 `ps-markup` |
| 6 | 1 `ps-component` (sottopassi sequenziali) |
| 7 | 1 `ps-markup` |
| 8 | 1 `ps-component` |
| 9 | nessuno — qui si cancellano file, lo fa il principale |

### 4.5 Nessuna fase parte se la precedente non è verde

Il checkpoint è scritto in fondo a ogni file di fase. Serve a tenere piccolo lo
spazio di ricerca quando qualcosa si rompe.

---

## 5. Il criterio di rilascio dei subagent

Ogni subagent, prima di dichiarare chiuso il proprio task, esegue:

```bash
cd /Users/fradidio/Sviluppo/pyspendless3
.venv/bin/python -m pyspendless.test.test_task19_0
```

> Nel repo ci sono **due** virtualenv: `.venv/` nella root e
> `pyspendless/.venv/`. `test_task22_0.py` usa il secondo,
> `.claude/settings.local.json` registra il primo. Verifica alla Fase 0 quale
> dei due ha le dipendenze e **fissa quello** nei file di fase, così i
> subagent non devono indovinare.

**Exit code 0 oppure il task non è finito.** Più i criteri della tabella
"verificabili dal subagent" del proprio file di fase.

Una regola che vale la pena ripetere agli agent: **il test non si modifica per
farlo passare.** Il CONTRACT è la specifica, il markup è l'implementazione. Se
il test dice che manca un id, va rimesso l'id.

L'unica modifica legittima al file di test durante la migrazione è togliere un
template da `whitelist_non_migrati` quando lo si migra.

---

## 6. Cosa puoi fare dal telefono

- leggere l'avanzamento, fase per fase
- rispondere quando l'agente chiede una decisione (i punti aperti D3, D7, D10,
  D11, D13 arrivano durante il lavoro)
- fermare o ridirigere
- ricevere la notifica a fine fase

Quello che **non** funziona dal telefono: chiudere il Mac. Se il Mac dorme,
la sessione continua a girare ma perde file e browser, e le fasi di verifica
si bloccano.

---

## 7. Gate sul diff — da controllare a ogni fase

```bash
git diff --stat
```

Deve toccare solo: `pyspendless/templates/**`, `pyspendless/static/**`,
`pyspendless/test/**`, `tools/**`, `docs/**`, `backlog/**`,
`.claude/agents/**`, `CLAUDE.md`, `README.md`.

Se compare `pyspendless/app.py`, `models.py`, `repository.py`, `conf.py` o
`report_*.py` → **stop**. Il restyling ha sconfinato dalla presentazione al
comportamento, e l'affermazione "isofunzionale" non è più dimostrabile.

---

## 8. Versionamento

Come da `CLAUDE.md`: l'assistente **non** esegue `git commit`, `git push` né
`git tag` se non glielo chiedi esplicitamente. Le fasi producono modifiche ai
file e si fermano lì.

Suggerimento: un commit per fase, così il rollback è per fase. Ma lo decidi tu.
