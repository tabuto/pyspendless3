-- Creazione tabella Group
CREATE TABLE IF NOT EXISTS USER_GROUP (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES Account(id),
    owner_user_id TEXT NOT NULL REFERENCES User(id)
);
