# Specifica Funzionale: Gestione Primo Login (Onboarding)

Questo documento descrive il flusso di onboarding per un utente che effettua il login per la prima volta.

## Obiettivo

Guidare un nuovo utente attraverso i passaggi fondamentali di configurazione (creazione account, wallet, categorie) per garantire che il suo ambiente sia pronto all'uso dopo il primo accesso.

## Flusso Generale

1.  **Login e Verifica**: L'utente esegue il login tramite Google. Il sistema verifica se l'utente esiste già nel database.
2.  **Utente Nuovo**: Se l'utente non esiste, viene avviato il flusso di onboarding.
3.  **Creazione Account**: L'utente deve creare un "Account", che è il contenitore principale per utenti, wallet e dati. Può invitare collaboratori.
4.  **Creazione Wallet**: All'account deve essere associato almeno un "Wallet" (portafoglio) per tracciare le spese.
5.  **Setup Categorie**: Le categorie di spesa di default vengono create e associate all'account.
6.  **Redirect Finale**: L'utente viene reindirizzato alla dashboard principale (`/home`).

---

## Modifiche e Nuove Pagine

### 1. Modifica a `GET /auth/callback` (in `app.py`)

La logica di questo endpoint deve essere estesa:

- **Dopo l'autenticazione Google**: Ottenere l'email dell'utente.
- **Verifica Esistenza Utente**: Controllare tramite `repository.get_user_by_email(email)` se l'utente è già presente nella tabella `User`.
- **Se l'utente esiste**:
    - Verificare se ha un account e almeno un wallet. Se non li ha, reindirizzare alle fasi successive dell'onboarding (es. `/onboarding/wallet`).
    - Se l'ambiente è completo, `redirect('/home')`.
- **Se l'utente non esiste**:
    - `redirect('/onboarding/account')` per avviare il processo di creazione.

### 2. Fase 1: Creazione Account

#### Pagina HTML: `templates/ps-manage-account.html`

- **Scopo**: Permettere al nuovo utente di dare un nome al suo account e di invitare collaboratori.
- **Contenuto**:
    - Un titolo, es: "Benvenuto! Crea il tuo account".
    - Un form (`method="POST"`, `action="/onboarding/account"`) che contiene:
        - Input di testo per il **Nome Account** (es. "Famiglia Rossi", "Ufficio", etc.). `name="account_name"`, obbligatorio.
        - Un'area per inserire gli **indirizzi email dei collaboratori** (opzionale). Potrebbe essere un `textarea` dove ogni riga è un'email, o un campo di testo con un pulsante "Aggiungi". `name="collaborator_emails"`.
        - Un pulsante di submit, es: **"Salva Account e Prosegui"**.

#### API: Nuove rotte in `app.py`

- **`GET /onboarding/account`**
    - **Logica**: Renderizza semplicemente il template `ps-manage-account.html`.
    - **Accesso**: Richiede che l'utente sia autenticato (sessione Flask con info parziali da Google).

- **`POST /onboarding/account`**
    - **Logica**:
        1.  Recupera `account_name` e `collaborator_emails` dal form.
        2.  Recupera le informazioni dell'utente loggato dalla sessione.
        3.  Chiama una nuova funzione del repository: `repository.create_account_and_initial_users(account_name, owner_info, collaborator_emails)`.
        4.  Se l'operazione ha successo, `redirect('/onboarding/wallet')`.
    - **Accesso**: Richiede utente autenticato.

### 3. Fase 2: Creazione Wallet

#### Pagina HTML: `templates/ps-manage-wallet.html`

- **Scopo**: Creare il primo wallet se non ne esistono.
- **Contenuto**:
    - Un titolo, es: "Crea il tuo primo portafoglio".
    - Un form (`method="POST"`, `action="/onboarding/wallet"`) per creare un nuovo wallet:
        - Input di testo per il **Nome Wallet**. `name="wallet_name"`, obbligatorio.
        - (Opzionale) Select per la **Valuta** (es. EUR, USD). `name="currency"`. Se non specificato, usa default da `conf.py`.
        - Pulsante di submit: **"Crea Wallet e vai alla Home"**.
    - (Opzionale) Una lista (inizialmente vuota) dei wallet già creati per questo account.

#### API: Nuove rotte in `app.py`

- **`GET /onboarding/wallet`**
    - **Logica**:
        1.  Verifica se l'account dell'utente ha già dei wallet (`repository.get_wallets_for_account(account_id)`).
        2.  Se sì, `redirect('/onboarding/categories')`.
        3.  Se no, renderizza `ps-manage-wallet.html`.
    - **Accesso**: Richiede utente autenticato con un account già creato.

- **`POST /onboarding/wallet`**
    - **Logica**:
        1.  Recupera `wallet_name` e `currency` dal form.
        2.  Chiama `repository.create_wallet(account_id, wallet_name, currency)`.
        3.  `redirect('/onboarding/categories')`.
    - **Accesso**: Richiede utente autenticato con un account.

### 4. Fase 3: Setup Categorie

Questa fase non richiede interazione con l'utente.

#### API: Nuova rotta in `app.py`

- **`GET /onboarding/categories`**
    - **Logica**:
        1.  Verifica se l'account ha già categorie associate (`repository.count_categories_for_account(account_id)`).
        2.  Se non ne ha, chiama una nuova funzione `repository.copy_categories_from_template(account_id)`.
        3.  In ogni caso, `redirect('/home')`.
    - **Accesso**: Richiede utente autenticato con un account.

---

## Modifiche al Repository (`repository.py`)

- **`create_account_and_initial_users(account_name, owner_info, collaborator_emails)`**
    - Deve eseguire in una singola transazione:
        1.  Creare un nuovo record `Account` con `account_name`.
        2.  Creare il record `User` per l'utente *owner* (loggato) e associarlo all'account appena creato.
        3.  Per ogni email in `collaborator_emails`:
            - Creare un record `User` con stato "invitato" o un record in una tabella `Invites`.
            - Associare l'utente/invito all'account.

- **`copy_categories_from_template(account_id)`**
    - **Logica**:
        1.  Seleziona tutte le righe da `CategoryTemplate`.
        2.  Per ogni riga, crea un nuovo record in `Category`, copiando i dati e impostando `account_id` a quello fornito.
        3.  Eseguire tutto in una transazione.
