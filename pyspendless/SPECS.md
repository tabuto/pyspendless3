# SPECS

Documento di specifica per la realizzazione di una webApp in Python 3, Flask, SQLAlchemy e SQLite per il salvataggio e la gestione delle spese.

## Obiettivo
Applicazione web per la gestione di spese personali e condivise. Registrazione tramite Google OAuth consentita solo se l'email è presente in una whitelist. Supporto a più account/utenti, wallet e categorie; retrocompatibilità con la tabella MOVEMENTS esistente.

## Requisiti funzionali
- Registrazione/login tramite Google OAuth2.
- Solo email presenti in una whitelist possono completare la registrazione.
- Utente registrato può:
  - creare 1 gruppo (nomeGruppo) e invitare altri utenti a condividerlo;
  - creare, aggiungere e modificare wallet;
  - creare, aggiungere e modificare categorie;
  - creare, aggiungere e modificare movimenti (spese/entrate).
- Relazioni dati:
  - Ad ogni Account sono legati uno o più Users.
  - Ad ogni Account sono legati uno o più Wallets.
  - Ad ogni Wallet sono legati i Movements (spese).
  - Ogni Movement è legato ad un User, una Category e un Wallet.

## Requisiti non funzionali
- DB: SQLite (file locale) con SQLAlchemy ORM.
- Tutte le configurazioni e costanti risiedono in `conf.py`.
- Segreti e variabili d'ambiente in `.env`.
- API RESTful implementate in `app.py`.
- Logica di accesso al DB incapsulata in `repository.py`.
- Compatibilità retrospettiva con tabella MOVEMENTS fornita.

## Struttura del progetto (cartella `pyspendless/`)
- `app.py` — entry point e definizione delle rotte/endpoint (API).
- `models.py` — definizione delle entità SQLAlchemy e mapping alle tabelle.
- `conf.py` — configurazioni, costanti e funzione per ottenere la connessione al DB.
- `repository.py` — funzioni CRUD e astrazione dell'accesso ai dati.
- `.env` — variabili d'ambiente e secret (non committare nel VCS).

## Entities (descrizione e campi principali)
1. Account
   - id: Integer PK
   - name: String
   - created_at: DateTime
   - relazione: has many Users, Wallets, Groups

2. User
   - id: UUID PK
   - google_id: String (unique)
   - email: String (unique)
   - name: String
   - account_id: FK -> Account
   - role: String (e.g., owner, member)
   - created_at

3. Wallet
   - id: Integer PK
   - uuid / code: String unique
   - name: String
   - currency: String (es. EUR)
   - account_id: FK -> Account
   - created_at
   - relazione: has many Movements

4. Category
   - id: Integer PK
   - name: String
   - account_id: FK (categorie per account)
   - type: Enum (expense | income | transfer)
   - template_id: FK -> CategoryTemplate (opzionale)

5. CategoryTemplate
   - id: Integer PK
   - name: String
   - type: Enum (expense | income | transfer)
   - config: JSON (opzionale, per default extra)
   - descrizione: Categorie di default che vengono copiate e associate all'Account subito dopo la registrazione. Gli utenti possono modificare la loro copia delle categorie.

6. emailWhitelist
   - id: Integer PK
   - email: String (unique)
   - added_at: DateTime
   - note: String (opzionale)

7. Movement (retrocompatibilità con tabella esistente)
   - id: varchar(100) PRIMARY KEY
   - move_date: date
   - move_year: int
   - move_month: int
   - category: varchar(100)   -- (store category.name o id come string per retrocompat)
   - wallet: varchar(100)     -- (store wallet.code o id come string per retrocompat)
   - income: decimal(10,2)
   - expense: decimal(10,2)
   - note: varchar(255)
   - user: varchar(100)       -- (store user.email o user.id come string per retrocompat)
   - account_id: int

   Nota: Per nuove implementazioni è consigliato avere anche i campi FK:
   - user_id: Integer FK -> User.id
   - category_id: Integer FK -> Category.id
   - wallet_id: Integer FK -> Wallet.id
   Questi possono essere nullable per mantenere compatibilità con i record esistenti.

6. UserGroup
   - id: Integer PK
   - name: String (nomeGruppo)
   - account_id: FK -> Account
   - owner_user_id: FK -> User.id

7. GroupMembership / Invite
   - id
   - group_id
   - user_id (nullable fino ad accettazione)
   - invite_email
   - invited_by_user_id
   - status: Enum (pending, accepted, declined)
   - token: String (per link di invito)

## Modello relazionale - Riepilogo
- Account(1) — Users(N)
- Account(1) — Wallets(N)
- Wallet(1) — Movements(N)
- User(1) — Movements(N)
- Category(1) — Movements(N)
- UserGroup(1) — GroupMembership(N) — User(N)

## Rotte principali (API) — da implementare in `app.py`
- Auth
  - GET /auth/login -> redirect a Google OAuth
  - GET /auth/callback -> callback Google, verifica whitelist, crea User/Account se necessario
  - POST /auth/logout
- Users
  - GET /users/me
  - GET /users/:id
- Accounts
  - GET /accounts/:id
  - POST /accounts (creazione se applicabile)
- Wallets
  - GET /accounts/:id/wallets
  - POST /accounts/:id/wallets
  - PUT /wallets/:id
  - DELETE /wallets/:id
- Categories
  - GET /accounts/:id/categories
  - POST /accounts/:id/categories
  - PUT /categories/:id
  - DELETE /categories/:id
- Movements
  - GET /accounts/:id/movements[?wallet=...&user=...&year=...&month=...]
  - POST /accounts/:id/movements
  - PUT /movements/:id
  - DELETE /movements/:id
- Groups e Inviti
  - POST /accounts/:id/groups
  - POST /groups/:id/invite  (body: invite_email)
  - GET /groups/:id/members
  - POST /groups/:id/accept?token=...

Authorization: tutte le rotte scrittura devono verificare che l'utente appartenga all'Account o al Group pertinente. Usare decorator per controllo ruoli/permessi.

## Flusso di autenticazione e whitelist
1. L'utente clicca "Login with Google" e viene reindirizzato al provider (Authlib o similare).
2. Al ritorno del callback si ottiene l'email e l'ID Google.
3. Prima di creare l'account locale, verificare che l'email sia nella whitelist.
   - Whitelist gestita in `conf.py` (es. lista di domini o lista esplicita di email) oppure in DB (tabella Whitelist).
4. Se autorizzata: creare o aggiornare User associato ad un Account.
5. Se non autorizzata: negare l'accesso e mostrare messaggio.

## Database e retrocompatibilità
- La tabella MOVEMENTS deve essere preservata con lo schema esatto fornito:

  CREATE TABLE MOVEMENTS(
    id varchar(100) PRIMARY KEY,
    move_date date,
    move_year int,
    move_month int,
    category varchar(100),
    wallet varchar(100),
    income decimal(10,2),
    expense decimal(10,2),
    note varchar(255),
    user varchar(100),
    account_id int
  );

- In `models.py` definire un mapping SQLAlchemy per `Movement` che mappi i campi esistenti e includa colonne addizionali FK (user_id, category_id, wallet_id) con nullable=True per retrocompatibilità.

## conf.py (contenuti e costanti)
- COSTANTI / CONFIGURAZIONI (esempi):
  - DATABASE_URL (sqlite:///...)
  - SECRET_KEY
  - GOOGLE_CLIENT_ID
  - GOOGLE_CLIENT_SECRET
  - OAUTH_REDIRECT_URI
  - WHITELIST_EMAILS or WHITELIST_DOMAINS
  - DEFAULT_CURRENCY
  - PAGINATION_LIMIT

- Funzioni utili:
  - get_db_engine(), get_db_session(), init_db()
  - load_env() (usa python-dotenv per caricare `.env`)

## .env (variabili suggerite)
- FLASK_ENV=development
- DATABASE_URL=sqlite:///./data/pyspendless.db
- SECRET_KEY=changeme
- GOOGLE_CLIENT_ID=...
- GOOGLE_CLIENT_SECRET=...
- OAUTH_REDIRECT_URI=http://localhost:5000/auth/callback
- WHITELIST_EMAILS=alice@example.com,bob@example.com

## repository.py
- Funzioni CRUD per ogni entità (Account, User, Wallet, Category, Movement, UserGroup, Invite)
- Metodi consigliati:
  - create_user_from_oauth(info)
  - get_or_create_account(name)
  - get_wallets_for_account(account_id)
  - create_movement(data)
  - update_movement(id, data)
  - query_movements(filter...)
- Gestire transazioni e rollback per operazioni composte.

## Script per ambiente virtuale (consigliato)
- Creazione e setup (bash):
  1. python3 -m venv .venv
  2. source .venv/bin/activate
  3. pip install -U pip
  4. pip install -r requirements.txt
  5. cp .env.example .env e popolare i valori
  6. flask run (o python -m app)

- Esempio `requirements.txt`:
  - Flask
  - SQLAlchemy
  - Flask-SQLAlchemy
  - Authlib
  - python-dotenv
  - marshmallow (opzionale, per serializzazione)
  - alembic (opzionale, per migrazioni)

## Sicurezza
- Non committare `.env` o secret.
- Proteggere cookie di sessione (Secure, HttpOnly) e usare HTTPS in produzione.
- Limitare dimensione upload e validare input.
- Controllare che le API modifichino solo risorse appartenenti all'Account dell'utente autenticato.

## Test e manutenzione
- Fornire test unitari per repository e integrazione per rotte principali.
- Script di migrazione (alembic) importante per gestire campi aggiuntivi mantenendo compatibilità con la tabella MOVEMENTS.

## Note finali
- Tutte le costanti e regole (es. whitelist) centralizzate in `conf.py`.
- La retrocompatibilità è ottenuta mantenendo la tabella MOVEMENTS e aggiungendo colonne FK nullable; le API devono continuare a leggere/scrivere nei campi previsti.
- Implementare logica di invitation/acceptance per la condivisione dei gruppi con token e-mail.
- Dopo la registrazione, le categorie di default vengono copiate dalla tabella CategoryTemplate e associate all'Account. Ogni utente può modificare la propria copia delle categorie.
- La whitelist delle email è gestita tramite la tabella emailWhitelist, che contiene tutte le email autorizzate alla registrazione.

## UI e Template Bootstrap

- **Template**: Tutte le pagine devono utilizzare il template Bootstrap **AdminLTE 3** (riferimento: [AdminLTE v3 Index3](https://adminlte.io/themes/v3/index3.html)).
- **Libreria Grafici**: I grafici devono essere renderizzati utilizzando **Chart.js**.
- **Comunicazione FE-BE**: Il Front End comunica con il Back End esclusivamente tramite chiamate **API REST** con **AJAX** e formato dati **JSON**.
- **Layout e Navigazione**:
  - **Con Sidebar**: Tutte le pagine relative ad un utente loggato devono includere la barra di navigazione laterale. Queste pagine includono:
    - Home
    - Crea nuovo movimento
    - Visualizza movimenti
    - Settings
    - Profilo
  - **Senza Sidebar**: Le seguenti pagine devono essere prive della barra di navigazione laterale:
    - Login
    - Inizializzazione account
    - Onboarding
    - Errori bloccanti

- Struttura consigliata del progetto per frontend:

  ├── app.py
  ├── repository.py
  ├── conf.py
  ├── models.py
  ├── static/
  │   ├── css/
  │   │   └── adminlte.min.css
  │   └── js/
  │       └── adminlte.min.js
  ├── templates/
  │   ├── base.html              <-- Layout base con sidebar (per utenti loggati)
  │   ├── base_auth.html         <-- Layout base senza sidebar (per login/errori)
  │   └── ...

- Per includere risorse statiche (CSS/JS), usare sempre `url_for`:
  
  `<link rel="stylesheet" href="{{ url_for('static', filename='css/adminlte.min.css') }}">`

- Integrare il sistema di messaggistica di Flask (`flask.flash`) con gli Alerts di Bootstrap per mostrare errori o successi all'utente. Esempio in Jinja2:

  ```html
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  ```

- Le pagine HTML devono estendere `base.html` (o `base_auth.html`) e sfruttare i blocchi Jinja2 per contenuto dinamico.

