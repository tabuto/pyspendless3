# Fase 0 — Il metro di misura

**Chi**: **agente principale**. **Non si delega.**
**Dipende da**: niente.
**Fatto quando**: i file qui sotto esistono, `.venv/bin/python test/test_task27_0.py`
gira e stampa `0 controlli superati, N falliti` — con **una riga** per ogni
controllo, non uno stack trace.
**Vincolo cardine**: **nessun file applicativo viene modificato.** Se in questa
fase cambia una riga di `app.py`, `repository.py`, `models.py` o di un template,
la fase è sbagliata. L'unica eccezione è il DDL (è documentazione dello schema,
non codice eseguito dall'app).

## Perché non si delega

Qui si scrive il criterio con cui si valuteranno le cinque fasi successive.
Delegare a un subagent la scrittura del proprio metro è il modo più diretto di
ottenere un metro che dice sempre "fatto".

## Cosa produce

| File | Ruolo |
|---|---|
| `pyspendless/test/test_task27_0.py` | lo script di controllo, 3 sezioni selezionabili (`repo`, `api`, `contract`), exit code 0/1 |
| `sql/sqllite/NEXT_RELEASE/alter_recurrentmovement_add_due_day.sql` | i due `ADD COLUMN`, idempotenti quanto SQLite lo consente |
| `sql/sqllite/create_recurrentmovement.sql` | DDL aggiornato con le due colonne |

**Non** produce profili di agente: `ps-py` e `ps-ui` esistono già e sono
durevoli (spec §12). Se ti accorgi che manca loro un'istruzione, è un'istruzione
di **progetto** e va in `CLAUDE.md` o nel file di fase — non in un profilo
nuovo.

## Le tre sezioni

```bash
cd pyspendless
.venv/bin/python test/test_task27_0.py repo        # Fase 1
.venv/bin/python test/test_task27_0.py api         # Fase 2
.venv/bin/python test/test_task27_0.py contract    # Fasi 3-4
```

Indipendenti: la Fase 2 può lavorare con `api` rossa e `repo` verde. Finché una
fase non è implementata, la sua sezione fallisce con **un** messaggio che dice
cosa manca.

### Sezione `repo`

Database SQLite **in-memory** creato al volo (`Base.metadata.create_all`), come
`test_task26_0.py`: non tocca in nessun caso il database di `.env`.

1. **Schema**: `RecurrentMovement.due_day` e `.skip_period` esistono, sono
   nullable, e `create_all` su un DB vuoto non esplode.
2. **I 17 casi di `task27-spec.md` §9**, uno per riga di output. Si costruiscono
   un account, un template e i movimenti della riga, si chiama
   `get_all_with_status(account_id, today=<la data del caso>)` e si confronta
   `rm.status`. `today` **iniettato**, mai `date.today()`.
3. **`get_pending_for_account` è coerente con `get_all_with_status`**: per ogni
   caso, `rm in pending ⟺ rm.status == 'pending'`. Due implementazioni della
   stessa regola sarebbero due regole.
4. **`rm.due_date`**: `date(2027, 2, 28)` per `due_day = 31` a febbraio 2027,
   `None` quando `due_day is None`.
5. **`current_month_date` ≠ `last_move_date`** (R5 della specifica): template
   con un movimento a ottobre **e** uno a novembre, `today` a novembre →
   `current_month_date` è la data di novembre. Il controllo esiste perché usare
   `last_move_date` nel badge è l'errore più probabile della Fase 3.
6. **`set_skip_period`**: scrive il periodo passato, e `None` lo azzera.
7. **Isolamento**: `get_all_with_status(account_B)` non vede i template di A; un
   movimento dell'account B che puntasse a un template di A non lo chiude.
8. **`create`/`update` accettano `due_day`**, compreso `due_day = None` in
   update per smettere di monitorare.

### Sezione `api`

Flask test client su app in-memory, come fa `test_task23_0.py`.

1. `GET /api/recurrent-movements/pending` → 200, lista, **solo** i `pending`.
2. `POST /api/recurrent-movements/<id>/skip` → 200, e il `GET` successivo non
   contiene più quel template.
3. `DELETE /api/recurrent-movements/<id>/skip` → 200, e il template torna fra i
   `pending`.
4. **Il periodo non arriva dal client**: un `POST .../skip` con
   `{"period": "2027-01"}` nel body scrive **comunque** il periodo corrente. Il
   campo extra si ignora, non si onora.
5. **Isolamento (task24-0)**: tutte e tre le rotte con l'`id` di un template di
   un altro account → **404**. Senza sessione → redirect/401 come le altre.
6. **Validazione `due_day`** su `POST`/`PUT`: `0`, `32`, `-1`, `"quindici"` →
   **400**; `1`, `31`, `null` → 200/201.

### Sezione `contract`

Controlli **statici** sui template (lettura del file, regex), nella convenzione
di `test_task19_0.py`: non aprono un browser.

| Controllo | Perché |
|---|---|
| `ps-recurrent-mov.html` ha `id="rm_due_day"` con `type="number"`, `min="1"`, `max="31"`, **senza** `required` | il campo è opzionale (decisione 2026-11-16) |
| il payload JS del submit contiene `due_day` | altrimenti il campo si vede e non si salva |
| la `<th>` "Stato" esiste e "Data ultima spesa" non è più l'unica colonna di data | A7 |
| l'`onclick` di `editRecurrent(` ha **8** argomenti, oppure la chiamata è stata sostituita da un `dataset` | R1: l'arità è il contratto |
| `ps-home.html` cita `recurrent_id=` e la rotta `/skip` | A7 |
| `ps-home.html` rende la card **dentro** un `{% if %}` sulle proposte | niente card vuota quando non c'è nulla |
| `ps-add-mov.html` imposta `move_date` da una variabile di prefill | il passo 3 di §7.3: la data la mette il server |
| `ps-add-mov.html` fa scattare un `change` sulla select al load | il passo 4: la logica di riempimento si innesca, non si riscrive |
| il conteggio di `bootstrap.` **non aumenta** nei tre template toccati: `ps-recurrent-mov.html` = 2, `ps-home.html` = 0, `ps-add-mov.html` = 0 | il task19-0 ha rimosso Bootstrap, e `window.bootstrap.Modal` è solo uno **shim** in `ps-ui.js` tenuto in vita per 12 call site da migrare. I 2 di `ps-recurrent-mov.html` sono preesistenti e restano; un tredicesimo allungherebbe la vita al debito |

## Due cose da accertare prima di chiudere la fase

1. **R4**: `MovementRepository.update_movement` ricalcola `move_year` e
   `move_month` quando cambia `move_date`? Si legge
   [repository.py:1070](../../../pyspendless/repository.py) e si risponde nel
   file di fase. Se **non** li ricalcola, è un bug preesistente che tocca anche
   le dashboard: si apre una voce `MB-NNN` e **non** lo si corregge qui.
2. **La regressione è verde?** Le quattro suite elencate in `CLAUDE.md` ("Come
   si verifica") al 2026-11-16 passano, e `test_task1_3.py` è già rosso da
   prima. Se qualcosa è cambiato, si accerta **adesso**: una suite già rossa
   prima della Fase 1 renderebbe impossibile distinguere un danno nuovo da uno
   preesistente.

Gli altri vincoli (Python 3.9, nessuna dipendenza nuova, 404 e non 403, stile)
**non si ripetono qui**: stanno in `CLAUDE.md`, in copia unica, ed è quella che
i subagent leggono.

## Il metro va validato, non solo scritto

Come in task26-0: i 17 casi si eseguono contro un'implementazione di riferimento
usa-e-getta, **scritta fuori dal repo e buttata**, finché non sono 17/17 verdi.
Serve a dimostrare che i casi sono coerenti fra loro e che l'harness **sa**
diventare verde. Un metro che non può passare è peggio di nessun metro.

Quell'implementazione non entra nel repo: scriverla è la Fase 1.
