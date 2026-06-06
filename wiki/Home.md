# PySpendless

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite)
![AdminLTE](https://img.shields.io/badge/UI-AdminLTE_3-green)
![Auth](https://img.shields.io/badge/Auth-Google_OAuth_2.0-red?logo=google)

**PySpendless** è un'applicazione web per la gestione delle spese personali e condivise. Permette di registrare entrate e uscite, organizzarle per wallet e categoria, visualizzare dashboard aggregate e condividere i dati con altri utenti tramite gruppi.

---

## Indice

- [Funzionalità](#funzionalità)
- [Architettura e stack tecnologico](#architettura-e-stack-tecnologico)
- [Struttura del progetto](#struttura-del-progetto)
- [Modello dati](#modello-dati)
- [Prerequisiti](#prerequisiti)
- [Installazione](#installazione)
- [Variabili d'ambiente](#variabili-dambiente)
- [Avvio dell'applicazione](#avvio-dellapplicazione)
- [Rotte principali](#rotte-principali)
- [Deploy su PythonAnywhere](#deploy-su-pythonanywhere)
- [Sicurezza](#sicurezza)
- [Roadmap](#roadmap)

---

## Funzionalità

### Autenticazione
- Login tramite **Google OAuth 2.0**
- Accesso consentito solo alle email presenti in una **whitelist** (gestita via DB o pannello admin)
- Creazione automatica di Account, User e categorie di default al primo accesso
- Sessione persistente (7 giorni)

### Movimenti
- Registrazione di **spese** e **entrate** con data, categoria, wallet e note
- Visualizzazione movimenti con filtri per anno, mese, keyword e categoria
- Modifica e cancellazione di movimenti esistenti
- Layout **responsive**: tabella su desktop, card con scroll infinito su mobile
- **Movimenti ricorrenti**: template predefiniti per operazioni ripetitive
- **Import** da CSV ed **export** con filtri (tutto, anno, anno+mese, categoria, keyword)

### Wallet
- Creazione e gestione di più **portafogli** (es. contante, carta, conto corrente)
- Valuta configurabile per wallet
- Ordinamento personalizzato

### Categorie
- Categorie di tipo **spesa**, **entrata** o **trasferimento**
- Template di default copiati automaticamente al primo accesso
- Ordinamento custom e alfabetico
- Rinomina con aggiornamento automatico dei movimenti collegati

### Dashboard
- **Dashboard mensile**: andamento entrate/uscite del mese corrente con grafici Chart.js
- **Dashboard annuale**: riepilogo anno per anno e trend per categoria

### Gruppi e condivisione
- Creazione di un gruppo e invito di altri utenti tramite **link o email**
- Gestione degli inviti (pending, accepted, declined)
- Visualizzazione dei membri del gruppo

### Pannello Admin
- Gestione della **whitelist email** (aggiunta/rimozione)
- Visualizzazione e cancellazione utenti registrati
- Accessibile solo all'utente amministratore

### Altro
- **Modalità manutenzione** attivabile via variabile d'ambiente (`MAINTENANCE_MODE=1`)
- Pagina di **onboarding** per la configurazione iniziale dell'account

---

## Architettura e stack tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Python 3, Flask |
| ORM / DB | SQLAlchemy + SQLite |
| Autenticazione | Authlib (Google OAuth 2.0) |
| UI framework | AdminLTE 3 (Bootstrap 4) |
| Grafici | Chart.js |
| Tabelle interattive | DataTables |
| Template engine | Jinja2 |
| Comunicazione FE→BE | REST API + AJAX + JSON |
| Migrazioni DB | Alembic |
| Variabili d'ambiente | python-dotenv |
| Hosting consigliato | PythonAnywhere |

### Flusso di comunicazione

```
Browser  ──AJAX/JSON──►  Flask (app.py)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              repository.py        conf.py
                    │
                    ▼
              SQLAlchemy ORM
                    │
                    ▼
              SQLite (file .db)
```

---

## Struttura del progetto

```
pyspendless3/
├── pyspendless/
│   ├── app.py              # Entry point Flask: rotte e gestione HTTP
│   ├── models.py           # Entità SQLAlchemy
│   ├── repository.py       # Logica CRUD e accesso al DB
│   ├── conf.py             # Configurazioni, costanti, sessione DB
│   ├── requirements.txt    # Dipendenze Python
│   ├── .env                # Variabili d'ambiente (NON committare)
│   ├── .env_pa             # Variabili per PythonAnywhere (NON committare)
│   ├── static/
│   │   ├── css/            # AdminLTE e CSS custom
│   │   └── js/             # AdminLTE, Chart.js e JS custom
│   └── templates/
│       ├── ps-base.html         # Layout base (con sidebar, utenti loggati)
│       ├── ps-login.html        # Pagina di login (senza sidebar)
│       ├── ps-home.html         # Home / riepilogo
│       ├── ps-add-mov.html      # Creazione movimento
│       ├── ps-show-mov.html     # Visualizzazione movimenti
│       ├── ps-search-mov.html   # Ricerca movimenti
│       ├── ps-dashboard-monthly.html
│       ├── ps-dashboard-yearly.html
│       ├── ps-recurrent-mov.html
│       ├── ps-setting-*.html    # Pagine impostazioni
│       ├── ps-onboarding.html
│       └── ps-maintenance.html
├── sql/
│   └── sqllite/
│       ├── create_all.sql            # Crea tutte le tabelle
│       ├── insert_categorytemplate.sql  # Inserisce categorie di default
│       └── NEXT_RELEASE/             # Script per la prossima versione
├── migrations/             # Script Alembic
├── data/                   # File database SQLite (NON committare)
└── backlog/                # Documentazione task e specifiche
```

---

## Modello dati

### Entità principali

```
Account ──< User
Account ──< Wallet
Account ──< Category
Account ──< UserGroup ──< GroupMembership >── User
Wallet  ──< Movement
User    ──< Movement
Category──< Movement
CategoryTemplate ──< Category
Account ──< RecurrentMovement
```

### Descrizione entità

| Entità | Descrizione |
|---|---|
| **Account** | Contenitore principale; aggrega utenti, wallet e categorie |
| **User** | Utente registrato via Google OAuth; legato a un Account |
| **Wallet** | Portafoglio (es. contante, carta); ha valuta e ordinamento custom |
| **Category** | Categoria di spesa/entrata/trasferimento, specifica per Account |
| **CategoryTemplate** | Template di categorie predefinite, copiate ad ogni nuovo Account |
| **Movement** | Singola transazione (spesa o entrata); ha FK a User, Category, Wallet |
| **RecurrentMovement** | Template di movimento ricorrente per pre-popolare il form |
| **UserGroup** | Gruppo per condivisione tra utenti dello stesso Account |
| **GroupMembership** | Associazione utente–gruppo con gestione inviti (token, status) |
| **EmailWhitelist** | Email autorizzate all'accesso |
| **Token** | Token one-time per inviti e link di condivisione |

> **Retrocompatibilità:** la tabella `Movement` mantiene i campi legacy (`category`, `wallet`, `user` come stringhe) accanto ai nuovi FK nullable (`category_id`, `wallet_id`, `user_id`).

---

## Prerequisiti

- Python 3.9 o superiore
- `sqlite3` disponibile nel PATH
- Credenziali **Google OAuth 2.0** (Client ID e Client Secret) — [guida Google Cloud Console](https://console.cloud.google.com/)
- (Opzionale) Account PythonAnywhere per il deploy

---

## Installazione

### 1. Clona il repository

```bash
git clone https://github.com/tabuto/pyspendless3.git
cd pyspendless3
```

### 2. Crea e attiva l'ambiente virtuale

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# oppure
.venv\Scripts\activate           # Windows
```

### 3. Installa le dipendenze

```bash
.venv/bin/pip install -U pip
.venv/bin/pip install -r pyspendless/requirements.txt
```

### 4. Configura le variabili d'ambiente

```bash
cp pyspendless/.env.example pyspendless/.env
```

Modifica `pyspendless/.env` con i tuoi valori (vedi [Variabili d'ambiente](#variabili-dambiente)).

### 5. Inizializza il database

```bash
sqlite3 data/pyspendless.db < sql/sqllite/create_all.sql
sqlite3 data/pyspendless.db < sql/sqllite/insert_categorytemplate.sql
```

### 6. Aggiungi la tua email alla whitelist

```bash
sqlite3 data/pyspendless.db \
  "INSERT INTO emailWhitelist (email, added_at) VALUES ('tua-email@gmail.com', datetime('now'));"
```

---

## Variabili d'ambiente

File: `pyspendless/.env`

| Variabile | Obbligatoria | Descrizione | Esempio |
|---|---|---|---|
| `FLASK_ENV` | No | Modalità Flask | `development` |
| `SECRET_KEY` | ✅ | Chiave segreta sessione Flask | `una-stringa-casuale-lunga` |
| `DATABASE_URL` | ✅ | Percorso al file SQLite | `sqlite:///./data/pyspendless.db` |
| `GOOGLE_CLIENT_ID` | ✅ | Client ID Google OAuth | `123...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | ✅ | Client Secret Google OAuth | `GOCSPX-...` |
| `OAUTH_REDIRECT_URI` | ✅ | URL di callback OAuth | `http://localhost:5000/auth/callback` |
| `WHITELIST_EMAILS` | No | Email autorizzate (virgola) | `alice@gmail.com,bob@gmail.com` |
| `BASE_URL` | No | URL base dell'app | `http://localhost:5000` |
| `ADMIN_USER_ID` | No | ID utente amministratore | `1` |
| `MAINTENANCE_MODE` | No | Abilita manutenzione (`1`/`0`) | `0` |

> ⚠️ Non committare mai il file `.env` nel repository.

---

## Avvio dell'applicazione

### Sviluppo locale

```bash
# Necessario per OAuth su HTTP (solo locale)
export OAUTHLIB_INSECURE_TRANSPORT=1

# Metodo 1 — modulo Python
.venv/bin/python -m pyspendless.app

# Metodo 2 — Flask CLI
export FLASK_APP=pyspendless.app
export FLASK_ENV=development
.venv/bin/flask run
```

L'applicazione sarà disponibile su **http://localhost:5000**

### Produzione

```bash
# Senza OAUTHLIB_INSECURE_TRANSPORT (richiede HTTPS)
gunicorn -w 2 "pyspendless.app:app"
```

---

## Rotte principali

### Autenticazione

| Metodo | Rotta | Descrizione |
|---|---|---|
| `GET` | `/login` | Pagina di login |
| `GET` | `/auth/login` | Redirect a Google OAuth |
| `GET` | `/auth/callback` | Callback Google; verifica whitelist e crea utente |
| `POST` | `/auth/logout` | Logout e pulizia sessione |

### Navigazione

| Metodo | Rotta | Descrizione |
|---|---|---|
| `GET` | `/home` | Home page dell'utente |
| `GET` | `/create` | Form creazione movimento |
| `GET` | `/movements` | Visualizzazione movimenti (con filtri) |
| `GET` | `/ps-search-mov` | Ricerca avanzata movimenti |
| `GET` | `/recurrent-movements` | Gestione movimenti ricorrenti |
| `GET` | `/dashboard/monthly` | Dashboard mensile |
| `GET` | `/dashboard/yearly` | Dashboard annuale |
| `GET` | `/onboarding` | Onboarding nuovo utente |

### Impostazioni

| Metodo | Rotta | Descrizione |
|---|---|---|
| `GET` | `/settings/categories` | Gestione categorie |
| `GET` | `/settings/wallets` | Gestione wallet |
| `GET` | `/settings/group` | Gestione gruppo e inviti |
| `GET` | `/settings/import-export` | Import/export movimenti |
| `GET` | `/settings/admin` | Pannello amministrativo |

### API REST (JSON)

| Metodo | Rotta | Descrizione |
|---|---|---|
| `GET` | `/api/movements` | Lista movimenti (filtri: anno, mese, wallet, user) |
| `POST` | `/api/movements` | Crea movimento |
| `DELETE` | `/api/movements/<id>` | Elimina movimento |
| `GET` | `/api/search-movements` | Ricerca con keyword |
| `GET` | `/api/categories` | Lista categorie dell'account |
| `POST` | `/api/accounts/<id>/categories` | Crea categoria |
| `PUT` | `/api/categories/<id>` | Modifica categoria |
| `DELETE` | `/api/categories/<id>` | Elimina categoria |
| `GET` | `/api/accounts/<id>/wallets` | Lista wallet |
| `POST` | `/api/accounts/<id>/wallets` | Crea wallet |
| `PUT` | `/api/wallets/<id>` | Modifica wallet |
| `DELETE` | `/api/wallets/<id>` | Elimina wallet |
| `GET` | `/api/recurrent-movements` | Lista movimenti ricorrenti |
| `POST` | `/api/recurrent-movements` | Crea movimento ricorrente |
| `PUT` | `/api/recurrent-movements/<id>` | Modifica movimento ricorrente |
| `DELETE` | `/api/recurrent-movements/<id>` | Elimina movimento ricorrente |
| `GET` | `/api/stats/monthly` | Statistiche mensili per grafici |
| `GET` | `/api/stats/yearly` | Statistiche annuali |
| `GET` | `/api/stats/category-trend` | Trend per categoria |
| `POST` | `/api/export/movements` | Esporta movimenti in CSV |
| `POST` | `/api/import/movements` | Importa movimenti da CSV |
| `POST` | `/api/groups/<id>/invite` | Invia invito al gruppo |
| `GET` | `/api/groups/<id>/members` | Lista membri del gruppo |
| `POST` | `/api/generate-link` | Genera link di condivisione |

---

## Deploy su PythonAnywhere

1. Carica il progetto su PythonAnywhere (via `git clone` o upload manuale).
2. Crea un virtualenv con Python 3.x e installa le dipendenze.
3. Crea il file `pyspendless/.env_pa` con le variabili d'ambiente per la produzione:
   - `OAUTH_REDIRECT_URI`: URL pubblico del callback, es. `https://tuousername.pythonanywhere.com/auth/callback`
   - `DATABASE_URL`: percorso assoluto al file `.db`, es. `sqlite:////home/tuousername/pyspendless3/data/pyspendless.db`
4. Configura la Web app di PythonAnywhere con WSGI che punta a `pyspendless.app:app`.
5. Aggiungi le variabili d'ambiente nella sezione **Environment variables** del pannello PythonAnywhere.
6. Assicurati che il dominio `*.pythonanywhere.com` sia registrato come **Authorized redirect URI** nella Google Cloud Console.

> ⚠️ Non usare `OAUTHLIB_INSECURE_TRANSPORT=1` in produzione: PythonAnywhere fornisce HTTPS di default.

---

## Sicurezza

- Il file `.env` non deve mai essere committato nel VCS (è in `.gitignore`).
- L'accesso è limitato alle email presenti nella tabella `emailWhitelist`.
- I cookie di sessione sono configurati con `HttpOnly` e `SameSite=Lax`; usare `Secure=True` su HTTPS in produzione.
- Tutte le API di scrittura verificano che l'utente appartenga all'Account corretto.
- Il pannello admin è protetto da un decoratore dedicato (`@admin_required`) che controlla l'ID utente.
- I link di invito ai gruppi usano token one-time con scadenza.

---

## Roadmap

Le seguenti funzionalità sono pianificate o in lavorazione:

| Feature | Descrizione |
|---|---|
| Dashboard overall | Andamento entrate/uscite anno per anno |
| Totale wallet | Visualizzazione del saldo complessivo dei wallet |
| Filtri avanzati movimenti | Filtro per anno senza mese + filtro keyword sulle note |
| Gestione categorie avanzata | Sezioni separate entrata/uscita, merge automatico su rinomina |
| Export avanzato | Filtri multipli: tutto, anno, anno+mese, categoria, keyword |

---

*Documentazione generata dal progetto [pyspendless3](https://github.com/tabuto/pyspendless3).*
