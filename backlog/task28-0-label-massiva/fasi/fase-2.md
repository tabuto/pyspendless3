# Fase 2 — L'API

**Chi**: subagent **`ps-py`** (haiku).
**Dipende da**: Fase 1 (`repo` verde).
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task28_0.py api`
esce con **exit code 0**, `repo` resta verde, e le quattro suite di regressione
di `CLAUDE.md` restano verdi.
**File che puoi toccare**: `pyspendless/app.py`. **Nient'altro** — non
`repository.py` (chiusa in Fase 1), non i template (Fase 3), non il test.

## Il mandato

Due interventi, entrambi in `app.py`.

### 1. `api_bulk_update_movements` ([app.py:933](../../../pyspendless/app.py))

Legge `add_labels` dal body e lo valida **prima** di toccare il database:

```python
add_labels_raw = data.get('add_labels')
```

| Caso | Risposta |
|---|---|
| `category_id is None and note is None and not add_labels_raw` | `400 {'error': 'Specificare almeno categoria, nota o label da applicare'}` |
| `add_labels_raw` presente e non è una `list` | `400 {'error': 'add_labels deve essere una lista di nomi'}` |
| più di `MAX_LABELS_PER_MOVEMENT` elementi | `400` con il limite nel messaggio |
| un elemento non è una stringa, o `labels.is_valid(nome.lstrip('#'))` è falso | `400 {'error': 'Label non valida: <nome>'}` |

Il `#` iniziale si accetta e si toglie (`lstrip('#')`), come fa già
`_parse_movement_filters` ([app.py:530](../../../pyspendless/app.py)).

**Perché qui si risponde 400 e nel filtro si ignora in silenzio** (decisione D7
della specifica): la query string del filtro è input non fidato di una
navigazione, e una grafia storta non deve impedire di vedere la pagina. Qui
l'utente ha premuto "Applica" su N movimenti: un nome scartato in silenzio è
una modifica che non avviene senza che nessuno lo dica. Scrivilo nel commento,
perché è la domanda che si farà il prossimo che legge le due regole diverse.

`is_valid` si importa con il doppio fallback già usato nello stesso file
([app.py:500](../../../pyspendless/app.py)): `from .labels import ...` e, su
`ImportError`, `from labels import ...`.

**Il vincolo del tipo resta legato alla categoria.** Il blocco
"Per cambiare categoria in blocco, filtra prima per Entrata o Uscita"
([app.py:960](../../../pyspendless/app.py)) sta **dentro**
`if category_id is not None:` e lì deve restare: una richiesta con solo
`add_labels` e nessun filtro per tipo è legittima e deve rispondere `200`
(criterio A8, caso 7 della sezione `api`). Se lo sposti fuori, quel caso
diventa rosso.

La chiamata al repository passa il parametro nuovo e la risposta diventa:

```python
result = movement_repo.bulk_update_movements(..., add_labels=add_labels)
return jsonify(result), 200   # {'updated': N, 'skipped': M, 'labels': [...]}
```

`updated` conserva il significato di oggi (D9): è il campo che il JavaScript
esistente legge, e cambiarglielo romperebbe un contratto per un dettaglio di
presentazione.

### 2. Il contesto del template di `/movements`

Il `render_template("ps-show-mov.html", ...)`
([app.py:620](../../../pyspendless/app.py)) **non** passa i due limiti, a
differenza di quello del form movimento ([app.py:486](../../../pyspendless/app.py)).
Vanno aggiunti, con lo stesso commento di allora:

```python
# Limiti del campo labels: resi come data-* sul campo, cosi'
# ps-labels.js non li duplica (task26-0)
max_note_length=MAX_NOTE_LENGTH,
max_labels_per_movement=MAX_LABELS_PER_MOVEMENT,
```

Sono già importati in testa al file
([app.py:10](../../../pyspendless/app.py)): non reimportarli localmente.

Senza questo passo il template della Fase 3 renderebbe
`data-ps-labels-max=""`, Jinja non solleverebbe, `ps-labels.js` ripiegherebbe
sul suo default di 10 e **nessun test lo vedrebbe** se non il caso 10 della
sezione `api`, che esiste per questo: un fallimento muto in cui il limite del
server e quello del campo possono divergere senza che nulla se ne accorga.

## Trappole misurate

1. **`data.get('add_labels')` su una lista vuota** è falsy: `[]` deve dare
   `400` "Specificare almeno…" (caso 5), non `200` con zero label. Usa un
   controllo esplicito, non `if add_labels_raw is not None`.
2. **Validare prima di aprire la sessione DB**: i casi 3, 4 e 6 verificano che
   **nessun** movimento sia stato modificato. Un `400` emesso dopo un giro di
   scritture li farebbe passare per caso oggi e fallire domani.
3. **L'isolamento per account non si tocca**: `account_id` viene dalla
   sessione, i filtri da `_parse_movement_filters()`, e un `category_id` di un
   altro account resta `404` (caso 8, comportamento di oggi — vedi
   `backlog/task24-0-auth-assessment.md`). Non c'è nessun id di label in
   input: le label si creano o si riusano per nome **nell'account della
   sessione**, quindi non c'è una seconda superficie da difendere.

## Stile

Docstring della rotta aggiornata (oggi dice "una nuova categoria e/o una nuova
nota": va detto anche delle label), commenti in italiano sul **perché**,
nessun refactoring collaterale. Il formato degli errori è quello delle rotte
accanto: `jsonify({'error': '...'}), <codice>`.
