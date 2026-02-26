-- Migration: Aggiunta colonna order_index alla tabella Category
-- Task: 7.0 - Miglioramento Gestione Categorie
-- Descrizione: Aggiunge il campo order_index per permettere ordinamento personalizzato delle categorie

ALTER TABLE Category ADD COLUMN order_index INTEGER DEFAULT 0;
