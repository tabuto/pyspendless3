# Task 1.3 — Implementazione logica di salvataggio Utente e Account post-login

## Obiettivo
Implementare la logica di backend per gestire il primo accesso di un utente tramite Google OAuth. Se l'utente non esiste nel sistema, deve essere creato un nuovo **User** associato a un nuovo **Account**, e popolate le **Category** di default.

## Prerequisiti
- Il database SQLite deve essere inizializzato (vedi Task 1.2).
- La configurazione del DB e le credenziali Google sono nel file `.env` e caricate in `conf.py`.
- I modelli SQLAlchemy (`models.py`) devono essere definiti.

## Specifiche Funzionali
La logica deve essere eseguita nella callback della rotta `/auth/callback` (o in una funzione di servizio chiamata da essa, es. in `repository.py` o `services.py`).

### Flusso di creazione
1. **Ricezione Dati OAuth**: Ottenere `email`, `google_id`, `name` dal provider Google.
2. **Controllo Whitelist**:
   - Verificare che l'email sia presente nella tabella `emailWhitelist` (o nella configurazione `WHITELIST_EMAILS` se gestita staticamente).
   - **Se non presente**: Interrompere il processo, non creare nulla e restituire errore all'utente ("Accesso non autorizzato").
3. **Verifica Esistenza Utente**:
   - Cercare nella tabella `User` se esiste già un record con quel `google_id` (o `email`).
   - **Se esiste**: Aggiornare eventuali campi (es. ultimo accesso) e loggare l'utente.
4. **Creazione Nuovo Utente (se non esiste)**:
   - **Creazione Account**: 
     - Creare una nuova istanza di `Account` (es. `name="Account di {User Name}"`).
     - Salvare e ottenere l'`id` generato.
   - **Creazione User**:
     - Creare l'istanza `User` collegata all'`account_id` appena creato.
     - Ruolo: definire un ruolo di default (es. "owner").
   - **Creazione Categorie**:
     - Leggere la tabella `CategoryTemplate`.
     - Per ogni template, creare una nuova riga nella tabella `Category` associata al nuovo `Account`.
     - Copiare `name`, `type` e altre proprietà dal template.
   - **Commit**: Eseguire il commit della transazione per salvare Account, User e Categorie atomicamente.

## Dettagli Tecnici

### File interessati
- **`app.py`**: Gestione route `/auth/callback`.
- **`repository.py`** (o `auth_service.py`): Implementare la funzione `create_user_from_oauth(user_info)`.
- **`models.py`**: Utilizzo delle classi `User`, `Account`, `Category`, `CategoryTemplate`, `EmailWhitelist`.

### Query e Logica (Pseudo-code)

```python
def create_user_from_oauth(user_info):
    email = user_info['email']
    
    # 1. Whitelist Check
    whitelist_entry = db.session.query(EmailWhitelist).filter_by(email=email).first()
    if not whitelist_entry:
        raise UnauthorizedError("Email non in whitelist")

    # 2. Check User Existence
    existing_user = db.session.query(User).filter_by(google_id=user_info['sub']).first()
    if existing_user:
        return existing_user

    # 3. Create Account
    new_account = Account(name=f"Account di {user_info['name']}")
    db.session.add(new_account)
    db.session.flush() # Per avere account.id

    # 4. Create User
    new_user = User(
        public_uid=str(uuid.uuid4()),  # Generazione Public UID
        google_id=user_info['sub'],
        email=email,
        name=user_info['name'],
        account_id=new_account.id,
        role='owner'
    )
    db.session.add(new_user)

    # 5. Copy Categories from Template
    templates = db.session.query(CategoryTemplate).all()
    for t in templates:
        new_cat = Category(
            name=t.name,
            type=t.type,
            account_id=new_account.id,
            template_id=t.id
        )
        db.session.add(new_cat)

    db.session.commit()
    return new_user
```

## Setup di prova
- Assicurarsi di avere almeno una email nella `emailWhitelist` per testare il successo.
- Provare con una email non in whitelist per testare il rifiuto.
