# Task 7.0: Miglioramento Gestione Categorie - Implementato

## Riepilogo Implementazione

### 1. ✅ Modifiche al Database
- **File**: `sql/sqllite/NEXT_RELEASE/alter_category_add_order.sql`
- **Azione**: Aggiunta colonna `order_index INTEGER DEFAULT 0` alla tabella `Category`
- **Stato**: Migrazione applicata con successo al database

### 2. ✅ Modifiche al Modello
- **File**: `pyspendless/models.py`
- **Azione**: Aggiunto campo `order_index = Column(Integer, nullable=False, default=0)` alla classe `Category`
- **Stato**: Modello aggiornato e testato

### 3. ✅ Modifiche al Repository
- **File**: `pyspendless/repository.py`
- **Classe**: `CategoryRepository`

**Metodi aggiornati:**

#### `get_categories_for_account(account_id, order_by_index=True)`
- Nuovo parametro opzionale `order_by_index`
- Se `True`: ordina per `order_index` e poi per `name`
- Se `False`: ordina solo per `name` (alfabetico)

#### `create_category(..., order_index=0)`
- Nuovo parametro opzionale `order_index` con default 0
- Permette di specificare l'ordine alla creazione

#### `update_category(category_id, data)`
- **Logica completa di rinomina e merge implementata:**

**CASO A - Rinomina Semplice** (nuovo nome NON esiste):
1. Aggiorna il nome nella tabella `Category`
2. Aggiorna retrocompatibilità: campo `category` (stringa) in tutti i `Movement` correlati

**CASO B - Merge/Unificazione** (nuovo nome ESISTE già):
1. Aggiorna tutti i `Movement` che puntano alla vecchia categoria per usare il nuovo nome
2. Aggiorna `category_id` dei movimenti per puntare alla categoria esistente
3. Aggiorna `order_index` della categoria target se specificato
4. Elimina la categoria vecchia (ora ridondante)

- **Transazioni atomiche**: Usa commit/rollback per garantire consistenza
- **Gestione errori**: Solleva SQLAlchemyError in caso di problemi

### 4. ✅ Modifiche alle API
- **File**: `pyspendless/app.py`

**API aggiornate:**

#### `GET /api/categories`
- **Risposta aggiornata**: Include campo `order_index` per ogni categoria
- **Ordinamento**: Usa `order_by_index=True` per default

#### `POST /api/accounts/<id>/categories`
- **Nuovo campo**: Accetta `order_index` (opzionale, default 0)
- **Risposta aggiornata**: Include `order_index` nella risposta JSON

#### `PUT /api/categories/<id>`
- **Supporto completo**: Gestisce aggiornamento di `name` e `order_index`
- **Gestione errori migliorata**: Cattura eccezioni e ritorna errori dettagliati
- **Risposta aggiornata**: Include `order_index`
- **Logica**: Delega al repository la gestione di rinomina/merge

### 5. ✅ Modifiche al Template
- **File**: `pyspendless/templates/ps-setting-categories.html` (completamente riscritto)
- **Backup**: Vecchio template salvato come `ps-setting-categories-old.html`

**Nuove funzionalità UI:**

#### Layout con Tabs
- **Tab "Uscite"**: Mostra solo categorie di tipo `expense`
- **Tab "Entrate"**: Mostra solo categorie di tipo `income`
- **Separazione visiva**: Icone colorate (rosso per uscite, verde per entrate)

#### Campo Ordine
- **Input numerico**: Ogni categoria ha un campo di input per `order_index`
- **Aggiornamento rapido**: Modifica dell'ordine avviene on-change senza aprire modal
- **Validazione**: Accetta solo numeri interi ≥ 0

#### Ordinamento Flessibile
- **Bottone toggle**: "Ordine Alfabetico" ↔ "Ordine Personalizzato"
- **Stato persistente**: Durante la sessione
- **Default**: Ordinamento per `order_index` (personalizzato)

#### Modal Aggiungi Categoria
- **Nuovo campo**: Input per `order_index` (opzionale, default 0)
- **Hint**: Testo di aiuto per spiegare l'uso

#### Modal Modifica Categoria
- **Campo Ordine**: Modificabile direttamente nel modal
- **Avviso merge**: Testo informativo che spiega il comportamento di unificazione
- **Conferma merge**: Dialog di conferma se si rinomina con un nome esistente

#### JavaScript Migliorato
- **Gestione locale dello stato**: Array `allCategories` per rendering reattivo
- **Toggle ordinamento**: Funzione che cambia tra alfabetico e personalizzato
- **Aggiornamento ordine inline**: Funzione `updateCategoryOrder()` per modifiche rapide
- **Validazione client-side**: Controllo sui valori numerici
- **UX ottimizzata**: Alert temporanei, conferme per azioni distruttive

## Funzionalità Implementate

### ✅ Separazione Categorie per Tipo
Le categorie di entrata e uscita sono visualizzate in tab separate per una migliore organizzazione.

### ✅ Ordinamento Personalizzato Persistente
Il campo `order_index` nel database permette agli utenti di ordinare le categorie come preferiscono. L'ordine viene salvato e mantenuto tra le sessioni.

### ✅ Aggiornamento Ordine Rapido
Gli utenti possono modificare l'ordine direttamente dalla tabella senza aprire modal.

### ✅ Toggle Alfabetico
Possibilità di visualizzare temporaneamente le categorie in ordine alfabetico per facilitare la ricerca.

### ✅ Rinomina Intelligente con Coerenza Dati
La rinomina di una categoria aggiorna automaticamente tutti i movimenti esistenti nel campo `category` (retrocompatibilità).

### ✅ Merge Automatico
Se si rinomina una categoria con un nome già esistente, il sistema:
- Unifica automaticamente le due categorie
- Sposta tutti i movimenti alla categoria target
- Elimina la categoria ridondante
- Mantiene la consistenza del database

### ✅ Transazioni Atomiche
Tutte le operazioni di modifica sono gestite con transazioni per garantire la consistenza del database in caso di errore.

## Test Eseguiti

### ✅ Test Database
```bash
sqlite3 data/pyspendless3.db "PRAGMA table_info(Category);"
```
**Risultato**: Colonna `order_index` presente e configurata correttamente.

### ✅ Test Modello
```python
from models import Category
from conf import get_db_session
db = get_db_session()
cats = db.query(Category).first()
print(f'order_index: {cats.order_index}')
```
**Risultato**: Campo `order_index` accessibile e funzionante (valore: 0).

## Compatibilità

### ✅ Retrocompatibilità Movements
Il campo `category` (stringa) nella tabella `MOVEMENTS` viene sempre aggiornato durante le operazioni di rinomina/merge, mantenendo la compatibilità con codice esistente.

### ✅ Default Values
Il campo `order_index` ha default 0, quindi categorie esistenti e nuove categorie create senza specificare l'ordine funzionano correttamente.

### ✅ Migration Non-Distruttiva
La migrazione aggiunge solo una colonna con un valore default, senza modificare dati esistenti.

## Note Tecniche

### Sicurezza
- Tutte le API verificano l'autenticazione dell'utente
- Le operazioni sono limitate all'account dell'utente loggato
- Validazione lato client e server per `order_index`

### Performance
- Query ordinate a livello database
- Rendering client-side per evitare ricaricamenti completi
- Aggiornamenti parziali quando possibile

### UX
- Feedback immediato tramite alert temporanei
- Conferme per azioni potenzialmente distruttive (merge, delete)
- Hint e testi informativi per guidare l'utente

## File Modificati

1. `sql/sqllite/NEXT_RELEASE/alter_category_add_order.sql` (nuovo)
2. `pyspendless/models.py` (modificato)
3. `pyspendless/repository.py` (modificato - CategoryRepository)
4. `pyspendless/app.py` (modificato - API categories)
5. `pyspendless/templates/ps-setting-categories.html` (riscritto)
6. `data/pyspendless3.db` (migrato)

## File di Backup

- `pyspendless/templates/ps-setting-categories-old.html` (backup del vecchio template)

## Status: ✅ COMPLETATO

Tutte le specifiche del Task 7.0 sono state implementate con successo.
