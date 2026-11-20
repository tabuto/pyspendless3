# Fase 1 — Il repository

**Chi**: subagent **`ps-py`** (haiku).
**Dipende da**: Fase 0.
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task28_0.py repo`
esce con **exit code 0**, e le quattro suite di regressione di `CLAUDE.md`
restano verdi.
**File che puoi toccare**: `pyspendless/repository.py`. **Nient'altro** — non
`app.py` (è la Fase 2), non i template, non il test (è il metro: se un caso ti
sembra sbagliato, **fermati e dillo**, non modificarlo).

## Il mandato

Un parametro in più su
`MovementRepository.bulk_update_movements` ([repository.py:1095](../../../pyspendless/repository.py)):

```python
def bulk_update_movements(
    self,
    account_id: int,
    filters: Dict[str, Any],
    category=None,
    category_id: Optional[int] = None,
    note: Optional[str] = None,
    add_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

**Il tipo di ritorno cambia**: oggi è `int`, diventa un dict
`{'updated': int, 'skipped': int, 'labels': List[str]}`. L'unico chiamante è
`api_bulk_update_movements` ([app.py:984](../../../pyspendless/app.py)), che la
Fase 2 adegua; il caso 16 della sezione `repo` verifica che con
`add_labels=None` i numeri siano quelli di oggi.

> Se preferisci non toccare la firma di ritorno, **non** aggiungere un secondo
> metodo che duplica il corpo: due implementazioni della stessa operazione sono
> due operazioni da tenere allineate. Il dict è la scelta della specifica.

### 1. Risolvere il registro, una volta

Prima del ciclo, e **solo se c'è almeno un movimento** da scrivere
(spec §5: con zero movimenti filtrati non si registra niente):

```python
canon_names = []
if add_labels and movements:
    label_repo = LabelRepository(self.db)
    canon_note = label_repo.sync_from_note(
        account_id, ' '.join('#' + n.lstrip('#') for n in add_labels))
    canon_names = labels.extract(canon_note)
```

`labels` si importa con il doppio fallback che usa già `sync_from_note`
([repository.py:700](../../../pyspendless/repository.py)): `import labels` e, su
`ImportError`, `from . import labels`. Il progetto si importa in due modi (piatto
e come package) e un import senza fallback passa i test e si rompe in
produzione — è già successo.

**Non** chiamare `sync_from_note` dentro il ciclo. Il caso 7 della sezione
`repo` conta le chiamate con una spia e pretende esattamente 1 su 5 movimenti.

### 2. Il ciclo

Per ogni movimento, nell'ordine di spec §4: categoria, poi nota (identica per
tutti), poi le label (una nota diversa per ciascuno).

L'append usa `labels.add_label(note, name)` — già idempotente
case-insensitive, già con l'`rstrip`, già con il caso `None` → `'#name'`. **Non
riscriverla** e non usare una concatenazione a mano: la funzione ha 112 casi di
test alle spalle.

Prima di scrivere, i due limiti di spec §6 — importati da `conf`, non
riscritti:

```python
from conf import MAX_NOTE_LENGTH, MAX_LABELS_PER_MOVEMENT  # con il fallback .conf
```

| Condizione sul movimento | Cosa fai |
|---|---|
| `labels.has_label(nota, name)` | niente (no-op), e **non** è un salto |
| le label distinte già nella nota sono `>= MAX_LABELS_PER_MOVEMENT` | salti questa label su questo movimento, `skipped` conta il movimento **una volta sola** |
| `len(add_label(nota, name)) > MAX_NOTE_LENGTH` | come sopra |

Il conteggio è **per movimento**, non per coppia (movimento, label): un
movimento che non ha ricevuto una delle tre label richieste va in `skipped`
una volta, e se ne ha ricevuta almeno una va **anche** in `updated`. Il caso 12
distingue "saltato" da "no-op": leggilo prima di scrivere il ciclo.

### 3. Il commit

Resta **uno solo**, in fondo, come oggi. Nessun commit per movimento: su un
filtro annuale sono migliaia di transazioni per lo stesso risultato.

## Trappole misurate

1. **`get_movements_for_account(**filters)` con `filters = {}`** restituisce
   tutti i movimenti dell'account: è il comportamento che il caso 16 e il test
   del task26-0 (`test_task26_0.py:286`) danno per buono. Non aggiungere
   default ai filtri.
2. **`m.note` può essere `None`**: `add_label(None, 'casa')` ritorna `'#casa'`,
   ma `len(m.note)` su `None` solleva. Misura la lunghezza sul **risultato** di
   `add_label`, non sull'originale.
3. **Il contatore delle label già presenti** si ricava da
   `labels.extract_norm(m.note)`, che deduplica case-insensitive: contare le
   occorrenze di `'#'` nel testo darebbe un numero diverso (e sbagliato) su
   `'#casa #casa'` o su `'ordine #12 del mese'`.
4. **`sync_from_note` con un solo nome** restituisce la nota canonicalizzata,
   non la lista: le grafie canoniche si rileggono con `labels.extract`, nello
   stesso ordine in cui sono state passate. Il caso 4 verifica l'ordine.

## Stile

Commenti in italiano che dicono **perché** (il modello di forma è
`TokenRepository` e `WalletRepository` nello stesso file), docstring aggiornata
con il parametro e il nuovo ritorno, **nessun refactoring collaterale**: la
riga 1110 (`get_movements_for_account`) e il blocco della categoria si toccano
solo se il metro lo chiede.

Se una scelta non è coperta né dalla specifica né dal test, prendi la più
conservativa, scrivi nel commento perché, e **segnalala** nel riepilogo.
