-- Creazione tabella Category
CREATE TABLE IF NOT EXISTS Category (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES Account(id),
    type TEXT NOT NULL CHECK(type IN ('expense','income','transfer')),
    template_id INTEGER REFERENCES CategoryTemplate(id)
);
