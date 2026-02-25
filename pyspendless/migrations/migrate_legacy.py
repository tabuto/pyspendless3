#!/usr/bin/env python3
"""
Script di Migrazione Database Legacy -> PySpendless3

Questo script migra i dati dal database legacy (spendless-legacy.db) al nuovo database PySpendless3.
Segue la strategia descritta in task4-0.md con 4 fasi principali:
1. Validazione prerequisiti
2. Migrazione categorie
3. Migrazione wallet
4. Migrazione movimenti
5. Validazione post-migrazione

Uso:
    python -m pyspendless.migrations.migrate_legacy --legacy-db data/spendless-legacy.db --mapping my_mapping.json --dry-run
    python -m pyspendless.migrations.migrate_legacy --legacy-db data/spendless-legacy.db --mapping my_mapping.json
"""

import argparse
import json
import logging
import sqlite3
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal

# Setup path per import
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pyspendless.models import Account, User, Wallet, Category, Movement
from pyspendless.conf import DATABASE_URL, get_db_engine, get_db_session


# ===== LOGGING CONFIGURATION =====
def setup_logging(log_file: Optional[str] = None, verbose: bool = False):
    """Configura il logging per la migrazione"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w'))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


# ===== UTILITIES =====
def normalize_string(s: str) -> str:
    """Normalizza una stringa (trim, lowercase)"""
    return s.strip() if s else ""


def normalize_category_name(name: str) -> str:
    """Normalizza il nome di una categoria per confronto e deduplicazione"""
    normalized = normalize_string(name)
    # Mantieni la capitalizzazione originale ma rimuovi spazi extra
    return ' '.join(normalized.split())


# ===== MIGRATION STATS =====
class MigrationStats:
    """Traccia le statistiche della migrazione"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None
        
        # Categories
        self.categories_analyzed = 0
        self.categories_created = 0
        self.categories_duplicates = []
        self.categories_mapping = {}
        
        # Wallets
        self.wallets_created = 0
        self.wallets_mapping = {}
        
        # Movements
        self.movements_total_legacy = 0
        self.movements_migrated = 0
        self.movements_skipped = 0
        self.movements_errors = []
        
        # Validation
        self.validation_results = {}
    
    def finalize(self):
        """Finalizza le statistiche"""
        self.end_time = datetime.now()
    
    def duration_seconds(self) -> int:
        """Ritorna la durata in secondi"""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return 0
    
    def to_dict(self) -> Dict:
        """Converte le statistiche in dizionario per JSON"""
        return {
            "migration_summary": {
                "status": "SUCCESS" if self.movements_skipped < self.movements_total_legacy * 0.01 else "PARTIAL",
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": self.duration_seconds()
            },
            "categories": {
                "analyzed": self.categories_analyzed,
                "created": self.categories_created,
                "duplicates_consolidated": len(self.categories_duplicates)
            },
            "wallets": {
                "created": self.wallets_created
            },
            "movements": {
                "total_legacy": self.movements_total_legacy,
                "migrated": self.movements_migrated,
                "skipped": self.movements_skipped,
                "success_rate": f"{(self.movements_migrated / self.movements_total_legacy * 100):.2f}%" if self.movements_total_legacy > 0 else "0%"
            },
            "validation": self.validation_results,
            "errors": self.movements_errors[:20]  # Limita a primi 20 errori
        }


# ===== MIGRATION CLASS =====
class LegacyMigrator:
    """Gestisce la migrazione dal database legacy"""
    
    def __init__(self, legacy_db_path: str, mapping: Dict, dry_run: bool = False, 
                 batch_size: int = 500, logger: Optional[logging.Logger] = None):
        self.legacy_db_path = legacy_db_path
        self.mapping = mapping
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.logger = logger or logging.getLogger(__name__)
        self.stats = MigrationStats()
        
        # Connections
        self.legacy_conn = None
        self.new_session = None
        
        # Mappings (da costruire durante migrazione)
        self.category_name_to_id = {}  # legacy_name -> new_id
        self.wallet_name_to_id = {}    # legacy_name -> new_id
        self.user_name_to_id = {}      # legacy_name -> new_id
    
    def __enter__(self):
        """Context manager entry"""
        self.legacy_conn = sqlite3.connect(self.legacy_db_path)
        self.legacy_conn.row_factory = sqlite3.Row
        self.new_session = get_db_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.legacy_conn:
            self.legacy_conn.close()
        if self.new_session:
            self.new_session.close()
    
    # ===== FASE 0: PREREQUISITI E VALIDAZIONE =====
    
    def validate_prerequisites(self) -> bool:
        """Valida tutti i prerequisiti prima di iniziare la migrazione"""
        self.logger.info("=== FASE 0: Validazione Prerequisiti ===")
        
        # 1. Verifica account esiste
        account_id = self.mapping.get('account_id')
        if not account_id:
            self.logger.error("❌ account_id non specificato nel mapping")
            return False
        
        account = self.new_session.query(Account).filter_by(id=account_id).first()
        if not account:
            self.logger.error(f"❌ Account con ID {account_id} non trovato")
            return False
        
        self.logger.info(f"✅ Account trovato: {account.name} (ID: {account_id})")
        
        # 2. Verifica utenti esistono
        user_mapping = self.mapping.get('user_mapping', {})
        if not user_mapping:
            self.logger.error("❌ user_mapping non specificato")
            return False
        
        for legacy_user, user_info in user_mapping.items():
            user_id = user_info.get('user_id')
            if not user_id:
                self.logger.error(f"❌ user_id non specificato per {legacy_user}")
                return False
            
            user = self.new_session.query(User).filter_by(id=user_id, account_id=account_id).first()
            if not user:
                self.logger.error(f"❌ User {user_id} non trovato o non appartiene all'account {account_id}")
                return False
            
            self.user_name_to_id[legacy_user] = user_id
            self.logger.info(f"✅ User '{legacy_user}' -> ID {user_id} ({user.email})")
        
        # 3. Verifica no existing data
        existing_movements = self.new_session.query(Movement).filter_by(account_id=account_id).count()
        if existing_movements > 0:
            self.logger.warning(f"⚠️  Trovati {existing_movements} movimenti esistenti per questo account")
            response = input("Continuare comunque? (y/n): ")
            if response.lower() != 'y':
                return False
        
        # 4. Verifica legacy DB accessibile
        if not Path(self.legacy_db_path).exists():
            self.logger.error(f"❌ Database legacy non trovato: {self.legacy_db_path}")
            return False
        
        # Verifica struttura
        cursor = self.legacy_conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM MOVEMENTS")
        count = cursor.fetchone()['cnt']
        self.stats.movements_total_legacy = count
        self.logger.info(f"✅ Database legacy accessibile: {count} movimenti trovati")
        
        return True
    
    def create_backup(self) -> Optional[str]:
        """Crea un backup del database nuovo"""
        if self.dry_run:
            self.logger.info("🔄 Dry-run: Backup non necessario")
            return None
        
        # Estrai il path del database da DATABASE_URL
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL.replace('sqlite:///', '')
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                shutil.copy2(db_path, backup_path)
                self.logger.info(f"✅ Backup creato: {backup_path}")
                return backup_path
            except Exception as e:
                self.logger.error(f"❌ Errore creazione backup: {e}")
                return None
        
        self.logger.warning("⚠️  Backup non supportato per database non-SQLite")
        return None
    
    # ===== FASE 1: CATEGORIE =====
    
    def migrate_categories(self) -> bool:
        """Migra le categorie dal database legacy"""
        self.logger.info("\n=== FASE 1: Migrazione Categorie ===")
        
        account_id = self.mapping['account_id']
        
        # 1. Estrai categorie uniche dal legacy DB
        cursor = self.legacy_conn.cursor()
        cursor.execute("""
            SELECT 
                category,
                SUM(CASE WHEN income > 0 THEN 1 ELSE 0 END) as income_count,
                SUM(CASE WHEN expense > 0 THEN 1 ELSE 0 END) as expense_count
            FROM MOVEMENTS
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
        """)
        
        legacy_categories = cursor.fetchall()
        self.stats.categories_analyzed = len(legacy_categories)
        self.logger.info(f"📊 Trovate {len(legacy_categories)} categorie uniche nel DB legacy")
        
        # 2. Normalizza e deduplica
        category_data = {}  # normalized_name -> (original_name, type, income_count, expense_count)
        duplicates = []
        
        for row in legacy_categories:
            original_name = row['category']
            normalized_name = normalize_category_name(original_name)
            income_count = row['income_count']
            expense_count = row['expense_count']
            
            # Determina il tipo
            if income_count > 0 and expense_count == 0:
                cat_type = 'income'
            elif expense_count > 0 and income_count == 0:
                cat_type = 'expense'
            else:
                cat_type = 'transfer'
            
            # Check duplicati
            if normalized_name in category_data:
                duplicates.append({
                    "from": original_name,
                    "to": category_data[normalized_name][0]
                })
                self.logger.debug(f"Duplicato: '{original_name}' -> '{category_data[normalized_name][0]}'")
            else:
                category_data[normalized_name] = (original_name, cat_type, income_count, expense_count)
        
        self.stats.categories_duplicates = duplicates
        self.logger.info(f"🔄 Consolidati {len(duplicates)} duplicati")
        
        # 3. Crea categorie nel nuovo DB
        for normalized_name, (original_name, cat_type, inc_cnt, exp_cnt) in category_data.items():
            # Usa il nome normalizzato per la nuova categoria
            new_category = Category(
                name=normalized_name,
                account_id=account_id,
                type=cat_type,
                template_id=None
            )
            
            if not self.dry_run:
                self.new_session.add(new_category)
                self.new_session.flush()  # Per ottenere l'ID
                category_id = new_category.id
            else:
                category_id = f"dry_run_{len(self.category_name_to_id) + 1}"
            
            # Mappa sia il nome normalizzato che l'originale
            self.category_name_to_id[normalized_name] = category_id
            self.category_name_to_id[original_name] = category_id
            
            self.stats.categories_created += 1
            self.stats.categories_mapping[normalized_name] = category_id
            
            self.logger.debug(f"Creata categoria: {normalized_name} (type={cat_type}, id={category_id})")
        
        if not self.dry_run:
            self.new_session.commit()
        
        self.logger.info(f"✅ Create {self.stats.categories_created} categorie")
        return True
    
    # ===== FASE 2: WALLET =====
    
    def migrate_wallets(self) -> bool:
        """Migra i wallet dal database legacy"""
        self.logger.info("\n=== FASE 2: Migrazione Wallet ===")
        
        account_id = self.mapping['account_id']
        
        # 1. Estrai wallet unici
        cursor = self.legacy_conn.cursor()
        cursor.execute("""
            SELECT DISTINCT wallet 
            FROM MOVEMENTS 
            WHERE wallet IS NOT NULL AND wallet != ''
            ORDER BY wallet
        """)
        
        legacy_wallets = [row['wallet'] for row in cursor.fetchall()]
        self.logger.info(f"📊 Trovati {len(legacy_wallets)} wallet unici")
        
        # 2. Crea wallet nel nuovo DB
        for wallet_name in legacy_wallets:
            # Genera code (uppercase, no spaces)
            wallet_code = wallet_name.replace(' ', '').upper()
            
            new_wallet = Wallet(
                code=wallet_code,
                name=wallet_name,
                currency='EUR',
                account_id=account_id
            )
            
            if not self.dry_run:
                self.new_session.add(new_wallet)
                self.new_session.flush()
                wallet_id = new_wallet.id
            else:
                wallet_id = f"dry_run_{len(self.wallet_name_to_id) + 1}"
            
            self.wallet_name_to_id[wallet_name] = wallet_id
            self.stats.wallets_created += 1
            self.stats.wallets_mapping[wallet_name] = wallet_id
            
            self.logger.debug(f"Creato wallet: {wallet_name} (code={wallet_code}, id={wallet_id})")
        
        if not self.dry_run:
            self.new_session.commit()
        
        self.logger.info(f"✅ Creati {self.stats.wallets_created} wallet")
        return True
    
    # ===== FASE 3: MOVIMENTI =====
    
    def migrate_movements(self) -> bool:
        """Migra i movimenti dal database legacy in batch"""
        self.logger.info("\n=== FASE 3: Migrazione Movimenti ===")
        
        account_id = self.mapping['account_id']
        
        # 1. Conta movimenti totali
        cursor = self.legacy_conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM MOVEMENTS")
        total = cursor.fetchone()['cnt']
        
        self.logger.info(f"📊 Migrazione di {total} movimenti in batch da {self.batch_size}")
        
        # 2. Processa in batch
        offset = 0
        batch_num = 0
        
        while offset < total:
            batch_num += 1
            self.logger.info(f"🔄 Batch {batch_num}: movimenti {offset + 1} - {min(offset + self.batch_size, total)}")
            
            # Fetch batch
            cursor.execute(f"""
                SELECT * FROM MOVEMENTS 
                ORDER BY move_date, id
                LIMIT {self.batch_size} OFFSET {offset}
            """)
            
            movements = cursor.fetchall()
            
            # Process batch
            for row in movements:
                try:
                    self._migrate_single_movement(row, account_id)
                except Exception as e:
                    self.logger.error(f"❌ Errore migrazione movimento {row['id']}: {e}")
                    self.stats.movements_skipped += 1
                    self.stats.movements_errors.append({
                        "movement_id": row['id'],
                        "error": str(e),
                        "action": "skipped"
                    })
            
            # Commit batch
            if not self.dry_run:
                try:
                    self.new_session.commit()
                    self.logger.debug(f"✅ Batch {batch_num} committato")
                except Exception as e:
                    self.logger.error(f"❌ Errore commit batch {batch_num}: {e}")
                    self.new_session.rollback()
                    return False
            
            offset += self.batch_size
        
        self.logger.info(f"✅ Migrati {self.stats.movements_migrated} movimenti")
        self.logger.info(f"⚠️  Skippati {self.stats.movements_skipped} movimenti")
        
        return True
    
    def _migrate_single_movement(self, row: sqlite3.Row, account_id: int):
        """Migra un singolo movimento"""
        movement_id = row['id']
        
        # Mapping dati
        legacy_user = row['user']
        legacy_category = row['category']
        legacy_wallet = row['wallet']
        
        # Ottieni FK
        user_id = self.user_name_to_id.get(legacy_user)
        if not user_id:
            raise ValueError(f"User '{legacy_user}' non trovato nel mapping")
        
        category_id = self.category_name_to_id.get(legacy_category)
        if not category_id:
            raise ValueError(f"Category '{legacy_category}' non trovata nel mapping")
        
        wallet_id = self.wallet_name_to_id.get(legacy_wallet)
        if not wallet_id:
            raise ValueError(f"Wallet '{legacy_wallet}' non trovato nel mapping")
        
        # Normalizza categoria per campo legacy
        normalized_category = normalize_category_name(legacy_category)
        
        # Crea movimento
        movement = Movement(
            id=movement_id,
            move_date=row['move_date'],
            move_year=row['move_year'],
            move_month=row['move_month'],
            
            # Campi legacy (stringhe) - usa il nome normalizzato per category
            category=normalized_category,
            wallet=legacy_wallet,
            user=legacy_user,
            
            # Campi nuovi (FK)
            category_id=category_id,
            wallet_id=wallet_id,
            user_id=user_id,
            account_id=account_id,
            
            # Dati finanziari
            income=Decimal(str(row['income'])) if row['income'] else None,
            expense=Decimal(str(row['expense'])) if row['expense'] else None,
            note=row['note']
        )
        
        if not self.dry_run:
            self.new_session.add(movement)
        
        self.stats.movements_migrated += 1
    
    # ===== FASE 4: VALIDAZIONE =====
    
    def validate_migration(self) -> bool:
        """Valida la migrazione confrontando i dati"""
        self.logger.info("\n=== FASE 4: Validazione Post-Migrazione ===")
        
        if self.dry_run:
            self.logger.info("🔄 Dry-run: Validazione saltata")
            return True
        
        account_id = self.mapping['account_id']
        
        # 1. Count movements
        new_count = self.new_session.query(Movement).filter_by(account_id=account_id).count()
        self.logger.info(f"📊 Movimenti nel nuovo DB: {new_count}")
        self.stats.validation_results['movements_count_new'] = new_count
        self.stats.validation_results['movements_count_legacy'] = self.stats.movements_total_legacy
        
        # 2. Verifica FK non nulle
        null_user_id = self.new_session.query(Movement).filter_by(account_id=account_id, user_id=None).count()
        null_category_id = self.new_session.query(Movement).filter_by(account_id=account_id, category_id=None).count()
        null_wallet_id = self.new_session.query(Movement).filter_by(account_id=account_id, wallet_id=None).count()
        
        self.logger.info(f"FK NULL - user_id: {null_user_id}, category_id: {null_category_id}, wallet_id: {null_wallet_id}")
        self.stats.validation_results['null_fk_user'] = null_user_id
        self.stats.validation_results['null_fk_category'] = null_category_id
        self.stats.validation_results['null_fk_wallet'] = null_wallet_id
        
        # 3. Verifica totali income/expense
        cursor = self.legacy_conn.cursor()
        cursor.execute("SELECT SUM(income) as total_income, SUM(expense) as total_expense FROM MOVEMENTS")
        legacy_totals = cursor.fetchone()
        
        new_result = self.new_session.execute(text("""
            SELECT SUM(income) as total_income, SUM(expense) as total_expense 
            FROM Movement 
            WHERE account_id = :account_id
        """), {"account_id": account_id}).fetchone()
        
        legacy_income = float(legacy_totals['total_income'] or 0)
        legacy_expense = float(legacy_totals['total_expense'] or 0)
        new_income = float(new_result[0] or 0)
        new_expense = float(new_result[1] or 0)
        
        self.logger.info(f"💰 Income - Legacy: {legacy_income:.2f}, Nuovo: {new_income:.2f}")
        self.logger.info(f"💸 Expense - Legacy: {legacy_expense:.2f}, Nuovo: {new_expense:.2f}")
        
        self.stats.validation_results['total_income_legacy'] = legacy_income
        self.stats.validation_results['total_income_new'] = new_income
        self.stats.validation_results['total_expense_legacy'] = legacy_expense
        self.stats.validation_results['total_expense_new'] = new_expense
        
        # 4. Check integrità
        income_match = abs(legacy_income - new_income) < 0.01
        expense_match = abs(legacy_expense - new_expense) < 0.01
        
        if income_match and expense_match and null_user_id == 0 and null_category_id == 0 and null_wallet_id == 0:
            self.logger.info("✅ Validazione PASSED")
            self.stats.validation_results['integrity_check'] = 'PASSED'
            return True
        else:
            self.logger.warning("⚠️  Validazione FAILED - Verificare i dati")
            self.stats.validation_results['integrity_check'] = 'FAILED'
            return False
    
    # ===== ORCHESTRAZIONE =====
    
    def run(self) -> bool:
        """Esegue l'intera migrazione"""
        try:
            # Fase 0: Prerequisiti
            if not self.validate_prerequisites():
                self.logger.error("❌ Validazione prerequisiti fallita")
                return False
            
            # Backup
            if not self.dry_run:
                backup_path = self.create_backup()
                if backup_path:
                    self.logger.info(f"💾 Backup salvato: {backup_path}")
            
            # Fase 1: Categorie
            if not self.migrate_categories():
                self.logger.error("❌ Migrazione categorie fallita")
                return False
            
            # Fase 2: Wallet
            if not self.migrate_wallets():
                self.logger.error("❌ Migrazione wallet fallita")
                return False
            
            # Fase 3: Movimenti
            if not self.migrate_movements():
                self.logger.error("❌ Migrazione movimenti fallita")
                return False
            
            # Fase 4: Validazione
            validation_ok = self.validate_migration()
            
            # Finalizza stats
            self.stats.finalize()
            
            return validation_ok
            
        except Exception as e:
            self.logger.error(f"❌ Errore durante migrazione: {e}", exc_info=True)
            if not self.dry_run:
                self.new_session.rollback()
            return False


# ===== MAIN =====
def main():
    """Entry point dello script"""
    parser = argparse.ArgumentParser(
        description='Migrazione Database Legacy -> PySpendless3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Dry-run per vedere cosa accadrà
  python -m pyspendless.migrations.migrate_legacy --legacy-db data/spendless-legacy.db --mapping my_mapping.json --dry-run
  
  # Esecuzione reale
  python -m pyspendless.migrations.migrate_legacy --legacy-db data/spendless-legacy.db --mapping my_mapping.json
  
  # Con logging dettagliato
  python -m pyspendless.migrations.migrate_legacy --legacy-db data/spendless-legacy.db --mapping my_mapping.json --verbose --log-file migration.log
        """
    )
    
    parser.add_argument('--legacy-db', required=True, help='Path al database legacy (es. data/spendless-legacy.db)')
    parser.add_argument('--mapping', required=True, help='Path al file JSON con il mapping user/account')
    parser.add_argument('--dry-run', action='store_true', help='Esegue senza commit (test)')
    parser.add_argument('--batch-size', type=int, default=500, help='Numero movimenti per batch (default: 500)')
    parser.add_argument('--log-file', help='File di log dettagliato')
    parser.add_argument('--verbose', action='store_true', help='Output dettagliato')
    parser.add_argument('--report', help='Path per salvare il report JSON finale')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_file, args.verbose)
    
    logger.info("=" * 60)
    logger.info("🚀 PySpendless3 - Migrazione Database Legacy")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("⚠️  DRY-RUN MODE - Nessun dato sarà modificato")
    
    # Carica mapping
    try:
        with open(args.mapping, 'r') as f:
            mapping = json.load(f)
        logger.info(f"✅ Mapping caricato da: {args.mapping}")
    except Exception as e:
        logger.error(f"❌ Errore caricamento mapping: {e}")
        return 1
    
    # Esegui migrazione
    try:
        with LegacyMigrator(
            legacy_db_path=args.legacy_db,
            mapping=mapping,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            logger=logger
        ) as migrator:
            success = migrator.run()
            
            # Report finale
            logger.info("\n" + "=" * 60)
            logger.info("📊 REPORT FINALE")
            logger.info("=" * 60)
            
            report = migrator.stats.to_dict()
            logger.info(json.dumps(report, indent=2))
            
            # Salva report su file se richiesto
            if args.report:
                with open(args.report, 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"💾 Report salvato in: {args.report}")
            
            if success:
                logger.info("\n✅ Migrazione completata con successo!")
                return 0
            else:
                logger.error("\n❌ Migrazione completata con errori")
                return 1
                
    except Exception as e:
        logger.error(f"❌ Errore fatale: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
