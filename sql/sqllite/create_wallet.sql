-- Creazione tabella Wallet
CREATE TABLE IF NOT EXISTS Wallet (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    currency TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES Account(id),
    created_at DATETIME NOT NULL
);
