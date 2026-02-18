#!/usr/bin/env python3
"""
Test script per verificare l'implementazione del Task 1.3
Simula la creazione di un utente dopo OAuth login
"""

import sys
import os

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, os.path.dirname(__file__))

from conf import get_db_session
from repository import UserRepository, UnauthorizedError

def test_oauth_user_creation():
    """
    Test della funzione create_user_from_oauth
    """
    print("=" * 60)
    print("TEST: Creazione utente da OAuth Google")
    print("=" * 60)
    
    # Simula i dati che arrivano da Google OAuth
    user_info_whitelisted = {
        'sub': 'google-test-id-123456',
        'email': 'tabuto83@gmail.com',  # Email in whitelist
        'name': 'Test User'
    }
    
    user_info_not_whitelisted = {
        'sub': 'google-test-id-999999',
        'email': 'notauthorized@example.com',  # Email NON in whitelist
        'name': 'Unauthorized User'
    }
    
    db = get_db_session()
    user_repo = UserRepository(db)
    
    # Test 1: Email in whitelist
    print("\n✓ Test 1: Email in whitelist")
    print(f"   Email: {user_info_whitelisted['email']}")
    
    try:
        user = user_repo.create_user_from_oauth(user_info_whitelisted)
        print(f"   ✓ Utente creato con successo!")
        print(f"     - ID: {user.id}")
        print(f"     - Public UID: {user.public_uid}")
        print(f"     - Email: {user.email}")
        print(f"     - Nome: {user.name}")
        print(f"     - Account ID: {user.account_id}")
        print(f"     - Ruolo: {user.role}")
        
        # Verifica che le categorie siano state create
        from repository import CategoryRepository
        cat_repo = CategoryRepository(db)
        categories = cat_repo.get_categories_for_account(user.account_id)
        print(f"     - Categorie create: {len(categories)}")
        
        # Mostra alcune categorie
        if categories:
            print(f"       Esempi:")
            for cat in categories[:5]:
                print(f"         • {cat.name} ({cat.type})")
            if len(categories) > 5:
                print(f"         ... e altre {len(categories) - 5} categorie")
        
    except UnauthorizedError as e:
        print(f"   ✗ ERRORE: {e}")
    except Exception as e:
        print(f"   ✗ ERRORE IMPREVISTO: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Email NON in whitelist
    print("\n✓ Test 2: Email NON in whitelist (deve fallire)")
    print(f"   Email: {user_info_not_whitelisted['email']}")
    
    try:
        user = user_repo.create_user_from_oauth(user_info_not_whitelisted)
        print(f"   ✗ ERRORE: L'utente non avrebbe dovuto essere creato!")
    except UnauthorizedError as e:
        print(f"   ✓ Correttamente bloccato: {e}")
    except Exception as e:
        print(f"   ✗ ERRORE IMPREVISTO: {e}")
    
    # Test 3: Utente già esistente
    print("\n✓ Test 3: Login di utente già esistente")
    print(f"   Email: {user_info_whitelisted['email']}")
    
    try:
        user = user_repo.create_user_from_oauth(user_info_whitelisted)
        print(f"   ✓ Utente esistente recuperato correttamente!")
        print(f"     - ID: {user.id}")
        print(f"     - Email: {user.email}")
        
        # Verifica che non ci siano duplicati di account
        from repository import CategoryRepository
        cat_repo = CategoryRepository(db)
        categories = cat_repo.get_categories_for_account(user.account_id)
        print(f"     - Categorie nell'account: {len(categories)}")
        print(f"       (non dovrebbero essere duplicate)")
        
    except Exception as e:
        print(f"   ✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
    
    db.close()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETATI")
    print("=" * 60)

if __name__ == '__main__':
    test_oauth_user_creation()
