# Specifica Funzionale: Gestione Primo Login (Onboarding)

Questo documento descrive il flusso di onboarding semplificato per un utente che effettua il login per la prima volta.

## Obiettivo

Guidare un nuovo utente attraverso un unico passaggio di configurazione (creazione account e wallet) per garantire che il suo ambiente sia pronto all'uso dopo il primo accesso.

## Flusso Generale

1.  **Login e Verifica**: L'utente esegue il login tramite Google. Il sistema verifica se l'utente esiste già nel database.
2.  **Utente Nuovo**: Se l'utente non esiste, viene avviato il flusso di onboarding.
3.  **Onboarding Unificato**: L'utente viene reindirizzato a una pagina unica dove inserisce le informazioni essenziali: Nome Account e Nome Wallet.
4.  **Creazione Automatica**: Al submit, il sistema crea Account, Utente, Wallet e le categorie di default.
5.  **Redirect Finale**: L'utente viene reindirizzato alla dashboard principale (`/home`).

---

## Modifiche e Nuove Pagine

### 1. Modifica a `GET /auth/callback` (in `app.py`)

La logica di questo endpoint deve essere estesa:

- **Dopo l'autenticazione Google**: Ottenere l'email dell'utente.
- **Verifica Esistenza Utente**: Controllare tramite `repository.get_user_by_email(email)` se l'utente è già presente nella tabella `User`.
- **Se l'utente esiste**:
    - `redirect('/home')`.
- **Se l'utente non esiste**:
    - `redirect('/onboarding')` per avviare il processo di creazione.

### 2. Pagina Onboarding

#### Pagina HTML: `templates/ps-onboarding.html`

- **Scopo**: Raccogliere in un'unica schermata le informazioni necessarie per inizializzare l'utenza.
- **Contenuto**:
    - Un titolo, es: "Benvenuto! Configura il tuo spazio".
    - Un form (`method="POST"`, `action="/onboarding"`) che contiene:
        - **Nome Account** (es. "Famiglia Rossi", "Spese Personali"). `name="account_name"`, obbligatorio.
        - **Nome Wallet** (es. "Portafoglio Principale", "Banca X"). `name="wallet_name"`, obbligatorio.
        - Un pulsante di submit, es: **"Inizia"**.

#### API: Nuove rotte in `app.py`

- **`GET /onboarding`**
    - **Logica**: Renderizza il template `ps-onboarding.html`.
    - **Accesso**: Richiede che l'utente sia autenticato (sessione Flask con info parziali da Google, ma non ancora nel DB come User).

- **`POST /onboarding`**
    - **Logica**:
        1.  Recupera `account_name` e `wallet_name` dal form.
        2.  Recupera le informazioni dell'utente loggato dalla sessione (email, nome, foto).
        3.  Chiama una nuova funzione del repository: `repository.complete_onboarding(user_info, account_name, wallet_name)`.
        4.  Se l'operazione ha successo, `redirect('/home')`.
    - **Accesso**: Richiede sessione autenticata (Google).

---

## Modifiche al Repository (`repository.py`)

- **`complete_onboarding(user_info, account_name, wallet_name)`**
    - Deve eseguire in una singola transazione:
        1.  **Creare Account**: Inserire un nuovo record in `Account` con `account_name`. Recuperare `account_id`.
        2.  **Creare Utente**: Inserire il record `User` (con i dati da `user_info`) associato all'`account_id`.
        3.  **Creare Wallet**: Inserire un nuovo record in `Wallet` con `wallet_name` associato all'`account_id`.
        4.  **Setup Categorie**:
            - Selezionare tutte le righe da `CategoryTemplate`.
            - Per ogni riga, creare un nuovo record in `Category`, copiando i dati e impostando `account_id`.
