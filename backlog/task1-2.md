# Task 1.2 — Creazione Database e Tabelle SQLite

## Obiettivo
Creare il database SQLite e tutte le tabelle delle entità specificate in `SPECS.md`, predisponendo la struttura per la gestione delle spese personali e condivise.

## Struttura delle cartelle
- `sql/sqllite/` — conterrà gli script SQL di creazione delle tabelle.

## Istruzioni

1. **Crea il database**
   - Puoi creare il file database (es. `pyspendless3.db`) tramite SQLite CLI o Python/Flask.
   - Esempio CLI:
     ```bash
     sqlite3 ./data/pyspendless3.db
     ```

2. **Crea le tabelle**
   - Per ogni entità, crea uno script SQL nella cartella `sql/sqllite/`.
   - Gli script devono essere eseguibili in sequenza per creare tutte le tabelle e le relazioni.

3. **Esegui gli script**
   - Da terminale:
     ```bash
     sqlite3 ./data/pyspendless3.db < sql/sqllite/create_all.sql
     ```

---

## Specifica delle tabelle

### 1. Account
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL
- `created_at` DATETIME NOT NULL

### 2. User
- `id` TEXT PRIMARY KEY (UUID)
- `google_id` TEXT UNIQUE NOT NULL
- `email` TEXT UNIQUE NOT NULL
- `name` TEXT NOT NULL
- `account_id` INTEGER NOT NULL REFERENCES Account(id)
- `role` TEXT NOT NULL
- `created_at` DATETIME NOT NULL

### 3. Wallet
- `id` INTEGER PRIMARY KEY
- `code` TEXT UNIQUE NOT NULL
- `name` TEXT NOT NULL
- `currency` TEXT NOT NULL
- `account_id` INTEGER NOT NULL REFERENCES Account(id)
- `created_at` DATETIME NOT NULL

### 4. Category
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL
- `account_id` INTEGER NOT NULL REFERENCES Account(id)
- `type` TEXT NOT NULL CHECK(type IN ('expense','income','transfer'))
- `template_id` INTEGER REFERENCES CategoryTemplate(id)

### 5. CategoryTemplate
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL
- `type` TEXT NOT NULL CHECK(type IN ('expense','income','transfer'))
- `config` TEXT (JSON opzionale)

### 6. emailWhitelist
- `id` INTEGER PRIMARY KEY
- `email` TEXT UNIQUE NOT NULL
- `added_at` DATETIME NOT NULL
- `note` TEXT

### 7. Movement (retrocompatibile)
- `id` TEXT PRIMARY KEY
- `move_date` DATE NOT NULL
- `move_year` INTEGER NOT NULL
- `move_month` INTEGER NOT NULL
- `category` TEXT NOT NULL
- `wallet` TEXT NOT NULL
- `income` DECIMAL(10,2)
- `expense` DECIMAL(10,2)
- `note` TEXT
- `user` TEXT NOT NULL
- `account_id` INTEGER NOT NULL REFERENCES Account(id)
- `user_id` TEXT REFERENCES User(id) NULL
- `category_id` INTEGER REFERENCES Category(id) NULL
- `wallet_id` INTEGER REFERENCES Wallet(id) NULL

### 8. Group
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL
- `account_id` INTEGER NOT NULL REFERENCES Account(id)
- `owner_user_id` TEXT NOT NULL REFERENCES User(id)

### 9. GroupMembership / Invite
- `id` INTEGER PRIMARY KEY
- `group_id` INTEGER NOT NULL REFERENCES Group(id)
- `user_id` TEXT REFERENCES User(id)
- `invite_email` TEXT NOT NULL
- `invited_by_user_id` TEXT NOT NULL REFERENCES User(id)
- `status` TEXT NOT NULL CHECK(status IN ('pending','accepted','declined'))
- `token` TEXT NOT NULL

---

## Script di esempio
- Crea un file `create_all.sql` in `sql/sqllite/` che includa tutti i comandi di creazione delle tabelle nell'ordine corretto.
- Per ogni tabella, crea uno script separato se necessario (es: `create_account.sql`, `create_user.sql`, ...).

---

## Esecuzione
1. Popola la cartella `sql/sqllite/` con gli script SQL.
2. Esegui `create_all.sql` per creare tutte le tabelle nel database.
3. Verifica la creazione con:
   ```bash
   sqlite3 ./data/pyspendless.db ".tables"
   ```

---

**Nota:**
- Le relazioni FK sono implementate tramite `REFERENCES`.
- I campi FK aggiuntivi in `Movement` sono nullable per retrocompatibilità.
- Adatta i tipi se necessario per compatibilità con SQLite.
