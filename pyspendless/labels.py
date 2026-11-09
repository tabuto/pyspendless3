"""
Parser e manipolatore di label nei testi delle note.

Modulo di funzioni pure: nessun import del progetto, nessuno stato, nessun I/O.
È il vocabolario che tutte le altre fasi usano. Viene importato da conf.py
per registrare la funzione SQL ps_has_label.

La grammatica: una label è '#' seguito da 2-30 caratteri in [0-9A-Za-z_-],
delimitata a sinistra da inizio stringa o da un carattere che non è di parola
(Unicode), '#' o '-'; a destra da fine stringa o da un carattere che non è di
parola o '-'. Il confronto è case-insensitive; la grafia memorizzata è quella
canonica (forma come scritta nel testo).

Riferimento: backlog/task26-0-labels/task26-spec.md §3, §5, §6.
"""

import re

MIN_LABEL_LEN = 2
MAX_LABEL_LEN = 30

# La regex trova candidati; è is_valid() a decidere aggiungendo la regola
# che il primo e ultimo carattere non possono essere '-'.
# Il lookahead (?![\w-]) copre TUTTI i caratteri di parola Unicode, non solo
# il charset della label: è la differenza fra ignorare '#città' e riconoscerci
# dentro '#cit' (che sarebbe una sorpresa per l'utente).
LABEL_RE = re.compile(r'(?<![\w#-])#([0-9A-Za-z_-]{2,30})(?![\w-])')


def is_valid(name):
    """Valida un nome di label.

    Args:
        name: il nome senza '#' (lunghezza, charset, primo/ultimo carattere).

    Returns:
        bool: True se il nome è valido per una label.
    """
    if not isinstance(name, str):
        return False
    if len(name) < MIN_LABEL_LEN or len(name) > MAX_LABEL_LEN:
        return False
    if not re.fullmatch(r'[0-9A-Za-z_-]+', name):
        return False
    # Primo e ultimo carattere non '-'
    if name[0] == '-' or name[-1] == '-':
        return False
    return True


def extract(note):
    """Estrae label da una nota.

    Ordine di prima comparsa, dedup case-insensitive (vince la prima grafia
    incontrata), grafia come scritta nel testo (non normalizzata).

    Args:
        note: il testo della nota, o None.

    Returns:
        List[str]: label estratte (senza '#'), in ordine di prima comparsa.
    """
    if not note:
        return []

    seen = set()
    result = []

    for match in LABEL_RE.finditer(note):
        name = match.group(1)
        # Validiamo: la regex trova candidati, is_valid() decide
        if not is_valid(name):
            continue
        name_norm = name.lower()
        if name_norm not in seen:
            seen.add(name_norm)
            result.append(name)

    return result


def extract_norm(note):
    """Estrae label da una nota in forma normalizzata (minuscole).

    Args:
        note: il testo della nota, o None.

    Returns:
        List[str]: label estratte (senza '#'), minuscole, dedup.
    """
    raw = extract(note)
    seen = set()
    result = []
    for name in raw:
        norm = name.lower()
        if norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def has_label(note, name):
    """Verifica se una label è presente nella nota (case-insensitive).

    Args:
        note: il testo della nota, o None.
        name: il nome della label (con o senza '#').

    Returns:
        bool: True se la label è presente.
    """
    if not note or not name:
        return False

    # Accettiamo un '#' davanti a name
    if name.startswith('#'):
        name = name[1:]

    if not is_valid(name):
        return False

    # Cerchiamo una label di nome name (case-insensitive) nel testo
    labels = extract(note)
    name_norm = name.lower()
    return any(label.lower() == name_norm for label in labels)


def add_label(note, name):
    """Aggiunge una label alla nota (se non presente).

    Append in coda (' #name'), mai in mezzo. Idempotente: se la label c'è
    già (case-insensitive) la nota torna invariata. note vuota/None → '#name'.

    Args:
        note: il testo della nota, o None.
        name: il nome della label (con o senza '#').

    Returns:
        str: la nota con la label aggiunta.
    """
    # Accettiamo un '#' davanti a name
    if name.startswith('#'):
        name = name[1:]

    if not is_valid(name):
        return note or ''

    if not note:
        return '#{}'.format(name)

    # Se la label è già presente (case-insensitive), non aggiungiamo
    if has_label(note, name):
        return note

    # Append in coda
    note = note.rstrip()
    if note:
        return '{} #{}'.format(note, name)
    else:
        return '#{}'.format(name)


def remove_label(note, name):
    """Rimuove tutte le occorrenze di una label dalla nota.

    Applica normalize_space al risultato.

    Args:
        note: il testo della nota, o None.
        name: il nome della label (con o senza '#').

    Returns:
        str: la nota senza la label, con spazi normalizzati.
    """
    if not note:
        return ''

    # Accettiamo un '#' davanti a name
    if name.startswith('#'):
        name = name[1:]

    if not is_valid(name):
        return note

    name_norm = name.lower()

    # Cerchiamo tutte le occorrenze di questa label (case-insensitive) e rimuoviamo
    # Costruiamo il risultato pezzo per pezzo
    result = []
    last_end = 0

    for match in LABEL_RE.finditer(note):
        candidate = match.group(1)
        if is_valid(candidate) and candidate.lower() == name_norm:
            # Rimuoviamo questa occorrenza
            result.append(note[last_end:match.start()])
            last_end = match.end()

    # Aggiungiamo il resto
    result.append(note[last_end:])
    text = ''.join(result)

    # Normalizza gli spazi
    return normalize_space(text)


def rename_label(note, old, new):
    """Rinomina tutte le occorrenze di una label.

    Sostituisce tutte le occorrenze di old (case-insensitive) con new.
    Se new era già presente nel testo, l'occorrenza di old si rimuove
    invece di sostituirla (merge). La prima occorrenza si sostituisce,
    le successive si rimuovono se new è ora presente.

    Args:
        note: il testo della nota, o None.
        old: il nome della label vecchia (con o senza '#').
        new: il nome della label nuova (con o senza '#'), grafia come passata.

    Returns:
        str: la nota con la label rinominata.
    """
    if not note:
        return ''

    # Togli '#' se presente
    if old.startswith('#'):
        old = old[1:]
    if new.startswith('#'):
        new = new[1:]

    if not is_valid(old) or not is_valid(new):
        return note

    old_norm = old.lower()
    new_norm = new.lower()

    # Verifica se new è già presente nel testo PRIMA di iniziare
    labels = extract(note)
    new_already_present = any(label.lower() == new_norm for label in labels)

    result = []
    last_end = 0

    for match in LABEL_RE.finditer(note):
        candidate = match.group(1)
        if is_valid(candidate) and candidate.lower() == old_norm:
            # Questa occorrenza è una label che vogliamo rinominare
            result.append(note[last_end:match.start()])
            if new_already_present:
                # new era già presente: rimuoviamo old (merge)
                # Non aggiungiamo nulla al result
                pass
            else:
                # Sostituiamo con new
                result.append('#{}'.format(new))
                # Da ora new è presente, le successive occorrenze di old
                # verranno rimosse (merge)
                new_already_present = True
            last_end = match.end()

    # Aggiungiamo il resto
    result.append(note[last_end:])
    text = ''.join(result)

    # Normalizza gli spazi
    return normalize_space(text)


def canonicalize(note, mapping):
    """Riscrive le grafie delle label presenti nel mapping.

    mapping è {name_norm: forma_canonica}. Non deduplica, non tocca le label
    fuori dal mapping, non normalizza gli spazi.

    Args:
        note: il testo della nota, o None.
        mapping: dict da {name_norm -> forma_canonica}.

    Returns:
        str: la nota con le grafie canonicizzate secondo il mapping.
    """
    if not note:
        return ''

    result = []
    last_end = 0

    for match in LABEL_RE.finditer(note):
        candidate = match.group(1)
        if is_valid(candidate):
            candidate_norm = candidate.lower()
            if candidate_norm in mapping:
                # Sostituiamo con la forma canonica
                result.append(note[last_end:match.start()])
                result.append('#{}'.format(mapping[candidate_norm]))
                last_end = match.end()

    # Aggiungiamo il resto
    result.append(note[last_end:])
    return ''.join(result)


def normalize_space(text):
    """Normalizza gli spazi nel testo, per riga.

    Per ogni riga:
    1. Sequenze di spazi e tab → un solo spazio
    2. Via lo spazio prima di `, . ; : ! ?` e di `)`, e dopo `(`
    3. strip() di ogni riga
    4. strip() finale della stringa

    Il newline sopravvive.

    Args:
        text: il testo da normalizzare.

    Returns:
        str: il testo normalizzato.
    """
    if not text:
        return text

    lines = text.split('\n')
    normalized_lines = []

    for line in lines:
        # 1. Collassa spazi e tab multipli in uno
        line = re.sub(r'[ \t]+', ' ', line)

        # 2. Via spazi prima di `, . ; : ! ?` e di `)`, dopo `(`
        line = re.sub(r' ([,;:.!?\)])', r'\1', line)
        line = re.sub(r'\( ', r'(', line)

        # 3. strip della riga
        line = line.strip()

        normalized_lines.append(line)

    # Ricucisci le righe
    result = '\n'.join(normalized_lines)

    # 4. strip finale della stringa
    result = result.strip()

    return result
