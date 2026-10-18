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

## Il CSS va compilato

La presentazione gira su **Tailwind CSS v4** (task19-0). Il foglio servito
alle pagine non si scrive a mano: si compila.

```
static/css/ps-tailwind.src.css   sorgente — token, @theme, @layer components
            ↓  ./tools/build-css.sh
static/css/ps-tailwind.css       output — VERSIONATO, è quello che il browser scarica
```

### Quando ricompilare

Ogni volta che cambia una `class="..."` in un template o una regola nel
sorgente. Tailwind genera **solo** le utility che trova scritte nei file: una
classe nuova in un template non esiste nel CSS finché non si ricompila.

```bash
./tools/build-css.sh
```

### Perché l'output è versionato

Su PythonAnywhere non c'è Node e **non esiste una fase di build**: il deploy è
`git pull` + Reload. Quindi il compilato sta in git, esattamente come ci stava
`adminlte.css` prima del restyling. Il binario che lo produce è
`tools/tailwindcss` — la CLI standalone, nessun `package.json`, nessuna
dipendenza npm.

### Se ci si dimentica

In produzione va il CSS vecchio: le classi nuove restano senza stile, ma
**l'app funziona**. È un fallimento degradato, non una pagina rotta.

Il controllo veloce: dopo una build, `git status` deve restare **pulito**. Se
la build modifica `ps-tailwind.css`, il commit precedente era incompleto.

Lo script fallisce apposta se l'output scende sotto i 5 KB (segno che la
compilazione è andata storta) o se `.gitignore` sta escludendo il file.

### Tema light/dark

`static/js/ps-theme.js` gestisce tre stati — `light`, `dark`, `system` —
persistiti in `localStorage['ps_theme']`. Nel `<head>` di `ps-base.html` c'è
uno snippet anti-FOUC che applica la classe `dark` **prima** del primo paint:
senza, la pagina lampeggia in chiaro e poi passa a scuro. La fonte di verità
di quello snippet è `PS_FOUC_SNIPPET` in `ps-theme.js`, da cui è copiato.

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