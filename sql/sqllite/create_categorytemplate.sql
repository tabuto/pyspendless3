-- CategoryTemplate
CREATE TABLE IF NOT EXISTS CategoryTemplate (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('expense','income','transfer')),
    config TEXT
);
