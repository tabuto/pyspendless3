# Task 4.0: Strategia di Migrazione Database Legacy

## Contesto

Il database legacy `spendless-legacy.db` contiene circa **5942 movimenti** dal 2018 al 2024, con dati relativi a 3 utenti legacy (Beatrice Santucci, Francesco di Dio, Personale) che devono essere migrati nel nuovo sistema PySpendless3.

### Schema Database Legacy

```sql
CREATE TABLE MOVEMENTS(
  id varchar(100) PRIMARY KEY,
  move_date date, 
  move_year int, 
  move_month int, 
  category varchar(100), 
  wallet varchar(100), 
  income decimal(10,2),
  expense decimal(10,2),
  note varchar(255),
  user varchar(100)
);
```

**Dati rilevati nel DB legacy:**
- **Utenti**: 3 valori distinti (`Beatrice Santucci`, `Francesco di Dio`, `Personale`)
- **Wallet**: 5 wallet (`BancoPosta`, `CashBea`, `CashFra`, `FinecoBea`, `FinecoFra`)
- **Categorie**: ~50 categorie (mix italiano/inglese, alcune con duplicati es. "Burocrazia" e "Burocrazia ")
- **Movimenti**: 5942 record dal 2018 al 2024
- **Nota**: Il DB legacy NON ha il campo `account_id`

### Schema Database Nuovo (PySpendless3)

Le entità principali sono:
- **Account**: Contenitore per utenti, wallet, categorie
- **User**: Utente con google_id, email, name, account_id, role
- **Wallet**: id, code, name, currency, account_id
- **Category**: id, name, account_id, type, template_id
- **Movement**: id, move_date, move_year, move_month, category (string legacy), wallet (string legacy), income, expense, note, user (string legacy), account_id, **user_id (FK)**, **category_id (FK)**, **wallet_id (FK)**

## Obiettivo della Migrazione

Migrare tutti i dati dal database legacy al nuovo database mantenendo:
1. **Integrità dei dati**: Tutti i movimenti, wallet e categorie devono essere preservati
2. **Retrocompatibilità**: I campi legacy (category, wallet, user come stringhe) devono essere popolati
3. **Nuove FK**: I campi user_id, category_id, wallet_id devono essere mappati correttamente
4. **Account ID**: Tutti i dati devono essere associati all'account corretto

## Strategia di Migrazione

### Fase 0: Prerequisiti e Validazione

#### Input Richiesto
Lo script di migrazione richiede in input un **mapping JSON** con la seguente struttura:

```json
{
  "account_id": 1,
  "user_mapping": {
    "Beatrice Santucci": {
      "user_id": 2,
      "email": "beatrice@example.com"
    },
    "Francesco di Dio": {
      "user_id": 3,
      "email": "francesco@example.com"
    },
    "Personale": {
      "user_id": 2,
      "email": "beatrice@example.com"
    }
  }
}
```

**Nota**: "Personale" può essere mappato allo stesso utente di uno dei due utenti principali.

#### Validazioni Preliminari

Prima di iniziare la migrazione, lo script deve verificare:

1. **Account Exists**: L'account_id specificato esiste nel database nuovo
2. **Users Exist**: Tutti gli user_id nel mapping esistono e appartengono all'account_id specificato
3. **No Existing Data**: Verificare che non ci siano già movimenti per questo account (evitare duplicati)
4. **Legacy DB Readable**: Il file spendless-legacy.db è accessibile e leggibile
5. **Backup Created**: Creare un backup del database nuovo prima della migrazione

### Fase 1: Analisi e Mappatura Categorie

#### 1.1 Estrazione Categorie Legacy

Estrarre tutte le categorie uniche dal database legacy:
- Normalizzare i nomi (trim, lowercase per confronto)
- Identificare duplicati (es. "Burocrazia" vs "Burocrazia ")
- Classificare come expense/income/transfer basandosi sui dati:
  - **Income**: Se la categoria ha solo movimenti con `income > 0` e `expense = 0`
  - **Expense**: Se la categoria ha solo movimenti con `expense > 0` e `income = 0`
  - **Transfer**: Se la categoria ha entrambi i tipi (raro)

#### 1.2 Creazione Categorie nel DB Nuovo

Per ogni categoria legacy:
```python
category = Category(
    name="<nome_categoria_normalizzato>",
    account_id=<account_id_from_mapping>,
    type="expense" | "income" | "transfer",
    template_id=None  # Non mappato a template
)
```

**Mapping da mantenere**: Creare un dizionario `legacy_category_name -> category_id` per la fase successiva.

**Strategia per duplicati**:
- Consolidare duplicati ovvi (es. "Burocrazia" e "Burocrazia ")
- Mantenere il nome normalizzato
- Loggare le operazioni di consolidamento

#### 1.3 Output Fase 1

```json
{
  "categories_created": 45,
  "categories_mapping": {
    "Food And Drink": 101,
    "Transportation": 102,
    "Salary": 103,
    ...
  },
  "duplicates_consolidated": [
    {"from": "Burocrazia ", "to": "Burocrazia"},
    {"from": "cura persona", "to": "Cura persona"}
  ]
}
```

### Fase 2: Analisi e Mappatura Wallet

#### 2.1 Estrazione Wallet Legacy

Wallet identificati:
- BancoPosta
- CashBea
- CashFra
- FinecoBea
- FinecoFra

#### 2.2 Creazione Wallet nel DB Nuovo

Per ogni wallet legacy:
```python
wallet = Wallet(
    code="<wallet_code>",  # Es. "BANCOPOSTA", "CASHBEA"
    name="<wallet_name>",  # Es. "BancoPosta", "Cash Beatrice"
    currency="EUR",  # Default
    account_id=<account_id_from_mapping>
)
```

**Mapping da mantenere**: Creare un dizionario `legacy_wallet_name -> wallet_id` per la fase successiva.

**Strategia naming**:
- `code`: Uppercase, senza spazi (es. "BANCOPOSTA")
- `name`: Nome descrittivo leggibile (es. "Banco Posta")

#### 2.3 Output Fase 2

```json
{
  "wallets_created": 5,
  "wallets_mapping": {
    "BancoPosta": 201,
    "CashBea": 202,
    "CashFra": 203,
    "FinecoBea": 204,
    "FinecoFra": 205
  }
}
```

### Fase 3: Migrazione Movimenti

#### 3.1 Strategia di Migrazione

Per ogni movimento nel database legacy:

1. **Estrazione dati legacy**
2. **Mapping utente**: Usare il mapping fornito in input per ottenere `user_id`
3. **Mapping categoria**: Usare il dizionario creato in Fase 1 per ottenere `category_id`
4. **Mapping wallet**: Usare il dizionario creato in Fase 2 per ottenere `wallet_id`
5. **Inserimento nel nuovo DB**

#### 3.2 Struttura Movimento Migrato

```python
movement = Movement(
    id="<legacy_id>",  # Mantenere lo stesso ID
    move_date=<legacy_move_date>,
    move_year=<legacy_move_year>,
    move_month=<legacy_move_month>,
    
    # Campi legacy (stringhe) - RETROCOMPATIBILITÀ
    category="<legacy_category_name>",
    wallet="<legacy_wallet_name>",
    user="<legacy_user_name>",
    
    # Campi nuovi (FK)
    category_id=<mapped_category_id>,
    wallet_id=<mapped_wallet_id>,
    user_id=<mapped_user_id>,
    account_id=<account_id_from_mapping>,
    
    # Dati finanziari
    income=<legacy_income>,
    expense=<legacy_expense>,
    note="<legacy_note>"
)
```

#### 3.3 Gestione Errori e Validazioni

Durante la migrazione di ogni movimento:

- **Verifica FK**: Assicurarsi che user_id, category_id, wallet_id esistano
- **Verifica ID duplicato**: Se l'ID esiste già, loggare e skipare (o generare nuovo ID)
- **Verifica integrità dati**:
  - `move_year` e `move_month` consistenti con `move_date`
  - `income >= 0` e `expense >= 0`
  - Almeno uno tra income/expense è > 0

**Gestione errori**:
- Loggare ogni errore con dettagli del movimento
- Continuare con i movimenti successivi
- A fine migrazione, fornire report con movimenti non migrati

#### 3.4 Batch Processing

Per gestire 5942 movimenti in modo efficiente:
- Processare in batch di 500 movimenti
- Commit transazione ogni batch
- Progress bar per monitorare l'avanzamento
- Possibilità di resume in caso di interruzione

#### 3.5 Output Fase 3

```json
{
  "total_movements_legacy": 5942,
  "movements_migrated": 5940,
  "movements_skipped": 2,
  "errors": [
    {
      "movement_id": "mov_123",
      "error": "Category 'Unknown' not found in mapping",
      "action": "skipped"
    }
  ]
}
```

### Fase 4: Verifica e Validazione Post-Migrazione

#### 4.1 Verifiche Quantitative

- **Count Movements**: Verificare che il numero di movimenti migrati corrisponda
- **Sum Income/Expense**: Verificare che i totali income/expense per anno siano identici
- **Count per User**: Verificare distribuzione movimenti per utente
- **Count per Wallet**: Verificare distribuzione movimenti per wallet
- **Count per Category**: Verificare distribuzione movimenti per categoria

#### 4.2 Verifiche Qualitative

Eseguire query di controllo:

```sql
-- Verifica FK non nulle (dovrebbero essere tutte popolate)
SELECT COUNT(*) FROM Movement WHERE user_id IS NULL;
SELECT COUNT(*) FROM Movement WHERE wallet_id IS NULL;
SELECT COUNT(*) FROM Movement WHERE category_id IS NULL;

-- Verifica coerenza account_id
SELECT COUNT(DISTINCT account_id) FROM Movement;  -- Dovrebbe essere 1

-- Verifica range anni
SELECT MIN(move_year), MAX(move_year) FROM Movement;  -- 2018, 2024
```

#### 4.3 Report Finale

```json
{
  "migration_summary": {
    "status": "SUCCESS",
    "start_time": "2026-02-24T15:00:00Z",
    "end_time": "2026-02-24T15:05:32Z",
    "duration_seconds": 332
  },
  "categories": {
    "created": 45,
    "duplicates_consolidated": 3
  },
  "wallets": {
    "created": 5
  },
  "movements": {
    "total_legacy": 5942,
    "migrated": 5940,
    "skipped": 2,
    "success_rate": "99.97%"
  },
  "validation": {
    "movements_with_fk": 5940,
    "movements_without_fk": 0,
    "total_income_legacy": 125430.50,
    "total_income_new": 125430.50,
    "total_expense_legacy": 98765.30,
    "total_expense_new": 98765.30,
    "integrity_check": "PASSED"
  },
  "errors": [
    {
      "movement_id": "mov_4521",
      "reason": "Duplicate ID",
      "action": "skipped"
    }
  ]
}
```

## Implementazione Script

### Struttura Proposta

```
pyspendless/
  ├── migrations/
  │   ├── __init__.py
  │   ├── migrate_legacy.py       # Script principale
  │   ├── mapping_template.json   # Template per il mapping input
  │   └── README.md               # Istruzioni d'uso
```

### File: `mapping_template.json`

```json
{
  "account_id": null,
  "user_mapping": {
    "Beatrice Santucci": {
      "user_id": null,
      "email": "beatrice@example.com"
    },
    "Francesco di Dio": {
      "user_id": null,
      "email": "francesco@example.com"
    },
    "Personale": {
      "user_id": null,
      "email": "beatrice@example.com"
    }
  }
}
```

### Uso dello Script

```bash
# 1. Creare il file di mapping
cp pyspendless/migrations/mapping_template.json my_mapping.json

# 2. Editare my_mapping.json con gli ID corretti

# 3. Eseguire la migrazione
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json \
  --dry-run  # Prima eseguire dry-run per vedere cosa succederà

# 4. Eseguire la migrazione reale
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json
```

### Opzioni dello Script

- `--legacy-db PATH`: Path al database legacy (required)
- `--mapping PATH`: Path al file JSON con il mapping (required)
- `--dry-run`: Esegue la migrazione senza commit (per test)
- `--backup`: Crea backup del DB nuovo prima della migrazione (default: true)
- `--batch-size N`: Numero di movimenti per batch (default: 500)
- `--log-file PATH`: File di log dettagliato (default: migration.log)
- `--resume`: Riprende una migrazione interrotta

## Rollback Strategy

In caso di problemi durante o dopo la migrazione:

### Rollback Automatico
- Se la migrazione fallisce durante l'esecuzione, la transazione corrente viene rollback
- I batch precedenti rimangono committati

### Rollback Manuale
1. **Restore da Backup**: Ripristinare il database dal backup automatico
2. **Delete by Account**: Cancellare tutti i dati per l'account migrato:
   ```sql
   DELETE FROM Movement WHERE account_id = X;
   DELETE FROM Category WHERE account_id = X;
   DELETE FROM Wallet WHERE account_id = X;
   ```

## Note Importanti

1. **ID Univoci**: Gli ID dei movimenti legacy vengono mantenuti. Se ci sono conflitti, lo script skippa il movimento o genera un nuovo ID (configurabile).

2. **Normalizzazione Categorie**: Le categorie vengono normalizzate (trim, case standardization) per evitare duplicati.

3. **Campi Legacy**: I campi `category`, `wallet`, `user` (stringhe) vengono sempre popolati per retrocompatibilità con eventuali query legacy.

4. **Performance**: Con batch di 500 movimenti, la migrazione di ~6000 record dovrebbe completare in 3-5 minuti.

5. **Idempotenza**: Lo script dovrebbe essere idempotente - se eseguito più volte con gli stessi dati, non deve creare duplicati.

6. **Logging**: Ogni operazione viene loggata in dettaglio per audit e troubleshooting.

## Checklist Pre-Migrazione

- [ ] Account di destinazione creato nel nuovo DB
- [ ] Utenti creati e associati all'account
- [ ] File mapping.json compilato con ID corretti
- [ ] Backup del database nuovo creato
- [ ] Database legacy accessibile e leggibile
- [ ] Dry-run eseguito con successo
- [ ] Report dry-run verificato
- [ ] Spazio disco sufficiente (almeno 2x dimensione DB)
- [ ] Ambiente di test validato

## Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Duplicazione dati | Bassa | Alto | Verifica preliminare no existing data |
| Mapping errato utenti | Media | Alto | Dry-run e validazione manuale |
| Categorie duplicate | Alta | Basso | Algoritmo normalizzazione robusto |
| Perdita dati | Molto Bassa | Critico | Backup automatico pre-migrazione |
| Inconsistenza FK | Bassa | Medio | Validazioni rigorose in ogni fase |
| Performance DB | Bassa | Basso | Batch processing e indicizzazione |

## Metriche di Successo

La migrazione è considerata **successo** se:
- ✅ >= 99% dei movimenti migrati correttamente
- ✅ Totali income/expense identici tra legacy e nuovo DB
- ✅ Tutte le FK (user_id, category_id, wallet_id) popolate
- ✅ Nessun errore di integrità referenziale
- ✅ Validazione post-migrazione passata
- ✅ Dashboard e API funzionanti con i dati migrati

## Timeline Stimata

1. **Preparazione** (15 min): Creazione mapping, backup, validazioni preliminari
2. **Fase 1 - Categorie** (5 min): Analisi, creazione, mappatura
3. **Fase 2 - Wallet** (2 min): Creazione e mappatura
4. **Fase 3 - Movimenti** (5-10 min): Migrazione 5942 record in batch
5. **Fase 4 - Validazione** (5 min): Verifiche e report
6. **Totale stimato**: 30-40 minuti

## Prossimi Passi

Questo documento descrive la strategia. I prossimi task saranno:
- **Task 4.1**: Implementazione script `migrate_legacy.py`
- **Task 4.2**: Test su database di staging
- **Task 4.3**: Esecuzione migrazione in produzione
- **Task 4.4**: Validazione e documentazione risultati
