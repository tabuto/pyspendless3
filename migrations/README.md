# Script di Migrazione CSV

## Descrizione
Script Python per importare spese da file CSV nel database PySpendless.

## Caratteristiche
- ✅ Importa spese da CSV con formato personalizzato
- ✅ Parsing robusto importi (supporta sia punto che virgola come separatore decimale)
- ✅ Match categorie case-insensitive
- ✅ Creazione automatica di categorie mancanti
- ✅ Creazione automatica di wallet per account
- ✅ Mapping utenti da file CSV
- ✅ Gestione errori con logging dettagliato
- ✅ Statistiche importazione complete

## File Richiesti

### 1. File CSV Sorgente
**Path:** `data/SPESE_2025-SPESE.csv`

**Formato:**
```csv
Informazioni cronologiche,Category,Data,EXPENSE,Wallet,NOTE,User,Ripartizione
12/02/2026 19.07.17,Health,12/02/2026,120,FinecoFra,Montatura con lenti adele,Francesco di Dio,Famiglia
```

**Campi:**
- `Informazioni cronologiche`: Timestamp creazione (ignorato)
- `Category`: Nome categoria
- `Data`: Data spesa (formato DD/MM/YYYY)
- `EXPENSE`: Importo (accetta punto o virgola)
- `Wallet`: Nome wallet
- `NOTE`: Descrizione
- `User`: Nome completo utente
- `Ripartizione`: Ignorato

### 2. File Mapping Utenti
**Path:** `data/user_mapping.csv`

**Formato:**
```csv
user_name,user_id,account_id
Francesco di Dio,1,1
Beatrice Santucci,2,1
```

**Campi:**
- `user_name`: Nome completo (deve corrispondere al campo User nel CSV sorgente)
- `user_id`: ID utente nel database
- `account_id`: ID account a cui associare i wallet

## Utilizzo

### Preparazione
1. Creare il file di mapping utenti:
```bash
cat > data/user_mapping.csv << EOF
user_name,user_id,account_id
Francesco di Dio,1,1
Beatrice Santucci,2,1
EOF
```

2. Verificare che il file CSV sorgente esista in `data/SPESE_2025-SPESE.csv`

### Esecuzione
```bash
cd /Users/fradidio/Sviluppo/pyspendless3
source .venv/bin/activate
python migrations/import_spese_csv.py
```

### Output Esempio
```
=== Importazione Spese da CSV ===

Caricamento mappings...
- 2 utenti mappati
- 18 categorie trovate

Importazione in corso...
  → Creata categoria: Health (ID: 19)
  → Creato wallet: FinecoFra (ID: 2) per account 1
  → Creato wallet: FinecoBea (ID: 3) per account 1
  Importate 100 righe...
  Importate 200 righe...
  ...

=== Importazione completata ===
Righe totali: 1512
Righe importate: 1512
Righe saltate: 0
Wallet creati: 3
Categorie create: 21

Wallet creati:
  - FinecoBea
  - FinecoFra
  - FinecoFraBea

Categorie create:
  - Accessori
  - Baby
  - Burocrazia
  - Clothing
  - Communication
  - Culture
  - Food And Drink
  - Health
  - Hobby
  - Household
  - Market
  - Offerte e beneficenza
  - Present
  - Sport
  - Trasportation
  - Travels
  - Work

✓ Importazione completata con successo!
```

## Logica Importazione

### 1. Parsing Importi
Gli importi vengono parsati in modo robusto:
- `120` → 120.00
- `120.50` → 120.50
- `120,50` → 120.50
- `12.4` → 12.40

### 2. Match Categorie
Le categorie vengono cercate in modo case-insensitive:
- `Health` trova `Health`, `health`, `HEALTH`
- Se non esiste, viene creata automaticamente con `type='expense'`

### 3. Match Wallet
I wallet vengono cercati in modo case-insensitive per combinazione `(nome, account_id)`:
- `FinecoFra` trova `finecoFra`, `FinecoFra`, `FINECOFRA`
- Se esiste un wallet con lo stesso nome (case-insensitive): riutilizzato
- Se non esiste: creato automaticamente con:
  - `code`: generato univocamente
  - `name`: dal CSV
  - `currency`: EUR (default)
  - `account_id`: dal mapping utenti

### 4. Date
Le date vengono convertite da `DD/MM/YYYY` a `YYYY-MM-DD`:
- `12/02/2026` → `2026-02-12`

## Gestione Errori

### File di Log
Gli errori vengono salvati in `migrations/migration_errors.log` con formato:
```
Riga 1482: Category not found: Present - Dati: {'Category': 'Present', ...}
```

### Comportamento
- Gli errori su singole righe NON bloccano l'importazione
- Le righe con errori vengono saltate e loggate
- Il processo continua fino alla fine del file
- Statistiche finali mostrano righe importate vs saltate

## Risultati Importazione

### Statistiche Esempio
```
✓ DATI IMPORTATI CON SUCCESSO

Movements totali: 1512
Wallets per account 1: 3
Categorie per account 1: 39

--- Wallets ---
  finecoFra (ID: 1): 623 movements, €43,601.40
  FinecoBea (ID: 2): 888 movements, €64,673.56
  FinecoFraBea (ID: 3): 1 movements, €6.00

--- Statistiche ---
Totale spese importate: €108,280.96

Movements per anno:
  2024: 813 movements
  2025: 594 movements
  2026: 105 movements
```

## Note Tecniche

### Match Case-Insensitive
- **Categorie**: Il matching avviene in modo case-insensitive per evitare duplicati
- **Wallet**: Il matching avviene in modo case-insensitive per evitare duplicati
  - `FinecoFra` e `finecoFra` sono considerati lo stesso wallet
  - Vengono riutilizzati wallet esistenti anche se hanno diversa capitalizzazione

### Campi Legacy vs FK
Lo script popola sia i campi legacy (stringhe) che i nuovi FK:
- `category` (string) + `category_id` (FK)
- `wallet` (string) + `wallet_id` (FK)
- `user` (string) + `user_id` (FK)

Questo garantisce compatibilità con il sistema esistente.

### Commit Batch
I dati vengono committati ogni 100 righe per:
- Migliorare le performance
- Permettere checkpoint intermedi
- Ridurre il rischio di perdita dati in caso di errore

### Encoding
Il file CSV viene letto con encoding UTF-8 per supportare caratteri speciali nelle note.

## Troubleshooting

### Errore: File non trovato
Verificare che i file esistano:
```bash
ls -la data/SPESE_2025-SPESE.csv
ls -la data/user_mapping.csv
```

### Errore: User not found in mapping
Verificare che tutti gli utenti nel CSV sorgente siano presenti in `user_mapping.csv`:
```bash
cut -d',' -f7 data/SPESE_2025-SPESE.csv | sort -u
```

### Errore: Account ID non esiste
Verificare che gli account_id nel mapping esistano nel database:
```python
from pyspendless.conf import get_db_session
from pyspendless.models import Account

db = get_db_session()
accounts = db.query(Account).all()
for a in accounts:
    print(f"Account ID: {a.id}, Name: {a.name}")
```

### Pulire Dati Importati
Per rimuovere i dati importati:
```python
from pyspendless.conf import get_db_session
from pyspendless.models import Movement, Wallet

db = get_db_session()

# Rimuovere movements per wallet specifici
wallet_ids = [2, 3, 4]  # IDs dei wallet da rimuovere
db.query(Movement).filter(Movement.wallet_id.in_(wallet_ids)).delete()
db.query(Wallet).filter(Wallet.id.in_(wallet_ids)).delete()
db.commit()
```

## Manutenzione

### Aggiornare Mapping Utenti
Aggiungere nuovi utenti in `data/user_mapping.csv`:
```csv
user_name,user_id,account_id
Nuovo Utente,3,1
```

### Modificare Valori Default
Editare lo script `migrations/import_spese_csv.py`:
- `currency`: Riga ~125
- `type` categoria: Riga ~65

## Autore
PySpendless Migration Tool
