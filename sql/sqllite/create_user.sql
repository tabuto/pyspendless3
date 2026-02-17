-- Creazione tabella User
CREATE TABLE IF NOT EXISTS User (
    id TEXT PRIMARY KEY,
    google_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES Account(id),
    role TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
