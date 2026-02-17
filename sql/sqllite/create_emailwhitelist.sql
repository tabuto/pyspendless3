-- emailWhitelist
CREATE TABLE IF NOT EXISTS emailWhitelist (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    added_at DATETIME NOT NULL,
    note TEXT
);
