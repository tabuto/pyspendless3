# PySpendless - Gestione Spese Personali

Applicazione web per la gestione di spese personali e condivise con autenticazione Google OAuth.

## Setup Iniziale

### 1. Creazione e attivazione ambiente virtuale

```bash
python3 -m venv .venv
source .venv/bin/activate  # Su macOS/Linux
# oppure
.venv\Scripts\activate     # Su Windows
```

### 2. Installazione dipendenze

```bash
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
```

### 3. Configurazione variabili d'ambiente

Copia il file `.env.example` in `.env` e compila i valori:

```bash
cp .env.example .env
```

Modifica `.env` con i tuoi valori:
- `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`: Credenziali OAuth Google
- `DATABASE_URL`: Percorso al database SQLite
- `SECRET_KEY`: Chiave segreta per Flask
- `WHITELIST_EMAILS`: Email autorizzate (separate da virgola)

### 4. Inizializzazione del database

Il database deve essere inizializzato con gli script SQL forniti:

```bash
# Assicurati di essere nella root del progetto
cd /Users/fradidio/Sviluppo/pyspendless3

# Crea il database con tutte le tabelle
sqlite3 data/pyspendless.db < sql/sqllite/create_all.sql

# Inserisci le categorie di default
sqlite3 data/pyspendless.db < sql/sqllite/insert_categorytemplate.sql

# Aggiungi le email alla whitelist (esempio manuale)
sqlite3 data/pyspendless.db
> INSERT INTO emailWhitelist (email, added_at) VALUES ('tua-email@gmail.com', datetime('now'));
> .quit
```

## Avvio dell'applicazione Flask

Assicurati di aver attivato l'ambiente virtuale e installato le dipendenze.

### Metodo 1: Python module

```bash
.venv/bin/python -m pyspendless.app
```

### Metodo 2: Flask CLI

```bash
export FLASK_APP=pyspendless.app
export FLASK_ENV=development
export OAUTHLIB_INSECURE_TRANSPORT=1  # Solo per sviluppo locale
.venv/bin/flask run
```

L'applicazione sarà disponibile su http://localhost:5000/

## Funzionalità implementate (Task 1.3)

### Autenticazione OAuth Google
- Login tramite Google OAuth 2.0
- Controllo whitelist email
- Creazione automatica Account e User al primo accesso
- Creazione automatica categorie di default dal template

### Struttura del codice

- **`models.py`**: Definizione dei modelli SQLAlchemy (Account, User, Category, etc.)
- **`repository.py`**: Logica di accesso ai dati e funzioni CRUD
- **`conf.py`**: Configurazioni, costanti e gestione database
- **`app.py`**: Route Flask e gestione HTTP

### Flusso di login

1. L'utente clicca su "Login with Google"
2. Viene reindirizzato a Google per l'autenticazione
3. Al callback, il sistema verifica se l'email è in whitelist
4. Se autorizzato e nuovo:
   - Crea un nuovo Account
   - Crea un nuovo User collegato all'Account
   - Copia tutte le categorie dai template
5. Se utente già esistente, lo autentica direttamente
6. Salva i dati nella sessione e reindirizza alla home

## Note per lo sviluppo

### Ambiente locale
In locale è necessario impostare:
```bash
export OAUTHLIB_INSECURE_TRANSPORT=1
```

### Produzione (PythonAnywhere)
Per il deploy su PythonAnywhere, aggiornare `.env_pa` con:
- `OAUTH_REDIRECT_URI`: L'URL pubblico del callback
- `DATABASE_URL`: Il percorso assoluto al database su PythonAnywhere