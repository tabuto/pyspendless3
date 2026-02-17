-- Creazione tabella Movement (retrocompatibile)
CREATE TABLE IF NOT EXISTS Movement (
    id TEXT PRIMARY KEY,
    move_date DATE NOT NULL,
    move_year INTEGER NOT NULL,
    move_month INTEGER NOT NULL,
    category TEXT NOT NULL,
    wallet TEXT NOT NULL,
    income DECIMAL(10,2),
    expense DECIMAL(10,2),
    note TEXT,
    user TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES Account(id),
    user_id TEXT REFERENCES User(id),
    category_id INTEGER REFERENCES Category(id),
    wallet_id INTEGER REFERENCES Wallet(id)
);
