# Task 27.0 — Movimenti ricorrenti attesi e non registrati

**Stato**: **PIANIFICATO** — specifica scritta, nessuna riga di codice.
**Data**: 2026-11-16 (specifica)
**Piano per fase**: `fasi/fase-0.md` … `fasi/fase-5.md` in questa cartella. La
specifica dice *cosa e perché*, i file di fase dicono *chi fa cosa e come si
verifica*.
**Versione app di partenza**: `_APP_VERSION = "0.4.1"` ([app.py:38](../../pyspendless/app.py))
**Repo**: `tabuto/pyspendless3`, branch `main`.
**Dipende da**: niente di bloccante. Tocca `RecurrentMovement` (task introdotto
prima del task19-0) e `Movement.recurrent_movement_id`.
**Interferisce con**: task25-0 (localizzazione, `PIANIFICATO`): questo task
introduce stringhe nuove in 3 template. Vedi §11 R2.
**Nuove dipendenze**: **nessuna**. Niente scheduler, niente cron, niente job.
**Vincolo di ambiente**: il virtualenv del progetto è **Python 3.9**
(`pyspendless/.venv`): niente `match`, niente `str | None` nelle annotazioni.

---

## 1. Obiettivo

Far sì che l'app **proponga** una spesa ricorrente quando è attesa nel mese
corrente, è passato il giorno della ricorrenza e nessun movimento del mese la
copre.

Il vincolo che decide tutto il resto:

> **La proposta non è un record: è il risultato di una query sul mese corrente.**

Nessuna tabella di occorrenze, nessun processo pianificato, nessuno stato da
mantenere allineato. Il 1° del mese l'insieme delle proposte si azzera da sé, e
un mese saltato è dimenticato — non perché ci sia codice che lo sopprime, ma
perché la finestra della query è **solo** il mese corrente. Questo è il modo in
cui il requisito "non mi interessa recuperare il passato" diventa una proprietà
del disegno invece che una regola da ricordare.

### Criteri di accettazione

| # | Criterio |
|---|---|
| A1 | Una spesa ricorrente con giorno atteso 15, al 15 del mese e senza movimento del mese legato, compare fra le proposte. Al 14 no. |
| A2 | Registrare il movimento dalla proposta fa sparire la proposta, senza nessuna azione aggiuntiva. |
| A3 | Una spesa ricorrente con giorno atteso 31 è proposta dal 28 febbraio (clamp all'ultimo giorno del mese). |
| A4 | Un movimento del mese **precedente** legato al template non chiude la proposta del mese corrente; un movimento del mese corrente registrato **prima** del giorno atteso la chiude. |
| A5 | "Ignora questo mese" fa sparire la proposta fino alla fine del mese, e **solo** fino alla fine del mese: nessuna traccia da ripulire, nessuno storico. |
| A6 | Le spese ricorrenti esistenti, che non hanno un giorno atteso, non producono nessuna proposta: al primo deploy non compare niente. |
| A7 | Le proposte si vedono in `/home` (card con elenco) e nella pagina Spese Ricorrenti (colonna Stato); da ciascuna si arriva al form di creazione pre-compilato, con la **data di scadenza del mese corrente** già impostata. |
| A8 | `GET /api/recurrent-movements/pending` restituisce la stessa lista in JSON, con le stesse garanzie di isolamento per account delle altre API. |
| A9 | Nessuna dipendenza nuova, nessuna fase di build sul server: il deploy resta `git pull` + Reload, più un `ALTER TABLE` una volta. |
| A10 | Un template senza giorno atteso si comporta **esattamente** come oggi (isofunzionalità sul percorso non monitorato). |

---

## 2. Che cosa c'è già (ricognizione del 2026-11-16)

Tre fatti del codice attuale su cui si appoggia tutto:

| Dove | Fatto |
|---|---|
| [models.py:190](../../pyspendless/models.py) | `RecurrentMovement` è un **template puro**: `name`, `category_id`, `wallet_id`, `income`/`expense`, `note`, `account_id`, `created_at`. **Nessuna nozione di quando è attesa.** È tutto quello che manca. |
| [models.py:142](../../pyspendless/models.py) | `Movement.recurrent_movement_id` (FK, `ON DELETE SET NULL`) esiste e viene valorizzato dal form quando l'utente sceglie il template nella select "Spesa Ricorrente" ([app.py:1074](../../pyspendless/app.py)). È il legame che dice "questo movimento copre quel template". |
| [app.py:1053](../../pyspendless/app.py) | `Movement.move_year` e `move_month` sono derivati da `move_date` su **ogni** creazione. Quindi "registrata nel mese corrente" è un match esatto su due interi, non un range di date — e usa gli indici che ci sono già. |

E un quarto, che risparmia lavoro: `RecurrentMovementRepository.get_all_for_account`
([repository.py:2294](../../pyspendless/repository.py)) calcola già
`last_move_date` = `MAX(move_date)` dei movimenti legati, con una subquery e un
`outerjoin`. La colonna "Data ultima spesa" della pagina Spese Ricorrenti viene
da lì.

---

## 3. Il modello dati: due colonne, entrambe nullable

```sql
ALTER TABLE RecurrentMovement ADD COLUMN due_day     INTEGER;
ALTER TABLE RecurrentMovement ADD COLUMN skip_period TEXT;
```

| Colonna | Tipo | Significato |
|---|---|---|
| `due_day` | `INTEGER` nullable, 1–31 | giorno del mese atteso. **`NULL` = template non monitorato**: nessuna proposta, mai. |
| `skip_period` | `TEXT` nullable, forma `'2026-11'` | il mese per cui l'utente ha detto "ignora". **Un solo campo, sovrascritto**, mai storicizzato. |

Due proprietà di questa scelta, entrambe volute:

- **`due_day` nullable rende la migrazione banale**: `ADD COLUMN` su SQLite non
  ricostruisce la tabella, non serve backfill, e i template esistenti restano
  silenziosi finché non si imposta il giorno a mano. Al primo deploy non compare
  nessuna proposta (A6) — niente valanga di avvisi su dati storici.
- **`skip_period` si autoscade**: contiene un periodo, non un booleano. Al
  cambio di mese il confronto `skip_period != periodo_corrente` è vero da sé.
  Nessun job di pulizia, nessuna riga che cresce.

### Perché non c'è un flag `active`

`due_day IS NULL` **già** significa "non monitorare questo template". Un
booleano in più sarebbe un secondo modo di dire la stessa cosa, con due stati
incoerenti possibili (`active = 0` con `due_day = 15`). Un modo solo.

### Perché un giorno e non una data

La ricorrenza di questo task è **mensile e solo mensile**. Una data completa
(`due_date DATE`) implicherebbe un "prossima occorrenza" da far avanzare dopo
ogni registrazione: stato da mantenere, cioè esattamente ciò che §1 evita. Un
giorno del mese è l'unica informazione che serve, e non invecchia.

---

## 4. La regola

Una funzione sola, nel repository, con `today` **iniettabile** (è il motivo per
cui i test di §9 possono esistere senza congelare l'orologio di sistema):

```python
from calendar import monthrange
from datetime import date

PENDING_STATUSES = ('none', 'registered', 'skipped', 'pending', 'upcoming')

def get_all_with_status(self, account_id, today=None):
    today = today or date.today()
    period = '{:04d}-{:02d}'.format(today.year, today.month)
    last_day = monthrange(today.year, today.month)[1]

    # template coperti da un movimento di QUESTO mese, con la data
    covered = dict(
        self.db.query(
            Movement.recurrent_movement_id,
            func.max(Movement.move_date),
        )
        .filter(
            Movement.account_id == account_id,
            Movement.move_year == today.year,
            Movement.move_month == today.month,
            Movement.recurrent_movement_id.isnot(None),
        )
        .group_by(Movement.recurrent_movement_id)
    )

    rows = (
        self.db.query(RecurrentMovement)
        .filter(RecurrentMovement.account_id == account_id)
        .order_by(RecurrentMovement.name)
        .all()
    )

    for rm in rows:
        if rm.due_day is None:
            rm.status, rm.due_date = 'none', None
            continue
        rm.due_date = date(today.year, today.month, min(rm.due_day, last_day))
        rm.current_month_date = covered.get(rm.id)
        if rm.id in covered:
            rm.status = 'registered'
        elif rm.skip_period == period:
            rm.status = 'skipped'
        elif today >= rm.due_date:
            rm.status = 'pending'
        else:
            rm.status = 'upcoming'
    return rows


def get_pending_for_account(self, account_id, today=None):
    return [rm for rm in self.get_all_with_status(account_id, today)
            if rm.status == 'pending']
```

Due query, entrambe su colonne indicizzate, su volumi familiari (una decina di
template). Il clamp del giorno sta in Python perché SQLite non lo esprime in
modo portabile — e perché è l'unico punto in cui vive, invece di essere
duplicato in ogni `WHERE`.

### I cinque stati, in ordine di precedenza

L'ordine **è** la specifica: `none` → `registered` → `skipped` → `pending` →
`upcoming`. Il primo che si applica vince.

| Stato | Quando | Reso come |
|---|---|---|
| `none` | `due_day IS NULL` | `—`, testo attenuato |
| `registered` | esiste un movimento del mese corrente legato al template | badge verde, *"Registrata il 03/11"* |
| `skipped` | `skip_period` è il periodo corrente (e non è registrata) | badge attenuato, *"Ignorata a novembre"* + azione di ripristino |
| `pending` | `oggi >= data di scadenza del mese`, non registrata, non ignorata | badge di attenzione, *"Attesa il 15"* |
| `upcoming` | scadenza del mese ancora futura | testo attenuato, *"Attesa il 15"* |

`registered` ha la precedenza su `skipped` di proposito: se ignori il mese e poi
registri davvero, lo stato vero è "registrata". Il contrario darebbe un badge
che mente.

### `>=` e non `>`

Al giorno di scadenza la proposta **c'è già** (decisione dell'utente,
2026-11-16). È il giorno in cui serve, non il giorno dopo.

### Due registrazioni nello stesso mese

Una basta: `covered` è un `dict` per `recurrent_movement_id`, e la presenza
della chiave chiude la proposta. Non si propone la seconda rata.

### Cancellare il movimento riapre la proposta

Conseguenza diretta, e corretta: se il movimento non c'è più, la spesa non
risulta registrata. Nessun codice dedicato.

---

## 5. Il punto debole, dichiarato

La condizione "registrata" dipende da `Movement.recurrent_movement_id`, che è
valorizzato **solo** se l'utente sceglie il template nella select del form. Due
conseguenze reali, misurate sul codice:

1. se registri l'affitto a mano senza scegliere il template, la proposta resta
   aperta;
2. **le spese registrate via MCP/Alexa non valorizzano mai il campo**:
   [mcp_server.py:706](../../pyspendless/mcp_server.py) costruisce il movimento
   senza `recurrent_movement_id`. Una spesa dettata a voce non chiude la
   proposta.

### Decisione (2026-11-16): opzione A

**Solo il legame esplicito, più l'azione "Ignora questo mese".** La regola si
spiega in una frase e non ha falsi negativi silenziosi: se registri la spesa per
un'altra strada, chiudi la proposta con un click.

| | Alternativa | Perché scartata |
|---|---|---|
| **B** | Fallback euristico: stessa categoria + wallet nel mese ⇒ considerata registrata | Chiude il buco MCP ma introduce falsi positivi **invisibili** (due Netflix nello stesso mese, una spesa Casa qualunque che chiude la proposta dell'affitto), e la regola non è più spiegabile all'utente. |
| **C** | Far dedurre il template al server MCP quando categoria e wallet coincidono con **un solo** template dell'account | Pulita, ma allarga il task al percorso Alexa/OAuth. **Rinviata**, registrata come `MB-013`. |

---

## 6. Le API

Due endpoint nuovi, più due campi sui due esistenti.

| Metodo | Rotta | Cosa fa |
|---|---|---|
| `GET` | `/api/recurrent-movements/pending` | la lista delle proposte dell'account, come JSON (A8) |
| `POST` | `/api/recurrent-movements/<int:rm_id>/skip` | scrive `skip_period` = **periodo corrente calcolato dal server** |
| `DELETE` | `/api/recurrent-movements/<int:rm_id>/skip` | azzera `skip_period` (ripristina la proposta) |
| `POST`/`PUT` | `/api/recurrent-movements[/<id>]` | accettano `due_day` (`null` o 1–31) |

### Il periodo non arriva dal client

`POST .../skip` **non** accetta un periodo nel body: lo calcola da
`date.today()`. Accettarlo vorrebbe dire permettere a una chiamata di silenziare
un mese arbitrario — compreso un mese futuro, che è uno stato impossibile da
raggiungere dalla UI e che nessuna parte del codice sa interpretare.

### Isolamento per account

Il task24-0 ha registrato fra i tre findings di priorità Alta **"ricorrenti
senza verifica id"**. Ogni endpoint nuovo passa da
`RecurrentMovementRepository.get_by_id(rm_id, account_id)`
([repository.py:2319](../../pyspendless/repository.py)), che filtra per account,
e restituisce **404** (non 403) quando non trova: non si distingue "non esiste"
da "non è tuo".

---

## 7. Dove si vede

### 7.1 Card in `/home`

[ps-home.html](../../pyspendless/templates/ps-home.html) oggi è quasi vuota
(benvenuto + 3 card di navigazione): è il posto naturale. Una card che compare
**solo** se ci sono proposte:

> **2 movimenti ricorrenti attesi**
> Affitto — € 650,00 — atteso il 5 [Registra] [Ignora questo mese]
> Netflix — € 12,99 — atteso il 12 [Registra] [Ignora questo mese]

`[Registra]` è un link a `/create?recurrent_id=N`. `[Ignora questo mese]` è un
`fetch` sul `POST .../skip` che rimuove la riga dal DOM.

### 7.2 Pagina Spese Ricorrenti

[ps-recurrent-mov.html](../../pyspendless/templates/ps-recurrent-mov.html):

- il form guadagna il campo **"Giorno del mese"** (`<input type="number"
  min="1" max="31">`, **opzionale** — decisione dell'utente, 2026-11-16, con
  l'aiuto *"lascia vuoto per non ricevere proposte"*);
- la colonna **"Data ultima spesa"** diventa **"Stato"**, resa dai cinque stati
  di §4 (e `last_move_date` resta disponibile per il testo del badge
  `registered`).

### 7.3 Form di creazione pre-compilato

`/create?recurrent_id=N` ([app.py:421](../../pyspendless/app.py)):

1. il server verifica che il template sia dell'account (§6), altrimenti `flash`
   + redirect come fa già `repeat_from`;
2. preseleziona l'`<option>` nella select `recurrent_template`, che **ha già**
   tutti i `data-*` che servono
   ([ps-add-mov.html:43](../../pyspendless/templates/ps-add-mov.html));
3. imposta `move_date` alla **data di scadenza del mese corrente** (decisione
   dell'utente, 2026-11-16), cioè `rm.due_date` di §4 — modificabile;
4. al `load`, il JS fa scattare un evento `change` sulla select, e l'handler che
   esiste già ([ps-add-mov.html:210](../../pyspendless/templates/ps-add-mov.html))
   riempie tipo, categoria, wallet, importo e nota.

Il passo 4 è il motivo per cui questa parte è piccola: la logica di riempimento
non si riscrive, si innesca. Nota che quell'handler **non tocca la data** ("La
data NON viene toccata", commento in chiaro nel file): è esattamente ciò che
serve, perché la data la mette il server al passo 3 e nessuno la sovrascrive.

---

## 8. Cosa questo task NON fa

- **Non crea mai il movimento da sola.** Un movimento inserito in automatico per
  una spesa che poi non è stata pagata sporca i saldi e, a distanza di un mese,
  non è distinguibile da uno vero. Propone, e la registrazione resta un atto
  dell'utente.
- **Non recupera i mesi arretrati.** Per costruzione (§1), non per scelta.
- **Non introduce frequenze diverse dal mensile** (settimanale, bimestrale,
  annuale).
- **Non manda notifiche** (email, push): la proposta si vede entrando nell'app.
- **Non deduce il template sul percorso MCP/Alexa** (§5, opzione C → `MB-013`).

---

## 9. Il metro di misura

`pyspendless/test/test_task27_0.py`, scritto in **Fase 0, prima** di qualunque
riga di implementazione, nella convenzione del progetto (classe `Checker`,
`sys.exit`, SQLite in-memory — **non** pytest, **non** unittest: vedi
`test_task26_0.py`). Tre sezioni indipendenti:

```bash
cd pyspendless
.venv/bin/python test/test_task27_0.py repo        # Fase 1
.venv/bin/python test/test_task27_0.py api         # Fase 2
.venv/bin/python test/test_task27_0.py contract    # Fasi 3-4
.venv/bin/python test/test_task27_0.py             # tutte
```

Il cuore della sezione `repo` è una tabella di casi sulle date, perché la regola
di §4 **è** una funzione di `(due_day, today, movimenti, skip_period)`:

| # | `due_day` | `today` | movimento legato | `skip_period` | stato atteso |
|---|---|---|---|---|---|
| 1 | 15 | 2026-11-14 | — | — | `upcoming` |
| 2 | 15 | 2026-11-15 | — | — | **`pending`** |
| 3 | 15 | 2026-11-16 | — | — | `pending` |
| 4 | 31 | 2027-02-27 | — | — | `upcoming` |
| 5 | 31 | 2027-02-28 | — | — | **`pending`** (clamp) |
| 6 | 31 | 2027-01-31 | — | — | `pending` (nessun clamp) |
| 7 | 15 | 2026-11-20 | 2026-11-01 | — | `registered` |
| 8 | 15 | 2026-11-20 | 2026-11-16 | — | `registered` |
| 9 | 15 | 2026-11-20 | 2026-10-15 | — | **`pending`** (mese scorso) |
| 10 | 15 | 2026-11-20 | 2026-12-15 | — | `pending` (mese prossimo) |
| 11 | 15 | 2026-11-20 | 2×novembre | — | `registered` (una basta) |
| 12 | `NULL` | 2026-11-20 | — | — | `none` |
| 13 | 15 | 2026-11-20 | — | `2026-11` | `skipped` |
| 14 | 15 | 2026-11-20 | — | `2026-10` | **`pending`** (autoscadenza) |
| 15 | 15 | 2026-11-20 | 2026-11-16 | `2026-11` | `registered` (precedenza) |
| 16 | 1 | 2026-11-01 | — | — | `pending` |
| 17 | 15 | 2026-11-20 | template di un altro account | — | non compare nella lista |

Il caso **9** è il requisito "non recuperare il passato" ridotto a un assert: un
movimento di ottobre non chiude novembre, e il novembre mancato non riapparirà a
dicembre. Il caso **14** è l'autoscadenza di `skip_period`. Il **5** e il **6**
sono il clamp.

---

## 10. File toccati

| File | Cosa |
|---|---|
| `pyspendless/models.py` | `due_day`, `skip_period` su `RecurrentMovement` |
| `sql/sqllite/create_recurrentmovement.sql` | DDL aggiornato |
| `sql/sqllite/NEXT_RELEASE/alter_recurrentmovement_add_due_day.sql` | **nuovo** — i due `ADD COLUMN` da eseguire sul server |
| `pyspendless/repository.py` | `get_all_with_status`, `get_pending_for_account`, `set_skip_period`; `due_day` in `create`/`update` |
| `pyspendless/app.py` | `/home` passa le proposte; 3 endpoint di §6; `/create` accetta `recurrent_id` |
| `pyspendless/templates/ps-home.html` | card delle proposte |
| `pyspendless/templates/ps-recurrent-mov.html` | campo "Giorno del mese", colonna "Stato" |
| `pyspendless/templates/ps-add-mov.html` | preselezione + data da `recurrent_id` |
| `pyspendless/test/test_task27_0.py` | **nuovo** — il metro (Fase 0) |
| `pyspendless/static/css/ps-tailwind.css` | rigenerato da `./tools/build-css.sh` (classi nuove) |
| `.claude/agents/ps-py.md`, `.claude/agents/ps-ui.md` | **già scritti** (2026-11-16) e **durevoli**: non sono artefatti di questo task e non si toccano |
| `CLAUDE.md` | **già aggiornato** (2026-11-16): "Vincoli che valgono per ogni intervento" e "Delega a subagent" |
| `backlog/features.md` | riga del task |
| `backlog/00-task-minor-bugfix.md` | `MB-013` (§5 opzione C) |

---

## 11. Rischi

| # | Rischio | Mitigazione |
|---|---|---|
| **R1** | `editRecurrent(...)` è chiamata da un `onclick` inline con **7 argomenti posizionali** ([ps-recurrent-mov.html:120](../../pyspendless/templates/ps-recurrent-mov.html)). Aggiungere `due_day` come ottavo è la via del diff minimo, ma un argomento posizionale in più su una firma già lunga è il posto in cui si scambiano due parametri senza che nessuno se ne accorga. | Fase 3: `due_day` va **in coda**, e la sezione `contract` del metro verifica l'arità della chiamata generata dal template. Se la Fase 3 preferisce passare a `data-*` + `dataset`, è un miglioramento accettato — purché i test restino verdi. |
| **R2** | task25-0 (localizzazione) è `PIANIFICATO`: le stringhe nuove di questo task non sarebbero in catalogo. | Le stringhe nascono in italiano, come tutto il resto del progetto: i `msgid` del task25-0 sono in italiano, quindi l'estrazione le prenderà quando quel task partirà. Nessun lavoro doppio, nessun blocco nei due sensi. |
| **R3** | Fuso orario: PythonAnywhere gira in UTC, `date.today()` è la data del server. A cavallo di mezzanotte la proposta può comparire con qualche ora di sfasamento rispetto all'ora locale. | Accettato e non corretto: tutta l'app usa già `date.today()` lato server ([app.py:421](../../pyspendless/app.py) e seguenti). Introdurre qui un fuso orario per utente creerebbe un'incoerenza con la data di default dei movimenti. Se diventerà un problema, è un task sul fuso orario, non su questo. |
| **R4** | `update_movement` non ricalcola `move_year`/`move_month` quando cambia la data? Da verificare in Fase 0: se non li ricalcola, spostare un movimento da ottobre a novembre non chiuderebbe la proposta di novembre. | Fase 0 lo accerta e, se il buco c'è, lo registra come `MB-NNN` separato: è un bug preesistente che tocca le dashboard, non una conseguenza di questo task. |
| **R5** | Il badge `registered` mostra la data del movimento del mese corrente, ma `get_all_for_account` calcola `last_move_date` sul **totale** dei movimenti legati (anche dei mesi passati). Usare quel campo per il badge mostrerebbe una data di un altro mese. | §4 espone `current_month_date` (il `MAX` ristretto al mese corrente) accanto a `last_move_date`. Il badge usa il primo, la colonna storica il secondo. Il metro verifica che siano distinti. |

---

## 12. Le fasi

| Fase | Chi | Criterio di "fatto" |
|---|---|---|
| **0** — il metro di misura | **agente principale**, non si delega | i file di §9 esistono, la suite gira e dice `0 superati, N falliti` |
| **1** — modello, migrazione, regola | `ps-py` (haiku) | `test_task27_0.py repo` → exit code **0** |
| **2** — le API | `ps-py` (haiku) | `test_task27_0.py api` → exit code **0** |
| **3** — pagina Spese Ricorrenti | `ps-ui` (haiku) | `test_task27_0.py contract` → exit code **0** |
| **4** — card home + prefill | `ps-ui` (haiku) | `test_task27_0.py contract` → exit code **0** |
| **5** — CSS, verifica visiva, rilascio | **agente principale** | `./tools/build-css.sh` + `git status` pulito; proposta di bump a `0.5.0` |

Il modello di delega è quello che ha funzionato nel task19-0 e nel task26-0:
l'agente principale progetta i criteri e verifica, i subagent haiku implementano
contro un **exit code**, non contro un giudizio. Per questo la Fase 0 non si
delega: scrivere il proprio metro di misura è il modo più diretto di ottenere un
metro che dice sempre "fatto".

### Gli agenti sono durevoli, non di questo task

`ps-py` e `ps-ui` ([.claude/agents/](../../.claude/agents/)) sono stati scritti
il 2026-11-16 e **non appartengono a questo task**: portano il metodo (leggi
`CLAUDE.md`, leggi la specifica, leggi il file di fase, non modificare il metro,
riepiloga così) e **nessuna coordinata**. Il mandato sta nei file di fase, che
sono per definizione specifici.

È una rottura voluta con la convenzione precedente, in cui ogni task generava i
propri agenti: i nove profili che nominano un task (`ps-markup`, `ps-labels-py`,
`ps-i18n-*`, …) sono di task chiusi e restano come storia. Gli invarianti di
progetto che quei nove ricopiavano a mano — Python 3.9, nessuna dipendenza
nuova, 404 e non 403, stile, convenzione dei test — stanno ora in `CLAUDE.md`,
in copia unica.

Conseguenza per questo task: la Fase 0 **non** produce profili di agente.
