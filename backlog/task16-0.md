# Task 16.0: Funzione "Esporta" nel pannello di visualizzazione dei movimenti

## Obiettivo
Nuovo pulsante "Esporta" nella finestra di visualizzazione dei movimenti (/movements).
Il pulsante si abilita se sono presenti dei movimenti in tabella.
Al click del pulsante viene generato un csv con tutti i movimenti estratti dalla ricerca.
Il CSV ha il seguente formato:

Formato CSV richiesto:
Data,Categoria,Wallet,Entrata,Spesa,Note
Esempio: 2024-02-15,Spesa,WALLET123,100.00,,Acquisto

Attenzione:
la tabella della pagina /movements è paginata. il CSV deve contenere tutti i movimenti che la query di ricerca seleziona e non solo la pagina visualizzata.

## Specifiche di dettaglio (chiarimenti raccolti)

### 1. Ambito del pulsante: desktop e mobile
La pagina `/movements` mostra i movimenti in due viste distinte ([ps-show-mov.html](../pyspendless/templates/ps-show-mov.html)):
- **Desktop** (`≥md`): tabella con paginazione client-side via DataTables. Il server renderizza già *tutti* i movimenti filtrati in un'unica risposta (variabile `movements` in `movements()`, [app.py:466](../pyspendless/app.py:466)); DataTables pagina solo lato client.
- **Mobile** (`<md`): vista a card con infinite scroll server-side, che carica progressivamente pagine da `/api/movements` ([app.py:549](../pyspendless/app.py:549)) riusando i parametri di filtro correnti nella query string.

Il pulsante "Esporta" deve essere disponibile e funzionante **sia su desktop che su mobile**, e in entrambi i casi deve produrre il CSV completo di tutti i movimenti filtrati (non solo quelli già caricati/visibili in quel momento sullo schermo mobile con lo scroll infinito).

### 2. Sorgente dati per l'export
Va creato/esteso un endpoint dedicato lato server che:
- accetta via query string GET gli stessi parametri di filtro usati dalla route `movements()`: `date_from`, `date_to`, `wallet_id`, `category_type`, `category_id` (multiplo), `keywords`;
- riusa `movement_repo.get_movements_for_account(...)` con quei filtri (stessa logica già usata da `movements()`, [app.py:466-474](../pyspendless/app.py:466));
- restituisce il CSV completo indipendentemente dalla paginazione client-side (desktop) o dallo stato dello scroll infinito (mobile).

Un endpoint GET (non POST) è necessario per permettere il download diretto (link/`window.location`) sia da desktop che da mobile.

Nota: esiste già un endpoint `/api/export/movements` (POST, [app.py:1581](../pyspendless/app.py:1581)) che genera un CSV nello stesso formato ma **esporta tutti i movimenti dell'account ignorando i filtri correnti**. Va esteso per accettare i filtri sopra descritti (oppure sostituito da un nuovo endpoint) — non deve rimanere un export "tutti i movimenti" quando l'utente ha una ricerca attiva.

### 3. Colonna "Wallet" nel CSV
Il valore da scrivere nella colonna `Wallet` è il **codice del wallet** (`wallet.code`), non il nome visualizzato in tabella (`wallet_obj.name`).

Motivo: l'endpoint di import esistente `/api/import/movements` ([app.py:1626](../pyspendless/app.py:1626)) cerca il wallet tramite `wallet.code` (riga [1684](../pyspendless/app.py:1684)), non tramite il nome. Il CSV esportato deve quindi essere direttamente reimportabile con la funzione di import esistente, senza modifiche manuali.

### 4. Formattazione importi
`Entrata` e `Spesa` vanno formattati con **due decimali fissi** (es. `100.00`, non `100.0`). L'implementazione attuale di `/api/export/movements` usa `float(m.income)` che produce una sola cifra decimale quando non necessaria — va corretto usando una formattazione tipo `"%.2f"`.

### 5. Abilitazione del pulsante
Il pulsante è abilitato solo se sono presenti movimenti da esportare:
- su desktop, in base al conteggio righe già renderizzate nella tabella;
- su mobile, in base al conteggio card/movimenti già noto al client (es. `total` restituito da `/api/movements`).

### 6. Dettagli minori (default proposti, da confermare in validazione)
- Nome del file scaricato: `movimenti_YYYYMMDD.csv` (data odierna).
- Endpoint: si propone di **estendere** `/api/export/movements` esistente aggiungendo il supporto ai filtri, piuttosto che crearne uno nuovo separato.
