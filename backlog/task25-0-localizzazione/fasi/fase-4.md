# Fase 4 — I messaggi di Python

**Chi**: **6 × `ps-i18n-python`** su **haiku**, **in sequenza** (non in
parallelo: vedi §4.1 qui sotto).
**Durata**: 1-2 giorni.
**Dipende da**: Fase 1 verde e committata. **Non** dipende dalla Fase 2 né
dalla 3: tocca solo Python, quindi può girare **in parallelo alla Fase 3** —
è il modo più efficace di accorciare il calendario.

È la fase più delicata del task, per una ragione sola: le f-string. Avvolgere
una stringa in un template è reversibile a vista; convertire
`f'... {n} ...'` in `ngettext(...) % {...}` cambia codice eseguibile.

---

## 4.1 Perché in sequenza

Le slice di `app.py` sono **intervalli di righe dello stesso file**. Due
subagent in parallelo sullo stesso file si sovrascrivono a vicenda, e in
worktree separati il conflitto si scopre al merge, quando le righe si sono già
spostate.

Quindi: **una invocazione per volta, ognuna rilegge il file**. Le slice servono
a tenere piccolo il contesto di haiku, non a parallelizzare.

| # | Ambito | Righe | Messaggi attesi |
|---|---|---|---|
| 4.A | `app.py` — auth, onboarding, pagine, movimenti | 1-1000 | ~50 |
| 4.B | `app.py` — ricorrenti, pagine di impostazioni, admin, categorie | 1000-1550 | ~45 |
| 4.C | `app.py` — wallet, gruppi, export/import | 1550-2200 | ~55 |
| 4.D | `app.py` — account, profilo, token, connessioni OAuth | 2200-2951 | ~50 |
| 4.E | `repository.py` | tutto | ~30 (su 73 candidate: il resto sono log e chiavi interne) |
| 4.F | `oauth_server.py` | tutto | ~7 |

Gli intervalli sono indicativi e vanno **ricalcolati sull'inventario della
Fase 0**: quello che conta è che una slice non spezzi una funzione a metà.

## 4.2 Che cosa si avvolge

| Sì | No |
|---|---|
| `flash(...)` — 33 occorrenze in `app.py` | `logger.debug/info/warning/error(...)` — **mai** |
| I valori delle chiavi `'error'`, `'message'`, `'success'` nelle risposte `jsonify` (172 occorrenze): il JS di pagina li mostra all'utente, **sono interfaccia** | Le **chiavi** dei dizionari JSON (`'error'` resta `'error'`: è un contratto d'API) |
| I messaggi delle eccezioni che arrivano all'utente | I messaggi delle eccezioni interne, i commenti, i docstring |
| Le etichette che finiscono in una risposta resa all'utente | I nomi di categoria/wallet/nota che arrivano dal DB |

**La regola che decide i casi dubbi**: se la stringa può finire sotto gli occhi
di chi usa l'app, si avvolge. Se finisce in un file di log che legge solo
l'amministratore, no.

## 4.3 Le f-string: la conversione, in tre forme

`pybabel extract` **non vede** le f-string, e `_(f'...')` cerca nel catalogo la
stringa *già interpolata*: non la trova mai. Tre casi, tre forme.

**Senza conteggio**, un solo valore:

```python
# prima — app.py:1997
errors.append(f"Categoria '{category_name}' non trovata")
# dopo
errors.append(_("Categoria '%(nome)s' non trovata") % {'nome': category_name})
```

**Con un conteggio** → `ngettext`, sempre, anche quando in italiano la frase
"suona bene" al plurale:

```python
# prima — app.py:1526
flash(f'Categoria eliminata e {movements_count} movimenti spostati')
# dopo
flash(ngettext(
    'Categoria eliminata e %(num)d movimento spostato',
    'Categoria eliminata e %(num)d movimenti spostati',
    movements_count) % {'num': movements_count})
```

**A livello di modulo** (fuori dal ciclo di richiesta, quando non esiste una
lingua) → `lazy_gettext`:

```python
from flask_babel import lazy_gettext as _l
ETICHETTE = {'expense': _l('Spesa'), 'income': _l('Entrata')}
```

Tre divieti:

1. **Placeholder nominali**, mai posizionali. `%(nome)s`, non `%s`: il
   traduttore deve poterli riordinare, e un placeholder sbagliato si becca in
   verifica invece che in produzione.
2. **Niente concatenazione.** `_('Errore: ') + str(e)` produce un msgid con i
   due punti e lo spazio dentro, e il traduttore non sa cosa segue. Si scrive
   `_('Errore: %(dettaglio)s') % {'dettaglio': e}`.
3. **Il valore interpolato non si traduce.** `category_name` arriva dal DB: è
   contenuto dell'utente.

## 4.4 Import

`from flask_babel import gettext as _, ngettext`. In `app.py` c'è già il blocco
`try/except ImportError` per gli import relativi/assoluti (righe 9-19): il
nuovo import **non va dentro quel blocco** — `flask_babel` è un pacchetto
installato, non un modulo del progetto, e non ha due grafie.

---

## Criteri di accettazione

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A4.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code — i messaggi nel contratto DOM sono ancora quelli |
| A4.2 | `.venv/bin/python -m pyspendless.test.test_task25_0` esce **0** | exit code |
| A4.3 | `.venv/bin/python -m py_compile pyspendless/<file>` esce 0 | exit code — una parentesi persa in una conversione è il modo più comune di sbagliare |
| A4.4 | `tools/check-i18n.py --file pyspendless/<file>` esce **0** | exit code |
| A4.5 | Nessun `_(f"` e nessun `_(` seguito da concatenazione | grep, coperto da A4.4 |
| A4.6 | Nessun `logger.` avvolto | grep: `logger\.[a-z]*(_\(` non trova nulla |
| A4.7 | Ogni stringa con un conteggio usa `ngettext` | ispezione dell'elenco dell'inventario (Fase 0 §0.3) |
| A4.8 | Il numero di `flash(` e di `jsonify(` è **identico** a prima | conteggio prima/dopo: una conversione non deve far sparire una risposta |
| A4.9 | `git status --short` mostra **solo** il file assegnato, e niente `translations/` | ispezione |

### Verificabili solo dall'agente principale (dopo il merge)

| # | Criterio |
|---|---|
| A4.10 | `./tools/build-i18n.sh` esce 0; il `.pot` contiene i msgid con i placeholder nominali |
| A4.11 | I percorsi che producono un flash si percorrono in Chrome e il messaggio compare, in italiano, come prima: creazione movimento, invito a un gruppo, import CSV con una riga sbagliata, eliminazione di una categoria con movimenti |
| A4.12 | Le risposte di errore delle API mostrano ancora il messaggio nel JS di pagina (una `fetch` con un id inesistente) |
| A4.13 | Il log è ancora in italiano e **non** passa dal catalogo |
| A4.14 | `git diff --stat` tocca solo `app.py`, `repository.py`, `oauth_server.py` |

## Definition of done

Nessuna f-string in un messaggio utente, tutti i conteggi su `ngettext`, il
contratto verde, e i flash che compaiono in Chrome esattamente come prima.

> **Se una slice torna imprecisa** — parentesi sbagliate, log avvolti,
> `%s` posizionali — **si rilancia quella slice su sonnet**. Non si riscrive la
> definizione dell'agente per un caso difficile: `app.py` è il file più grande
> del progetto, ed è normale che una slice su quattro richieda un modello più
> grande.
