# Fase 1 — Modello, migrazione, la regola

**Chi**: subagent **`ps-py`** (haiku).
**Dipende da**: Fase 0.
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task27_0.py repo`
esce con **exit code 0**.
**File che puoi toccare**: `pyspendless/models.py`, `pyspendless/repository.py`.
**Nient'altro** — non `app.py`, non i template, non il metro.

## Il mandato

Due colonne e una funzione. La funzione è il cuore del task: ogni altra fase la
consuma e nessuna la riscrive.

### 1. `pyspendless/models.py` — le due colonne

Su `RecurrentMovement` ([models.py:190](../../../pyspendless/models.py)), in coda
ai campi esistenti e **prima** della sezione `# Relationships`:

```python
due_day = Column(Integer, nullable=True)      # giorno del mese atteso, 1-31; NULL = non monitorato
skip_period = Column(Text, nullable=True)     # 'YYYY-MM' ignorato dall'utente; si autoscade
```

Niente `default`, niente `CheckConstraint`: il range 1–31 si valida all'API
(Fase 2), dove c'è un messaggio da restituire. Un vincolo nel DB darebbe un
`IntegrityError` da tradurre, cioè lo stesso lavoro due volte.

Il DDL in `sql/sqllite/` è già aggiornato dalla Fase 0: **non toccarlo**.

### 2. `pyspendless/repository.py` — `get_all_with_status`

Il corpo è in `task27-spec.md` §4. Copialo e fallo funzionare; se devi
discostarti, i test dicono dove.

I quattro punti su cui i test sono severi:

| | Regola |
|---|---|
| `today` | parametro con default `None` → `date.today()`. **Mai** `date.today()` dentro il corpo in un altro punto: i test iniettano la data, e una seconda lettura dell'orologio renderebbe un caso non riproducibile a cavallo di mezzanotte. |
| precedenza | `none` → `registered` → `skipped` → `pending` → `upcoming`. Il primo che si applica vince. `registered` **prima** di `skipped` (caso 15). |
| clamp | `min(due_day, monthrange(y, m)[1])`. Un `due_day = 31` a febbraio non deve mai costruire un `date(2027, 2, 31)`: è un `ValueError`, non un clamp. |
| `current_month_date` | il `MAX(move_date)` **ristretto al mese corrente**, attributo distinto da `last_move_date`. Vedi la trappola 2. |

### 3. `get_pending_for_account`

```python
def get_pending_for_account(self, account_id, today=None):
    return [rm for rm in self.get_all_with_status(account_id, today)
            if rm.status == 'pending']
```

Esattamente così: un filtro, non una seconda query. Il test 3 della sezione
`repo` verifica che le due funzioni non possano divergere.

### 4. `set_skip_period`

```python
def set_skip_period(self, rm_id, account_id, period):
    """period: 'YYYY-MM' per ignorare, None per ripristinare."""
    rm = self.get_by_id(rm_id, account_id)
    if not rm:
        return None
    rm.skip_period = period
    self.db.commit()
    self.db.refresh(rm)
    return rm
```

`get_by_id(rm_id, account_id)` **sempre**: è il filtro per account, ed è il
finding Alta del task24-0. Non scrivere una query nuova senza quel filtro.

### 5. `create` e `update` accettano `due_day`

- `create(...)`: nuovo parametro keyword `due_day=None`, in coda alla firma per
  non rompere le chiamate esistenti.
- `update(...)`: dentro il blocco dei campi, `if 'due_day' in data: rm.due_day =
  data['due_day']`. Il `in data` e non `data.get(...)`: serve poter **azzerare**
  il giorno passando `None` esplicito, che è come l'utente smette di monitorare
  un template.

Non toccare la logica di `sync_from_note` / `LabelRepository` che è lì: non è
affare di questa fase.

## Le tre trappole

1. **`get_all_for_account` esiste e continua a esistere.** Non la sostituire e
   non la "unificare" con `get_all_with_status`: la pagina Spese Ricorrenti usa
   `last_move_date` (storico, tutti i mesi) e la Fase 3 userà `status` e
   `current_month_date`. Due domande diverse, due metodi. Il refactoring è una
   tentazione ragionevole e qui è fuori perimetro.
2. **`last_move_date` non è `current_month_date`.** Il `MAX` di
   `get_all_for_account` è su **tutti** i movimenti legati: se l'affitto è stato
   pagato a ottobre e non a novembre, `last_move_date` è di ottobre. Usarlo come
   prova di registrazione farebbe sparire tutte le proposte di chi ha pagato
   almeno una volta in passato — cioè romperebbe esattamente il caso 9.
3. **Gli attributi che assegni (`rm.status`, `rm.due_date`,
   `rm.current_month_date`) non sono colonne.** Sono attributi Python su istanze
   mappate, come fa già `get_all_for_account` con `last_move_date`. Non
   dichiararli nel modello, non provare a persisterli. E non chiamare
   `self.db.commit()` dentro `get_all_with_status`: è una lettura.

## Cosa NON fare

- Non aggiungere un flag `active` (spec §3).
- Non aggiungere colonne per la frequenza (settimanale, annuale): fuori
  perimetro (spec §8).
- Non toccare `mcp_server.py`: il buco del percorso Alexa è dichiarato e
  rinviato (spec §5, `MB-013`).
- Non modificare `test/test_task27_0.py`. Mai, per nessun motivo. Se un caso ti
  sembra sbagliato, **fermati e dillo**: non lo correggi.
