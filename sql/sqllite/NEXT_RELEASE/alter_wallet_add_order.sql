-- Migration: Aggiunta colonna order_index alla tabella Wallet
-- Task: 7.1 - Miglioramento Gestione Wallet
-- Descrizione: Aggiunge il campo order_index per permettere ordinamento personalizzato dei wallet

ALTER TABLE Wallet ADD COLUMN order_index INTEGER DEFAULT 0;
