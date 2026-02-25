# Quick Start - Migrazione Database Legacy

## Step-by-Step Guide

### 1. Preparazione Account e Utenti

Prima di eseguire la migrazione, assicurati di avere:

```bash
# Controlla account disponibili
sqlite3 data/pyspendless3.db "SELECT id, name FROM Account;"

# Controlla utenti
sqlite3 data/pyspendless3.db "SELECT id, email, name, account_id FROM User;"
```

### 2. Crea il Mapping File

```bash
# Copia il template
cp pyspendless/migrations/mapping_template.json migration_mapping.json

# Edita con i tuoi valori
nano migration_mapping.json
```

Esempio con dati reali:
```json
{
  "account_id": 1,
  "user_mapping": {
    "Beatrice Santucci": {
      "user_id": 3,
      "email": "beatrice@example.com"
    },
    "Francesco di Dio": {
      "user_id": 2,
      "email": "tabuto83@gmail.com"
    },
    "Personale": {
      "user_id": 3,
      "email": "beatrice@example.com"
    }
  }
}
```

### 3. Test con Dry-Run

```bash
source .venv/bin/activate

python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping migration_mapping.json \
  --dry-run \
  --verbose
```

### 4. Esegui Migrazione Reale

```bash
python -m pyspendless.migrations.migrate_legacy \
  --legacy-db data/spendless-legacy.db \
  --mapping migration_mapping.json \
  --log-file migration.log \
  --report migration_report.json
```

### 5. Verifica Risultati

```bash
# Controlla report
cat migration_report.json | python -m json.tool

# Controlla dati migrati
sqlite3 data/pyspendless3.db "SELECT COUNT(*) as total FROM Movement WHERE account_id = 1;"
sqlite3 data/pyspendless3.db "SELECT COUNT(*) as total FROM Category WHERE account_id = 1;"
sqlite3 data/pyspendless3.db "SELECT COUNT(*) as total FROM Wallet WHERE account_id = 1;"
```

## Rollback (se necessario)

```bash
# Restore da backup automatico
cp data/pyspendless3.db.backup_YYYYMMDD_HHMMSS data/pyspendless3.db

# O rimuovi dati per account specifico
sqlite3 data/pyspendless3.db << EOF
DELETE FROM Movement WHERE account_id = 1;
DELETE FROM Category WHERE account_id = 1 AND template_id IS NULL;
DELETE FROM Wallet WHERE account_id = 1;
EOF
```

## Checklist

- [ ] Account creato nel nuovo DB
- [ ] Utenti creati e verificati
- [ ] File mapping_mapping.json compilato correttamente
- [ ] Dry-run eseguito e verificato
- [ ] Backup manuale creato (opzionale)
- [ ] Migrazione eseguita
- [ ] Validazione passata
- [ ] Report salvato e archiviato
