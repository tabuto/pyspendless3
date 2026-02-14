# Task 1-1: Configurare la pagina di login (Google OAuth) secondo SPECS.md

## Obiettivo
Implementare la pagina di login e il relativo flusso di autenticazione tramite Google OAuth2, seguendo le specifiche di `SPECS.md`.

## Istruzioni

1. **Configurazione ambiente**
   - Assicurati che `.env` contenga le variabili:
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`
     - `OAUTH_REDIRECT_URI`
     - `WHITELIST_EMAILS` (opzionale, se non usi la tabella `emailWhitelist`)
   - Verifica che `requirements.txt` includa `Flask`, `Authlib`, `python-dotenv`.

2. **Aggiornamento configurazione**
   - In `conf.py`, aggiungi le costanti e le funzioni per caricare le variabili d'ambiente e restituire i parametri OAuth.
   - Implementa la funzione `load_env()` per caricare `.env`.

3. **Definizione delle rotte di autenticazione** (`app.py`)
   - `GET /auth/login`: reindirizza a Google OAuth.
   - `GET /auth/callback`: gestisce il callback, verifica la whitelist, crea/aggiorna User e Account.
   - `POST /auth/logout`: esegue il logout.

4. **Whitelist**
   - Implementa la verifica che l'email ottenuta da Google sia presente nella whitelist (`emailWhitelist` in DB o lista in `conf.py`).
   - Se l'email non è autorizzata, mostra un messaggio di errore.

5. **Creazione/aggiornamento utente**
   - Se l'utente è autorizzato, crea o aggiorna la tabella `User` e associa l'utente a un `Account`.
   - Se è la prima registrazione, copia le categorie di default da `CategoryTemplate`.

6. **Frontend (pagina di login)**
   - Crea un template `login.html` che estende `base.html`.
   - Inserisci un pulsante "Login with Google" che punta a `/auth/login`.
   - Utilizza Bootstrap per lo stile.
   - Integra il sistema di messaggistica Flask (`flash`) per mostrare errori/successi.

7. **Sicurezza**
   - Proteggi i cookie di sessione (Secure, HttpOnly).
   - Usa HTTPS in produzione.

8. **Test**
   - Verifica che solo le email whitelisted possano accedere.
   - Testa il flusso di login/logout e la creazione utente/account.

## Riferimenti
- Vedi `SPECS.md` sezioni: "Flusso di autenticazione e whitelist", "Rotte principali (API)", "UI e Template Bootstrap".
- Esempi di codice e dettagli aggiuntivi sono in `SPECS.md`.
