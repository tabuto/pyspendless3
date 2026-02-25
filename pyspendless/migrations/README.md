# Migrazione Database Legacy -> PySpendless3

Questa directory contiene lo script per migrare i dati dal database legacy (`spendless-legacy.db`) al nuovo database PySpendless3.

## Panoramica

Lo script `migrate_legacy.py` implementa la strategia di migrazione descritta in `backlog/task4-0.md`, seguendo un processo in 4 fasi:

1. **Fase 0 - Validazione Prerequisiti**: Verifica account, utenti, database legacy
2. **Fase 1 - Migrazione Categorie**: Estrae, normalizza e crea le categorie
3. **Fase 2 - Migrazione Wallet**: Crea i wallet nel nuovo database
4. **Fase 3 - Migrazione Movimenti**: Migra tutti i movimenti in batch
5. **Fase 4 - Validazione**: Verifica integrità e correttezza dei dati

## Prerequisiti

Prima di eseguire la migrazione:

- [ ] Account di destinazione creato nel nuovo DB
- [ ] Utenti creati e associati all'account
- [ ] File mapping.json compilato con ID corretti
- [ ] Database legacy accessibile (`data/spendless-legacy.db`)
- [ ] Backup manuale del database (opzionale - lo script ne crea uno automatico)

## Preparazione

### 1. Creare il file di mapping

Il file di mapping definisce come mappare gli utenti legacy agli utenti nel nuovo sistema:

```bash
cp pyspendless/migrations/mapping_template.json my_mapping.json
```

### 2. Compilare il mapping

Editare `my_mapping.json` con gli ID corretti:

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

**Note:**
- `account_id`: L'ID dell'account nel nuovo database dove migrare i dati
- `user_mapping`: Mappa ogni nome utente legacy al corrispondente user_id nel nuovo DB
- "Personale" può essere mappato a uno dei due utenti principali

### 3. Ottenere gli ID corretti

Per trovare gli ID di account e utenti nel nuovo database:

```bash
# Entrare in sqlite3
sqlite3 data/pyspendless3.db

# Trovare account
SELECT id, name FROM Account;

# Trovare utenti per un account specifico
SELECT id, email, name, account_id FROM User WHERE account_id = 1;

# Uscire
.quit
```

## Utilizzo

### Dry-Run (Test senza modifiche)

**Importante**: Eseguire sempre un dry-run prima della migrazione reale!

```bash
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json \
  --dry-run \
  --verbose
```

Questo comando:
- ✅ Valida tutti i prerequisiti
- ✅ Simula la migrazione senza modificare i dati
- ✅ Mostra cosa verrà creato/migrato
- ✅ Identifica eventuali problemi

### Migrazione Reale

Dopo aver verificato il dry-run:

```bash
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json \
  --log-file migration.log \
  --report migration_report.json
```

### Opzioni Disponibili

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `--legacy-db PATH` | Path al database legacy (richiesto) | - |
| `--mapping PATH` | Path al file JSON di mapping (richiesto) | - |
| `--dry-run` | Esegue senza commit (test) | false |
| `--batch-size N` | Movimenti per batch | 500 |
| `--log-file PATH` | File di log dettagliato | stdout |
| `--verbose` | Output dettagliato (debug) | false |
| `--report PATH` | Salva report JSON finale | - |

## Processo di Migrazione

### Fase 1: Categorie

Lo script:
1. Estrae tutte le categorie uniche dal DB legacy
2. Normalizza i nomi (trim spazi, gestione duplicati)
3. Determina il tipo (income/expense/transfer) basandosi sui dati
4. Crea le categorie nel nuovo DB
5. Mantiene un mapping `legacy_name -> category_id`

**Gestione Duplicati**: Categorie come "Burocrazia" e "Burocrazia " (con spazio) vengono consolidate.

### Fase 2: Wallet

Lo script:
1. Estrae i wallet unici dal DB legacy
2. Genera un `code` (uppercase, no spazi)
3. Crea i wallet nel nuovo DB con currency EUR
4. Mantiene un mapping `legacy_name -> wallet_id`

### Fase 3: Movimenti

Lo script:
1. Processa i movimenti in batch (default 500)
2. Per ogni movimento:
   - Mappa user, category, wallet ai nuovi ID
   - Mantiene i campi legacy (stringhe) per retrocompatibilità
   - Popola i nuovi FK (user_id, category_id, wallet_id)
   - Assegna l'account_id corretto
3. Commit ogni batch
4. Gestisce errori continuando con i movimenti successivi

**Campi Movimento Migrato**:
```python
Movement(
    id="<legacy_id>",           # Mantiene ID originale
    move_date, move_year, move_month,
    
    # Legacy (stringhe)
    category="<normalized_name>",
    wallet="<legacy_wallet>",
    user="<legacy_user>",
    
    # Nuovi FK
    category_id=<mapped_id>,
    wallet_id=<mapped_id>,
    user_id=<mapped_id>,
    account_id=<account_id>,
    
    income, expense, note
)
```

### Fase 4: Validazione

Lo script verifica:
- ✅ Numero movimenti migrati vs legacy
- ✅ Tutte le FK (user_id, category_id, wallet_id) sono popolate
- ✅ Totali income/expense identici tra legacy e nuovo DB
- ✅ Nessuna FK NULL
- ✅ Account_id consistente

## Output e Report

### Durante l'esecuzione

Lo script mostra progress in tempo reale:

```
=== FASE 0: Validazione Prerequisiti ===
✅ Account trovato: Family Account (ID: 1)
✅ User 'Beatrice Santucci' -> ID 2 (beatrice@example.com)
...

=== FASE 1: Migrazione Categorie ===
📊 Trovate 47 categorie uniche nel DB legacy
🔄 Consolidati 3 duplicati
✅ Create 45 categorie

=== FASE 2: Migrazione Wallet ===
📊 Trovati 5 wallet unici
✅ Creati 5 wallet

=== FASE 3: Migrazione Movimenti ===
📊 Migrazione di 5942 movimenti in batch da 500
🔄 Batch 1: movimenti 1 - 500
...
✅ Migrati 5940 movimenti
⚠️  Skippati 2 movimenti
```

### Report Finale

Il report JSON contiene statistiche dettagliate:

```json
{
  "migration_summary": {
    "status": "SUCCESS",
    "start_time": "2026-02-25T10:00:00",
    "end_time": "2026-02-25T10:05:32",
    "duration_seconds": 332
  },
  "categories": {
    "analyzed": 47,
    "created": 45,
    "duplicates_consolidated": 2
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
    "movements_count_legacy": 5942,
    "movements_count_new": 5940,
    "null_fk_user": 0,
    "null_fk_category": 0,
    "null_fk_wallet": 0,
    "total_income_legacy": 125430.50,
    "total_income_new": 125430.50,
    "total_expense_legacy": 98765.30,
    "total_expense_new": 98765.30,
    "integrity_check": "PASSED"
  },
  "errors": [
    {
      "movement_id": "mov_4521",
      "error": "Duplicate ID",
      "action": "skipped"
    }
  ]
}
```

## Gestione Errori e Rollback

### Backup Automatico

Lo script crea automaticamente un backup del database prima della migrazione:
```
pyspendless.db.backup_20260225_100000
```

### Rollback Manuale

In caso di problemi, per ripristinare:

```bash
# Opzione 1: Restore da backup
cp data/pyspendless3.db.backup_YYYYMMDD_HHMMSS data/pyspendless3.db

# Opzione 2: Delete per account
sqlite3 data/pyspendless3.db
DELETE FROM Movement WHERE account_id = 1;
DELETE FROM Category WHERE account_id = 1;
DELETE FROM Wallet WHERE account_id = 1;
.quit
```

### Errori Comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| "Account non trovato" | account_id errato nel mapping | Verificare con `SELECT * FROM Account` |
| "User non trovato" | user_id errato o non appartiene all'account | Verificare con `SELECT * FROM User WHERE account_id = X` |
| "Category not found" | Categoria non creata (fase 1 fallita) | Controllare log fase 1 |
| "Duplicate ID" | Movimento con ID già esistente | Normale se si ri-esegue migrazione |

## Metriche di Successo

La migrazione è considerata **SUCCESS** se:
- ✅ >= 99% dei movimenti migrati
- ✅ Totali income/expense identici (±0.01€)
- ✅ Tutte le FK popolate (0 NULL)
- ✅ Nessun errore di integrità referenziale
- ✅ Validazione PASSED

## Timeline Stimata

Per ~6000 movimenti:
- Preparazione: 5-10 minuti
- Fase 1 (Categorie): 1-2 minuti
- Fase 2 (Wallet): < 1 minuto
- Fase 3 (Movimenti): 3-5 minuti
- Fase 4 (Validazione): 1-2 minuti
- **Totale**: 10-20 minuti

## Note Importanti

1. **Idempotenza**: Lo script può essere eseguito più volte. I movimenti con ID duplicato vengono skippati.

2. **Normalizzazione**: Le categorie vengono normalizzate (trim, consolidamento duplicati) automaticamente.

3. **Retrocompatibilità**: I campi legacy (category, wallet, user come stringhe) vengono sempre popolati.

4. **Performance**: Batch processing per gestire grandi volumi di dati.

5. **Logging**: Ogni operazione viene loggata per audit e troubleshooting.

## Troubleshooting

### Problema: Migrazione lenta

**Soluzione**: Aumentare batch size
```bash
--batch-size 1000
```

### Problema: Categorie duplicate

**Soluzione**: Lo script gestisce automaticamente i duplicati consolidandoli. Verificare nel log:
```
Duplicato: 'Burocrazia ' -> 'Burocrazia'
```

### Problema: FK NULL dopo migrazione

**Soluzione**: Verificare che tutti i mapping siano corretti nel file JSON. Eseguire:
```sql
SELECT DISTINCT user FROM MOVEMENTS;  -- nel DB legacy
```
E assicurarsi che tutti gli utenti siano nel mapping.

## Supporto

Per problemi o domande:
1. Controllare il file di log (`--log-file migration.log`)
2. Verificare il report JSON (`--report migration_report.json`)
3. Eseguire dry-run con `--verbose` per dettagli

## Esempi Completi

### Esempio 1: Prima migrazione (dry-run + reale)

```bash
# Step 1: Preparazione
cp pyspendless/migrations/mapping_template.json my_mapping.json
# Editare my_mapping.json con ID corretti

# Step 2: Dry-run
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json \
  --dry-run \
  --verbose

# Step 3: Migrazione reale
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json \
  --log-file logs/migration_$(date +%Y%m%d_%H%M%S).log \
  --report reports/migration_report.json
```

### Esempio 2: Migrazione con batch personalizzato

```bash
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping my_mapping.json \
  --batch-size 1000 \
  --verbose \
  --log-file migration.log
```

### Esempio 3: Solo validazione (dopo migrazione manuale)

```bash
# Per validare dati già migrati manualmente
sqlite3 data/pyspendless3.db
SELECT COUNT(*) as movements FROM Movement WHERE account_id = 1;
SELECT SUM(income) as total_income, SUM(expense) as total_expense FROM Movement WHERE account_id = 1;
.quit
```

## Checklist Pre-Migrazione

Prima di eseguire la migrazione reale:

- [ ] Dry-run eseguito con successo
- [ ] Report dry-run verificato
- [ ] Mapping JSON corretto e validato
- [ ] Account e utenti esistono nel DB
- [ ] Backup manuale del database creato (opzionale)
- [ ] Spazio disco sufficiente (almeno 2x dimensione DB)
- [ ] Ambiente di produzione vs test chiarito
- [ ] Team informato della migrazione (se applicabile)

## Checklist Post-Migrazione

Dopo la migrazione:

- [ ] Validation PASSED
- [ ] Report salvato e archiviato
- [ ] Dashboard funzionante con nuovi dati
- [ ] Query di test eseguite con successo
- [ ] Backup pre-migrazione conservato
- [ ] Documentazione aggiornata
