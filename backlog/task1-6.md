# Task 1.6 - Implementazione Settings Applicativi

## Obiettivo
Realizzare la sezione di configurazione e gestione dell'applicazione accessibile agli utenti loggati. La sezione deve permettere la gestione di Categorie, Wallet, Gruppi e funzionalità di Import/Export.

## Requisiti Generali
- **Template**: Tutte le pagine devono estendere `base.html` per includere la sidebar di navigazione (come da specifiche AdminLTE).
- **Comunicazione**: Tutte le operazioni di scrittura (creazione, modifica, cancellazione) e lettura dati per le tabelle devono avvenire tramite chiamate **AJAX** (fetch o axios) verso le API REST.
- **Feedback Utente**: Utilizzare i Toast o Alert di AdminLTE/Bootstrap per notificare l'esito delle operazioni (successo/errore).
- **Layout**: Utilizzare le card e i componenti di AdminLTE per organizzare i contenuti.

## Pagine da Implementare

### 1. Gestione Categorie (`templates/ps-setting-categories.html`)
**L'utente deve poter gestire le categorie associate al proprio Account.**

- **Route Backend**:
  - `GET /settings/categories` (renderizza la pagina HTML).
  - API: Assicurarsi che esistano gli endpoint CRUD per le categorie (`GET`, `POST`, `PUT`, `DELETE` su `/api/accounts/<id>/categories` o simili).

- **Funzionalità UI**:
  - **Lista Categorie**: Visualizzare una tabella con le categorie esistenti (Nome, Tipo: Entrata/Uscita/Trasferimento).
  - **Aggiungi Categoria**: Un pulsante o form in una modale per creare una nuova categoria. Campo obbligatorio: Nome, Tipo.
  - **Modifica**: Possibilità di rinominare una categoria esistente.
  - **Elimina**: Possibilità di eliminare una categoria (con conferma). *Gestire il caso in cui la categoria sia già usata in dei movimenti (es. impedire cancellazione o soft-delete).*

### 2. Gestione Wallet (`templates/ps-setting-wallet.html`)
**L'utente deve poter creare e rinominare i propri conti/wallet e visualizzarne il saldo.**

- **Route Backend**:
  - `GET /settings/wallets` (renderizza la pagina HTML).
  - API: Endpoint CRUD per i wallet.

- **Funzionalità UI**:
  - **Lista Wallet**: Visualizzare card o tabella con i wallet attivi.
  - **Saldo**: Per ogni wallet, visualizzare il saldo attuale (calcolato sommando le entrate e sottraendo le uscite dai movimenti associati).
  - **Aggiungi Wallet**: Form/Modale per creare un nuovo wallet (Nome, Valuta).
  - **Rinomina**: Possibilità di cambiare il nome del wallet.
  - **Elimina/Archivia**: (Opzionale nel task, ma previsto dalle best practice) permettere di disattivare un wallet.

### 3. Gestione Gruppo e Utenti (`templates/ps-setting-group.html`)
**L'utente owner deve poter gestire i membri del proprio gruppo di spesa.**

- **Route Backend**:
  - `GET /settings/group` (renderizza la pagina HTML).
  - API: Endpoint per invitare utenti (`POST /groups/:id/invite`), rimuovere membri, listare membri.

- **Funzionalità UI**:
  - **Lista Membri**: Visualizzare gli utenti che hanno accesso all'Account condiviso (Nome, Email, Ruolo/Stato).
  - **Invita Utente**: Form per inserire l'email di un utente da invitare. L'invio genera una entry in `GroupMembership` (vedi SPECS).
  - **Rimuovi Utente**: Pulsante per revocare l'accesso ad un utente (solo per Owner).
  - **Visualizza Invitati in attesa**: Mostrare gli inviti inviati ma non ancora accettati.

### 4. Import / Export (`templates/ps-setting-import-export.html`)
**Strumenti per il backup e il ripristino dei dati o l'importazione massiva.**

- **Route Backend**:
  - `GET /settings/import-export` (renderizza la pagina HTML).
  - `POST /api/export/movements` (genera e scarica CSV).
  - `POST /api/import/movements` (accetta file CSV e processa l'inserimento).

- **Funzionalità UI**:
  - **Export**:
    - Pulsante "Esporta Movimenti in CSV".
    - Permettere eventualmente di filtrare per data (opzionale).
  - **Import**:
    - Area di **Drag & Drop** (o pulsante "Sfoglia") per caricare un file `.csv`.
    - Al caricamento del file, inviare via AJAX il file al backend.
    - Mostrare una progress bar o spinner durante l'elaborazione.
    - Mostrare un report finale: "X movimenti importati, Y errori".
    - **Formato CSV atteso**: Specificare chiaramente nella UI l'header richiesto (Data, Categoria, Wallet, Importo, Spesa/Entrata, Note).

## Implementazione Tecnica
1.  **Backend (`app.py` / `settings_routes.py`)**:
    - Creare le route che servono i template HTML (es. `@app.route('/settings/categories')`).
    - Verificare che le API REST JSON per Categorie, Wallet, Gruppi e Movimenti (per import/export) siano complete e funzionanti come definito in `repository.py` e `SPECS.md`.
    - Aggiungere logica di parsing CSV per l'importazione e generazione CSV per l'esportazione.

2.  **Frontend**:
    - Creare i 4 file HTML nella cartella `templates/`.
    - Collegare le pagine nel menu laterale (Sidebar) di `base.html` sotto una voce "Impostazioni" o come voci singole se preferito.
    - Scrivere il codice JavaScript (può essere inline nel blocco `{% block scripts %}` o in file JS dedicati in `static/js/`) per gestire le chiamate AJAX e la manipolazione del DOM.

## Note
- **Gestione Ruoli**: Aggiungere alla tabella `User` l'attributo `admin` (integer/boolean). All'atto della creazione di un nuovo Account, l'utente creatore deve avere `admin=1`.
- **Logica di Importazione (Anti-duplicati)**: Durante l'importazione dei movimenti da CSV, l'ID del movimento deve essere generato come hash (es. SHA256 o MD5) della concatenazione di: `data + importo + categoria + wallet + nota`. Se un movimento con questo ID esiste già, l'inserimento deve essere ignorato per evitare duplicati.
- Assicurarsi che solo gli utenti autorizzati (es. appartenenti all'account) possano eseguire modifiche.
- Per l'importazione, gestire i duplicati (vedi sopra) o errori di validazione (es. categoria non esistente -> creare o segnare errore).
