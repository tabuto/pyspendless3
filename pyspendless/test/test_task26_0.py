#!/usr/bin/env python3
"""
Verifica locale del task26-0 (labels sui movimenti).

Non e' pytest (il progetto non lo usa: vedi test_task22_0.py, test_task23_0.py):
e' uno script di controllo riproducibile con assert espliciti, che lavora SOLO
su database SQLite in-memory creati al volo. Non tocca in nessun caso il
database configurato in .env.

QUESTO FILE E' IL METRO DI MISURA DELLE FASI 1-7 (scritto in Fase 0, prima di
qualunque riga di implementazione). Ogni fase delegata ha come criterio di
"fatto" l'exit code di una sezione di questo script, non un giudizio:

    .venv/bin/python test/test_task26_0.py parser   # Fase 1  (labels.py)
    .venv/bin/python test/test_task26_0.py repo     # Fase 2  (schema, repository, ps_has_label)
    .venv/bin/python test/test_task26_0.py api      # Fase 3  (/api/labels, filtro)
    .venv/bin/python test/test_task26_0.py contract # Fasi 4-7 (JS, template, nav, CSS)
    .venv/bin/python test/test_task26_0.py          # tutte

Exit code 0 se tutti i controlli della selezione passano, 1 altrimenti.

Finche' una fase non e' implementata la sua sezione fallisce con UN messaggio
che dice cosa manca (non con uno stack trace): le sezioni sono indipendenti,
quindi la Fase 2 puo' lavorare con la sezione 'repo' rossa e la 'parser' verde.
"""

import io
import json
import os
import re
import sys
import uuid
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                      # pyspendless/
ROOT = os.path.dirname(PKG)                      # repo


# ===========================================================================
# Infrastruttura
# ===========================================================================

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

    def group(self, description, failures, total):
        """Un controllo per gruppo di casi: i 112 casi delle fixture non
        meritano 112 righe di output, ma un fallimento deve dire QUALE caso."""
        if not failures:
            self.passed += 1
            print('  OK   {} ({}/{} casi)'.format(description, total, total))
            return
        self.failed += 1
        self.failures.append(description)
        print('  FAIL {} ({}/{} casi falliti)'.format(description, len(failures), total))
        for f in failures[:5]:
            print('         - {}'.format(f))
        if len(failures) > 5:
            print('         ... e altri {}'.format(len(failures) - 5))

    def missing(self, fase, cosa, errore):
        """La fase non e' ancora implementata: un messaggio, non 20."""
        self.failed += 1
        self.failures.append('Fase {} non implementata'.format(fase))
        print('  FAIL Fase {} non ancora implementata: {}'.format(fase, cosa))
        print('         {}'.format(errore))

    def section(self, title):
        print('\n== {} =='.format(title))

    def summary(self):
        print('\n{}\n{} controlli superati, {} falliti'.format('-' * 68, self.passed, self.failed))
        if self.failures:
            print('\nFalliti:')
            for failure in self.failures:
                print('  - {}'.format(failure))
        return 0 if self.failed == 0 else 1


def load_cases():
    with io.open(os.path.join(HERE, 'fixtures', 'labels_cases.json'), encoding='utf-8') as fh:
        return json.load(fh)


def read(*parts):
    with io.open(os.path.join(*parts), encoding='utf-8') as fh:
        return fh.read()


def in_memory_factory():
    """Engine in-memory con le funzioni SQL del progetto registrate.

    register_sqlite_functions() e' il punto che la Fase 2 deve esportare da
    conf.py: se il test registrasse ps_has_label da solo, verificherebbe una
    copia della funzione e non quella che gira in produzione.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from models import Base
    import conf

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False},
                           poolclass=StaticPool)
    conf.register_sqlite_functions(engine)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)


def seed_account(db, name='Famiglia Test'):
    """Account + utente + wallet + due categorie. Ritorna un dict di id."""
    from models import Account, User, Category
    from repository import WalletRepository

    account = Account(name=name)
    db.add(account)
    db.flush()
    user = User(public_uid=str(uuid.uuid4()), google_id='g-{}'.format(uuid.uuid4()),
                email='u-{}@example.com'.format(uuid.uuid4()), name='Utente',
                account_id=account.id, role='member')
    db.add(user)
    expense = Category(name='Spesa', account_id=account.id, type='expense')
    income = Category(name='Stipendio', account_id=account.id, type='income')
    db.add_all([expense, income])
    db.flush()
    wallet = WalletRepository(db).create_wallet(code='W-{}'.format(uuid.uuid4().hex[:6]),
                                                name='Contanti', account_id=account.id)
    db.commit()
    return {'account_id': account.id, 'user_id': user.id, 'wallet_id': wallet.id,
            'category_id': expense.id, 'income_category_id': income.id,
            'user_email': user.email, 'wallet_code': wallet.code}


def movement_payload(ids, note, day=5):
    from datetime import date
    return {
        'id': str(uuid.uuid4()),
        'move_date': date(2026, 3, day), 'move_year': 2026, 'move_month': 3,
        'category': 'Spesa', 'wallet': ids['wallet_code'],
        'income': None, 'expense': 10.0, 'note': note,
        'user': ids['user_email'], 'account_id': ids['account_id'],
        'user_id': ids['user_id'], 'category_id': ids['category_id'],
        'wallet_id': ids['wallet_id'],
    }


# ===========================================================================
# SEZIONE 'parser' — Fase 1: pyspendless/labels.py
# ===========================================================================

def check_parser(checker):
    checker.section("Fase 1 — labels.py (grammatica, dalle fixture condivise)")

    try:
        import labels
    except Exception as exc:
        checker.missing(1, 'pyspendless/labels.py', '{}: {}'.format(type(exc).__name__, exc))
        return

    required = ['is_valid', 'extract', 'extract_norm', 'has_label', 'add_label',
                'remove_label', 'rename_label', 'canonicalize', 'normalize_space',
                'LABEL_RE', 'MIN_LABEL_LEN', 'MAX_LABEL_LEN']
    absent = [name for name in required if not hasattr(labels, name)]
    if absent:
        checker.missing(1, 'labels.py incompleto', 'mancano: {}'.format(', '.join(absent)))
        return

    cases = load_cases()

    def run(group, fn, args_of, expected_of=lambda c: c['expected']):
        failures = []
        for case in cases[group]:
            try:
                got = fn(*args_of(case))
            except Exception as exc:
                failures.append('{!r} -> eccezione {}: {}'.format(case, type(exc).__name__, exc))
                continue
            want = expected_of(case)
            if isinstance(want, bool):
                ok = bool(got) is want
            else:
                ok = got == want
            if not ok:
                failures.append('{} -> atteso {!r}, ottenuto {!r}'.format(
                    {k: v for k, v in case.items() if k != 'nota'}, want, got))
        checker.group('labels.{}'.format(group), failures, len(cases[group]))

    run('is_valid', labels.is_valid, lambda c: (c['name'],))
    run('extract', labels.extract, lambda c: (c['note'],))
    run('extract_norm', labels.extract_norm, lambda c: (c['note'],))
    run('has_label', labels.has_label, lambda c: (c['note'], c['label']))
    run('add_label', labels.add_label, lambda c: (c['note'], c['label']))
    run('remove_label', labels.remove_label, lambda c: (c['note'], c['label']))
    run('rename_label', labels.rename_label, lambda c: (c['note'], c['old'], c['new']))
    run('canonicalize', labels.canonicalize, lambda c: (c['note'], c['mapping']))
    run('normalize_space', labels.normalize_space, lambda c: (c['text'],))

    # Vincoli strutturali: labels.py e' importato da conf.py (ps_has_label) e
    # deve restare senza dipendenze, altrimenti nasce un ciclo di import.
    source = read(labels.__file__)
    checker.check('labels.py non importa SQLAlchemy ne moduli del progetto (lo importa conf.py)',
                  not re.search(r'^\s*(from|import)\s+(sqlalchemy|models|repository|conf|app)\b',
                                source, re.M))
    checker.check('MIN_LABEL_LEN=2, MAX_LABEL_LEN=30',
                  labels.MIN_LABEL_LEN == 2 and labels.MAX_LABEL_LEN == 30,
                  (labels.MIN_LABEL_LEN, labels.MAX_LABEL_LEN))
    checker.check('extract() e\' idempotente sul risultato di remove_label()',
                  labels.extract(labels.remove_label('a #coop b #buoni', 'coop')) == ['buoni'])


# ===========================================================================
# SEZIONE 'repo' — Fase 2: schema, LabelRepository, hook, ps_has_label
# ===========================================================================

def check_repo(checker):
    checker.section("Fase 2 — schema, LabelRepository, hook nei repository, ps_has_label")

    try:
        import conf
        from models import Label, Movement
        from repository import (LabelRepository, MovementRepository,
                                RecurrentMovementRepository)
        if not hasattr(conf, 'register_sqlite_functions'):
            raise AttributeError("conf.register_sqlite_functions assente")
    except Exception as exc:
        checker.missing(2, 'models.Label / LabelRepository / conf.register_sqlite_functions',
                        '{}: {}'.format(type(exc).__name__, exc))
        return

    engine, factory = in_memory_factory()
    db = factory()
    ids = seed_account(db)
    other = seed_account(db, name='Altro Account')
    labels_repo = LabelRepository(db)
    mov_repo = MovementRepository(db)

    # --- sync_from_note: crea, riusa, canonicalizza -------------------------
    note = labels_repo.sync_from_note(ids['account_id'], 'Spesa coop settimanale #buoni #coop')
    rows = db.query(Label).filter_by(account_id=ids['account_id']).all()
    checker.check('sync_from_note crea una riga per label (#buoni, #coop)',
                  sorted(r.name_norm for r in rows) == ['buoni', 'coop'],
                  [r.name_norm for r in rows])
    checker.check('sync_from_note ritorna la nota (invariata se le grafie sono gia\' canoniche)',
                  note == 'Spesa coop settimanale #buoni #coop', note)

    note2 = labels_repo.sync_from_note(ids['account_id'], 'altra spesa #COOP')
    rows = db.query(Label).filter_by(account_id=ids['account_id'], name_norm='coop').all()
    checker.check('riuso case-insensitive: #COOP non crea una seconda riga', len(rows) == 1, len(rows))
    checker.check('canonicalizzazione (D4): #COOP riscritta nella grafia del registro',
                  note2 == 'altra spesa #coop', note2)

    checker.check('label non valida nel testo (#a) non crea righe',
                  labels_repo.sync_from_note(ids['account_id'], 'spesa #a') == 'spesa #a'
                  and db.query(Label).filter_by(account_id=ids['account_id']).count() == 2)

    labels_repo.sync_from_note(other['account_id'], 'spesa #segreta')
    checker.check('isolamento fra account: la label di un account non finisce nell\'altro',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='segreta').count() == 0)

    # --- l'hook sta nel repository, non nelle rotte -------------------------
    mov = mov_repo.create_movement(movement_payload(ids, 'pane #Nuova1'))
    checker.check('create_movement registra le label e salva la nota canonica',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='nuova1').count() == 1
                  and mov.note == 'pane #Nuova1', mov.note)

    mov_repo.update_movement(mov.id, {'note': 'pane #nuova2'})
    checker.check('update_movement registra le label',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='nuova2').count() == 1)

    mov_repo.bulk_update_movements(account_id=ids['account_id'], filters={}, note='rifatta #nuova3')
    checker.check('bulk_update_movements registra le label (import CSV e correzione massiva passano da qui)',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='nuova3').count() == 1)

    rec_repo = RecurrentMovementRepository(db)
    rec_repo.create(
        account_id=ids['account_id'], name='Affitto', category_id=ids['category_id'],
        wallet_id=ids['wallet_id'], movement_type='expense', amount=500.0, note='affitto #casa')
    checker.check('RecurrentMovementRepository.create registra le label',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='casa').count() == 1)

    # --- ps_has_label in SQL -----------------------------------------------
    db.query(Movement).delete()
    db.commit()
    for note_text in ['spesa #coop settimanale', 'spesa #coopx', 'spesa #coop #buoni', None, 'niente']:
        mov_repo.create_movement(movement_payload(ids, note_text))

    from sqlalchemy import func
    q = db.query(Movement).filter(func.ps_has_label(Movement.note, 'coop') == 1)
    checker.check('ps_has_label distingue #coop da #coopx (il LIKE non lo farebbe)',
                  q.count() == 2, q.count())
    checker.check('ps_has_label su note NULL non solleva e non matcha',
                  db.query(Movement).filter(func.ps_has_label(Movement.note, 'niente') == 1).count() == 0)

    found = mov_repo.get_movements_for_account(ids['account_id'], labels=['coop'])
    checker.check('get_movements_for_account(labels=[...]) filtra', len(found) == 2, len(found))
    found = mov_repo.get_movements_for_account(ids['account_id'], labels=['coop', 'buoni'])
    checker.check('piu\' label in AND, non in OR (semantica Jira)', len(found) == 1, len(found))
    found = mov_repo.get_movements_for_account(ids['account_id'], labels=['inesistente'])
    checker.check('label inesistente: zero risultati, nessun errore', found == [], found)

    stats = mov_repo.get_movements_stats(ids['account_id'], labels=['coop'])
    checker.check('get_movements_stats accetta lo stesso filtro (le statistiche seguono i filtri)',
                  abs(float(stats['total_expense']) - 20.0) < 0.001, stats.get('total_expense'))
    # expenses_by_category e' una query SEPARATA dentro get_movements_stats:
    # dimenticarci il filtro fa mostrare al grafico tutte le categorie del
    # periodo mentre la tabella sotto e' filtrata (trovato in UAT).
    per_cat = sum(c['total'] for c in stats['expenses_by_category'])
    checker.check('anche expenses_by_category (il grafico) rispetta il filtro per label',
                  abs(per_cat - 20.0) < 0.001, stats['expenses_by_category'])

    # --- rinomina, merge, eliminazione -------------------------------------
    renamed = labels_repo.rename_label(_label_id(db, Label, ids, 'coop'), 'Coop', ids['account_id'])
    notes = sorted(m.note or '' for m in db.query(Movement).all())
    checker.check('rename_label riscrive le note dei movimenti',
                  any('#Coop' in n for n in notes) and not any('#coop ' in n for n in notes), notes)
    checker.check('rename_label aggiorna name e name_norm',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='coop').one().name == 'Coop')
    checker.check('rename_label ritorna il numero di movimenti riscritti', renamed == 2, renamed)

    labels_repo.sync_from_note(ids['account_id'], 'spesa #coopp')
    mov_repo.create_movement(movement_payload(ids, 'spesa #coopp e #Coop'))
    merged = labels_repo.rename_label(_label_id(db, Label, ids, 'coopp'), 'Coop', ids['account_id'])
    checker.check('merge: la riga sorgente sparisce dal registro',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='coopp').count() == 0)
    checker.check('merge: nessuna nota con la label doppia',
                  not any((m.note or '').count('#Coop') > 1 for m in db.query(Movement).all()),
                  [m.note for m in db.query(Movement).all()])

    counts = {c['name_norm']: c['movements_count'] for c in labels_repo.get_labels_with_counts(ids['account_id'])}
    checker.check('get_labels_with_counts conta i movimenti per label',
                  counts.get('coop') == 3, counts)

    found = labels_repo.search(ids['account_id'], 'oop')
    checker.check('search() cerca per SOTTOSTRINGA (LIKE %q%), non solo per prefisso',
                  [l.name_norm for l in found] == ['coop', 'coopx'], [l.name_norm for l in found])
    found = labels_repo.search(ids['account_id'], '%')
    checker.check("search(): il '%' nella query non e' un carattere jolly",
                  found == [], [l.name_norm for l in found])

    deleted = labels_repo.delete_label(_label_id(db, Label, ids, 'coop'), ids['account_id'])
    checker.check('delete_label rimuove la label dal testo delle note',
                  not any('#Coop' in (m.note or '') for m in db.query(Movement).all()),
                  [m.note for m in db.query(Movement).all()])
    checker.check('delete_label cancella la riga e ritorna i movimenti toccati',
                  db.query(Label).filter_by(account_id=ids['account_id'], name_norm='coop').count() == 0
                  and deleted == 3, deleted)

    # --- concorrenza sul vincolo UNIQUE ------------------------------------
    db.commit()
    errors = []

    def worker():
        session = factory()
        try:
            LabelRepository(session).sync_from_note(ids['account_id'], 'gara #contesa')
            session.commit()
        except Exception as exc:               # noqa: BLE001 - e' quello che misuriamo
            errors.append('{}: {}'.format(type(exc).__name__, exc))
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    db.expire_all()
    checker.check('corsa fra due membri sulla stessa label nuova: una sola riga, nessuna eccezione',
                  not errors and db.query(Label).filter_by(
                      account_id=ids['account_id'], name_norm='contesa').count() == 1, errors)

    # --- backfill ----------------------------------------------------------
    try:
        sys.path.insert(0, os.path.join(ROOT, 'migrations'))
        from backfill_labels import backfill
    except Exception as exc:
        checker.missing(2, 'migrations/backfill_labels.py (funzione backfill(db))',
                        '{}: {}'.format(type(exc).__name__, exc))
        db.close()
        return

    fresh_engine, fresh_factory = in_memory_factory()
    fdb = fresh_factory()
    fids = seed_account(fdb)
    fmov = MovementRepository(fdb)
    from datetime import date
    old = movement_payload(fids, 'vecchia #Coop', day=1)
    old['move_date'] = date(2024, 1, 1)
    new = movement_payload(fids, 'nuova #COOP', day=2)
    fmov.create_movement(old)
    fmov.create_movement(new)
    fdb.query(Label).delete()                 # simula il DB pre-task26
    fdb.commit()

    created = backfill(fdb)
    rows = fdb.query(Label).filter_by(account_id=fids['account_id']).all()
    checker.check('backfill popola il registro dalle note esistenti', len(rows) == 1, len(rows))
    checker.check('backfill: grafia dal movimento piu\' vecchio (deterministico)',
                  rows and rows[0].name == 'Coop', rows[0].name if rows else None)
    again = backfill(fdb)
    checker.check('backfill idempotente: la seconda esecuzione non crea nulla',
                  again == 0 and fdb.query(Label).filter_by(account_id=fids['account_id']).count() == 1,
                  (created, again))
    fdb.close()
    db.close()


def _label_id(db, Label, ids, name_norm):
    row = db.query(Label).filter_by(account_id=ids['account_id'], name_norm=name_norm).one()
    return row.id


# ===========================================================================
# SEZIONE 'api' — Fase 3: /api/labels, filtro, pagina
# ===========================================================================

def check_api(checker):
    checker.section("Fase 3 — /api/labels, filtro ?label=, /settings/labels (Flask test client)")

    try:
        import app as app_module
        from models import Label, Movement
        from repository import LabelRepository, MovementRepository
    except Exception as exc:
        checker.missing(3, 'import di app.py', '{}: {}'.format(type(exc).__name__, exc))
        return

    engine, factory = in_memory_factory()
    setup = factory()
    ids = seed_account(setup)
    other = seed_account(setup, name='Altro Account')
    lrepo = LabelRepository(setup)
    mrepo = MovementRepository(setup)
    mrepo.create_movement(movement_payload(ids, 'spesa #coop settimanale'))
    mrepo.create_movement(movement_payload(ids, 'spesa #coop #buoni'))
    mrepo.create_movement(movement_payload(ids, 'spesa #coopx'))
    lrepo.sync_from_note(ids['account_id'], 'seminata #cosmetica')
    lrepo.sync_from_note(other['account_id'], 'altro account #segreta')
    setup.commit()
    coop_id = _label_id(setup, Label, ids, 'coop')
    segreta_id = _label_id(setup, Label, other, 'segreta')
    setup.close()

    original = app_module.get_db_session
    app_module.get_db_session = lambda: factory()
    flask_app = app_module.app
    flask_app.config['TESTING'] = True

    try:
        with flask_app.test_client() as client:
            resp = client.get('/api/labels?q=co')
            checker.check('GET /api/labels senza sessione -> 401', resp.status_code == 401, resp.status_code)

            with client.session_transaction() as sess:
                sess['user_id'] = ids['user_id']
                sess['account_id'] = ids['account_id']

            resp = client.get('/api/labels?q=co')
            data = resp.get_json()
            names = [row['name'] for row in (data or [])]
            # 'coopx' e' in registro perche' il setup crea un movimento con
            # quella nota: contiene 'co', quindi la ricerca per sottostringa
            # DEVE restituirla (atteso corretto in Fase 3, era sbagliato in Fase 0).
            checker.check('GET /api/labels?q=co -> match LIKE %co% dell\'account',
                          resp.status_code == 200
                          and sorted(names) == ['coop', 'coopx', 'cosmetica'], (resp.status_code, names))
            checker.check('prefix-match prima (ordinamento del dropdown)',
                          names and names[0] == 'coop', names)
            checker.check('le label di un altro account non compaiono',
                          'segreta' not in names, names)

            resp = client.get('/api/labels?q=oop')
            names = [row['name'] for row in (resp.get_json() or [])]
            checker.check('GET /api/labels?q=oop -> ricerca per sottostringa (LIKE %oop%)',
                          names == ['coop', 'coopx'], names)

            resp = client.get('/api/labels?q=co&limit=1')
            checker.check('limit rispettato', len(resp.get_json() or []) == 1, resp.get_json())

            resp = client.get('/api/labels?with_counts=1')
            counts = {row['name_norm']: row['movements_count'] for row in (resp.get_json() or [])}
            checker.check('GET /api/labels?with_counts=1 -> conteggio movimenti per label',
                          counts.get('coop') == 2 and counts.get('cosmetica') == 0, counts)

            resp = client.put('/api/labels/{}'.format(segreta_id), json={'name': 'rubata'})
            checker.check('PUT su label di un altro account -> 404 (lezione del task24-0)',
                          resp.status_code == 404, resp.status_code)
            resp = client.delete('/api/labels/{}'.format(segreta_id))
            checker.check('DELETE su label di un altro account -> 404', resp.status_code == 404, resp.status_code)

            resp = client.put('/api/labels/{}'.format(coop_id), json={'name': 'non valida!'})
            checker.check('PUT con nome non valido -> 400', resp.status_code == 400, resp.status_code)

            resp = client.put('/api/labels/{}'.format(coop_id), json={'name': 'Coop'})
            check_db = factory()
            notes = [m.note or '' for m in check_db.query(Movement).all()]
            checker.check('PUT rinomina: note riscritte e 200',
                          resp.status_code == 200 and any('#Coop' in n for n in notes), (resp.status_code, notes))
            checker.check('PUT rinomina: #coopx non toccata',
                          any('#coopx' in n for n in notes), notes)
            check_db.close()

            resp = client.get('/movements?label=Coop&date_from=2026-01-01&date_to=2026-12-31')
            checker.check('GET /movements?label= -> 200', resp.status_code == 200, resp.status_code)
            resp = client.get('/movements?label=non!valida&date_from=2026-01-01&date_to=2026-12-31')
            checker.check('label non valida nella query string: ignorata, mai un 500',
                          resp.status_code == 200, resp.status_code)

            resp = client.get('/api/movements?label=Coop&date_from=2026-01-01&date_to=2026-12-31')
            payload = resp.get_json() or {}
            rows = payload.get('movements', payload if isinstance(payload, list) else [])
            checker.check('GET /api/movements?label= filtra (2 movimenti su 3)',
                          resp.status_code == 200 and len(rows) == 2, (resp.status_code, len(rows)))

            resp = client.get('/api/movements/export?label=Coop&date_from=2026-01-01&date_to=2026-12-31')
            checker.check('export CSV accetta lo stesso filtro', resp.status_code == 200, resp.status_code)

            resp = client.post('/api/movements', json={
                'move_date': '2026-03-09', 'category_id': ids['category_id'],
                'wallet_id': ids['wallet_id'], 'expense': 12.5, 'income': None,
                'note': 'nuovo movimento #dalform'})
            check_db = factory()
            created = check_db.query(Label).filter_by(account_id=ids['account_id'], name_norm='dalform').count()
            check_db.close()
            checker.check('POST /api/movements registra la label dal testo, senza campo "labels" nel payload',
                          resp.status_code in (200, 201) and created == 1, (resp.status_code, created))

            resp = client.delete('/api/labels/{}'.format(coop_id))
            check_db = factory()
            notes = [m.note or '' for m in check_db.query(Movement).all()]
            remaining = check_db.query(Label).filter_by(account_id=ids['account_id'], name_norm='coop').count()
            check_db.close()
            checker.check('DELETE /api/labels: via dalle note e dal registro',
                          resp.status_code == 200 and remaining == 0
                          and not any('#Coop' in n for n in notes), (resp.status_code, remaining, notes))

            resp = client.get('/settings/labels')
            checker.check('GET /settings/labels -> 200', resp.status_code == 200, resp.status_code)
    finally:
        app_module.get_db_session = original


# ===========================================================================
# SEZIONE 'contract' — Fasi 4-7: JS, template, nav, CSS compilato
# ===========================================================================

def check_contract(checker):
    checker.section("Fasi 4-7 — ps-labels.js, template, nav, CSS compilato")

    # Fase 4 — il JS non si esegue qui (nessun Node nel progetto: la grammatica
    # JS si verifica con tools/probe-labels.html nel browser). Qui si controlla
    # solo che il file esista e dichiari le stesse funzioni del gemello Python.
    js_path = os.path.join(PKG, 'static', 'js', 'ps-labels.js')
    if not os.path.exists(js_path):
        checker.missing(4, 'pyspendless/static/js/ps-labels.js', 'file assente')
    else:
        js = read(js_path)
        required = ['isValid', 'extract', 'hasLabel', 'addLabel', 'removeLabel',
                    'renameLabel', 'canonicalize', 'normalizeSpace', 'decorate']
        absent = [fn for fn in required if fn not in js]
        checker.check('ps-labels.js espone le funzioni del contratto ({})'.format(', '.join(required)),
                      not absent, 'mancano: {}'.format(absent))
        checker.check('ps-labels.js non usa lookbehind nelle regex (Safari < 16.4)',
                      '(?<' not in js)
        checker.check('ps-labels.js regge l\'assenza di TomSelect (CDN giu\': degrado, non errore)',
                      "typeof TomSelect" in js)
        checker.check('ps-labels.js costruisce le chip con nodi DOM, non con innerHTML',
                      'innerHTML' not in js or 'createElement' in js)

    # Fase 5 — campo labels nel form movimento e nelle ricorrenti
    for template, fase in (('ps-add-mov.html', 5), ('ps-recurrent-mov.html', 5)):
        path = os.path.join(PKG, 'templates', template)
        html = read(path)
        checker.check('{}: campo labels agganciato alla textarea della nota'.format(template),
                      'data-ps-labels' in html and 'ps-labels.js' in html,
                      'data-ps-labels={} ps-labels.js={}'.format('data-ps-labels' in html, 'ps-labels.js' in html))

    # Fase 6 — chip read-only in elenco e ricerca
    for template in ('ps-show-mov.html', 'ps-search-mov.html'):
        html = read(os.path.join(PKG, 'templates', template))
        checker.check('{}: note marcate con data-ps-note per la resa a chip'.format(template),
                      'data-ps-note' in html)
        # Senza l'include, decorate() non gira mai: le chiamate sono protette da
        # `typeof PsLabels !== 'undefined'`, quindi il difetto sarebbe SILENZIOSO
        # (nessun errore in console, solo note senza chip).
        checker.check('{}: carica ps-labels.js'.format(template),
                      'js/ps-labels.js' in html)
    show = read(os.path.join(PKG, 'templates', 'ps-show-mov.html'))
    checker.check('ps-show-mov.html: decorate richiamato su draw.dt (DataTables ridisegna le celle)',
                  'draw.dt' in show)
    checker.check('ps-show-mov.html: filtro per label nel pannello filtri',
                  'name="label"' in show or "name='label'" in show)

    # Fase 7 — pagina e nav
    checker.check('esiste templates/ps-setting-labels.html',
                  os.path.exists(os.path.join(PKG, 'templates', 'ps-setting-labels.html')))
    nav = read(os.path.join(PKG, 'templates', 'ps-nav.html'))
    checker.check('ps-nav.html: voce Impostazioni -> Labels', "settings_labels" in nav)
    t19 = read(HERE, 'test_task19_0.py')
    checker.check('/settings/labels aggiunta a NAV_LINKS_ORDER (il contratto della nav del task19-0)',
                  '/settings/labels' in t19)

    # Il passo che si dimentica: CSS sorgente aggiornato ma non compilato.
    src = read(os.path.join(PKG, 'static', 'css', 'ps-tailwind.src.css'))
    out = read(os.path.join(PKG, 'static', 'css', 'ps-tailwind.css'))
    checker.check('.ps-label-chip definita in ps-tailwind.src.css', 'ps-label-chip' in src)
    checker.check('.ps-label-chip presente anche in ps-tailwind.css COMPILATO (./tools/build-css.sh)',
                  'ps-label-chip' in out)

    # MAX_NOTE_LENGTH: una sola definizione, in conf.py
    mcp = read(os.path.join(PKG, 'mcp_server.py'))
    checker.check('MAX_NOTE_LENGTH vive in conf.py e mcp_server.py la importa',
                  not re.search(r'^MAX_NOTE_LENGTH\s*=\s*\d+', mcp, re.M))

    checker.check('esiste tools/probe-labels.html (sonda JS degli stessi casi)',
                  os.path.exists(os.path.join(ROOT, 'tools', 'probe-labels.html')))

    # Il progetto si importa in DUE modi: piatto (come questo test e il dev
    # server) e come PACKAGE (come il WSGI di PythonAnywhere). Tutto il resto
    # del test gira in modalita' piatta, quindi un import senza fallback
    # relativo passerebbe qui e si romperebbe in produzione su ogni pagina che
    # tocca il DB -- e' successo con `from labels import has_label` in conf.py.
    import subprocess
    script = ('import sys; sys.path.insert(0, %r);'
              'from pyspendless import conf; conf.get_db_engine()' % ROOT)
    proc = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    checker.check('il progetto importato come package crea l\'engine (nessun import piatto nascosto)',
                  proc.returncode == 0, proc.stderr.decode('utf-8', 'replace').strip().splitlines()[-1:])


# ===========================================================================

SECTIONS = {
    'parser': check_parser,
    'repo': check_repo,
    'api': check_api,
    'contract': check_contract,
}


def main():
    wanted = [a for a in sys.argv[1:] if not a.startswith('-')] or list(SECTIONS)
    unknown = [w for w in wanted if w not in SECTIONS]
    if unknown:
        print('Sezioni sconosciute: {}. Disponibili: {}'.format(
            ', '.join(unknown), ', '.join(SECTIONS)))
        sys.exit(2)

    checker = Checker()
    for name in wanted:
        SECTIONS[name](checker)
    sys.exit(checker.summary())


if __name__ == '__main__':
    main()
