#!/usr/bin/env python3
"""
Script di migrazione per importare spese da CSV.

Utilizzo:
    python migrations/import_spese_csv.py

File richiesti:
    - data/SPESE_2025-SPESE.csv (file sorgente)
    - data/user_mapping.csv (mapping utenti)
"""

import csv
import sys
import uuid
from datetime import datetime
from pathlib import Path
from decimal import Decimal

# Aggiungere il path per importare i moduli pyspendless
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspendless.models import Movement, Category, Wallet, User, Account
from pyspendless.conf import get_db_session


def parse_amount(value: str) -> Decimal:
    """Parse amount supporting both comma and dot as decimal separator."""
    if not value or not value.strip():
        raise ValueError("Empty amount value")
    
    # Remove spaces
    value = value.strip()
    
    # Replace comma with dot for decimal separator
    value = value.replace(',', '.')
    
    try:
        return Decimal(value)
    except Exception:
        raise ValueError(f"Invalid amount format: {value}")


def parse_date(date_str: str) -> str:
    """Parse date from DD/MM/YYYY to YYYY-MM-DD."""
    if not date_str or not date_str.strip():
        raise ValueError("Empty date value")
    
    try:
        # Parse DD/MM/YYYY
        dt = datetime.strptime(date_str.strip(), '%d/%m/%Y')
        # Return in YYYY-MM-DD format
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str} (expected DD/MM/YYYY)")


def find_or_create_category(db, category_name: str, categories_map: dict, account_id: int, created_categories: set, category_type: str = 'expense') -> int:
    """Find category ID by name (case-insensitive) or create if not exists.
    
    Args:
        db: Database session
        category_name: Name of the category
        categories_map: Current map of category names to IDs
        account_id: Account ID to associate new categories with
        created_categories: Set to track newly created categories
        category_type: Type of category ('expense' or 'income'), defaults to 'expense'
        
    Returns:
        int: Category ID
    """
    category_lower = category_name.strip().lower()
    
    # Search existing categories (case-insensitive)
    for cat_name, cat_id in categories_map.items():
        if cat_name.lower() == category_lower:
            return cat_id
    
    # Category doesn't exist, create it
    new_category = Category(
        name=category_name.strip(),
        account_id=account_id,
        type=category_type,
        template_id=None
    )
    
    db.add(new_category)
    db.flush()  # Get the ID without committing
    
    # Update the map for future lookups
    categories_map[new_category.name] = new_category.id
    created_categories.add(category_name.strip())
    
    print(f"  → Creata categoria: {category_name.strip()} (ID: {new_category.id})")
    
    return new_category.id


def load_user_mapping(csv_path: str) -> dict:
    """Load user name to user_id and account_id mapping from CSV.
    
    Returns:
        dict: {user_name: {'user_id': int, 'account_id': int}}
    """
    user_map = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            user_name = row['user_name'].strip()
            user_id = int(row['user_id'])
            account_id = int(row['account_id'])
            
            user_map[user_name] = {
                'user_id': user_id,
                'account_id': account_id
            }
    
    return user_map


def load_categories_map(db) -> dict:
    """Load categories from DB into a name->id map."""
    categories = db.query(Category).all()
    
    # Create map: category_name -> category_id
    categories_map = {cat.name: cat.id for cat in categories}
    
    return categories_map


def get_or_create_wallet(db, wallet_name: str, account_id: int, created_wallets: set) -> int:
    """Get existing wallet or create new one.
    
    Args:
        db: Database session
        wallet_name: Name of the wallet (e.g., "FinecoFra")
        account_id: Account ID to associate the wallet with
        created_wallets: Set to track newly created wallets
        
    Returns:
        int: Wallet ID
    """
    # Search for existing wallet by name (case-insensitive) and account_id
    wallets = db.query(Wallet).filter_by(account_id=account_id).all()
    
    wallet_name_lower = wallet_name.strip().lower()
    
    for wallet in wallets:
        if wallet.name.lower() == wallet_name_lower:
            return wallet.id
    
    # Wallet doesn't exist, create it
    # Use wallet name as code (simple, no suffixes)
    wallet_code = wallet_name
    
    new_wallet = Wallet(
        code=wallet_code,
        name=wallet_name,
        currency='EUR',
        account_id=account_id,
        created_at=datetime.utcnow()
    )
    
    db.add(new_wallet)
    db.flush()  # Get the ID without committing
    
    created_wallets.add(wallet_name)
    print(f"  → Creato wallet: {wallet_name} (ID: {new_wallet.id}) per account {account_id}")
    
    return new_wallet.id


def import_expenses(csv_path: str, user_mapping_path: str):
    """Main import function."""
    
    print("=== Importazione Spese da CSV ===\n")
    
    db = get_db_session()
    
    try:
        # Load mappings
        print("Caricamento mappings...")
        user_map = load_user_mapping(user_mapping_path)
        categories_map = load_categories_map(db)
        
        print(f"- {len(user_map)} utenti mappati")
        print(f"- {len(categories_map)} categorie trovate\n")
        
        # Track created wallets and categories
        created_wallets = set()
        created_categories = set()
        
        # Statistics
        total_rows = 0
        imported = 0
        skipped = 0
        errors = []
        
        # Read and import CSV
        print("Importazione in corso...")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Detect if CSV has EXPENSE or INCOME column
            fieldnames = reader.fieldnames
            has_expense = 'EXPENSE' in fieldnames
            has_income = 'INCOME' in fieldnames
            
            if not has_expense and not has_income:
                raise ValueError("CSV deve contenere la colonna EXPENSE o INCOME")
            
            if has_expense and has_income:
                raise ValueError("CSV non può contenere sia EXPENSE che INCOME")
            
            is_income_file = has_income
            amount_column = 'INCOME' if is_income_file else 'EXPENSE'
            
            print(f"Tipo di file rilevato: {'INCOME' if is_income_file else 'EXPENSE'}\n")
            
            for row_num, row in enumerate(reader, start=2):  # start=2 perché riga 1 è header
                total_rows += 1
                
                try:
                    # Parse fields
                    date_str = parse_date(row['Data'])
                    amount = parse_amount(row[amount_column])
                    user_name = row['User'].strip()
                    user_info = user_map.get(user_name)
                    
                    if not user_info:
                        raise ValueError(f"User not found in mapping: {user_name}")
                    
                    user_id = user_info['user_id']
                    account_id = user_info['account_id']
                    
                    # Find or create category
                    # For INCOME files, create categories as 'income' type
                    cat_type = 'income' if is_income_file else 'expense'
                    category_id = find_or_create_category(db, row['Category'], categories_map, account_id, created_categories, cat_type)
                    
                    # Get or create wallet
                    wallet_name = row['Wallet'].strip()
                    wallet_id = get_or_create_wallet(db, wallet_name, account_id, created_wallets)
                    
                    # Parse date for year/month extraction
                    move_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Generate unique ID for movement
                    movement_id = str(uuid.uuid4())
                    
                    # Create movement record
                    # Note: Movement table has legacy fields (category, wallet, user as strings)
                    # and new FK fields (category_id, wallet_id, user_id)
                    # We populate both for compatibility
                    
                    # Get category name for legacy field
                    category_name = None
                    for cat_name, cat_id in categories_map.items():
                        if cat_id == category_id:
                            category_name = cat_name
                            break
                    
                    # Get wallet code for legacy field
                    wallet_obj = db.query(Wallet).get(wallet_id)
                    wallet_code = wallet_obj.code if wallet_obj else str(wallet_id)
                    
                    # Get user email for legacy field
                    user_obj = db.query(User).get(user_id)
                    user_email = user_obj.email if user_obj else str(user_id)
                    
                    movement = Movement(
                        id=movement_id,
                        move_date=move_date_obj,
                        move_year=move_date_obj.year,
                        move_month=move_date_obj.month,
                        category=category_name or str(category_id),  # Legacy field
                        wallet=wallet_code,  # Legacy field
                        income=amount if is_income_file else None,
                        expense=None if is_income_file else amount,
                        note=row['NOTE'].strip() if row['NOTE'] else '',
                        user=user_email,  # Legacy field
                        account_id=account_id,
                        # New FK fields
                        user_id=str(user_id),
                        category_id=category_id,
                        wallet_id=wallet_id
                    )
                    
                    db.add(movement)
                    imported += 1
                    
                    # Commit ogni 100 righe
                    if imported % 100 == 0:
                        db.commit()
                        print(f"  Importate {imported} righe...")
                
                except Exception as e:
                    skipped += 1
                    error_msg = f"Riga {row_num}: {str(e)} - Dati: {row}"
                    errors.append(error_msg)
                    print(f"  ERRORE riga {row_num}: {str(e)}")
        
        # Final commit
        db.commit()
        
        # Print statistics
        print(f"\n=== Importazione completata ===")
        print(f"Righe totali: {total_rows}")
        print(f"Righe importate: {imported}")
        print(f"Righe saltate: {skipped}")
        print(f"Wallet creati: {len(created_wallets)}")
        print(f"Categorie create: {len(created_categories)}")
        
        if created_wallets:
            print(f"\nWallet creati:")
            for wallet_name in sorted(created_wallets):
                print(f"  - {wallet_name}")
        
        if created_categories:
            print(f"\nCategorie create:")
            for category_name in sorted(created_categories):
                print(f"  - {category_name}")
        
        # Save errors to log
        if errors:
            error_log_path = Path(__file__).parent / 'migration_errors.log'
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(errors))
            print(f"\nErrori salvati in: {error_log_path}")
    
    except Exception as e:
        db.rollback()
        print(f"\nERRORE FATALE: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        db.close()


if __name__ == '__main__':
    # Load environment
    from pyspendless.conf import load_env
    load_env()
    
    import sys
    
    # Check for command line arguments
    if len(sys.argv) >= 3:
        csv_path = Path(sys.argv[1])
        user_mapping_path = Path(sys.argv[2])
    else:
        # Default paths
        csv_path = Path(__file__).parent.parent / 'data' / 'SPESE_2025-SPESE.csv'
        user_mapping_path = Path(__file__).parent.parent / 'data' / 'user_mapping.csv'
    
    if not csv_path.exists():
        print(f"ERRORE: File non trovato: {csv_path}")
        sys.exit(1)
    
    if not user_mapping_path.exists():
        print(f"ERRORE: File mapping utenti non trovato: {user_mapping_path}")
        print(f"Creare il file con struttura:")
        print("user_name,user_id,account_id")
        print("Francesco di Dio,1,1")
        print("Beatrice Santucci,2,2")
        sys.exit(1)
    
    import_expenses(str(csv_path), str(user_mapping_path))
    print("\n✓ Importazione completata con successo!")
