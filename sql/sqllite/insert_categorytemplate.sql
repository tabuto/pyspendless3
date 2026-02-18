-- Inserimento categorie di default per CategoryTemplate

-- INCOMES
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Stipendio', 'income', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Freelance', 'income', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Investimenti', 'income', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Regali / Bonus', 'income', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Altre Entrate', 'income', NULL);

-- EXPENSES
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Alimentari', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Abitazione', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Utenze', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Trasporti', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Assicurazioni', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Salute', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Svago', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Ristoranti & Bar', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Shopping', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Educazione', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Viaggi', 'expense', NULL);
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Altro Uscite', 'expense', NULL);

-- TRANSFER
INSERT INTO CategoryTemplate (name, type, config) VALUES ('Trasferimento', 'transfer', NULL);
