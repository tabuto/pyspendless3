# Task 15.0: Colonna "Data ultima spesa" nell'elenco spese ricorrenti

## Obiettivo

Aggiungere la colonna **Data ultima spesa** alla tabella delle spese ricorrenti (`/recurrent-movements`). La colonna mostra la data dell'ultimo movimento effettivamente registrato che è stato creato usando quella spesa ricorrente come template. Se nessun movimento è mai stato registrato con quel template, la cella mostra "—".

---

## 1. Analisi della situazione attuale

Il modello `RecurrentMovement` (`pyspendless/models.py`, riga 183) è usato esclusivamente come template per pre-compilare il form di inserimento movimento. Attualmente:

- Non esiste alcun legame FK tra `Movement` e `RecurrentMovement`.
- Il payload inviato da `ps-add-mov.html` all'API `/api/movements` (metodo POST) **non include** il campo `recurrent_movement_id`.
- Non è quindi possibile risalire, dai movimenti esistenti, al template ricorrente usato per crearli.

Per implementare la feature è necessario **aggiungere il tracciamento esplicito**: quando l'utente crea un movimento partendo da un template ricorrente, l'ID del template viene salvato sul movimento.

---

## 2. Modifiche da effettuare

### 2.1 Schema DB — nuovo file SQL di migrazione

Creare il file `sql/sqllite/NEXT_RELEASE/alter_movement_add_recurrent_id.sql`:

```sql
ALTER TABLE Movement
  ADD COLUMN recurrent_movement_id INTEGER
  REFERENCES RecurrentMovement(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_movement_recurrent
  ON Movement(recurrent_movement_id);
```

> SQLite consente `ALTER TABLE … ADD COLUMN` solo per colonne nullable senza default diverso da NULL. Il vincolo FK è supportato ma richiede `PRAGMA foreign_keys = ON` a runtime (già attivo nell'app tramite SQLAlchemy).

### 2.2 `pyspendless/models.py` — modello `Movement`

Aggiungere il campo e la relationship al modello `Movement` (dopo la riga 136):

```python
recurrent_movement_id = Column(
    Integer,
    ForeignKey('RecurrentMovement.id', ondelete='SET NULL'),
    nullable=True
)

# Relationship
recurrent_movement_obj = relationship('RecurrentMovement', foreign_keys=[recurrent_movement_id])
```

### 2.3 `pyspendless/templates/ps-add-mov.html` — invio del template ID

Nel listener `change` del select `#recurrent_template` (riga ~151), leggere l'`id` del template selezionato e memorizzarlo in un campo hidden (o in una variabile JS):

```html
<input type="hidden" id="recurrent_movement_id" value="">
```

Nel listener `change`:
```js
document.getElementById('recurrent_movement_id').value = selected.value || '';
```

Nel payload del submit (riga ~184), aggiungere il campo:
```js
const formData = {
  ...
  recurrent_movement_id: parseInt(document.getElementById('recurrent_movement_id').value) || null,
};
```

### 2.4 `pyspendless/app.py` — route `POST /api/movements` (riga ~circa 450)

Accettare e passare il nuovo campo nel dizionario `data` che viene fornito a `MovementRepository.create_movement`. Il metodo `create_movement` (repository.py riga 621) usa `Movement(**data)`, quindi è sufficiente che il campo sia presente nel dict solo quando non è `None`:

```python
recurrent_movement_id = body.get('recurrent_movement_id')
if recurrent_movement_id:
    data['recurrent_movement_id'] = int(recurrent_movement_id)
```

Non è necessario modificare `create_movement` in `repository.py` poiché usa `**data`.

### 2.5 `pyspendless/repository.py` — `RecurrentMovementRepository.get_all_for_account`

Sostituire il metodo `get_all_for_account` (riga 1299) con una query che recupera anche la data dell'ultimo movimento associato tramite subquery:

```python
from sqlalchemy import func

def get_all_for_account(self, account_id: int):
    """Restituisce tutte le spese ricorrenti con la data dell'ultimo movimento associato."""
    subq = (
        self.db.query(
            Movement.recurrent_movement_id,
            func.max(Movement.move_date).label('last_move_date')
        )
        .filter(Movement.account_id == account_id)
        .group_by(Movement.recurrent_movement_id)
        .subquery()
    )

    rows = (
        self.db.query(RecurrentMovement, subq.c.last_move_date)
        .outerjoin(subq, RecurrentMovement.id == subq.c.recurrent_movement_id)
        .filter(RecurrentMovement.account_id == account_id)
        .order_by(RecurrentMovement.name)
        .all()
    )

    # Inietta last_move_date come attributo sull'oggetto per semplicità nel template
    for rm, last_date in rows:
        rm.last_move_date = last_date

    return [rm for rm, _ in rows]
```

L'import di `Movement` è già presente nella classe (`from .models import …`) — verificare che sia nella stessa sezione degli import del repository.

### 2.6 `pyspendless/templates/ps-recurrent-mov.html` — nuova colonna

**Intestazione** (riga ~77), aggiungere `<th>` dopo "Nota":
```html
<th>Data ultima spesa</th>
```

**Corpo tabella** (riga ~95), aggiungere `<td>` dopo la cella Nota:
```html
<td>
  {% if rm.last_move_date %}
    {{ rm.last_move_date.strftime('%d/%m/%Y') }}
  {% else %}
    —
  {% endif %}
</td>
```

Aggiornare il `colspan` della riga vuota da `7` a `8` (riga ~109):
```html
<td colspan="8" class="text-center text-muted py-3">Nessuna spesa ricorrente definita</td>
```

---

## 3. Note tecniche

- La subquery usa `func.max(Movement.move_date)` che opera sul tipo `Date` di SQLAlchemy: il confronto e l'ordinamento sono corretti senza conversioni a stringa.
- Il campo `recurrent_movement_id` su `Movement` è nullable: i movimenti creati manualmente (senza selezionare un template) mantengo `NULL` e non influenzano le statistiche delle spese ricorrenti.
- Nessuna migrazione dei dati storici è necessaria: i movimenti precedenti avranno `recurrent_movement_id = NULL` e il comportamento della colonna sarà "—" per tutti i template fino al primo utilizzo successivo alla migrazione.
- La route `/recurrent-movements` in `app.py` (riga ~882) non richiede modifiche al codice Python, poiché `get_all_for_account` restituisce già gli stessi oggetti `RecurrentMovement` con l'attributo `last_move_date` iniettato dinamicamente.
- La modifica non impatta le route dei Reports (task 13), la ricerca movimenti (`/ps-search-mov`), né i filtri per data (task 14).

---

## 4. Piano di implementazione

1. Creare il file SQL di migrazione (`alter_movement_add_recurrent_id.sql`) ed eseguirlo sul DB di sviluppo.
2. Aggiornare `models.py` con il nuovo campo e la relationship.
3. Aggiornare `ps-add-mov.html`: campo hidden + aggiornamento listener JS + payload submit.
4. Aggiornare la route `POST /api/movements` in `app.py` per leggere e salvare `recurrent_movement_id`.
5. Aggiornare `get_all_for_account` in `repository.py` con la subquery.
6. Aggiornare il template `ps-recurrent-mov.html` con la nuova colonna.
7. Test manuali: creare un movimento dal template → verificare che la data compaia nella lista; creare un movimento manuale → verificare che non alteri le altre righe.

---

## Criteri di accettazione

- [ ] Creando un movimento tramite un template ricorrente, il campo `recurrent_movement_id` viene salvato correttamente nel DB.
- [ ] La colonna "Data ultima spesa" mostra la data più recente del movimento associato al template, formattata `GG/MM/AAAA`.
- [ ] Per i template mai usati, la colonna mostra "—".
- [ ] I movimenti creati senza selezionare un template non influenzano la colonna di nessun template.
- [ ] La tabella rimane funzionante per le azioni Modifica ed Elimina (colspan aggiornato).
- [ ] I movimenti esistenti (pre-migrazione) non mostrano date errate.
