# Fase 2 — Schema, `LabelRepository`, hook, `ps_has_label`

**Chi**: subagent **`ps-labels-py`** (haiku).
**Dipende da**: Fase 1 verde.
**Fatto quando**: `.venv/bin/python test/test_task26_0.py repo` esce con
**exit code 0** (30 controlli), e `parser` resta verde.
**File che puoi toccare**: `pyspendless/models.py`, `pyspendless/conf.py`,
`pyspendless/repository.py`, `migrations/backfill_labels.py` (nuovo).
**Il DDL esiste già** (`sql/sqllite/create_label.sql`, scritto in Fase 0): non
lo riscrivi, ma `models.py` deve combaciare con quello.

## 2.1 `models.py`

```python
class Label(Base):
    __tablename__ = 'Label'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(Text, nullable=False)     # grafia canonica
    name_norm  = Column(Text, nullable=False)     # name.lower()
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('account_id', 'name_norm', name='uq_label_account_name'),)
    account = relationship('Account', back_populates='labels')
```

Più `labels = relationship('Label', back_populates='account')` su `Account`.
`UniqueConstraint` va importato da `sqlalchemy`.

## 2.2 `conf.py` — `register_sqlite_functions(engine)`

Una funzione **esportata** (la chiama anche il test, che altrimenti
verificherebbe una copia della funzione invece di quella di produzione):

```python
def register_sqlite_functions(engine):
    from labels import has_label
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _record):
        fn = lambda note, name: 1 if has_label(note, name) else 0
        try:
            dbapi_conn.create_function("ps_has_label", 2, fn, deterministic=True)
        except TypeError:        # sqlite3 troppo vecchio per deterministic
            dbapi_conn.create_function("ps_has_label", 2, fn)
```

Va chiamata su `_engine` dentro `get_db_engine()`, **subito dopo**
`create_engine(...)` e prima che la connessione venga usata. Verificato in
Fase 0: `deterministic=True` passa, e `query.count()` con `limit/offset`
resta corretto.

Nella stessa fase si spostano qui due costanti:

```python
MAX_NOTE_LENGTH = 500            # oggi in mcp_server.py:116
MAX_LABELS_PER_MOVEMENT = 10
```

e `mcp_server.py` le importa invece di definirle (una riga; il test `contract`
verifica che `mcp_server.py` non abbia più la propria definizione).

## 2.3 `LabelRepository`

| Metodo | Contratto |
|---|---|
| `sync_from_note(account_id, note) -> str` | **Il cuore della fase.** Estrae le label, trova-o-crea la riga per `name_norm`, e **ritorna la nota canonicalizzata** (`labels.canonicalize` col mapping del registro). La nota ritornata è quella che il chiamante salva. |
| `search(account_id, q, limit=10) -> List[Label]` | `LIKE %q%` su `name_norm`, prefix-match prima, poi alfabetico. |
| `get_labels_with_counts(account_id) -> List[dict]` | `{id, name, name_norm, movements_count}`. **Una** query sui movimenti (`id, note`) e conteggio in Python con un `Counter`: non una query per label. |
| `rename_label(label_id, new_name, account_id) -> int` | Riscrive le note dei movimenti coinvolti, aggiorna `name`/`name_norm`. Se `new_name` collide con un'altra label dell'account → **merge**: le note passano da `labels.rename_label`, la riga sorgente viene cancellata. Ritorna i movimenti riscritti. |
| `delete_label(label_id, account_id) -> int` | `labels.remove_label` sulle note dei movimenti coinvolti, poi `DELETE` della riga. Ritorna i movimenti toccati. |

`rename_label` e `delete_label` lavorano in **una** transazione: o tutte le
note sono riscritte, o nessuna.

**Scrivi una nota solo se è cambiata.** `labels.remove_label` e
`labels.rename_label` applicano `normalize_space` al risultato *anche quando non
trovano la label*: chiamarle su tutti i movimenti e salvare sempre
riscriverebbe la spaziatura di note che non c'entrano nulla. Confronta il
valore di ritorno con quello di partenza e assegna solo se differiscono — vale
anche per il conteggio ritornato, che deve contare i movimenti **toccati**, non
quelli esaminati.

**La corsa fra due membri.** Due sessioni che creano `#nuova` insieme fanno
scattare l'`UNIQUE`. `sync_from_note` deve: tentare l'insert in un
**savepoint** (`db.begin_nested()`), e su `IntegrityError` fare rollback del
solo savepoint e **rileggere** la riga. Il test lo verifica con due thread e
due sessioni: nessuna eccezione deve uscire, e in tabella deve restare **una**
riga.

## 2.4 L'hook: nel repository, non nelle rotte

`sync_from_note` va chiamata — e il suo **valore di ritorno** usato come nota —
in cinque punti:

- `MovementRepository.create_movement`
- `MovementRepository.update_movement` (solo se `note` è fra i campi aggiornati)
- `MovementRepository.bulk_update_movements` (quando `note is not None`)
- `RecurrentMovementRepository.create_recurrent_movement`
- `RecurrentMovementRepository.update_recurrent_movement`

È così che import CSV, correzione massiva e tool MCP registrano le label senza
saperlo. Niente chiamate a `sync_from_note` da `app.py`: se ti viene la
tentazione, l'hook è nel posto sbagliato.

## 2.5 Il filtro

`labels: Optional[List[str]] = None` come **ultimo** parametro di
`get_movements_for_account` e di `get_movements_stats` (entrambe sono chiamate
con keyword, quindi aggiungerlo in coda non rompe nessun chiamante):

```python
if labels:
    for name in labels:
        query = query.filter(func.ps_has_label(Movement.note, name) == 1)
```

**In AND**, non in OR — diverso dai `keywords`, che sono in OR
(`repository.py:720`). Il predicato va applicato **dopo** gli altri filtri
nella stessa `WHERE`: `ps_has_label` è una scansione, e conviene che veda meno
righe possibile. `search_movements` **non** cambia in questa fase.

## 2.6 `migrations/backfill_labels.py`

Script eseguibile **e** importabile: il test fa `from backfill_labels import backfill`.

- `backfill(db) -> int` (numero di label create): scorre i movimenti di tutti
  gli account ordinati per `(account_id, move_date, id)`, estrae le label, e
  per ogni `(account_id, name_norm)` mancante crea la riga con la grafia del
  movimento **più vecchio** (deterministico e ripetibile).
- **Idempotente**: una seconda esecuzione crea 0 righe.
- **Non riscrive le note.**
- Eseguito da riga di comando usa `conf.get_db_session()` e stampa un
  riepilogo; eseguito dal test riceve la sessione in-memory. Nessun
  `commit()` implicito in posti strani: una transazione, un commit alla fine.
