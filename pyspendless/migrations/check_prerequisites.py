#!/usr/bin/env python3
"""
Helper script per verificare i prerequisiti prima della migrazione
"""

import sqlite3
import sys
import json
from pathlib import Path

def check_new_db(db_path: str):
    """Verifica il nuovo database"""
    print("🔍 Controllo nuovo database...")
    
    if not Path(db_path).exists():
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Account
    print("\n📋 Account disponibili:")
    cursor.execute("SELECT id, name, created_at FROM Account")
    accounts = cursor.fetchall()
    for acc in accounts:
        print(f"  - ID {acc['id']}: {acc['name']} (created: {acc['created_at']})")
    
    # Users
    print("\n👥 Utenti disponibili:")
    cursor.execute("SELECT id, email, name, account_id, role FROM User ORDER BY account_id, id")
    users = cursor.fetchall()
    for user in users:
        print(f"  - ID {user['id']}: {user['name']} ({user['email']}) - Account {user['account_id']} - Role: {user['role']}")
    
    # Movimenti esistenti
    print("\n📊 Movimenti esistenti per account:")
    cursor.execute("SELECT account_id, COUNT(*) as cnt FROM Movement GROUP BY account_id")
    movements = cursor.fetchall()
    if movements:
        for mov in movements:
            print(f"  - Account {mov['account_id']}: {mov['cnt']} movimenti")
    else:
        print("  - Nessun movimento presente")
    
    conn.close()
    return True


def check_legacy_db(db_path: str):
    """Verifica il database legacy"""
    print("\n🔍 Controllo database legacy...")
    
    if not Path(db_path).exists():
        print(f"❌ Database legacy non trovato: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Movimenti totali
    cursor.execute("SELECT COUNT(*) as cnt FROM MOVEMENTS")
    total = cursor.fetchone()['cnt']
    print(f"📊 Movimenti totali: {total}")
    
    # Utenti legacy
    cursor.execute("SELECT DISTINCT user FROM MOVEMENTS ORDER BY user")
    users = [row['user'] for row in cursor.fetchall()]
    print(f"\n👥 Utenti legacy ({len(users)}):")
    for user in users:
        cursor.execute("SELECT COUNT(*) as cnt FROM MOVEMENTS WHERE user = ?", (user,))
        count = cursor.fetchone()['cnt']
        print(f"  - {user}: {count} movimenti")
    
    # Wallet legacy
    cursor.execute("SELECT DISTINCT wallet FROM MOVEMENTS ORDER BY wallet")
    wallets = [row['wallet'] for row in cursor.fetchall()]
    print(f"\n💰 Wallet legacy ({len(wallets)}):")
    for wallet in wallets:
        print(f"  - {wallet}")
    
    # Categorie legacy
    cursor.execute("SELECT DISTINCT category FROM MOVEMENTS ORDER BY category")
    categories = [row['category'] for row in cursor.fetchall()]
    print(f"\n📂 Categorie legacy ({len(categories)}):")
    for cat in categories[:20]:  # Primi 20
        print(f"  - {cat}")
    if len(categories) > 20:
        print(f"  ... e altre {len(categories) - 20} categorie")
    
    # Range date
    cursor.execute("SELECT MIN(move_year) as min_year, MAX(move_year) as max_year FROM MOVEMENTS")
    years = cursor.fetchone()
    print(f"\n📅 Range anni: {years['min_year']} - {years['max_year']}")
    
    conn.close()
    return True


def generate_mapping_template(legacy_db_path: str, output_path: str):
    """Genera un template di mapping basato sui dati legacy"""
    print(f"\n📝 Generazione template mapping...")
    
    conn = sqlite3.connect(legacy_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT user FROM MOVEMENTS ORDER BY user")
    users = [row['user'] for row in cursor.fetchall()]
    
    mapping = {
        "account_id": None,
        "user_mapping": {}
    }
    
    for user in users:
        mapping["user_mapping"][user] = {
            "user_id": None,
            "email": f"{user.lower().replace(' ', '')}@example.com"
        }
    
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Template salvato in: {output_path}")
    print("\n⚠️  IMPORTANTE: Modifica il file e inserisci gli ID corretti prima di usarlo!")
    
    conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Verifica prerequisiti migrazione')
    parser.add_argument('--new-db', default='data/pyspendless3.db', help='Path nuovo database')
    parser.add_argument('--legacy-db', default='data/spendless-legacy.db', help='Path database legacy')
    parser.add_argument('--generate-mapping', help='Genera template mapping in questo file')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔧 PySpendless3 - Verifica Prerequisiti Migrazione")
    print("=" * 60)
    
    # Check new DB
    if not check_new_db(args.new_db):
        sys.exit(1)
    
    # Check legacy DB
    if not check_legacy_db(args.legacy_db):
        sys.exit(1)
    
    # Generate mapping template
    if args.generate_mapping:
        generate_mapping_template(args.legacy_db, args.generate_mapping)
    
    print("\n" + "=" * 60)
    print("✅ Verifica completata!")
    print("=" * 60)
    
    print("\n📋 Prossimi passi:")
    if args.generate_mapping:
        print(f"1. Modifica {args.generate_mapping} con gli ID corretti")
    else:
        print("1. Genera il mapping: --generate-mapping my_mapping.json")
    print("2. Esegui dry-run: python -m pyspendless.migrations.migrate_legacy --dry-run ...")
    print("3. Esegui migrazione reale")
    print("\nConsulta pyspendless/migrations/QUICKSTART.md per dettagli")


if __name__ == '__main__':
    main()
