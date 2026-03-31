# Task 11.0: Gestione Spese Ricorrenti

## Obiettivo

Implementare la gestione delle **spese ricorrenti** come archivio di template di movimento. L'utente può definire spese/entrate ricorrenti (es. affitto, abbonamenti) e richiamarle dalla maschera di creazione movimento per pre-popolare il form in un click, impostando automaticamente la data odierna.

---

## Analisi

### Stato attuale

- La tabella `Movement` registra i movimenti effettivi con data, categoria, wallet, importo e note.
- La maschera `ps-add-mov.html` (route `/create`) permette la creazione e modifica di un movimento.
- Non esiste alcun meccanismo per memorizzare template di spese ricorrenti.

### Problema

L'utente deve reinserire manualmente gli stessi dati ogni mese per spese fisse (affitto, bollette, abbonamenti). Manca un archivio di template riutilizzabili.

---

## Soluzione

### 1. Nuova tabella `RecurrentMovement`

Tabella gemella di `Movement`, senza i campi data (che sono specifici di ogni occorrenza). Aggiunge un campo `name` per identificare la spesa ricorrente nella UI.

**Colonne:**

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | Integer, PK, autoincrement | |
| `name` | Text, not null | Etichetta human-friendly (es. "Affitto", "Netflix") |
| `category_id` | Integer, FK → Category.id, not null | |
| `wallet_id` | Integer, FK → Wallet.id, not null | |
| `income` | Numeric(10,2), nullable | |
| `expense` | Numeric(10,2), nullable | |
| `note` | Text, nullable | |
| `account_id` | Integer, FK → Account.id, not null | |
| `created_at` | DateTime, not null, default now | |

**Vincoli:**
- `CHECK`: esattamente uno tra `income` e `expense` deve essere non-null (stesso vincolo logico di `Movement`)
- Indice su `account_id` per query filtrate per account

### 2. Nuova pagina Gestione Spese Ricorrenti

**Route:** `GET /recurrent-movements`  
**Template:** `ps-recurrent-mov.html`

La pagina contiene:
- **Lista** di tutte le spese ricorrenti dell'account corrente, con colonne: Nome, Tipo (Entrata/Uscita), Categoria, Wallet, Importo, Note, Azioni
- **Maschera inserimento/modifica** identica alla maschera di `ps-add-mov.html`, con le seguenti differenze:
  - Al posto del campo `Data` c'è il campo `Nome` (etichetta della spesa ricorrente)
  - Nessun campo data
- **Pulsanti azione** per ogni riga della lista: Modifica (apre la maschera precompilata), Elimina (con conferma)

### 3. Selettore spesa ricorrente nella maschera Crea Movimento

In `ps-add-mov.html`, aggiungere in cima al form un nuovo campo opzionale:

**Campo:** `<select id="recurrent_template">` con opzione vuota di default ("Seleziona spesa ricorrente…") e le spese ricorrenti dell'account come opzioni.

**Comportamento al cambio:**
- Se l'utente seleziona una spesa ricorrente, il form viene pre-popolato con: tipo movimento, categoria, wallet, importo, note — presi dalla spesa ricorrente
- Il campo `Data` rimane invariato (data odierna o quella già inserita)
- La selezione di un template non blocca la modifica manuale dei campi
- Il campo selettore è visibile **solo in modalità creazione** (nascosto in modifica)

---

## Specifiche Tecniche

### Model (`pyspendless/models.py`)

Aggiungere la classe `RecurrentMovement`:

```python
class RecurrentMovement(Base):
    """Template di spesa/entrata ricorrente — usato per pre-popolare il form di creazione movimento"""
    __tablename__ = 'RecurrentMovement'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('Category.id'), nullable=False)
    wallet_id = Column(Integer, ForeignKey('Wallet.id'), nullable=False)
    income = Column(Numeric(10, 2), nullable=True)
    expense = Column(Numeric(10, 2), nullable=True)
    note = Column(Text, nullable=True)
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    category_obj = relationship('Category', foreign_keys=[category_id])
    wallet_obj = relationship('Wallet', foreign_keys=[wallet_id])
    account = relationship('Account')
```

Aggiungere a `Account` la relationship:

```python
recurrent_movements = relationship('RecurrentMovement', back_populates='account')
```

### Migrazione DB

Creare script di migrazione in `migrations/` (o SQL in `sql/sqllite/`) per `CREATE TABLE RecurrentMovement`.

```sql
CREATE TABLE IF NOT EXISTS RecurrentMovement (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    category_id INTEGER NOT NULL REFERENCES Category(id),
    wallet_id   INTEGER NOT NULL REFERENCES Wallet(id),
    income   NUMERIC(10,2),
    expense  NUMERIC(10,2),
    note     TEXT,
    account_id  INTEGER NOT NULL REFERENCES Account(id),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_recurrent_movement_account ON RecurrentMovement(account_id);
```

### Route e API (`pyspendless/app.py`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/recurrent-movements` | Pagina gestione spese ricorrenti (HTML) |
| `GET` | `/api/recurrent-movements` | Lista spese ricorrenti dell'account (JSON) |
| `POST` | `/api/recurrent-movements` | Crea nuova spesa ricorrente (JSON) |
| `PUT` | `/api/recurrent-movements/<int:id>` | Modifica spesa ricorrente (JSON) |
| `DELETE` | `/api/recurrent-movements/<int:id>` | Elimina spesa ricorrente (JSON) |

**Payload POST/PUT:**
```json
{
  "name": "Affitto",
  "category_id": 5,
  "wallet_id": 2,
  "movement_type": "expense",
  "amount": 750.00,
  "note": "Pagamento mensile affitto"
}
```

**Response GET `/api/recurrent-movements`:**
```json
[
  {
    "id": 1,
    "name": "Affitto",
    "category_id": 5,
    "category_name": "Casa",
    "wallet_id": 2,
    "wallet_name": "Conto Corrente",
    "income": null,
    "expense": 750.00,
    "note": "Pagamento mensile affitto"
  }
]
```

### Template — Nuova pagina (`pyspendless/templates/ps-recurrent-mov.html`)

- Estende `ps-nav.html`
- **Sezione lista:** tabella Bootstrap responsive con colonne: Nome, Tipo, Categoria, Wallet, Importo, Note, Azioni
- **Sezione form:** identica a `ps-add-mov.html` ma con campo `Nome` al posto della data; gestione JS inline analoga (fetch POST/PUT, alert successo/errore, reset form)
- **Modal di conferma** per l'eliminazione (Bootstrap modal, richiama DELETE API)
- La lista si aggiorna dinamicamente dopo ogni operazione senza ricaricare la pagina

### Template — Modifica form creazione movimento (`pyspendless/templates/ps-add-mov.html`)

Aggiungere prima del campo `Data` un nuovo blocco (visibile solo in creazione):

```html
{% if not movement %}
<div class="mb-3" id="recurrent-template-block">
  <label for="recurrent_template" class="form-label">Spesa Ricorrente</label>
  <select class="form-select" id="recurrent_template" name="recurrent_template">
    <option value="">— Seleziona spesa ricorrente (opzionale) —</option>
    {% for rt in recurrent_movements %}
      <option value="{{ rt.id }}"
              data-movement-type="{{ 'income' if rt.income else 'expense' }}"
              data-category-id="{{ rt.category_id }}"
              data-wallet-id="{{ rt.wallet_id }}"
              data-amount="{{ rt.income or rt.expense }}"
              data-note="{{ rt.note or '' }}">
        {{ rt.name }}
      </option>
    {% endfor %}
  </select>
</div>
{% endif %}
```

**Logica JS** — listener su `change` del select:

```javascript
document.getElementById('recurrent_template')?.addEventListener('change', function () {
  const selected = this.options[this.selectedIndex];
  if (!selected.value) return;

  const movType = selected.dataset.movementType;
  const categoryId = selected.dataset.categoryId;
  const walletId = selected.dataset.walletId;
  const amount = selected.dataset.amount;
  const note = selected.dataset.note;

  document.getElementById('movement_type').value = movType;
  filterCategories(); // rifiltra le categorie per il tipo selezionato
  document.getElementById('category').value = categoryId;
  document.getElementById('wallet').value = walletId;
  document.getElementById('amount').value = amount;
  document.getElementById('note').value = note;
  // La data NON viene toccata
});
```

### Route `/create` — aggiornamento

Passare `recurrent_movements` al template:

```python
recurrent_movements = db.query(RecurrentMovement)\
    .filter(RecurrentMovement.account_id == current_user.account_id)\
    .order_by(RecurrentMovement.name)\
    .all()
return render_template('ps-add-mov.html', ..., recurrent_movements=recurrent_movements)
```

### Navigazione (`ps-nav.html`)

Aggiungere voce di menu "Spese Ricorrenti" nella navbar/sidebar, linkante a `/recurrent-movements`.

---

## File da modificare / creare

| File | Tipo | Modifica |
|------|------|----------|
| `pyspendless/models.py` | Modifica | Aggiungere classe `RecurrentMovement` e relationship su `Account` |
| `pyspendless/app.py` | Modifica | Aggiungere route pagina + 4 API endpoint; aggiornare route `/create` |
| `pyspendless/templates/ps-add-mov.html` | Modifica | Aggiungere selettore spesa ricorrente + logica JS |
| `pyspendless/templates/ps-recurrent-mov.html` | Nuovo | Pagina gestione spese ricorrenti (lista + form) |
| `pyspendless/templates/ps-nav.html` | Modifica | Aggiungere voce di menu |
| `migrations/` o `sql/sqllite/` | Nuovo | Script SQL migrazione tabella `RecurrentMovement` |

---

## Criteri di accettazione

- [ ] La tabella `RecurrentMovement` viene creata correttamente nel DB con tutti i vincoli.
- [ ] La pagina `/recurrent-movements` mostra la lista delle spese ricorrenti dell'account corrente.
- [ ] È possibile creare una nuova spesa ricorrente tramite il form della pagina dedicata.
- [ ] È possibile modificare una spesa ricorrente esistente: il form si precompila con i dati attuali.
- [ ] È possibile eliminare una spesa ricorrente con richiesta di conferma.
- [ ] In `ps-add-mov.html` (modalità creazione), è visibile il selettore "Spesa Ricorrente".
- [ ] Selezionando una spesa ricorrente, il form si pre-popola correttamente (tipo, categoria, wallet, importo, note).
- [ ] La data rimane invariata alla selezione di una spesa ricorrente.
- [ ] Il selettore non è visibile in modalità modifica di un movimento esistente.
- [ ] Le spese ricorrenti sono isolate per account (nessuna visibilità cross-account).
- [ ] La navbar contiene il link alla pagina Spese Ricorrenti.
