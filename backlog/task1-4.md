# Task 1.4: Inserimento Movimento Spesa

Questo task riguarda l'implementazione della funzionalità di inserimento di un nuovo movimento (spesa/entrata) utilizzando il form in `ps-add-mov.html`, con invio dati via AJAX/JSON.

## Obiettivi

1.  **Backend (API)**
    *   Implementare l'endpoint `POST /api/movements` (o `/accounts/:id/movements` come da SPECS) in `app.py` per ricevere i dati del movimento in formato JSON.
    *   L'API deve validare i dati, convertire i tipi (date, decimali) e salvare il movimento nel database usando `MovementRepository`.
    *   Assicurarsi che l'API gestisca correttamente i campi: `move_date`, `category_id`, `wallet_id`, `income`, `expense`, `note`, `user_id`.
    *   Calcolare campi derivati come `move_year` e `move_month` dalla data.
    *   Garantire la retrocompatibilità popolando anche i campi stringa legacy (`category`, `wallet`, `user`) con i nomi/codici corrispondenti.
    *   Implementare (o confermare esistenza di) un endpoint `GET /api/categories` (o `/accounts/:id/categories`) per restituire la lista delle categorie in formato JSON. Questo serve per "gestire le categorie del movimento" lato client o per future implementazioni dinamiche, anche se il template attuale le carica server-side. Assicurarsi che restituisca id e nome.

2.  **Frontend (`ps-add-mov.html`)**
    *   Modificare il form esistente per non usare il submit standard HTML.
    *   Aggiungere JavaScript per intercettare il submit del form:
        *   Raccogliere i dati dal form.
        *   Creare un payload JSON.
        *   Inviare una richiesta `POST` asincrona (fetch) all'API di creazione movimento.
    *   Implementare la logica di **successo**:
        *   Mostrare un messaggio di "Salvataggio avvenuto con successo" all'interno della pagina (usando un `div` alert bootstrap, non un popup/alert browser).
        *   Resettare il form (svuotare i campi) per permettere un nuovo inserimento immediato.
    *   Implementare la gestione degli **errori**:
        *   Mostrare un messaggio di errore se l'API fallisce.
    *   Impostare il campo data (`move_date`) con la data odierna (`today()`) come valore predefinito al caricamento della pagina.

## Dettagli Tecnici

### API Payload (Esempio)
```json
{
  "move_date": "2023-10-27",
  "category_id": 1,
  "wallet_id": 2,
  "amount": 25.50,
  "type": "expense",  // o dedurre da income/expense fields
  "note": "Spesa esempio",
  "user_id": 123
}
```
*Nota: Adattare il payload ai campi del form esistente (income/expense separati o unici).*

### File da modificare
- `pyspendless/app.py`: Aggiunta endpoint API.
- `pyspendless/templates/ps-add-mov.html`: Aggiunta script JS e container per messaggi.
- `pyspendless/repository.py`: Verifica/Aggiunta metodi necessari (es. `create_movement` già presente, assicurarsi che gestisca tutto).

### Note per l'implementazione
- Utilizzare `jsonify` di Flask per le risposte API.
- Gestire correttamente la sessione utente per associare il movimento all'account/utente corretto.
- Per il datepicker: l'input type="date" standard HTML5 va bene, impostare `value` via JS a `new Date().toISOString().split('T')[0]`.
