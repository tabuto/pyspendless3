# Come Usare il Sistema di Inviti - Guida Rapida

## Per l'Utente che Invita

### 1. Generare un Link di Invito

1. Accedi all'applicazione PySpendless
2. Vai su **Settings → Gestione Gruppo**
3. Clicca sul pulsante **"Invita Utente"**
4. Nel modal che si apre:
   - Inserisci l'email Gmail della persona che vuoi invitare
   - Clicca su **"Genera Link"**
5. Il sistema genera un link unico valido per 7 giorni
6. Puoi:
   - **Copiare** il link negli appunti
   - **Condividere** il link usando le funzioni native del tuo dispositivo (WhatsApp, Email, etc.)

### Esempio di Link Generato
```
http://localhost:5000/generate-link/callback?token=1c0e6095-f446-4460-b1d6-3d186542d402
```

## Per l'Utente Invitato

### Scenario 1: Hai già un account PySpendless

1. Clicca sul link ricevuto
2. Se sei già loggato, verrai automaticamente aggiunto all'account
3. Riceverai un messaggio di conferma
4. Verrai reindirizzato alla home

### Scenario 2: Non hai ancora un account PySpendless

1. Clicca sul link ricevuto
2. Verrai reindirizzato al login Google
3. Effettua il login con la tua email Gmail
4. Dopo il login, verrai automaticamente aggiunto all'account
5. Riceverai un messaggio di benvenuto e conferma
6. Verrai reindirizzato alla home

## Note Importanti

- ⏰ **Validità**: Il link di invito è valido per **7 giorni**
- 📧 **Email Gmail**: Solo email Gmail (`@gmail.com`) sono accettate
- 🔒 **Whitelist**: L'email deve essere nella whitelist del sistema per poter accedere
- ✅ **Monouso**: Ogni link può essere usato una sola volta
- 🔐 **Sicurezza**: Il token è un UUID univoco e viene invalidato dopo l'uso

## API - Per Sviluppatori

### Generare un Link di Invito

**Endpoint**: `POST /api/generate-link`

**Headers**:
```
Content-Type: application/json
```

**Body**:
```json
{
  "email": "invitato@gmail.com"
}
```

**Response** (Success):
```json
{
  "link": "http://localhost:5000/generate-link/callback?token=UUID"
}
```

**Response** (Error):
```json
{
  "error": "Solo email Gmail sono accettate"
}
```

### Accettare un Invito

**Endpoint**: `GET /generate-link/callback?token=UUID`

**Parametri**:
- `token` (required): UUID del token di invito

**Comportamento**:
- Se l'utente è loggato → aggiunge l'utente all'account
- Se l'utente NON è loggato → redirect a login OAuth, poi aggiunge all'account

## Variabili d'Ambiente

Assicurati di aver configurato nel file `.env`:

```bash
BASE_URL=http://localhost:5000  # URL base dell'applicazione
```

In produzione, imposta `BASE_URL` al dominio effettivo:
```bash
BASE_URL=https://pyspendless.example.com
```

## Troubleshooting

### "Link di invito non valido o scaduto"
- Il link ha più di 7 giorni
- Il link è già stato utilizzato
- Il token non esiste nel database

**Soluzione**: Genera un nuovo link di invito

### "Solo email Gmail sono accettate"
- Stai provando a invitare un'email non Gmail

**Soluzione**: Utilizza un indirizzo email @gmail.com

### "Accesso non autorizzato. La tua email non è nella whitelist."
- L'email dell'utente invitato non è nella whitelist del sistema

**Soluzione**: Chiedi all'amministratore di sistema di aggiungere l'email alla whitelist
