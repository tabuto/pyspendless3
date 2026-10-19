# PySpendless

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-lightgrey?logo=flask)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite)
![Tailwind CSS](https://img.shields.io/badge/UI-Tailwind_CSS_v4-38bdf8?logo=tailwindcss)
![Auth](https://img.shields.io/badge/Auth-Google_OAuth_2.0-red?logo=google)

**PySpendless** is a web application for tracking personal and shared expenses: record income and expenses, organise them by wallet and category, explore monthly and yearly dashboards, generate annual PDF reports and share your data with other users through groups. Sign-in is through Google OAuth 2.0, restricted to an email whitelist. It also exposes an **MCP server** (`/mcp`, plus an OAuth 2 variant for Alexa+) that lets you log expenses by talking to an AI assistant such as Claude.

<p align="center">
  <img src="https://raw.githubusercontent.com/wiki/tabuto/pyspendless3/images/movements-light.png" alt="Movements page, light theme" width="49%">
  <img src="https://raw.githubusercontent.com/wiki/tabuto/pyspendless3/images/movements-dark.png" alt="Movements page, dark theme" width="49%">
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/wiki/tabuto/pyspendless3/images/dashboard-monthly-light.png" alt="Monthly dashboard" width="49%">
  <img src="https://raw.githubusercontent.com/wiki/tabuto/pyspendless3/images/reports-light.png" alt="Annual report page" width="49%">
</p>

> The screenshots use fictitious demo data. **The application UI is currently in Italian**; the documentation is in English. More screenshots: [Screenshots](https://github.com/tabuto/pyspendless3/wiki/Screenshots).

## Main features

- **Movements**: create, edit, search and export expenses/income, with filters by period, wallet, category and keyword; recurrent movements; bulk edit of all filtered movements; CSV import/export.
- **Wallets and categories**: multiple wallets with their own currency and a preferred wallet per user; expense / income / transfer categories with default templates copied on first login.
- **Dashboards and reports**: monthly and yearly dashboards with charts, and an annual PDF report (year-over-year comparison, top expenses, category and wallet breakdown).
- **Groups**: share data between users of the same account through invitations.
- **MCP server and Alexa+**: log expenses by voice or chat. See [MCP server and Alexa+](https://github.com/tabuto/pyspendless3/wiki/MCP-and-Alexa).
- **Light / dark theme**, responsive layout (table on desktop, card list on mobile).
- **Admin panel** (email whitelist, registered users), **maintenance mode** and an onboarding page for new accounts.

The full guide to routes, data model and environment variables is in the [wiki](https://github.com/tabuto/pyspendless3/wiki) (source in [`wiki/Home.md`](wiki/Home.md)).

## Tech stack

| Component | Technology |
|---|---|
| Backend | Python 3, Flask |
| ORM / DB | SQLAlchemy + SQLite |
| Authentication | Authlib (Google OAuth 2.0) |
| UI | Tailwind CSS v4 (compiled CSS is committed) + Jinja2, small vanilla JS helpers |
| Charts / tables | Chart.js, DataTables, Tom Select |
| PDF reports | fpdf2 + matplotlib |
| Hosting | PythonAnywhere |

## Project structure

```
pyspendless3/
├── pyspendless/
│   ├── app.py           # Flask entry point: pages and API routes
│   ├── oauth_server.py  # OAuth 2 blueprint (Alexa+)
│   ├── mcp_server.py    # MCP tools and JSON-RPC handling
│   ├── models.py        # SQLAlchemy entities
│   ├── repository.py    # CRUD and data access logic
│   ├── conf.py          # Configuration, constants, DB session
│   ├── requirements.txt
│   ├── templates/       # Jinja2 templates (ps-*.html)
│   └── static/          # Compiled Tailwind CSS and JS helpers
├── sql/sqllite/         # Seed scripts (default category templates, ...)
├── migrations/          # Data migration scripts
├── tools/               # CSS build script, UI verification scripts
├── alexa-mcp-lambda/    # AWS Lambda bridge for an Alexa custom skill
├── backlog/             # Tasks, bugfix log and roadmap (in Italian)
├── wiki/                # Source of the GitHub wiki
└── CLAUDE.md            # Working rules for AI-assisted development (in Italian)
```

## Quick start (local)

```bash
git clone https://github.com/tabuto/pyspendless3.git
cd pyspendless3

python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -U pip
.venv/bin/pip install -r pyspendless/requirements.txt
```

Create `pyspendless/.env` (git-ignored) with at least `SECRET_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `OAUTH_REDIRECT_URI`. You need a Google OAuth 2.0 client from the [Google Cloud Console](https://console.cloud.google.com/) with `http://localhost:5000/auth/callback` as an authorized redirect URI. Details in the [wiki](https://github.com/tabuto/pyspendless3/wiki#environment-variables).

Create the database from the SQLAlchemy models, load the default category templates and whitelist your email:

```bash
mkdir -p data
DATABASE_URL=sqlite:///../data/pyspendless.db \
.venv/bin/python -c "from pyspendless.models import Base; from pyspendless.conf import get_db_engine; Base.metadata.create_all(bind=get_db_engine())"

sqlite3 data/pyspendless.db < sql/sqllite/insert_categorytemplate.sql
sqlite3 data/pyspendless.db \
  "INSERT INTO emailWhitelist (email, added_at) VALUES ('your-email@gmail.com', datetime('now'));"

export OAUTHLIB_INSECURE_TRANSPORT=1   # local only: OAuth over plain HTTP
.venv/bin/python -m pyspendless.app
```

The app is available at **http://localhost:5000**.

If you edit templates or `ps-tailwind.src.css`, rebuild the stylesheet with `./tools/build-css.sh`.

## Deployment

Production runs on PythonAnywhere (`tabuto.pythonanywhere.com`). Deployment is **manual**: the free PythonAnywhere plan does not support the API calls that the GitHub Action in `.github/workflows/deploy.yml` relied on, so that workflow is disabled. The release procedure and versioning convention (`_APP_VERSION` in `app.py`, `vX.Y.Z` tags) are described in [`CLAUDE.md`](CLAUDE.md#rilascio--deploy) (in Italian); a summary is in the [wiki](https://github.com/tabuto/pyspendless3/wiki#deploying-to-pythonanywhere).

The running version is exposed at `GET /version`.

## Documentation

| Resource | Contents |
|---|---|
| [Wiki](https://github.com/tabuto/pyspendless3/wiki) | Full guide: features, routes, data model, environment variables, deployment, security |
| [Screenshots](https://github.com/tabuto/pyspendless3/wiki/Screenshots) | Screenshot gallery (light/dark, desktop/mobile) |
| [MCP server and Alexa+](https://github.com/tabuto/pyspendless3/wiki/MCP-and-Alexa) | Personal tokens, OAuth 2, Alexa bridge |
| [`CLAUDE.md`](CLAUDE.md) | Project rules and release procedure (Italian) |
| [`pyspendless/SPECS.md`](pyspendless/SPECS.md) | Original functional specifications (Italian) |
| [`backlog/features.md`](backlog/features.md) | Feature backlog and status (Italian) |
| [`backlog/00-task-minor-bugfix.md`](backlog/00-task-minor-bugfix.md) | Minor bugfix / enhancement log, MB-NNN (Italian) |
