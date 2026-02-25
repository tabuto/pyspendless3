# Task 6.0: Importazione Dati da CSV Spese

Questo task riguarda l'implementazione di uno script di migrazione per importare le spese storiche da un file CSV con formato specifico.

## Obiettivo
Creare uno script nella directory `/migrations` per importare i dati dal file `data/SPESE_2025-SPESE.csv` nel database, utilizzando un file di mappa per associare gli utenti del vecchio sistema agli user_id del nuovo sistema.

## Struttura File CSV Sorgente
Il file `SPESE_2025-SPESE.csv` ha la seguente struttura:
```
Informazioni cronologiche,Category,Data,EXPENSE,Wallet,NOTE,User,Ripartizione
12/02/2026 19.07.17,Health,12/02/2026,120,FinecoFra,Montatura con lenti adele,Francesco di Dio,Famiglia
```

### Campi:
- **Informazioni cronologiche**: Timestamp creazione record (da ignorare o usare per audit)
- **Category**: Nome categoria (es. "Health", "Food And Drink", "Trasportation")
- **Data**: Data della spesa nel formato `DD/MM/YYYY`
- **EXPENSE**: Importo della spesa (può usare punto o virgola come separatore decimale)
- **Wallet**: Nome del wallet/account (es. "FinecoFra", "FinecoBea")
- **NOTE**: Descrizione/note della spesa
- **User**: Nome completo dell'utente (es. "Francesco di Dio", "Beatrice Santucci")
- **Ripartizione**: Campo da ignorare nell'importazione

## Requisiti

### 1. File di Mapping Utenti
- [ ] Creare un file CSV di mapping `data/user_mapping.csv` con struttura:
  ```csv
  user_name,user_id,account_id
  Francesco di Dio,1,1
  Beatrice Santucci,2,2
  ```
- [ ] Lo script deve caricare questo mapping all'inizio per tradurre i nomi utente in user_id e account_id
- [ ] Il campo `account_id` identifica l'account principale dell'utente a cui associare i wallet

### 2. Logica di Parsing Importi
- [ ] Implementare una funzione robusta `parse_amount(value)` che:
  - Accetta importi con punto come separatore decimale (es. `120.50`)
  - Accetta importi con virgola come separatore decimale (es. `120,50`)
  - Gestisce importi interi (es. `120`)
  - Rimuove eventuali spazi
  - Solleva eccezione chiara se il valore non è parsabile
  
  ```python
  def parse_amount(value: str) -> float:
      """Parse amount supporting both comma and dot as decimal separator."""
      if not value or not value.strip():
          raise ValueError("Empty amount value")
      
      # Remove spaces
      value = value.strip()
      
      # Replace comma with dot for decimal separator
      value = value.replace(',', '.')
      
      try:
          return float(value)
      except ValueError:
          raise ValueError(f"Invalid amount format: {value}")
  ```

### 3. Matching Categorie (Case-Insensitive)
- [ ] Il match delle categorie deve essere **case-insensitive**
- [ ] Implementare una funzione `find_category_id(category_name, categories_map)` che:
  - Confronta il nome categoria in modo case-insensitive
  - Restituisce l'ID della categoria se trovata
  - Solleva eccezione o logga warning se la categoria non esiste
  
  ```python
  def find_category_id(category_name: str, categories_map: dict) -> int:
      """Find category ID by name (case-insensitive)."""
      category_lower = category_name.strip().lower()
      
      for cat_name, cat_id in categories_map.items():
          if cat_name.lower() == category_lower:
              return cat_id
      
      raise ValueError(f"Category not found: {category_name}")
  ```

### 4. Mapping Wallets/Accounts
- [ ] Creare una mappa wallet_name -> account_id leggendo dalla tabella `Account`
- [ ] Se un wallet con quel nome non esiste:
  - Crearlo automaticamente (opzione consigliata)

### 5. Script di Migrazione
- [ ] Creare il file `/migrations/import_spese_csv.py`
- [ ] Lo script deve:
  1. Caricare il file di mapping utenti
  2. Caricare le categorie dal DB e creare una mappa nome->id
  3. Leggere il CSV riga per riga (saltando l'header)
  4. Per ogni riga:
     - Parsare la data (formato DD/MM/YYYY -> YYYY-MM-DD)
     - Parsare l'importo (gestendo punto e virgola)
     - Trovare user_id e account_id dalla mappa utenti
     - Trovare category_id (case-insensitive)
     - Trovare o creare wallet basandosi su nome e account_id
     - Ignorare il campo "Ripartizione"
     - Inserire record nella tabella `Expense`
  5. Gestire errori e logging:
     - Loggare ogni errore con il numero di riga
     - Contare righe processate/saltate/errori
     - Tracciare i wallet creati
     - Report finale con statistiche

### 6. Gestione Errori
- [ ] Lo script deve essere robusto e continuare l'importazione anche se alcune righe falliscono
- [ ] Implementare try-catch per ogni riga
- [ ] Salvare in un file `migration_errors.log` le righe che hanno dato errore
- [ ] Al termine mostrare statistiche:
  ```
  Importazione completata:
  - Righe totali: 1512
  - Righe importate: 1450
  - Righe saltate: 62
  - Errori: vedere migration_errors.log
  ```

## Struttura Script

```python
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
from datetime import datetime
from pathlib import Path

# Aggiungere il path per importare i moduli pyspendless
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspendless.models import db, Expense, Category, Account, User
from pyspendless.app import create_app


def parse_amount(value: str) -> float:
    """Parse amount supporting both comma and dot as decimal separator."""
    # ... implementazione ...


def parse_date(date_str: str) -> str:
    """Parse date from DD/MM/YYYY to YYYY-MM-DD."""
    # ... implementazione ...


def find_category_id(category_name: str, categories_map: dict) -> int:
    """Find category ID by name (case-insensitive)."""
    # ... implementazione ...


def load_user_mapping(csv_path: str) -> dict:
    """Load user name to user_id and account_id mapping from CSV.
    
    Returns:
        dict: {user_name: {'user_id': int, 'account_id': int}}
    """
    # ... implementazione ...


def load_categories_map() -> dict:
    """Load categories from DB into a name->id map."""
    # ... implementazione ...


def get_or_create_wallet(wallet_name: str, account_id: int) -> int:
    """Get existing wallet or create new one.
    
    Args:
        wallet_name: Name of the wallet (e.g., "FinecoFra")
        account_id: Account ID to associate the wallet with
        
    Returns:
        int: Wallet ID
    """
    # ... implementazione ...


def import_expenses(csv_path: str, user_mapping_path: str):
    """Main import function."""
    
    print("=== Importazione Spese da CSV ===\n")
    
    # Load mappings
    print("Caricamento mappings...")
    user_map = load_user_mapping(user_mapping_path)
    categories_map = load_categories_map()
    
    print(f"- {len(user_map)} utenti mappati")
    print(f"- {len(categories_map)} categorie trovate\n")
    
    # Track created wallets
    created_wallets = set()
    
    # Statistics
    total_rows = 0
    imported = 0
    skipped = 0
    errors = []
    
    # Read and import CSV
    print("Importazione in corso...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # start=2 perché riga 1 è header
            total_rows += 1
            
            try:
                # Parse fields
                date_str = parse_date(row['Data'])
                amount = parse_amount(row['EXPENSE'])
                category_id = find_category_id(row['Category'], categories_map)
                user_name = row['User'].strip()
                user_info = user_map.get(user_name)
                
                if not user_info:
                    raise ValueError(f"User not found in mapping: {user_name}")
                
                user_id = user_info['user_id']
                account_id = user_info['account_id']
                
                # Get or create wallet
                wallet_name = row['Wallet'].strip()
                wallet_id = get_or_create_wallet(wallet_name, account_id)
                
                # Track if wallet was created
                if wallet_name not in created_wallets:
                    # Check if it was just created
                    created_wallets.add(wallet_name)
                
                # Create expense record
                expense = Expense(
                    amount=amount,
                    date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                    description=row['NOTE'].strip(),
                    category_id=category_id,
                    wallet_id=wallet_id,
                    user_id=user_id
                )
                
                db.session.add(expense)
                imported += 1
                
                # Commit ogni 100 righe
                if imported % 100 == 0:
                    db.session.commit()
                    print(f"  Importate {imported} righe...")
                
            except Exception as e:
                skipped += 1
                error_msg = f"Riga {row_num}: {str(e)} - Dati: {row}"
                errors.append(error_msg)
                print(f"  ERRORE riga {row_num}: {str(e)}")
    
    # Final commit
    db.session.commit()
    
    # Print statistics
    print(f"\n=== Importazione completata ===")
    print(f"Righe totali: {total_rows}")
    print(f"Righe importate: {imported}")
    print(f"Righe saltate: {skipped}")
    print(f"Wallet creati: {len(created_wallets)}")
    
    # Save errors to log
    if errors:
        error_log_path = Path(__file__).parent / 'migration_errors.log'
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(errors))
        print(f"\nErrori salvati in: {error_log_path}")
    

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
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
```

## Pre-requisiti

### 1. Categorie
- [ ] Assicurarsi che tutte le categorie presenti nel CSV esistano nel database
- [ ] Lista categorie trovate nel CSV di esempio:
  - Health
  - Travels
  - Food And Drink
  - Trasportation
  - Baby
  - Market
  - Household
  - Accessori
  - Hobby
  - Clothing
  - Present
  - Sport

### 2. File di Mapping
- [ ] Creare `data/user_mapping.csv` prima di eseguire lo script
- [ ] Verificare che tutti gli utenti presenti nel CSV siano mappati
- [ ] Verificare che gli account_id specificati esistano nel database

### 3. Wallets
- [ ] I wallet vengono creati automaticamente se non esistono
- [ ] La ricerca del wallet è basata su: nome wallet + account_id
- [ ] Decidere i valori di default per i wallet creati automaticamente:
  - [ ] Currency (es. "EUR")
  - [ ] Initial balance (es. 0.0)
  - [ ] Tipo wallet (se applicabile)
  - [ ] Altri campi opzionali

## Esecuzione

```bash
# 1. Creare il file di mapping utenti
cat > data/user_mapping.csv << EOF
user_name,user_id,account_id
Francesco di Dio,1,1
Beatrice Santucci,2,2
EOF

# 2. Eseguire lo script
python migrations/import_spese_csv.py

# 3. Verificare i risultati
# Controllare il file migration_errors.log se presente
# Verificare nel database che i record siano stati importati
```

## Test e Validazione
- [ ] Testare lo script prima su un subset del CSV (prime 10 righe)
- [ ] Verificare che le date siano importate correttamente
- [ ] Verificare che gli importi siano corretti (somma totale)
- [ ] Controllare che le categorie siano assegnate correttamente
- [ ] Verificare che non ci siano duplicati

## Note Tecniche
- Ignorare completamente il campo "Ripartizione" come richiesto
- Il campo "Informazioni cronologiche" può essere usato per tracciare quando il record originale è stato creato, ma non è essenziale
- Gestire correttamente l'encoding UTF-8 per i caratteri speciali nelle note
- Considerare l'aggiunta di un campo `imported_from` nella tabella Expense per tracciare le spese importate
- I wallet vengono cercati per nome e account_id: questo significa che due utenti diversi possono avere wallet con lo stesso nome
- La creazione automatica dei wallet garantisce che l'importazione non fallisca per wallet mancanti
- È importante loggare la creazione dei wallet per permettere una revisione post-importazione

## Criteri di Accettazione
- Lo script importa correttamente tutte le righe valide dal CSV
- Gli importi sono parsati correttamente sia con punto che con virgola
- Le categorie sono matchate in modo case-insensitive
- Il campo Ripartizione è ignorato
- Gli errori sono loggati e non bloccano l'importazione
- Viene prodotto un report finale con statistiche
- I wallet vengono creati automaticamente se non esistono per l'account_id specificato
- Ogni spesa è associata al wallet corretto basandosi sul nome e sull'account_id dell'utente
- Il report finale include il numero di wallet creati durante l'importazione
