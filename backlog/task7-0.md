# Task 7.0: Miglioramento Gestione Categorie

Questo task si occupa di migliorare l'esperienza utente nella gestione delle categorie all'interno della pagina Settings, introducendo ordinamento personalizzato e logiche avanzate di rinomina e unificazione.

## Obiettivi
1. Separare visivamente le categorie di Entrata e Uscita.
2. Introdurre un ordinamento personalizzato persistente (tramite nuovo campo DB).
3. Gestire la coerenza dei dati (tabella MOVEMENTS) durante la rinomina delle categorie.
4. Implementare il "merge" automatico delle categorie in caso di conflitto di nomi.

## Modifiche al Database
È necessario aggiungere una colonna per l'ordinamento alla tabella `category`.
Lo script di migrazione dovrà essere posizionato in: `sql/sqllite/NEXT_RELEASE/alter_category_add_order.sql`.

```sql
ALTER TABLE category ADD COLUMN order_index INTEGER DEFAULT 0;
```

## Specifiche Funzionali

### 1. Interfaccia Settings Categorie
- **Separazione**: La pagina di gestione categorie deve presentare due sezioni o tab distinti: "Uscite" (Expense) e "Entrate" (Income).
- **Visualizzazione**: Elenco delle categorie con possibilità di modifica nome e ordine.
- **Ordinamento**:
  - Default: visualizzare le categorie ordinate per `order_index` (ascendente).
  - Opzione UI: permettere all'utente di ordinare temporaneamente la lista in ordine alfabetico per facilitare la ricerca.
- **Input Ordine**:
  - Campo numerico modificabile per ogni categoria.
  - Validazione: Accetta solo numeri interi positivi (>= 0).

### 2. Logica di Aggiornamento (Rinomina)
Quando l'utente modifica il nome di una categoria (es. da "Cibo" a "Alimentari"):

1. **Verifica Esistenza Destinazione**: Controllare se esiste già una categoria con il nome "Alimentari" per lo stesso Account e Tipo.

2. **Caso A: Il nuovo nome NON esiste (Semplice Rinomina)**
   - Aggiornare il record nella tabella `category`: `name = "Alimentari"`.
   - **Retrocompatibilità**: Aggiornare la tabella `movements`.
     - `UPDATE movements SET category = "Alimentari" WHERE category = "Cibo" AND account_id = :current_account_id`

3. **Caso B: Il nuovo nome ESISTE già (Merge/Unificazione)**
   - Esempio: Rinominare "Ristorante" in "Cibo", ma "Cibo" esiste già.
   - Aggiornare tutti i movimenti collegati alla *vecchia* categoria ("Ristorante") per puntare alla categoria *esistente* ("Cibo").
     - `UPDATE movements SET category = "Cibo" WHERE category = "Ristorante" AND account_id = :current_account_id`
   - Eliminare la *vecchia* categoria ("Ristorante") dal database, poiché ora è ridondante.

### 3. Backend (Repository)
Aggiornare `repository.py` per gestire la transazione atomica:
- Metodo `update_category(account_id, category_id, new_name, new_order)`
- Deve gestire all'interno di una transazione SQL (`session.begin()`, `commit()`, `rollback()`) sia l'update della tabella `category` che l'update massivo della tabella `movements`.

## Note Tecniche
- Mantenere la compatibilità con la colonna `category` (stringa) della tabella `MOVEMENTS` come da specifiche generali.
- Assicurarsi che l'ordinamento agisca solo a livello di visualizzazione e non alteri l'integrità dei dati storici se non richiesto esplicitamente.
