#!/usr/bin/env python3
"""
Verifica locale del task22-0 (wallet preferito per singolo utente).

Non e' pytest (il progetto non lo usa ancora, vedi dev_mcp_check.py): e' uno
script di controllo riproducibile, con assert espliciti, che lavora SOLO su
database SQLite temporanei/in-memory creati al volo. Non tocca in nessun caso
il database configurato in .env.

Copre due cose distinte:
  1. La nuova logica applicativa (UserRepository.get/set/unset_preferred_wallet,
     WalletRepository senza piu' la riserva su order_index=0) sullo schema
     NUOVO (quello di models.py).
  2. Lo script di migrazione `sql/sqllite/NEXT_RELEASE/alter_user_add_preferred_wallet.sql`,
     eseguito su uno schema VECCHIO (pre-task22-0, costruito a mano con le
     stesse tabelle/colonne) per verificare che il backfill assegni a ogni
     utente il wallet che era preferito per il suo account.

Uso:
    pyspendless/.venv/bin/python -m pyspendless.test.test_task22_0
    (oppure, da dentro pyspendless/.venv/bin/python test/test_task22_0.py)
"""

import os
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Account, User, Wallet
from repository import UserRepository, WalletRepository


class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []

    def check(self, description, condition, detail=''):
        if condition:
            self.passed += 1
            print('  OK   {}'.format(description))
        else:
            self.failed += 1
            self.failures.append(description)
            print('  FAIL {}{}'.format(description, ' -> {}'.format(detail) if detail else ''))

    def section(self, title):
        print('\n== {} =='.format(title))

    def summary(self):
        print('\n{}\n{} controlli superati, {} falliti'.format('-' * 60, self.passed, self.failed))
        if self.failures:
            print('\nFalliti:')
            for failure in self.failures:
                print('  - {}'.format(failure))
        return 0 if self.failed == 0 else 1


def in_memory_session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_account_with_users_and_wallets(db, n_users=2, n_wallets=2):
    account = Account(name='Famiglia Test')
    db.add(account)
    db.flush()

    users = []
    for i in range(n_users):
        user = User(
            public_uid=str(uuid.uuid4()),
            google_id='google-{}'.format(uuid.uuid4()),
            email='utente{}-{}@example.com'.format(i, uuid.uuid4()),
            name='Utente {}'.format(i),
            account_id=account.id,
            role='member'
        )
        db.add(user)
        users.append(user)
    db.flush()

    wallet_repo = WalletRepository(db)
    wallets = [
        wallet_repo.create_wallet(code=str(uuid.uuid4())[:8], name='Wallet {}'.format(i),
                                   account_id=account.id)
        for i in range(n_wallets)
    ]
    return account, users, wallets


def check_user_repository(checker):
    checker.section('UserRepository.get/set/unset_preferred_wallet (schema nuovo)')

    db = in_memory_session()
    account, (user1, user2), (wallet_a, wallet_b) = make_account_with_users_and_wallets(db)
    other_account, (other_user,), (other_wallet,) = make_account_with_users_and_wallets(
        db, n_users=1, n_wallets=1
    )

    user_repo = UserRepository(db)

    checker.check('nessun preferito appena creato',
                  user_repo.get_preferred_wallet(user1.id) is None)

    set_result = user_repo.set_preferred_wallet(user1.id, wallet_a.id, account.id)
    checker.check('set_preferred_wallet ritorna il wallet',
                  set_result is not None and set_result.id == wallet_a.id)
    checker.check('get_preferred_wallet rilegge il wallet impostato',
                  user_repo.get_preferred_wallet(user1.id).id == wallet_a.id)

    checker.check("il preferito e' per utente, non per account (isolamento)",
                  user_repo.get_preferred_wallet(user2.id) is None)

    user_repo.set_preferred_wallet(user2.id, wallet_b.id, account.id)
    checker.check("user1 resta sul proprio preferito dopo la scelta di user2",
                  user_repo.get_preferred_wallet(user1.id).id == wallet_a.id)
    checker.check("user2 ha il proprio preferito, diverso da user1",
                  user_repo.get_preferred_wallet(user2.id).id == wallet_b.id)

    cross_account = user_repo.set_preferred_wallet(user1.id, other_wallet.id, account.id)
    checker.check('wallet di un altro account viene rifiutato',
                  cross_account is None)
    checker.check("il preferito di user1 non e' cambiato dal tentativo rifiutato",
                  user_repo.get_preferred_wallet(user1.id).id == wallet_a.id)

    wrong_unset = user_repo.unset_preferred_wallet(user1.id, wallet_b.id)
    checker.check('unset con wallet_id diverso dal preferito corrente non ha effetto',
                  wrong_unset is None and user_repo.get_preferred_wallet(user1.id) is not None)

    unset_result = user_repo.unset_preferred_wallet(user1.id, wallet_a.id)
    checker.check('unset_preferred_wallet ritorna il wallet rimosso',
                  unset_result is not None and unset_result.id == wallet_a.id)
    checker.check('dopo unset nessun preferito per user1',
                  user_repo.get_preferred_wallet(user1.id) is None)
    checker.check("user2 non e' stato toccato dall'unset di user1",
                  user_repo.get_preferred_wallet(user2.id).id == wallet_b.id)

    db.close()


def check_order_index_no_longer_reserved(checker):
    checker.section('order_index non piu riservato (WalletRepository)')

    db = in_memory_session()
    account, (user1,), _wallets = make_account_with_users_and_wallets(db, n_users=1, n_wallets=0)
    wallet_repo = WalletRepository(db)

    first = wallet_repo.create_wallet(code='w1', name='Primo', account_id=account.id)
    checker.check("il primo wallet creato parte da order_index 0 (non piu' riservato)",
                  first.order_index == 0, first.order_index)

    second = wallet_repo.create_wallet(code='w2', name='Secondo', account_id=account.id)
    checker.check('il secondo wallet prende order_index successivo',
                  second.order_index == 1, second.order_index)

    try:
        WalletRepository.validate_order_index(-1)
        checker.check('validate_order_index rifiuta i negativi', False)
    except ValueError:
        checker.check('validate_order_index rifiuta i negativi', True)

    checker.check('validate_order_index accetta 0 (prima era riservato)',
                  WalletRepository.validate_order_index(0) == 0)

    db.close()


def check_delete_wallet_clears_preference(checker):
    checker.section('delete_wallet libera preferred_wallet_id pendenti')

    db = in_memory_session()
    account, (user1, _user2), (wallet_a, _wallet_b) = make_account_with_users_and_wallets(db)
    user_repo = UserRepository(db)
    wallet_repo = WalletRepository(db)

    user_repo.set_preferred_wallet(user1.id, wallet_a.id, account.id)
    wallet_repo.delete_wallet(wallet_a.id)

    db.refresh(user1)
    checker.check('preferred_wallet_id azzerato dopo la cancellazione del wallet',
                  user1.preferred_wallet_id is None, user1.preferred_wallet_id)
    checker.check('get_preferred_wallet torna None, non un errore',
                  user_repo.get_preferred_wallet(user1.id) is None)

    db.close()


def check_migration_backfill(checker):
    checker.section('Backfill SQL (schema pre-task22-0 -> post-task22-0)')

    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'sql', 'sqllite', 'NEXT_RELEASE', 'alter_user_add_preferred_wallet.sql'
    )
    with open(migration_path, encoding='utf-8') as f:
        migration_sql = f.read()

    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        # Schema "vecchio": User senza preferred_wallet_id, Wallet con order_index
        # (stato subito prima del task22-0).
        conn.execute(text("""
            CREATE TABLE Account (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE User (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                account_id INTEGER NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE Wallet (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0
            )
        """))

        # Account 1: due utenti, il wallet "Contanti" era il preferito (order_index=0).
        conn.execute(text("INSERT INTO Account (id, name) VALUES (1, 'Famiglia A')"))
        conn.execute(text("INSERT INTO User (id, email, account_id) VALUES (1, 'a1@example.com', 1)"))
        conn.execute(text("INSERT INTO User (id, email, account_id) VALUES (2, 'a2@example.com', 1)"))
        conn.execute(text("INSERT INTO Wallet (id, name, account_id, order_index) VALUES (1, 'Contanti', 1, 0)"))
        conn.execute(text("INSERT INTO Wallet (id, name, account_id, order_index) VALUES (2, 'Carta', 1, 1)"))

        # Account 2: un utente, nessun wallet preferito (nessuno a order_index 0).
        conn.execute(text("INSERT INTO Account (id, name) VALUES (2, 'Famiglia B')"))
        conn.execute(text("INSERT INTO User (id, email, account_id) VALUES (3, 'b1@example.com', 2)"))
        conn.execute(text("INSERT INTO Wallet (id, name, account_id, order_index) VALUES (3, 'Risparmio', 2, 1)"))

        for statement in migration_sql.split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))

        rows = conn.execute(text(
            "SELECT id, preferred_wallet_id FROM User ORDER BY id"
        )).fetchall()

    by_id = {row[0]: row[1] for row in rows}
    checker.check("utente 1 (account 1) eredita il wallet 'Contanti' (id 1)",
                  by_id.get(1) == 1, by_id)
    checker.check("utente 2 (account 1, stesso account) eredita LO STESSO wallet preferito",
                  by_id.get(2) == 1, by_id)
    checker.check('utente 3 (account 2, nessun preferito storico) resta senza preferito',
                  by_id.get(3) is None, by_id)


def main():
    checker = Checker()
    check_user_repository(checker)
    check_order_index_no_longer_reserved(checker)
    check_delete_wallet_clears_preference(checker)
    check_migration_backfill(checker)
    sys.exit(checker.summary())


if __name__ == '__main__':
    main()
