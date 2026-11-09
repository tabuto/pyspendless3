# Fase 1 — `pyspendless/labels.py` (la grammatica)

**Chi**: subagent **`ps-labels-py`** (haiku).
**Dipende da**: Fase 0.
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task26_0.py parser`
esce con **exit code 0** (12 controlli).
**File che puoi toccare**: `pyspendless/labels.py` (nuovo). **Nient'altro.**

## Il mandato

Un modulo di **funzioni pure**: nessuna classe, nessuno stato, nessun I/O,
nessun import del progetto. È il vocabolario che tutte le altre fasi usano.

```python
MIN_LABEL_LEN = 2
MAX_LABEL_LEN = 30
LABEL_RE = re.compile(r'(?<![\w#-])#([0-9A-Za-z_-]{2,30})(?![\w-])')
```

| Funzione | Firma | Contratto |
|---|---|---|
| `is_valid(name)` | `str -> bool` | `name` **senza** `#`. Lunghezza 2..30, charset `[0-9A-Za-z_-]`, primo e ultimo carattere **non** `-`. `is_valid('#coop')` è `False`. |
| `extract(note)` | `Optional[str] -> List[str]` | Label in ordine di **prima comparsa**, dedup case-insensitive (vince la prima grafia incontrata), grafia **come scritta**. `note=None` → `[]`. |
| `extract_norm(note)` | `Optional[str] -> List[str]` | Come sopra, minuscole. |
| `has_label(note, name)` | `-> bool` | Case-insensitive; tollera un `#` davanti a `name`. |
| `add_label(note, name)` | `-> str` | Append ` #name` **in coda**, mai in mezzo. Idempotente: se la label c'è già (case-insensitive) la nota torna invariata. `note` vuota/`None` → `'#name'`. |
| `remove_label(note, name)` | `-> str` | **Tutte** le occorrenze, poi `normalize_space`. |
| `rename_label(note, old, new)` | `-> str` | Tutte le occorrenze di `old` (case-insensitive) diventano `new` (grafia come passata). **Se `new` è già presente nel testo, l'occorrenza di `old` si rimuove** invece di sostituirla; lo stesso per la seconda occorrenza e le successive. |
| `canonicalize(note, mapping)` | `mapping: {name_norm: grafia}` | Riscrive la grafia delle label presenti nel mapping. **Non** deduplica, **non** tocca le label fuori dal mapping, **non** normalizza gli spazi. |
| `normalize_space(text)` | `-> str` | Vedi sotto. |

## `normalize_space`, riga per riga

È l'unico punto che decide come si ricuce il testo. Lavora **per riga**, non
sull'intera stringa:

1. dentro ogni riga, sequenze di spazi e tab → **un** solo spazio;
2. via lo spazio **prima** di `, . ; : ! ?` e di `)`, e **dopo** `(`;
3. `strip()` di ogni riga;
4. `strip()` finale della stringa intera.

Il newline **sopravvive**: `"riga uno #coop\nriga due"` senza `#coop` diventa
`"riga uno\nriga due"`, non `"riga uno riga due"`. La nota è una textarea, le
righe dell'utente sono sue. Le righe vuote in mezzo si rispettano
(`"a\n\nb"` resta `"a\n\nb"`).

## Le tre trappole

1. **Il lookahead copre tutti i caratteri di parola Unicode, non solo il
   charset della label.** È la differenza fra ignorare `#città` e riconoscerci
   dentro `#cit`. Non "semplificare" `(?![\w-])` in `(?![0-9A-Za-z_-])`.
2. **La regex trova *candidati*, `is_valid` decide.** `#-coop` e `#coop-`
   producono un candidato che `is_valid` scarta: il risultato è **nessuna
   label**, non una label troncata. Tieni un solo punto di verità sulla
   validità (`is_valid`), chiamato anche da `extract`.
3. **Sostituzioni multiple su indici**: se costruisci il risultato con
   `re.sub` e una callback, attento a non rompere l'ordine delle occorrenze; se
   lo costruisci a pezzi con `finditer`, ricordati la coda dopo l'ultimo match.

## Cosa NON fare

- Non importare `re` e poi usare `\b`: `#` non è un carattere di parola, e
  `\b#coop\b` non significa quello che sembra.
- Non toccare la punteggiatura dell'utente oltre lo spazio: `(#coop)` senza la
  label diventa `()`, ed è giusto così (c'è un caso nelle fixture).
- Non aggiungere funzioni "di comodo" non richieste. Le altre fasi usano questa
  tabella: ciò che non c'è non serve.
