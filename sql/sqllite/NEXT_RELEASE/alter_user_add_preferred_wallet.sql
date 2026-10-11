-- Migration: Aggiunta colonna preferred_wallet_id alla tabella User
-- Task: 22.0 - Wallet preferito per singolo utente
-- Descrizione: la preferenza del wallet passa da proprietà dell'account
--   (Wallet.order_index = 0, MB-004/MB-005) a proprietà del singolo utente.
--   Aggiunge User.preferred_wallet_id e, in backfill, assegna a ogni utente
--   il wallet che era preferito per il proprio account, cosi' da non perdere
--   la preferenza gia' impostata prima della migrazione.

ALTER TABLE User ADD COLUMN preferred_wallet_id INTEGER REFERENCES Wallet(id);

-- Backfill: ogni utente eredita il wallet che era "preferito" per il proprio
-- account (quello con order_index = 0). Se un account ha per dati storici piu'
-- wallet a 0, si usa lo stesso criterio deterministico gia' usato in passato
-- da WalletRepository.get_preferred_wallet (il primo in ordine alfabetico).
-- Account senza un wallet a order_index = 0 non vengono toccati: i loro
-- utenti restano senza preferito, stato legittimo.
UPDATE User
SET preferred_wallet_id = (
    SELECT w.id
    FROM Wallet w
    WHERE w.account_id = User.account_id
      AND w.order_index = 0
    ORDER BY w.name ASC
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1 FROM Wallet w
    WHERE w.account_id = User.account_id
      AND w.order_index = 0
);
