# Fase 2 — Le API

**Chi**: subagent **`ps-py`** (haiku).
**Dipende da**: Fase 1 (`repo` verde).
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task27_0.py api`
esce con **exit code 0**, e `repo` resta verde.
**File che puoi toccare**: `pyspendless/app.py`. **Nient'altro** — non i
template, non `repository.py` (è chiusa in Fase 1).

## Il mandato

Tre rotte nuove e due campi su quelle esistenti, nella sezione
`# ========== RECURRENT MOVEMENTS ==========` di
[app.py:1246](../../../pyspendless/app.py), subito **dopo** le quattro rotte che
ci sono già.

### 1. `GET /api/recurrent-movements/pending`

```python
@app.route("/api/recurrent-movements/pending", methods=['GET'])
def api_get_pending_recurrent_movements():
    """Movimenti ricorrenti attesi nel mese corrente e non ancora registrati."""
```

Copia la struttura di `api_get_recurrent_movements`
([app.py:1279](../../../pyspendless/app.py)): stesso controllo di sessione,
stesso `get_db_session()` / `try` / `finally: db.close()`, stesso formato di
errore. Payload per elemento:

```json
{
  "id": 7,
  "name": "Affitto",
  "movement_type": "expense",
  "amount": 650.00,
  "category_id": 3,
  "category_name": "Casa",
  "wallet_id": 1,
  "wallet_name": "Conto",
  "note": "affitto mensile",
  "due_day": 5,
  "due_date": "2026-11-05"
}
```

`due_date` in ISO (`rm.due_date.isoformat()`), non formattata: la formattazione
è della UI. `amount` è `float(rm.income or rm.expense)` come nelle rotte
esistenti.

### 2. `POST` e `DELETE /api/recurrent-movements/<int:rm_id>/skip`

```python
@app.route("/api/recurrent-movements/<int:rm_id>/skip", methods=['POST', 'DELETE'])
def api_skip_recurrent_movement(rm_id):
    """Ignora il movimento ricorrente per il mese corrente (POST), o ripristina (DELETE)."""
```

- `POST` → `period = '{:04d}-{:02d}'.format(today.year, today.month)` con
  `today = date.today()`, **calcolato qui**;
- `DELETE` → `period = None`;
- entrambi passano da `recurrent_repo.set_skip_period(rm_id, account_id, period)`;
- `None` di ritorno → `404` con `{'error': 'Spesa ricorrente non trovata'}`,
  esattamente il messaggio delle rotte esistenti.

**Il periodo non si legge dal body.** Se il client manda `{"period": "2027-01"}`
lo si ignora: non c'è nessuno stato dell'interfaccia che possa produrre quella
richiesta, e onorarla permetterebbe di silenziare un mese futuro — uno stato che
nessuna parte del codice sa poi interpretare. Il test 4 della sezione `api`
verifica proprio questo.

### 3. `due_day` su `POST` e `PUT /api/recurrent-movements`

Un solo helper, usato da entrambe:

```python
def _parse_due_day(raw):
    """Restituisce (value, error). value è None o un int 1-31."""
    if raw is None or raw == '':
        return None, None
    try:
        day = int(raw)
    except (TypeError, ValueError):
        return None, 'Giorno del mese non valido'
    if not 1 <= day <= 31:
        return None, 'Il giorno del mese deve essere fra 1 e 31'
    return day, None
```

In `api_create_recurrent_movement` ([app.py:1308](../../../pyspendless/app.py)):
`due_day` assente o `null` → `None`, errore → `400` con il messaggio.

In `api_update_recurrent_movement` ([app.py:1348](../../../pyspendless/app.py)):
il campo si inoltra a `update()` **solo se la chiave è presente nel body**,
perché `due_day: null` esplicito significa "smetti di monitorare" mentre
l'assenza della chiave significa "non toccare". `data` è già un dict:
`if 'due_day' in data: ...`.

### 4. `/create` accetta `recurrent_id`

Nella rotta `create` ([app.py:421](../../../pyspendless/app.py)), accanto a
`repeat_from` che fa già la stessa cosa:

```python
recurrent_id = request.args.get('recurrent_id')
...
prefill_recurrent = None
if recurrent_id and not movement:
    rows = recurrent_repo.get_all_with_status(account_id)
    prefill_recurrent = next((r for r in rows if str(r.id) == str(recurrent_id)), None)
    if not prefill_recurrent:
        flash('Spesa ricorrente non trovata', 'error')
        return redirect(url_for('recurrent_movements_page'))
```

Si passa da `get_all_with_status` e non da `get_by_id` perché serve anche
`due_date` per il passo successivo. Il filtro per account è dentro quel metodo
(Fase 1), quindi un `recurrent_id` di un altro account non si trova → `flash` +
redirect, come fa `repeat_from` per un movimento non suo.

Al `render_template` si aggiungono due variabili:

```python
prefill_recurrent_id=prefill_recurrent.id if prefill_recurrent else None,
prefill_date=prefill_recurrent.due_date if prefill_recurrent else None,
```

`prefill_date` può essere `None` anche con un template valido, se quel template
non ha `due_day`: in quel caso il form si comporta come oggi (data vuota). È un
caso raggiungibile solo scrivendo l'URL a mano, e non è un errore.

**Non toccare il template in questa fase**: `ps-add-mov.html` è della Fase 4.
Qui si passano le variabili, che restano inutilizzate fino ad allora. La sezione
`api` non guarda i template.

### 5. `/home` passa le proposte

```python
@app.route("/home")
def home():
    ...
    db = get_db_session()
    try:
        pending = RecurrentMovementRepository(db).get_pending_for_account(
            session.get('account_id'))
        return render_template("ps-home.html", user_email=user_email,
                               user_name=user_name, pending_recurrents=pending)
    finally:
        db.close()
```

La rotta `home` ([app.py:407](../../../pyspendless/app.py)) oggi **non apre
nessuna sessione di database**: è l'unica rotta autenticata che non lo fa. Dopo
questa fase la apre, con lo stesso `try`/`finally: db.close()` di tutte le
altre. Se il `finally` non c'è, la connessione resta appesa a ogni visita della
home: è il punto più facile da sbagliare di questa fase.

### 6. `/recurrent-movements` passa gli stati

Nella rotta `recurrent_movements_page` ([app.py:1248](../../../pyspendless/app.py)),
la riga

```python
recurrent_movements = recurrent_repo.get_all_for_account(account_id)
```

diventa

```python
recurrent_movements = recurrent_repo.get_all_for_account(account_id)
statuses = {rm.id: rm for rm in recurrent_repo.get_all_with_status(account_id)}
for rm in recurrent_movements:
    src = statuses.get(rm.id)
    rm.status = src.status if src else 'none'
    rm.due_date = src.due_date if src else None
    rm.current_month_date = src.current_month_date if src else None
```

Due chiamate e non una perché i due metodi rispondono a due domande diverse e
restano separati (vedi la trappola 1 della Fase 1): `get_all_for_account` porta
`last_move_date` (storico, tutti i mesi), `get_all_with_status` porta lo stato
del mese corrente. Qui si uniscono per la vista, e il template non fa aritmetica
sulle date.

**Tutte** le modifiche a `app.py` di questo task stanno in questa fase: le Fasi
3 e 4 toccano solo i template. Quindi queste variabili restano inutilizzate
finché quelle fasi non arrivano, e la pagina continua a funzionare come oggi.

## Le due trappole

1. **`get_all_with_status` è una lista di oggetti mappati con attributi
   aggiunti.** Dopo `db.close()` quegli oggetti sono detached: se li serializzi
   *dopo* il `finally` ottieni un `DetachedInstanceError`, e se tocchi
   `rm.category_obj` lo ottieni comunque perché è una relazione lazy. Costruisci
   il dict del JSON **dentro** il `try`, come fa `api_get_recurrent_movements`.
   Per la home, `pending_recurrents` viene passato a `render_template` dentro il
   `try`: Jinja valuta il template prima del `finally`, quindi funziona — ma
   solo se il `return render_template(...)` sta **dentro** il blocco.
2. **`int:rm_id` nel converter, non `str`.** `/skip` su un id non numerico deve
   dare 404 da Flask, non arrivare al repository.

## Cosa NON fare

- Non riscrivere le quattro rotte esistenti: si aggiungono due campi, non si
  rifattorizzano.
- Non aggiungere un tool MCP per le proposte: fuori perimetro (spec §8).
- Non accettare il periodo dal client.
- Non modificare `test/test_task27_0.py`. Se un caso ti sembra sbagliato,
  **fermati e dillo**.
