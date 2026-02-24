# Task 1.5: Visualizzazione Movimenti e Statistiche

## Obiettivo
Implementare la pagina per la visualizzazione dei movimenti (spese/entrate) con funzionalità di filtraggio avanzato, visualizzazione tabellare interattiva (DataTables) e grafica (Chart.js), rispettando i requisiti di `SPECS.md`.

## Specifiche Tecniche

### 1. Backend (`app.py` & `repository.py`)

#### `repository.py`
Estendere le funzionalità per supportare il filtraggio dinamico dei movimenti.
- Implementare/Aggiornare una funzione `get_movements(account_id, filters)` che accetti:
  - `year`, `month` (default: mese corrente)
  - `wallet_id` (opzionale)
  - `category_type` (expense, income, transfer - opzionale)
  - `category_id` (opzionale)
- La funzione deve restituire l'elenco dei movimenti filtrati.
- Implementare una funzione di aggregazione `get_movements_stats(account_id, filters)` per calcolare:
  - Totale Entrate (`income`)
  - Totale Uscite (`expense`)
  - Dati raggruppati per categoria per il grafico (Somma `expense` per `category`).

#### `app.py`
- Creare la rotta `GET /movements` (o `/ps-show-mov`).
- La view function deve:
  1. Recuperare i filtri dalla query string (`request.args`). Se assenti, usare anno/mese corrente.
  2. Recuperare le liste per i filtri (tutti i wallet, tutte le categorie dell'account, tipi categoria) da passare al template.
  3. Chiamare il repository per ottenere i movimenti e le statistiche filtrate.
  4. Renderizzare il template `ps-show-mov.html` passando: movimenti, statistiche, opzioni filtri, e filtri attivi.

### 2. Frontend (`ps-show-mov.html`)

Creare il file `templates/ps-show-mov.html` estendendo `base.html` (o `ps-base.html` se è quello in uso per l'app protetta).

#### Struttura Pagina
1.  **Barra dei Filtri**:
    - Form `GET` che ricarica la pagina con i nuovi parametri.
    - Dropdown per: **Anno**, **Mese**, **Wallet**, **Tipo Categoria**, **Categoria**.
    - Bottone "Filtra".

2.  **Sezione Statistiche (KPI Cards)**:
    - Card "Totale Entrate": Mostra la somma degli income filtrati.
    - Card "Totale Uscite": Mostra la somma delle expense filtrate.
    - (Opzionale) Card "Bilancio".

3.  **Grafico (Chart.js)**:
    - Canvas per un **Bar Chart**.
    - Asse X: Categorie.
    - Asse Y: Importi Spese (Expense).
    - I dati devono essere passati dal backend (es. tramite JSON in una variabile JS o attributo data-).

4.  **Tabella Movimenti (DataTables)**:
    - Tabella HTML con ID specifico (es. `#movementsTable`).
    - Colonne: Data, Categoria, Descrizione (Note), Wallet, Utente, Entrata, Uscita, Azioni (Modifica/Elimina).
    - Inizializzazione DataTables via Javascript (in `static/js/` o blocco script nel template) per paginazione e ordinamento client-side.
    - Classi Bootstrap per lo stile (`table table-striped ...`).

### 3. Integrazione Librerie (Static Assets)

Assicurarsi che le librerie siano incluse nel template (o in `base.html`):
- **Bootstrap 5** (già presente).
- **Chart.js**: Includere via CDN o file locale in `static/js/`.
- **DataTables** (con integrazione Bootstrap 5): Includere CSS e JS necessari.

### 4. Dettagli Implementativi & Vincoli
- **Retrocompatibilità**: La query deve lavorare sulla tabella `MOVEMENTS` come definito in `SPECS.md` (campi `income`, `expense`, `move_year`, `move_month`).
- **Layout**: Usare AdminLTE/Bootstrap come definito nel progetto.
- **Sicurezza**: Assicurarsi che l'utente veda solo i movimenti del proprio `account_id`.

### 5. Modifica Movimento (ps-add-mov.html)

La maschera di dettaglio movimento `ps-add-mov.html` deve supportare sia l'inserimento che la modifica di un movimento.

#### Backend (`app.py` & `repository.py`)
- Modificare la rotta `GET /ps-add-mov` per accettare un parametro opzionale `movement_id` nella query string.
- Se `movement_id` è presente:
  - Recuperare il movimento dal database tramite `repository.get_movement_by_id(movement_id, account_id)`.
  - Verificare che il movimento appartenga all'account dell'utente loggato.
  - Passare i dati del movimento al template per pre-compilare il form.
- Il form di salvataggio deve distinguere tra INSERT e UPDATE in base alla presenza dell'ID.

#### Frontend
- Modificare `ps-add-mov.html` per:
  - Pre-compilare i campi del form quando è presente un movimento da modificare.
  - Includere un campo hidden con l'ID del movimento (se in modifica).
  - Cambiare il titolo della pagina da "Aggiungi Movimento" a "Modifica Movimento" quando applicabile.
  - Il pulsante di submit deve riflettere l'azione (es. "Salva Movimento" sia per creazione che modifica).

### 6. Ricerca Movimenti (ps-search-mov.html)

Implementare una nuova pagina dedicata alla ricerca e visualizzazione di tutti i movimenti dell'account.

#### Backend (`app.py` & `repository.py`)

##### `repository.py`
- Implementare la funzione `search_movements(account_id, search_text=None, page=1, per_page=20)`:
  - Supporto per ricerca full-text su campi: `notes` (descrizione), nome categoria, nome wallet.
  - Paginazione server-side con parametri `page` e `per_page`.
  - Ritornare: lista movimenti, totale risultati, numero pagine.
  - Ordinamento default: data movimento (discendente).

##### `app.py`
- Creare la rotta `GET /ps-search-mov`:
  - Recuperare parametri: `search` (testo ricerca), `page` (default: 1).
  - Chiamare `repository.search_movements()`.
  - Renderizzare il template `ps-search-mov.html` passando: movimenti, info paginazione, testo ricerca corrente.

#### Frontend (`ps-search-mov.html`)

Creare il file `templates/ps-search-mov.html` estendendo `ps-base.html`.

##### Struttura Pagina
1. **Barra di Ricerca**:
   - Form `GET` con campo di input testo per la ricerca full-text.
   - Pulsante "Cerca".
   - Pulsante "Reset" per pulire i filtri e mostrare tutti i movimenti.

2. **Tabella Movimenti**:
   - Tabella HTML con Bootstrap styling.
   - Colonne: Data, Categoria, Descrizione (Notes), Wallet, Entrata, Uscita, Azioni.
   - Colonna "Azioni" con pulsanti:
     - **Modifica**: Link a `/ps-add-mov?movement_id=XXX`.
     - **Elimina**: Pulsante con conferma JavaScript.
   - Paginazione server-side con link alla stessa pagina con parametro `page`.

3. **Gestione Stato Vuoto**:
   - Se nessun risultato, mostrare messaggio "Nessun movimento trovato".

##### Integrazione
- La tabella deve essere responsive (Bootstrap).
- Evidenziare il testo cercato nei risultati (opzionale, tramite highlight JavaScript).

## Definition of Done
- [ ] La pagina `ps-show-mov.html` è accessibile agli utenti loggati.
- [ ] I filtri funzionano correttamente ricaricando i dati.
- [ ] Il grafico a barre mostra le spese per categoria in base ai filtri attivi.
- [ ] La tabella è paginata e ordinabile tramite DataTables.
- [ ] I totali (Entrate/Uscite) corrispondono alla somma dei dati visualizzati.
- [ ] La maschera `ps-add-mov.html` permette di modificare un movimento esistente quando viene passato `movement_id`.
- [ ] I dati del movimento vengono pre-caricati correttamente nel form di modifica.
- [ ] La pagina `ps-search-mov.html` mostra tutti i movimenti con paginazione server-side.
- [ ] La ricerca full-text funziona su descrizione, categoria e wallet.
- [ ] Il pulsante "Modifica" nella tabella apre il movimento in modalità modifica.
- [ ] Il pulsante "Elimina" rimuove il movimento dopo conferma.
