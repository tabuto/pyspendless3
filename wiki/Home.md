# PySpendless

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-lightgrey?logo=flask)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite)
![Tailwind CSS](https://img.shields.io/badge/UI-Tailwind_CSS_v4-38bdf8?logo=tailwindcss)
![Auth](https://img.shields.io/badge/Auth-Google_OAuth_2.0-red?logo=google)

**PySpendless** is a web application for tracking personal and shared expenses. Record income and expenses, organise them by wallet and category, explore aggregate dashboards, generate yearly PDF reports and share your data with other users through groups. It also exposes an **MCP server**, so you can log expenses by talking to an AI assistant such as Claude or Alexa+.

![Movements page, light theme](https://raw.githubusercontent.com/wiki/tabuto/pyspendless3/images/movements-light.png)

> **Note on language:** the application UI is currently in Italian. The documentation is in English; more screenshots are on the [Screenshots](https://github.com/tabuto/pyspendless3/wiki/Screenshots) page.

---

## Table of contents

- [Features](#features)
- [Architecture and tech stack](#architecture-and-tech-stack)
- [Project structure](#project-structure)
- [Data model](#data-model)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment variables](#environment-variables)
- [Running the application](#running-the-application)
- [Routes overview](#routes-overview)
- [Deploying to PythonAnywhere](#deploying-to-pythonanywhere)
- [Security](#security)
- [Roadmap](#roadmap)

See also: [Screenshots](https://github.com/tabuto/pyspendless3/wiki/Screenshots) · [MCP server and Alexa+](https://github.com/tabuto/pyspendless3/wiki/MCP-and-Alexa)

---

## Features

### Authentication
- Sign in with **Google OAuth 2.0**
- Access is restricted to the emails on a **whitelist** (managed in the database or from the admin panel)
- Account, user and default categories are created automatically on first login
- Persistent session (7 days)

### Movements
- Record **expenses** and **income** with date, category, wallet and note
- Browse movements with filters (date range, wallet, category, type, keyword), a summary of totals and a category chart
- Edit, delete and **repeat** an existing movement (opens the creation form pre-filled with today's date)
- **Bulk edit**: filter the movements, then change category and/or note on all of the results at once
- Dedicated **search** page (description, category, wallet)
- **Responsive** layout: table on desktop, card list with infinite scroll on mobile
- **Recurrent movements**: templates for repetitive operations
- **CSV import** and **CSV export** (the export honours the filters currently applied)

### Wallets
- Multiple **wallets** (e.g. cash, card, checking account), each with its own currency
- Custom ordering
- A **preferred wallet per user**, used as the default when logging movements

### Categories
- **Expense**, **income** and **transfer** categories
- Default templates copied automatically on first login
- Custom and alphabetical ordering
- Renaming a category updates the linked movements

### Dashboards and reports
- **Monthly dashboard**: income vs. expenses, spending by category and by wallet (Chart.js)
- **Yearly dashboard**: year totals and monthly trend per category
- **Annual PDF report** (Reports page): year summary, year-over-year comparison, monthly trend, top 10 expenses, category breakdown, wallet distribution and anomalous months

### Groups and sharing
- Create a group and invite other users by **link or email**
- Invitation management (pending, accepted, declined) and member list

### MCP server and Alexa+
- `/mcp` endpoint (JSON-RPC) with the tools `add_movement` and `list_categories`, authenticated with a **personal token** generated from the profile page
- `/mcp-oauth2` endpoint with OAuth 2 (authorization code + PKCE) for clients that require it, such as Alexa+
- Details in [MCP server and Alexa+](https://github.com/tabuto/pyspendless3/wiki/MCP-and-Alexa)

### Admin panel
- Manage the **email whitelist** (add/remove)
- List and delete registered users
- Available to the administrator user only

### Other
- **Light / dark theme**, persisted per browser
- **Maintenance mode**, switchable through an environment variable (`MAINTENANCE_MODE=1`)
- **Onboarding** page for the initial account setup
- Application version exposed at `GET /version`

---

## Architecture and tech stack

| Component | Technology |
|---|---|
| Backend | Python 3, Flask |
| ORM / DB | SQLAlchemy + SQLite |
| Authentication | Authlib (Google OAuth 2.0) |
| UI | Tailwind CSS v4 (compiled CSS is committed), Jinja2 templates, small vanilla JS helpers (`ps-ui.js`, `ps-theme.js`) |
| Charts | Chart.js |
| Interactive tables / selects | DataTables, Tom Select |
| PDF reports | fpdf2 + matplotlib |
| Frontend ↔ backend | REST API + AJAX + JSON |
| Environment variables | python-dotenv |
| Hosting | PythonAnywhere |

### Communication flow

```
Browser  ──AJAX/JSON──►  Flask (app.py, oauth_server.py)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              repository.py        conf.py
                    │
                    ▼
              SQLAlchemy ORM
                    │
                    ▼
              SQLite (.db file)
```

MCP clients (Claude, Alexa+) talk to `/mcp` and `/mcp-oauth2` in the same Flask app.

---

## Project structure

```
pyspendless3/
├── pyspendless/
│   ├── app.py              # Flask entry point: pages and API routes
│   ├── oauth_server.py     # OAuth 2 blueprint (/oauth/authorize, /oauth/token)
│   ├── mcp_server.py       # MCP tools and JSON-RPC handling
│   ├── models.py           # SQLAlchemy entities
│   ├── repository.py       # CRUD and data access logic
│   ├── conf.py             # Configuration, constants, DB session
│   ├── report_charts.py    # matplotlib charts for the PDF report
│   ├── report_pdf.py       # PDF report layout (fpdf2)
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # Environment variables (do NOT commit)
│   ├── .env_pa             # PythonAnywhere variables (do NOT commit)
│   ├── static/
│   │   ├── css/            # ps-tailwind.src.css (source) -> ps-tailwind.css (compiled)
│   │   └── js/             # ps-ui.js (modal/drawer/tabs), ps-theme.js (light/dark)
│   └── templates/          # Jinja2 templates, base layout: ps-base.html
├── sql/sqllite/            # Table creation and seed scripts
├── migrations/             # Data migration scripts
├── tools/                  # CSS build script, UI verification scripts
├── alexa-mcp-lambda/       # AWS Lambda bridge for an Alexa custom skill
├── data/                   # SQLite database files (do NOT commit)
└── backlog/                # Task notes, bugfix log, roadmap
```

---

## Data model

### Main entities

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

### Entity descriptions

| Entity | Description |
|---|---|
| **Account** | Main container; groups users, wallets and categories |
| **User** | User registered through Google OAuth, bound to an Account; stores the preferred wallet |
| **Wallet** | A wallet (e.g. cash, card); has a currency and a custom order |
| **Category** | Expense / income / transfer category, specific to an Account |
| **CategoryTemplate** | Default category templates, copied to every new Account |
| **Movement** | A single transaction (expense or income); FKs to User, Category and Wallet |
| **RecurrentMovement** | Recurrent movement template used to pre-fill the form |
| **UserGroup** | Group for sharing between users |
| **GroupMembership** | User–group association with invitation handling (token, status) |
| **EmailWhitelist** | Emails allowed to sign in |
| **Token** | Group invitation links, hashed personal MCP tokens and OAuth codes / access / refresh tokens |

> **Backward compatibility:** the `Movement` table keeps the legacy fields (`category`, `wallet`, `user` as strings) next to the newer nullable FKs (`category_id`, `wallet_id`, `user_id`).

---

## Prerequisites

- Python 3.9 or later
- `sqlite3` available in your `PATH`
- **Google OAuth 2.0** credentials (Client ID and Client Secret) — see the [Google Cloud Console](https://console.cloud.google.com/)
- (Optional) A PythonAnywhere account for deployment

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/tabuto/pyspendless3.git
cd pyspendless3
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# or
.venv\Scripts\activate           # Windows
```

### 3. Install the dependencies

```bash
.venv/bin/pip install -U pip
.venv/bin/pip install -r pyspendless/requirements.txt
```

### 4. Configure the environment variables

Create `pyspendless/.env` with your values (see [Environment variables](#environment-variables)). The file is git-ignored.

### 5. Initialise the database

Create the tables from the SQLAlchemy models, then load the default category templates:

```bash
DATABASE_URL=sqlite:///../data/pyspendless.db \
.venv/bin/python -c "from pyspendless.models import Base; from pyspendless.conf import get_db_engine; Base.metadata.create_all(bind=get_db_engine())"

sqlite3 data/pyspendless.db < sql/sqllite/insert_categorytemplate.sql
```

> The default category template names are in Italian. Edit `sql/sqllite/insert_categorytemplate.sql` before loading it if you prefer other names.

### 6. Add your email to the whitelist

```bash
sqlite3 data/pyspendless.db \
  "INSERT INTO emailWhitelist (email, added_at) VALUES ('your-email@gmail.com', datetime('now'));"
```

---

## Environment variables

File: `pyspendless/.env`

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | ✅ | Flask session secret (the default `changeme` must not be used) | `a-long-random-string` |
| `DATABASE_URL` | ✅ | SQLite URL. Relative paths are resolved from the `pyspendless/` folder (default: `sqlite:///../data/pyspendless.db`) | `sqlite:///../data/pyspendless.db` |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth Client ID | `123...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth Client Secret | `GOCSPX-...` |
| `OAUTH_REDIRECT_URI` | ✅ | OAuth callback URL | `http://localhost:5000/auth/callback` |
| `FLASK_ENV` | No | Flask mode (default `development`) | `development` |
| `WHITELIST_EMAILS` | No | Comma-separated authorised emails (the database whitelist is preferred) | `alice@gmail.com,bob@gmail.com` |
| `BASE_URL` | No | Application base URL (default `http://localhost:5000`) | `http://localhost:5000` |
| `ADMIN_USER_ID` | No | ID of the administrator user | `1` |
| `DEFAULT_CURRENCY` | No | Default wallet currency (default `EUR`) | `EUR` |
| `PAGINATION_LIMIT` | No | Page size for paginated lists (default `50`) | `50` |
| `MAINTENANCE_MODE` | No | Enable maintenance mode (`1`/`0`) | `0` |
| `OAUTH_ALEXA_CLIENT_ID` | No | Pre-registered OAuth 2 client for `/mcp-oauth2` | `alexa-client` |
| `OAUTH_ALEXA_CLIENT_SECRET` | No | Secret of that client | |
| `OAUTH_ALEXA_REDIRECT_URIS` | No | Comma-separated allowed redirect URIs for that client | |
| `OAUTH_MAX_MOVEMENT_AMOUNT` | No | Reserved: defined in `conf.py` but not enforced yet | |

> ⚠️ Never commit the `.env` file to the repository.

---

## Running the application

### Local development

```bash
# Required for OAuth over plain HTTP (local only)
export OAUTHLIB_INSECURE_TRANSPORT=1

.venv/bin/python -m pyspendless.app
```

The application is available at **http://localhost:5000**.

### Changing the UI

The UI is styled with Tailwind CSS. The compiled stylesheet is committed, because the production server has no build step. After touching any `class="..."` in a template or a rule in `ps-tailwind.src.css`, rebuild it:

```bash
./tools/build-css.sh
```

The script downloads the standalone Tailwind CLI into `tools/tailwindcss` (git-ignored) on first use.

### Production

```bash
# Without OAUTHLIB_INSECURE_TRANSPORT (HTTPS required)
gunicorn -w 2 "pyspendless.app:app"
```

---

## Routes overview

### Authentication

| Method | Route | Description |
|---|---|---|
| `GET` | `/login` | Login page |
| `GET` | `/auth/login` | Redirect to Google OAuth |
| `GET` | `/auth/callback` | Google callback; checks the whitelist and creates the user |
| `GET` | `/auth/logout` | Log out and clear the session |

### Pages

| Method | Route | Description |
|---|---|---|
| `GET` | `/home` | User home page |
| `GET` | `/create` | New movement form |
| `GET` | `/movements` | Movement list (with filters) |
| `GET` | `/ps-search-mov` | Movement search |
| `GET` | `/recurrent-movements` | Recurrent movements |
| `GET` | `/dashboard/monthly` | Monthly dashboard |
| `GET` | `/dashboard/yearly` | Yearly dashboard |
| `GET` | `/reports` | Annual PDF report |
| `GET` | `/onboarding` | New user onboarding |
| `GET` | `/version` | Application version |

### Settings

| Method | Route | Description |
|---|---|---|
| `GET` | `/settings/categories` | Category management |
| `GET` | `/settings/wallets` | Wallet management |
| `GET` | `/settings/group` | Group and invitations |
| `GET` | `/settings/import-export` | Import/export movements |
| `GET` | `/settings/profile` | Profile, personal MCP tokens, OAuth connections |
| `GET` | `/settings/admin` | Admin panel |

### REST API (JSON)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/movements` | List movements (filters: year, month, wallet, user, ...) |
| `POST` | `/api/movements` | Create a movement |
| `DELETE` | `/api/movements/<id>` | Delete a movement |
| `GET` | `/api/movements/export` | Export the filtered movements to CSV |
| `POST` | `/api/movements/bulk-update` | Change category and/or note on all filtered movements |
| `GET` | `/api/search-movements` | Keyword search |
| `GET` | `/api/categories` | List the account's categories |
| `POST` | `/api/accounts/<id>/categories` | Create a category |
| `PUT` | `/api/categories/<id>` | Update a category |
| `DELETE` | `/api/categories/<id>` | Delete a category |
| `GET` | `/api/accounts/<id>/wallets` | List wallets |
| `POST` | `/api/accounts/<id>/wallets` | Create a wallet |
| `PUT` | `/api/wallets/<id>` | Update a wallet |
| `PUT` / `DELETE` | `/api/wallets/<id>/preferred` | Set / clear the user's preferred wallet |
| `DELETE` | `/api/wallets/<id>` | Delete a wallet |
| `GET` | `/api/recurrent-movements` | List recurrent movements |
| `POST` | `/api/recurrent-movements` | Create a recurrent movement |
| `PUT` | `/api/recurrent-movements/<id>` | Update a recurrent movement |
| `DELETE` | `/api/recurrent-movements/<id>` | Delete a recurrent movement |
| `GET` | `/api/stats/monthly` | Monthly statistics for charts |
| `GET` | `/api/stats/yearly` | Yearly statistics |
| `GET` | `/api/stats/category-trend` | Per-category trend |
| `GET` | `/api/filters/years` | Years with data |
| `GET` | `/api/reports/annual` | Download the annual PDF report (`?year=`) |
| `POST` | `/api/export/movements` | Export movements to CSV |
| `POST` | `/api/import/movements` | Import movements from CSV |
| `POST` | `/api/groups/<id>/invite` | Invite someone to a group |
| `GET` | `/api/groups/<id>/members` | List group members |
| `POST` | `/api/generate-link` | Generate a sharing link |
| `GET` / `POST` | `/api/mcp-tokens` | List / create personal MCP tokens |
| `DELETE` | `/api/mcp-tokens/<hash>` | Revoke a personal MCP token |
| `GET` | `/api/oauth-connections` | List authorised OAuth apps |
| `DELETE` | `/api/oauth-connections/<client_id>` | Revoke an OAuth app |

### MCP and OAuth

| Method | Route | Description |
|---|---|---|
| `POST` | `/mcp` | MCP endpoint, personal-token authentication |
| `POST` | `/mcp-oauth2` | MCP endpoint, OAuth 2 access-token authentication |
| `GET` | `/oauth/authorize` | OAuth 2 authorization (consent page) |
| `POST` | `/oauth/authorize/confirm` | Consent confirmation |
| `POST` | `/oauth/token` | Token endpoint (authorization code + PKCE, client credentials, refresh) |
| `GET` | `/.well-known/oauth-*` | Discovery metadata |

---

## Deploying to PythonAnywhere

Deployment is **manual**: the free PythonAnywhere plan does not allow the API calls that the (disabled) GitHub Action in `.github/workflows/deploy.yml` relies on.

1. Put the project on PythonAnywhere (`git clone` or manual upload).
2. Create a virtualenv with Python 3.x and install the dependencies.
3. Create `pyspendless/.env_pa` with the production environment variables:
   - `OAUTH_REDIRECT_URI`: public callback URL, e.g. `https://yourusername.pythonanywhere.com/auth/callback`
   - `DATABASE_URL`: absolute path to the `.db` file, e.g. `sqlite:////home/yourusername/pyspendless3/data/pyspendless.db`
4. Configure the PythonAnywhere web app with a WSGI file pointing to `pyspendless.app:app`.
5. Add the environment variables in the **Environment variables** section of the PythonAnywhere dashboard.
6. Make sure the `*.pythonanywhere.com` domain is registered as an **Authorized redirect URI** in the Google Cloud Console.

To release an update: bump `_APP_VERSION` in `pyspendless/app.py`, rebuild the CSS (`./tools/build-css.sh`), commit, tag `vX.Y.Z` and push; then run `git pull` in a PythonAnywhere Bash console and click **Reload** on the *Web* tab. Check `GET /version` afterwards.

> ⚠️ Do not use `OAUTHLIB_INSECURE_TRANSPORT=1` in production: PythonAnywhere serves HTTPS by default.

---

## Security

- The `.env` file must never be committed (it is in `.gitignore`).
- Access is limited to the emails in the `emailWhitelist` table.
- Session cookies are `HttpOnly` and `SameSite=Lax`. `SESSION_COOKIE_SECURE` is currently set to `False` in `app.py`; set it to `True` when serving over HTTPS.
- Write APIs check that the user belongs to the right Account.
- The admin panel is protected by a dedicated decorator (`@admin_required`) that checks the user ID against `ADMIN_USER_ID`.
- Group invitation links use one-time tokens with an expiry date.
- Personal MCP tokens are shown once, stored hashed, and expire after 365 days.

---

## Roadmap

Planned or in progress (see `backlog/features.md`):

| Feature | Description |
|---|---|
| Overall dashboard | Income/expenses year by year |
| Wallet total | Show the overall balance across wallets |
| MCP rate limiting | Request limits on the `/mcp` endpoint |

---

*Documentation for the [pyspendless3](https://github.com/tabuto/pyspendless3) project.*
