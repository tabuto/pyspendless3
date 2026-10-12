# PySpendless

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite)
![Auth](https://img.shields.io/badge/Auth-Google_OAuth_2.0-red?logo=google)

**PySpendless** è un'applicazione web per la gestione di spese personali e condivise: registrazione di entrate/uscite, organizzazione per wallet e categoria, dashboard aggregate e condivisione dei dati con altri utenti tramite gruppi. Login tramite Google OAuth 2.0, accesso limitato a una whitelist di email.

## Funzionalità principali

- **Movimenti**: creazione, modifica, ricerca ed export di spese/entrate, con filtri per periodo, wallet, categoria e keyword; movimenti ricorrenti e correzione massiva su più movimenti filtrati.
- **Wallet e categorie**: più portafogli con valuta propria; categorie di spesa/entrata/trasferimento con template di default al primo accesso.
- **Dashboard**: riepilogo mensile e annuale con grafici.
- **Gruppi**: condivisione dei dati tra utenti dello stesso account tramite inviti.
- **Pannello admin**: gestione whitelist email e utenti registrati.
- **Modalità manutenzione** e pagina di onboarding per i nuovi account.

Guida completa a rotte, modello dati e variabili d'ambiente: [`wiki/Home.md`](wiki/Home.md).

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Python 3, Flask |
| ORM / DB | SQLAlchemy + SQLite |
| Autenticazione | Authlib (Google OAuth 2.0) |
| UI | AdminLTE 3 (Bootstrap 4) + Jinja2 |
| Grafici | Chart.js |
| Migrazioni DB | Alembic |
| Hosting | PythonAnywhere |

## Struttura del progetto

```
pyspendless3/
├── pyspendless/
│   ├── app.py          # Entry point Flask: rotte e gestione HTTP
│   ├── models.py       # Entità SQLAlchemy
│   ├── repository.py   # Logica CRUD e accesso al DB
│   ├── conf.py          # Configurazioni, costanti, sessione DB
│   ├── requirements.txt
│   ├── templates/       # Jinja2 (ps-*.html)
│   └── static/          # CSS/JS
├── sql/sqllite/         # Script di creazione/popolamento DB
├── migrations/          # Script di migrazione dati
├── backlog/             # Task, bugfix e roadmap (features.md, taskN-0.md)
├── wiki/                # Documentazione estesa
└── CLAUDE.md             # Regole operative per lo sviluppo assistito
```

## Avvio rapido in locale

```bash
git clone https://github.com/tabuto/pyspendless3.git
cd pyspendless3

python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -U pip
.venv/bin/pip install -r pyspendless/requirements.txt
```

Configura `pyspendless/.env` (non versionato) con almeno `SECRET_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OAUTH_REDIRECT_URI` — dettagli in [`wiki/Home.md`](wiki/Home.md#variabili-dambiente).

```bash
sqlite3 data/pyspendless.db < sql/sqllite/create_all.sql
sqlite3 data/pyspendless.db < sql/sqllite/insert_categorytemplate.sql
sqlite3 data/pyspendless.db \
  "INSERT INTO emailWhitelist (email, added_at) VALUES ('tua-email@gmail.com', datetime('now'));"

export OAUTHLIB_INSECURE_TRANSPORT=1   # solo in locale, OAuth su HTTP
.venv/bin/python -m pyspendless.app
```

App disponibile su **http://localhost:5000**.

## Deploy

Ambiente di produzione: PythonAnywhere (`tabuto.pythonanywhere.com`), working copy del server in `/home/tabuto/pyspendless3`.

Il deploy è **manuale**: l'account PythonAnywhere free non supporta le chiamate API su cui si basava la GitHub Action `.github/workflows/deploy.yml` (disabilitata). Procedura e convenzione di versionamento (`_APP_VERSION` in `app.py`, tag `vX.Y.Z`) in [`CLAUDE.md`](CLAUDE.md#rilascio--deploy).

Versione dell'applicazione esposta su `GET /version`.

## Documentazione

| File | Contenuto |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Regole di progetto e procedura di rilascio |
| [`wiki/Home.md`](wiki/Home.md) | Guida completa: rotte, modello dati, variabili d'ambiente, deploy |
| [`pyspendless/SPECS.md`](pyspendless/SPECS.md) | Specifiche funzionali originali |
| [`backlog/features.md`](backlog/features.md) | Backlog feature e relativo stato |
| [`backlog/00-task-minor-bugfix.md`](backlog/00-task-minor-bugfix.md) | Registro bugfix/evolutive minori (MB-NNN) |
