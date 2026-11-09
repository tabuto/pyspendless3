#!/usr/bin/env python3
"""
Converte in label le "parole-tag" dello storico (task26-0).

Prima del task26-0 le etichette si scrivevano a mano in fondo alla nota, senza
cancelletto: "Parcheggio tirana balcani2025". Per la grammatica delle label
quella parola non e' una label, quindi quei movimenti non si possono filtrare.
Questo script appende `#parola` in fondo alle note che contengono una delle
parole approvate.

NON riscrive la parola nuda: la lascia dov'e' e aggiunge il tag in fondo.
Toccare il testo scritto dall'utente piu' dello stretto necessario, in una
migrazione a senso unico, non vale il guadagno estetico.

    python migrations/add_labels_from_words.py                 # SIMULAZIONE (default)
    python migrations/add_labels_from_words.py --word valencia # una sola parola
    python migrations/add_labels_from_words.py --apply         # scrive, chiede conferma
    python migrations/add_labels_from_words.py --apply --yes   # scrive senza chiedere

**L'operazione non e' reversibile**: fare prima una copia del database.

    cp data/pyspendless3.db data/pyspendless3-prima-labels.db

E' idempotente: una seconda esecuzione non tocca nulla, perche' salta le note
che hanno gia' quella label.
"""

import argparse
import logging
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyspendless'))

from conf import get_db_session          # noqa: E402
from models import Movement              # noqa: E402
from repository import LabelRepository   # noqa: E402
import labels as L                       # noqa: E402


# Parola nuda da cercare nella nota  ->  label da appendere.
# Quasi sempre coincidono; `sudafrica` no, perche' quelle spese appartengono
# al viaggio gia' etichettato `#sudafrica2026` (indicazione dell'utente,
# 09/11/2026).
PAROLE = [
    ('balcani2025',   'balcani2025'),
    ('valencia',      'valencia'),
    ('travel',        'travel'),
    ('copenaghen',    'copenaghen'),
    ('leolandia',     'leolandia'),
    ('natalesicilia', 'natalesicilia'),
    ('ledro',         'ledro'),
    ('sudafrica',     'sudafrica2026'),
    ('romaconvale',   'romaconvale'),
    ('danilowedding', 'danilowedding'),
]

# Confine di parola che tiene conto degli accenti: `\b` di Python su `sudafrica`
# matcherebbe anche dentro `sudafrica2026`, che e' una label diversa.
BORDO = r'(?<![0-9A-Za-zÀ-ÿ_-]){}(?![0-9A-Za-zÀ-ÿ_-])'


def trova(db, parola):
    """Movimenti la cui nota contiene `parola` come parola intera."""
    rx = re.compile(BORDO.format(re.escape(parola)), re.IGNORECASE)
    tutti = db.query(Movement).filter(Movement.note.isnot(None)).all()
    return [m for m in tutti if m.note and rx.search(m.note)]


def appendi(note, label):
    """Aggiunge ` #label` in fondo, senza toccare il resto del testo.

    Volutamente diverso da labels.add_label(), che normalizza anche gli spazi
    di tutta la nota: qui si tocca il minimo indispensabile.
    """
    base = (note or '').rstrip()
    return '{} #{}'.format(base, label) if base else '#{}'.format(label)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true',
                    help='scrive davvero sul database (default: sola simulazione)')
    ap.add_argument('--yes', action='store_true', help='non chiedere conferma con --apply')
    ap.add_argument('--word', action='append', default=None,
                    help='limita a una parola (ripetibile)')
    args = ap.parse_args()

    coppie = [(p, l) for p, l in PAROLE if not args.word or p in args.word]
    if not coppie:
        print('Nessuna parola corrispondente a --word {}'.format(args.word))
        return 2

    db = get_db_session()
    # In sviluppo l'engine nasce con echo=True, e il log SQL renderebbe
    # illeggibile proprio il riepilogo che va letto PRIMA di applicare.
    # Va fatto dopo la creazione dell'engine (e' lui ad alzare il livello), e
    # sul logger figlio 'sqlalchemy.engine.Engine', che e' quello che echo usa.
    db.get_bind().echo = False
    logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.WARNING)
    label_repo = LabelRepository(db)
    totale, per_parola = 0, []

    try:
        for parola, label in coppie:
            movimenti = trova(db, parola)
            da_fare = [m for m in movimenti if not L.has_label(m.note, label)]
            per_parola.append((parola, label, len(movimenti), len(da_fare)))

            print('\n== {} -> #{} =='.format(parola, label))
            print('   note che contengono la parola: {}'.format(len(movimenti)))
            print('   gia\' etichettate, saltate:     {}'.format(len(movimenti) - len(da_fare)))
            print('   da etichettare:                {}'.format(len(da_fare)))
            if da_fare:
                date = sorted(m.move_date for m in da_fare)
                print('   periodo:                       {} -> {}'.format(date[0], date[-1]))
                for m in da_fare[:3]:
                    print('     prima: {}'.format(m.note))
                    print('     dopo : {}'.format(appendi(m.note, label)))
                if len(da_fare) > 3:
                    print('     ... e altri {}'.format(len(da_fare) - 3))

            if args.apply and da_fare:
                # Registra la label (o ne recupera la grafia canonica) senza
                # toccare nessuna nota: sync_from_note su un testo sintetico.
                canonica = label_repo.sync_from_note(
                    da_fare[0].account_id, '#{}'.format(label)).lstrip('#')
                for m in da_fare:
                    m.note = appendi(m.note, canonica)
            totale += len(da_fare)

        print('\n' + '-' * 68)
        print('Movimenti da etichettare in totale: {}'.format(totale))

        if not args.apply:
            print('\nSIMULAZIONE: non e\' stato scritto nulla.')
            print('Per applicare:  python migrations/add_labels_from_words.py --apply')
            print('Prima fai una copia:  cp data/pyspendless3.db data/pyspendless3-prima-labels.db')
            return 0

        if totale == 0:
            print('\nNiente da fare: nessuna modifica.')
            return 0

        if not args.yes:
            print('\nL\'operazione modifica il testo di {} note e NON e\' reversibile.'.format(totale))
            risposta = input('Procedo? [scrivi "si" per confermare] ').strip().lower()
            if risposta != 'si':
                db.rollback()
                print('Annullato: nessuna modifica scritta.')
                return 1

        db.commit()
        print('\nFatto: {} note aggiornate.'.format(totale))
        return 0
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
