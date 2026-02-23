-- Tabella token per gestire i token di invito
CREATE TABLE IF NOT EXISTS Token (
    uuid TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    create_date DATETIME NOT NULL,
    expire_date DATETIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    payload TEXT NOT NULL,
    CONSTRAINT check_token_status CHECK (status IN ('PENDING', 'USED', 'EXPIRED'))
);

-- Indici per migliorare le performance
CREATE INDEX IF NOT EXISTS idx_token_status ON Token(status);
CREATE INDEX IF NOT EXISTS idx_token_expire_date ON Token(expire_date);
CREATE INDEX IF NOT EXISTS idx_token_type ON Token(type);
