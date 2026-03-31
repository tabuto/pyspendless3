CREATE TABLE IF NOT EXISTS RecurrentMovement (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    category_id INTEGER NOT NULL REFERENCES Category(id),
    wallet_id   INTEGER NOT NULL REFERENCES Wallet(id),
    income      NUMERIC(10,2),
    expense     NUMERIC(10,2),
    note        TEXT,
    account_id  INTEGER NOT NULL REFERENCES Account(id),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_recurrent_movement_account ON RecurrentMovement(account_id);
