-- Cancellazione tabella User se esiste
DROP TABLE IF EXISTS User;

-- Creazione tabella User
CREATE TABLE User (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uid TEXT UNIQUE NOT NULL,
    google_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES Account(id),
    role TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
