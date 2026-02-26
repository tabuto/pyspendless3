# Task 7.1: Miglioramento Gestione Wallet

Questo task estende la gestione dei wallet descritta in `SPECS.md`, introducendo un campo di ordinamento persistente che influenza sia la pagina di configurazione sia i flussi di inserimento movimenti.

## Obiettivi
1. Aggiungere un campo di ordinamento ai wallet per account.
2. Consentire la modifica dell'ordinamento dalla pagina Settings dedicata ai wallet.
3. Visualizzare i wallet in tutte le UI (in particolare nella creazione/modifica movimento) seguendo l'ordinamento configurato.

## Modifiche al Database
- Aggiungere una colonna `order_index` (INTEGER, default 0) alla tabella `wallet`.
- Lo script SQL deve essere posizionato nella cartella `sql/sqllite/NEXT_RELEASE`, ad esempio `sql/sqllite/NEXT_RELEASE/alter_wallet_add_order.sql`.

```sql
ALTER TABLE wallet ADD COLUMN order_index INTEGER DEFAULT 0;
```

Aggiornare `models.py` e `repository.py` per esporre il nuovo campo, mantenendo la retrocompatibilità prevista in `SPECS.md`.

## Specifiche Funzionali

### 1. Settings > Wallets
- **Elenco ordinato**: caricare i wallet del corrente `account_id` ordinati per `order_index` ascendente (fallback alfabetico in caso di parità).
- **Editing ordine**: per ogni wallet, mostrare un campo numerico modificabile. Accettare solo interi positivi (>= 0). Aggiornare il DB tramite chiamata API dedicata (`PUT /wallets/:id` o endpoint specifico) riutilizzando la logica di autorizzazione esistente.
- **Validazione**: bloccare valori negativi e gestire conflitti (es. due wallet con lo stesso ordine) lasciando al frontend la responsabilità di suggerire valori coerenti; il backend deve comunque accettare duplicati senza crash, applicando successivamente anche un ordinamento alfabetico.

### 2. Creazione/Modifica Movimento
- Il componente (form) che permette di selezionare il wallet deve richiedere i dati ordinati per `order_index`. In caso di cache lato frontend, prevedere un refresh dopo modifiche ai wallet.
- L'API `GET /accounts/:id/wallets` deve supportare l'ordinamento lato server (`ORDER BY order_index ASC, name ASC`).
- In mancanza del nuovo campo sui record legacy (valore NULL), il backend deve trattare `NULL` come `0` per non rompere la retrocompatibilità.

### 3. Repository e Servizi
- Aggiornare le funzioni esistenti (`get_wallets_for_account`, `create_wallet`, `update_wallet`) per leggere/scrivere `order_index`.
- Quando si crea un nuovo wallet senza ordine esplicito, assegnare automaticamente `order_index = MAX(order_index)+1` per l'account corrente (o 0 se non esistono altri wallet).
- Garantire che gli aggiornamenti di ordinamento siano transazionali (`session.begin()` / `commit()` / `rollback()`), seguendo le convenzioni già adottate in `repository.py`.

## Note Tecniche
- Tutte le API coinvolte devono continuare a restituire/accettare dati in JSON via REST come specificato nel documento principale.
- Gli aggiornamenti lato UI devono integrare i componenti AdminLTE già in uso, mantenendo coerenza con la sidebar e il pattern di flash messages di Flask.
- Non sono richieste modifiche al modello `Movement` oltre all'ordinamento della lista di wallet mostrata nel form.
