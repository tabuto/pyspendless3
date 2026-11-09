#!/usr/bin/env python3
"""
Backfill delle label dal testo delle note esistenti (task26-0).

Script eseguibile e importabile: il test lo importa come `from backfill_labels import backfill`.

Scansiona i movimenti di tutti gli account ordinati per (account_id, move_date, id),
estrae le label, e per ogni (account_id, name_norm) mancante crea la riga con la grafia
del movimento più vecchio (deterministico e ripetibile). La grafia è invariata per tutti
gli account.

Non riscrive le note. Idempotente: una seconda esecuzione crea 0 righe.

Uso da riga di comando: python migrations/backfill_labels.py
Uso dal test: from backfill_labels import backfill; backfill(db_session)
"""

import os
import sys
from datetime import datetime

# Support per import relativo da pyspendless/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pyspendless'))

try:
    from conf import get_db_session, get_db_engine
    from models import Base, Movement, Label, Account
    from labels import extract
except ImportError:
    # Fallback se eseguito da una directory diversa
    try:
        from pyspendless.conf import get_db_session, get_db_engine
        from pyspendless.models import Base, Movement, Label, Account
        from pyspendless.labels import extract
    except ImportError:
        print("Errore: impossibile importare i moduli di PySpendless")
        sys.exit(1)


def backfill(db):
    """Popola il registro Label dalle note esistenti.

    Estrae le label dai movimenti, per ogni (account_id, name_norm) mancante
    crea una riga con la grafia del movimento più vecchio.

    Args:
        db: Sessione SQLAlchemy.

    Returns:
        int: Numero di righe create.
    """
    # Recupera i movimenti ordinati per (account_id, move_date, id)
    movements = db.query(Movement).order_by(
        Movement.account_id, Movement.move_date, Movement.id
    ).all()

    # Traccia quale grafia è stata assegnata a ogni (account_id, name_norm)
    # per garantire che il primo movimento visto definisca la forma canonica
    seen = {}  # (account_id, name_norm) -> name (grafia)

    labels_to_create = []

    for mov in movements:
        if not mov.note:
            continue

        account_id = mov.account_id
        labels = extract(mov.note)  # Restituisce label in ordine di prima comparsa

        for name in labels:
            name_norm = name.lower()
            key = (account_id, name_norm)

            if key not in seen:
                # Prima occorrenza di questa label in questo account: assegna la grafia
                seen[key] = name
                # Controlla se la riga esiste già nel database
                existing = db.query(Label).filter_by(
                    account_id=account_id, name_norm=name_norm
                ).first()
                if not existing:
                    labels_to_create.append(
                        Label(
                            account_id=account_id,
                            name=name,
                            name_norm=name_norm,
                            created_at=datetime.utcnow()
                        )
                    )

    # Inserisce tutte le label in una sola transazione
    created = len(labels_to_create)
    if labels_to_create:
        db.add_all(labels_to_create)
        db.commit()

    return created


def main():
    """Punto di ingresso da riga di comando."""
    # Crea il motore e inizializza le tabelle
    engine = get_db_engine()
    Base.metadata.create_all(bind=engine)

    # Crea una sessione
    db = get_db_session()

    try:
        created = backfill(db)
        print(f"Backfill completato: {created} label create")
    except Exception as e:
        print(f"Errore durante il backfill: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
