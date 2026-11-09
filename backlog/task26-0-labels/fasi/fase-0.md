# Fase 0 — Il metro di misura

**Chi**: **agente principale**. **Non si delega.**
**Stato**: **FATTA** il 2026-11-08.
**Vincolo cardine**: nessun file applicativo è stato modificato. Se in questa
fase cambia una riga di `app.py`, `repository.py` o di un template, la fase è
sbagliata.

## Perché non si delega

Qui si scrive il criterio con cui si valuteranno le sette fasi successive.
Delegare a un subagent la scrittura del proprio metro è il modo più diretto di
ottenere un metro che dice sempre "fatto".

## Cosa è stato prodotto

| File | Ruolo |
|---|---|
| `pyspendless/test/fixtures/labels_cases.json` | **112 casi** della grammatica: il contratto condiviso fra il parser Python e quello JavaScript. |
| `pyspendless/test/test_task26_0.py` | Lo script di controllo, in quattro sezioni selezionabili (`parser`, `repo`, `api`, `contract`), exit code 0/1. |
| `tools/probe-labels.html` | La sonda JS: gli stessi 112 casi contro `window.PsLabels`, più la verifica delle assunzioni su Tom Select. |
| `sql/sqllite/create_label.sql`, `sql/sqllite/NEXT_RELEASE/create_label.sql` | DDL della tabella `Label` (idempotente; il secondo è quello da eseguire sul server). |
| `.claude/agents/ps-labels-py.md` | Profilo dell'agente per le fasi 1-3. |
| `.claude/launch.json` | Configurazione `probe` (`python3 -m http.server 8765`) per aprire la sonda: con `file://` il `fetch` delle fixture è bloccato dalla CORS. |

`sql/sqllite/create_all.sql` guadagna la riga della nuova tabella — e anche
quella di `RecurrentMovement`, che mancava da prima di questo task.

## Come si usa il metro

```bash
cd pyspendless
.venv/bin/python test/test_task26_0.py parser     # Fase 1
.venv/bin/python test/test_task26_0.py repo       # Fase 2
.venv/bin/python test/test_task26_0.py api        # Fase 3
.venv/bin/python test/test_task26_0.py contract   # Fasi 4-7
.venv/bin/python test/test_task26_0.py            # tutte
```

Le quattro sezioni sono **indipendenti**: la Fase 2 può lavorare con `repo`
rossa e `parser` verde. Finché una fase non è implementata, la sua sezione
fallisce con **una** riga che dice cosa manca, non con uno stack trace.

Stato alla chiusura della Fase 0: `0 controlli superati, 17 falliti`. È il
colore giusto.

## Cinque cose scoperte in Fase 0 (e che cambiano le fasi successive)

### 1. Il progetto non usa unittest

La specifica parlava di `python -m unittest -k`. Sbagliato: `test_task22_0.py` e
`test_task23_0.py` sono script con una classe `Checker` e `sys.exit()`. Il metro
segue quella convenzione, e i criteri delle fasi 1-3 sono `test_task26_0.py
<sezione>`. La §18 della specifica è stata corretta.

### 2. Il virtualenv è Python **3.9**

Niente `match`, niente `str | None`, niente `dict[str, int]` nelle annotazioni
senza `from __future__ import annotations`. Vale per tutte le fasi Python.

### 3. `ps_has_label` funziona, verificato

`create_function(..., deterministic=True)` è accettato (SQLite 3.37),
`func.ps_has_label(Movement.note, 'coop') == 1` entra nella `WHERE`, e
`query.count()` più `limit/offset` restano corretti — cioè la paginazione di
`/movements` non si rompe. Verificato su SQLAlchemy 2.0.46 con un DB in-memory:
su 5 movimenti, `#coop` ne trova 2 e **non** prende `#coopx`.

### 4. Tom Select regge le assunzioni della specifica §9 — con due trappole

Sonda eseguita su Tom Select 2.3.1 dal CDN: 11 controlli verdi. In particolare
`create: true` + `createFilter`, `remove_button`, `maxItems: 10` e l'init
dentro a un contenitore `display:none` si comportano come previsto. Ma:

- **`addItem()` su un valore non ancora caricato non fa nulla, senza errore.**
  Le label del registro arrivano dal `load()` remoto, quindi per aggiungere una
  chip da codice (il riallineamento dalla textarea!) serve `addOption({name})`
  **prima** di `addItem(name)`. È il bug più probabile della Fase 4.
- **`load()` è ritardato di 300 ms** (`loadThrottle`): non è sincrono. Un test
  che controlla subito dopo non vede nessuna chiamata.

### 5. La regola del merge nella rinomina

`rename_label("spesa #coopp e #coop", "coopp", "coop")`: sostituire e poi
deduplicare darebbe `"spesa #coop e"`, con la congiunzione sospesa. La regola
scelta e messa nelle fixture è: **se la nuova label è già presente nel testo,
l'occorrenza vecchia si rimuove** invece di sostituirla → `"spesa e #coop"`.

## Il metro è stato validato, non solo scritto

I 112 casi sono stati eseguiti contro un'implementazione di riferimento
usa-e-getta (scritta fuori dal repo e buttata): **112/112 verdi**. Serviva a
dimostrare che le fixture sono coerenti fra loro e che l'harness sa diventare
verde — un metro che non può passare è peggio di nessun metro.

Quella implementazione **non** è nel repo: scriverla è la Fase 1.
