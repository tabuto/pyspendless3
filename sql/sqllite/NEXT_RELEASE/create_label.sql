-- Migration: nuova tabella Label
-- Task: 26.0 - Labels sui movimenti
-- Da eseguire sul DB esistente PRIMA del Reload della web app:
--   sqlite3 /home/tabuto/pyspendless3/data/pyspendless3.db < sql/sqllite/NEXT_RELEASE/create_label.sql
--
-- Idempotente (IF NOT EXISTS su tabella e indici): rieseguirlo non fa danni.
-- Non tocca nessuna tabella esistente e nessun dato: puo' essere eseguito
-- anche PRIMA che il codice del task26-0 sia in produzione, perche' finche'
-- l'applicazione non lo usa questo schema in piu' e' inerte.
--
-- Il popolamento iniziale del registro (le label gia' presenti nelle note dei
-- movimenti storici) NON e' qui: richiede la stessa grammatica del parser
-- (regex con confini di parola), che in SQL puro non si scrive. E' lo script
-- Python `migrations/backfill_labels.py`, da lanciare dopo questo file.
-- Se lo si dimentica, le label storiche non compaiono nell'autocompletamento
-- finche' i movimenti non vengono risalvati: fallimento degradato, non rotto.

CREATE TABLE IF NOT EXISTS Label (
    id         INTEGER  PRIMARY KEY AUTOINCREMENT,
    name       TEXT     NOT NULL,
    name_norm  TEXT     NOT NULL,
    account_id INTEGER  NOT NULL REFERENCES Account(id),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Unicita' per account, case-insensitive via name_norm: due membri dello
-- stesso account non possono creare due righe per la stessa label, ed e'
-- questo vincolo (non un controllo applicativo) a risolvere la corsa fra due
-- salvataggi contemporanei.
CREATE UNIQUE INDEX IF NOT EXISTS uq_label_account_name ON Label(account_id, name_norm);

-- Serve all'elenco della pagina Impostazioni e al dropdown
-- dell'autocompletamento, che filtrano sempre per account.
CREATE INDEX IF NOT EXISTS idx_label_account ON Label(account_id);
