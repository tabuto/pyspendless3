-- Tabella Label — registro delle etichette per account (task26-0)
--
-- NON e' un'associazione con i movimenti: l'appartenenza di una label a un
-- movimento vive nel testo di Movement.note e solo li' (decisione D1).
-- Questa tabella serve a tre cose:
--   1. autocompletamento del campo labels (ricerca LIKE su name_norm);
--   2. forma canonica della grafia (decisione D4: #Coop -> #coop se #coop
--      e' gia' in registro);
--   3. pagina Impostazioni -> Labels (rinomina, merge, eliminazione).
--
-- name      = grafia canonica, quella che va scritta nelle note
-- name_norm = lower(name): chiave di unicita' e colonna su cui gira la
--             ricerca. E' una colonna vera e non un COLLATE NOCASE perche'
--             cosi' l'unicita' case-insensitive non dipende dalla collation
--             del DBMS e il LIKE lavora su un valore gia' normalizzato.

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
