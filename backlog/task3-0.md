# Task 3.0: Implementazione processo di invito a collaborare

## Obiettivo
Permettere agli utenti di invitare altri utenti (account Google/Gmail) a collaborare sul proprio account PySpendless tramite un link di invito.

## Database
Creare una nuova tabella `token` per gestire i token di invito.

### Struttura Tabella `token`
- `uuid`: UUID (Primary Key)
- `type`: String (es. "SHARE")
- `create_date`: DateTime
- `expire_date`: DateTime
- `status`: String (es. "PENDING", "USED", "EXPIRED")
- `payload`: JSON/Text (contiene email invitata e account_id)

## Flusso Funzionale

### 1. Generazione Invito (UI & API)
- **UI**: Nella sezione di gestione del gruppo (`ps-setting-group.html`), l'utente inserisce l'email (GMAIL) della persona da invitare.
- **API**: `POST /generate-link`
    - Input: email da invitare.
    - Logica:
        1. Genera un nuovo UUID.
        2. Imposta `type` = "SHARE".
        3. Imposta `expire_date` a 7 giorni da oggi.
        4. Imposta `payload` con `{email: "email@gmail.com", account_id: current_user_account_id}`.
        5. Salva il record in tabella `token`.
    - Output: Restituisce l'URL di callback generation: `$$BASE_URL$$/generate-link/callback?token=$$UUID$$` (Nota: `$$BASE_URL$$` deve essere letto dalle variabili d'ambiente).
- **UI**: Mostra il link generato all'utente con un pulsante "Condividi" che invoca le funzioni di condivisione native del dispositivo (Web Share API) o permette di copiare il link.

### 2. Gestione Callback Invito (API)
- **Endpoint**: `GET /generate-link/callback`
- **Parametri**: `token` (UUID)

#### Scenario A: Utente Loggato
1. Verifica che il `token` sia valido (esiste, status="PENDING", non scaduto).
2. Legge il `payload` (email invitata, account_id target).
3. (Opzionale/Sicurezza) Verifica che l'email dell'utente loggato corrisponda all'email nel payload (o gestisce l'associazione se l'invito è generico, ma specifica dice "email GMAIL" quindi è specifico).
4. Aggiunge l'utente all'Account (tabella di associazione User-Account o logica GroupMembership esistente).
5. Invalida il token (status="USED").
6. Redirige alla Home o pagina di successo.

#### Scenario B: Utente NON Loggato
1. Verifica validità del token per evitare redirect inutili (opzionale ma consigliato).
2. Invia redirect all'OAuth di Google (`/auth/login` o custom flow).
3. **Importante**: Per mantenere il contesto del token dopo il login Google:
    - Usare il parametro `state` dell'OAuth per passare il token, OPPURE
    - Se possibile, impostare la `redirect_uri` direttamente a `.../generate-link/callback?token=$$UUID$$` (Attenzione: Google richiede URI esatte registrate, quindi l'approccio `state` è preferibile o salvare il token in sessione pre-redirect). *Nota del task: Il requisito chiede redirect URI con token, verificare fattibilità con Google Console, altrimenti usare `state` o sessione.*

## Note Tecniche
- La tabella `token` deve essere definita in SQL (`sql/sqllite/create_token.sql`).
- Aggiornare `models.py` e `repository.py` per gestire la nuova tabella.
- Implementare la logica di business in `app.py` o service dedicato.
- Gestire casistiche di errore (token scaduto, token non valido, utente già nel gruppo).
