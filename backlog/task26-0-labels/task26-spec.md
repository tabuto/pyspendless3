# Task 26.0 — Labels sui movimenti

**Stato**: **FASI 0-7 FATTE, FASE 8 A METÀ** (2026-11-08) — la funzione è
completa e verificata end-to-end sull'ambiente locale, sul database di
sviluppo reale (11 label trovate dal backfill fra le note esistenti). Restano
solo la UAT dell'utente, il bump di versione e il rilascio.
**Data**: 2026-11-08 (specifica e Fase 0)
**Piano per fase**: `fasi/fase-0.md` … `fasi/fase-8.md` in questa cartella. La
specifica dice *cosa e perché*, i file di fase dicono *chi fa cosa e come si
verifica*.
**Versione app di partenza**: `_APP_VERSION = "0.3.1"` ([app.py:36](../pyspendless/app.py))
**Repo**: `tabuto/pyspendless3`, branch `main`.
**Dipende da**: niente di bloccante. Tocca template usciti dal task19-0 (tutti
chiusi) e la pagina `/movements` del task21-0.
**Interferisce con**: task25-0 (localizzazione, `PIANIFICATO`). Vedi §15 R5.
**Nuove dipendenze**: **nessuna**. Il campo a chip riusa Tom Select, già nel
progetto via CDN e già "skinnato" in `ps-tailwind.src.css` (§9).
**Vincolo di ambiente**: il virtualenv del progetto è **Python 3.9**
(`pyspendless/.venv`): niente `match`, niente `str | None` nelle annotazioni.

---

## 1. Obiettivo

Dare ai movimenti delle **etichette** (`#buoni`, `#coop`, `#vacanza2026`) per
raggruppare spese che tagliano trasversalmente le categorie, con l'ergonomia
delle label di Jira: un campo a chip con elenco a discesa che filtra mentre si
digita, e la possibilità di creare una label nuova digitandola.

Il vincolo che decide tutto il resto:

> **La label non è un campo del movimento: è testo dentro `Movement.note`.**

`"Spesa coop settimanale #buoni #coop"` è la rappresentazione completa. Il
campo a chip è una **vista** sul testo della nota, e la tabella `LABEL` è un
**registro** per account che serve all'autocompletamento. Niente altro conosce
le label: chi scrive la nota (form, API, MCP/Alexa, import CSV) non deve
ricordarsi di aggiornare nulla.

### Criteri di accettazione

| # | Criterio |
|---|---|
| A1 | Dal form movimento si aggiunge una label scegliendola da un elenco che filtra con `LIKE %str%` mentre si digita, o creandola nuova; alla registrazione la label esiste in `LABEL` e appartiene all'account. |
| A2 | Le label di un movimento già salvato si vedono come chip riaprendolo in modifica, **anche** se sono state scritte a mano in mezzo al testo della nota. |
| A3 | Rimuovere una chip rimuove **quella label dal testo** della nota: `"Spesina #coop settimanale con #buoni"` → `"Spesina settimanale con #buoni"`. Nessuno spazio doppio, nessuno spazio prima della punteggiatura. |
| A4 | Le label sono dell'**account**: ogni membro vede e riusa quelle degli altri. |
| A5 | In `/movements` e `/ps-search-mov` le label nelle note sono rese come chip cliccabili, e il click filtra per quella label. |
| A6 | `/movements` ha un filtro per label (multi-selezione, semantica **AND**) che convive con i filtri esistenti e con l'export CSV. |
| A7 | Una pagina `Impostazioni → Labels` elenca le label con il numero di movimenti, e permette rinomina (con merge) ed eliminazione, riscrivendo le note dei movimenti coinvolti. |
| A8 | Nessuna nuova dipendenza Python, nessuna fase di build sul server: il deploy resta `git pull` + Reload (più lo script di backfill, una volta). |
| A9 | Un movimento senza label si comporta esattamente come oggi (isofunzionalità sul percorso senza label). |

---

## 2. Decisioni chiuse (sessione del 2026-11-08)

| # | Decisione | Alternativa scartata e perché |
|---|---|---|
| **D1** | **Solo tabella `LABEL`** (registro per account). Nessuna tabella ponte `MovementLabel`. | L'indice `MovementLabel` darebbe JOIN veloci e statistiche per label, ma va riallineato da **ogni** punto che scrive `note` (form, bulk-update, MCP, import): un punto dimenticato produce un disallineamento silenzioso e permanente. Con il solo registro l'unica fonte di verità resta il testo, quindi un disallineamento è impossibile per costruzione. Il prezzo è il filtro per label (§12): scansione, non indice. Accettabile su volumi familiari; se diventerà un problema, l'indice si aggiunge in un task successivo **senza** cambiare la semantica. |
| **D2** | Perimetro: form movimento, **spese ricorrenti**, **chip in elenco/ricerca**, **filtro per label**, **pagina Impostazioni**. | Correzione massiva e import/export **non** hanno UI delle label in questo task (ma registrano le label per via dell'hook, §7). Vedi §15. |
| **D3** | Le label orfane **restano** nel registro, e c'è una **pagina di gestione** in Impostazioni. | Cancellazione automatica delle orfane: farebbe sparire dall'autocompletamento le label storiche (`#vacanza2025`) proprio quando servono per rietichettare. |
| **D4** | **Forma canonica**: il registro conserva una sola grafia per label; al salvataggio la nota viene **riscritta** su quella grafia. `#Coop` con `#coop` già in registro → nella nota finisce `#coop`. | Preservare la grafia digitata: non crea doppioni (il match è case-insensitive) ma in elenco si vedrebbero chip `#Coop` e `#coop` per la stessa label. Forzare il minuscolo sempre: impedirebbe `#Vacanza2026`. |
| **D5** | Il campo a chip è un **Tom Select**, non un componente scritto a mano. | Vedi §9: è già nel progetto, già skinnato dark/light, e ha di serie i tre pezzi che servono (chip rimovibili, ricerca remota, creazione di un valore nuovo). |

### Default assunti (non discussi, correggibili in fase 0)

| # | Default |
|---|---|
| **P1** | Charset `[0-9A-Za-z_-]`, da **2 a 30** caratteri, **nessun accento**. |
| **P2** | La rimozione di una chip cancella **tutte** le occorrenze della label nel testo. |
| **P3** | La nota è l'unica fonte: le chip si riallineano mentre si digita nella textarea (evento `input`, debounce). |
| **P4** | Dropdown a max 10 risultati, ricerca a partire da **1** carattere digitato. |
| **P5** | Il backfill della migrazione popola `LABEL` scansionando le note dei movimenti esistenti. |
| **P6** | Max **10** label per movimento; la nota non può superare `MAX_NOTE_LENGTH` (500). |

---

## 3. Che cosa è una label — grammatica

Una label è `#` seguito da 2–30 caratteri in `[0-9A-Za-z_-]`, delimitata a
sinistra da inizio stringa o da un carattere che non è né di parola né `#` né
`-`, e a destra da fine stringa o da un carattere che non è di parola né `-`.
Il confronto è **case-insensitive**; la grafia memorizzata è quella canonica
(D4).

La regex trova **candidati**; è `is_valid()` a decidere, e aggiunge una regola
che la regex non esprime: la grafia **non può iniziare né finire con `-`**
(`#-coop` e `#coop-` non sono label, e non vengono troncate a `coop`). Un solo
punto di verità sulla validità, chiamato anche da `extract()`.

```python
# pyspendless/labels.py
LABEL_RE = re.compile(r'(?<![\w#-])#([0-9A-Za-z_-]{2,30})(?![\w-])')
```

```javascript
// static/js/ps-labels.js — stessa grammatica, senza lookbehind:
// Safari lo supporta solo da 16.4 e l'app è mobile-first.
const LABEL_RE = /(^|[^\p{L}\p{N}_#-])#([0-9A-Za-z_-]{2,30})(?![\p{L}\p{N}_-])/gu;
```

Il lookahead **non** si limita al charset della label (`[0-9A-Za-z_-]`) ma
copre tutti i caratteri di parola Unicode. È la differenza fra ignorare
`#città` e riconoscerci dentro una label `#cit`: la seconda sarebbe una
sorpresa pura per l'utente. Una label con accenti non è una label, e non viene
troncata.

Conseguenze volute, da verificare nei test:

| Testo | Label estratte | Perché |
|---|---|---|
| `#coop` | `coop` | — |
| `spesa #coop, pane` | `coop` | la virgola delimita, e resta nel testo |
| `(#coop)` | `coop` | parentesi delimitano |
| `##coop` | — | il `#` non è a inizio parola |
| `email#coop` | — | idem |
| `#coop#buoni` | `coop` | il secondo `#` è preceduto da una lettera |
| `#a` | — | sotto la lunghezza minima |
| `#1234` | `1234` | le sole cifre sono ammesse |
| `#città` | — | accento fuori charset, e niente troncamento |
| `#-coop`, `#coop-` | — | candidato scartato da `is_valid` |
| `#coop-bio` | `coop-bio` | `-` ammesso all'interno |
| `#coop #COOP` | `coop` (una) | dedup case-insensitive |

---

## 4. Modello dati

### `LABEL`

```python
class Label(Base):
    """Registro delle label di un account (task26-0).

    NON è un'associazione con i movimenti: l'appartenenza di una label a un
    movimento vive nel testo di Movement.note e solo lì (D1). Questa tabella
    serve all'autocompletamento, alla forma canonica (D4) e alla pagina di
    gestione.
    """
    __tablename__ = 'Label'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(Text, nullable=False)   # forma canonica, come va scritta nelle note
    name_norm  = Column(Text, nullable=False)   # name.lower(), chiave di unicità e di ricerca
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('account_id', 'name_norm', name='uq_label_account_name'),
    )

    account = relationship('Account', back_populates='labels')
```

`name_norm` è una colonna e non un `COLLATE NOCASE` o un indice su espressione:
l'unicità case-insensitive diventa un vincolo esplicito che non dipende dalla
collation del DBMS, e la ricerca `LIKE` del dropdown lavora su un valore già
normalizzato.

Su `Account` va aggiunto `labels = relationship('Label', back_populates='account')`.

### DDL e migrazione

- `sql/sqllite/create_label.sql` — **già scritto in Fase 0**, incluso in
  `create_all.sql`.
- `sql/sqllite/NEXT_RELEASE/create_label.sql` — **già scritto in Fase 0**: lo
  stesso `CREATE TABLE IF NOT EXISTS` più i due indici, da eseguire sul DB del
  server come per il task22-0. Idempotente e verificato; non tocca nessuna
  tabella esistente, quindi si può eseguire anche **prima** che il codice sia
  in produzione. `models.py` (Fase 2) deve combaciare con questo file.
- `migrations/backfill_labels.py` (nuovo) — scansiona `Movement.note` di tutti
  gli account e popola `LABEL`. **Idempotente** (`INSERT` solo se `name_norm`
  manca), eseguibile più volte. La grafia canonica scelta per ogni
  `(account_id, name_norm)` è quella del **movimento più vecchio**
  (`ORDER BY move_date, id`): deterministica e ripetibile. Il backfill **non**
  riscrive le note.

Il backfill è un passo manuale del rilascio (§19). Se lo si dimentica: le label
storiche non compaiono nell'autocompletamento finché un movimento non viene
risalvato — fallimento **degradato**, non rotto.

---

## 5. Il parser, in due copie

Le stesse funzioni servono in Python (server: registro, filtro, rinomina) e in
JavaScript (campo a chip, chip in elenco). Due implementazioni della stessa
grammatica sono un invito al disallineamento, quindi:

- `pyspendless/labels.py` (nuovo) — **funzioni pure**, nessun import di
  SQLAlchemy, nessuno stato:

| Funzione | Cosa fa |
|---|---|
| `is_valid(name)` | `name` **senza** `#`: charset e lunghezza. |
| `extract(note)` | label in ordine di prima comparsa, dedup case-insensitive, grafia come scritta. |
| `extract_norm(note)` | come sopra, minuscole. |
| `has_label(note, name)` | case-insensitive. |
| `add_label(note, name)` | append ` #name` in coda se assente; `note` vuota → `#name`. |
| `remove_label(note, name)` | rimuove **tutte** le occorrenze e normalizza gli spazi. |
| `rename_label(note, old, new)` | sostituisce tutte le occorrenze; se `new` era già presente, deduplica. |
| `canonicalize(note, mapping)` | `mapping` è `{name_norm: forma_canonica}`; riscrive le grafie (D4). |
| `normalize_space(text)` | collassa gli spazi multipli, toglie lo spazio prima della punteggiatura, `strip()`. |

- `pyspendless/static/js/ps-labels.js` (nuovo) — le stesse funzioni sotto
  `window.PsLabels`, con gli stessi nomi, più la parte di UI (§9, §11).

Il metro di misura è condiviso, non replicato: `pyspendless/test/fixtures/labels_cases.json`
contiene **112 casi** (`is_valid`, `extract`, `extract_norm`, `has_label`,
`add_label`, `remove_label`, `rename_label`, `canonicalize`, `normalize_space`)
usati sia da `test_task26_0.py` sia da `tools/probe-labels.html`, una paginetta
che esegue il JS sugli stessi casi e stampa PASS/FAIL. Il progetto non ha Node
(il binario `tools/tailwindcss` è una CLI standalone): la sonda JS si apre nel
browser, quindi la esegue **l'agente principale**, non un subagent.

I 112 casi sono stati validati in Fase 0 contro un'implementazione di
riferimento usa-e-getta (112/112), poi buttata: un metro che non può diventare
verde è peggio di nessun metro.

---

## 6. Normalizzazione degli spazi

Il requisito A3 ("eliminando `#coop`, `"Spesina #coop settimanale"` diventa
`"Spesina settimanale"`") significa che la rimozione non può essere una
semplice sostituzione con stringa vuota. `normalize_space` è l'unico punto che
decide, e vale per tutte le operazioni che toccano il testo:

| Prima | Label rimossa | Dopo |
|---|---|---|
| `Spesina #coop settimanale` | `coop` | `Spesina settimanale` |
| `#coop spesa` | `coop` | `spesa` |
| `spesa #coop` | `coop` | `spesa` |
| `spesa #coop, pane` | `coop` | `spesa, pane` |
| `#coop` | `coop` | `` (nota vuota: `Movement.note` è `nullable`) |
| `a #coop b #coop c` | `coop` | `a b c` |

---

## 7. Dove si registrano le label: un hook, in basso

`LabelRepository.sync_from_note(account_id, note) -> str` fa tre cose in una
volta, nella sessione del chiamante:

1. estrae le label dal testo;
2. per ognuna, trova o crea la riga in `LABEL` (per `name_norm`);
3. **restituisce la nota riscritta** con le grafie canoniche (D4).

Il valore restituito è quello che va salvato. L'hook si chiama **nel
repository**, non nelle rotte:

- `MovementRepository.create_movement`, `update_movement`, `bulk_update_movements`
- `RecurrentMovementRepository.create_recurrent_movement`, `update_recurrent_movement`

Così ogni scrittura di `note` registra le label senza che il chiamante lo sappia:
il form, `POST /api/movements`, l'import CSV (`/api/import/movements`), la
correzione massiva e il tool MCP `add_movement` (`mcp_server.py:606`) sono
coperti dallo stesso codice. È il motivo per cui l'API del form **non** riceve
un campo `labels`: manda solo `note`, come oggi.

**Concorrenza**: due membri dello stesso account che creano `#nuova`
contemporaneamente fanno scattare l'`UNIQUE` su `(account_id, name_norm)`.
`sync_from_note` cattura `IntegrityError`, fa `rollback` del savepoint e rilegge
la riga: la seconda scrittura riusa la label della prima. Da coprire con un test
che simula l'ordine (due sessioni, stessa label).

---

## 8. API

| Metodo | Rotta | Cosa fa |
|---|---|---|
| `GET` | `/api/labels?q=<str>&limit=10` | Autocompletamento. `LIKE %q%` su `name_norm`, prefix-match prima (`ORDER BY CASE WHEN name_norm LIKE 'q%' THEN 0 ELSE 1 END, name_norm`), `limit` max 50. Risposta `[{id, name}]`. **Senza** conteggi: costerebbe una scansione a ogni tasto. |
| `GET` | `/api/labels?with_counts=1` | Per la pagina Impostazioni: tutte le label dell'account con `movements_count`. **Una** query sui movimenti (`id, note`) e conteggio in Python con un `Counter`, non una query per label. |
| `PUT` | `/api/labels/<int:id>` | Body `{name}`. Rinomina: valida, riscrive le note dei movimenti coinvolti, aggiorna la riga. Se `name_norm` coincide con un'altra label → **merge** (§13). |
| `DELETE` | `/api/labels/<int:id>` | Rimuove la label dalle note dei movimenti coinvolti e cancella la riga. |

Tutte e quattro, per le lezioni del task24-0:

- 401 se `session['user_id']` manca;
- **verifica che `label.account_id == session['account_id']`** prima di
  qualunque scrittura (l'id in input non è fidato) → 404 se non combacia;
- `name` in input passa da `is_valid()` → 400, e **non** viene rimandato in
  pagina così com'è;
- `PUT` e `DELETE` in **una transazione**: o tutte le note sono riscritte, o
  nessuna.

---

## 9. Il campo a chip (Tom Select)

Tom Select è già caricato da CDN in `ps-show-mov.html:329` per il multi-select
delle categorie, ed è già skinnato light/dark in `ps-tailwind.src.css:776-810`
— compresa `.ts-dropdown .create`, cioè esattamente la voce "crea una label
nuova". Scrivere un combobox a mano significherebbe riscrivere chip rimovibili,
ricerca remota, navigazione da tastiera e ARIA già presenti e già testati.

Configurazione in `ps-labels.js`:

```javascript
new TomSelect('#labels', {
  plugins: ['remove_button'],
  valueField: 'name', labelField: 'name', searchField: 'name',
  create: true,                                   // label nuova digitandola
  createFilter: PsLabels.isValid,                 // stessa grammatica del server
  persist: false,
  shouldLoad: (q) => q.length >= 1,               // P4
  maxItems: 10,                                   // P6
  maxOptions: 10,                                 // P4
  load: (q, cb) => fetch('/api/labels?q=' + encodeURIComponent(q)) ...
});
```

Posizione nel form: **subito sotto** la textarea Nota, con l'hint "Le label
finiscono nella nota, scritte con `#`". Sotto e non sopra perché l'effetto di
una chip aggiunta è un testo che cambia: va visto, non indovinato.

Comportamento:

| Azione | Effetto sulla nota |
|---|---|
| Scelgo `#coop` dal dropdown | `PsLabels.addLabel(note, 'coop')` — append in coda se assente. |
| Digito `#nuova` e premo Enter | idem; la label nascerà in `LABEL` al salvataggio (§7), non prima. |
| Clic sulla `×` di una chip | `PsLabels.removeLabel(note, 'coop')` — tutte le occorrenze, spazi normalizzati (§6). |
| Scrivo `#coop` a mano nella textarea | le chip si riallineano all'evento `input` (debounce 150 ms). |
| Cancello `#coop` a mano dalla textarea | la chip sparisce, stesso evento. |

La textarea resta **completamente libera**: non è un campo di sola lettura, e
nessuna riscrittura avviene mentre si digita (solo al salvataggio, lato server,
per la forma canonica).

**Due trappole misurate in Fase 0** (sonda `tools/probe-labels.html`, 11
controlli verdi su Tom Select 2.3.1):

1. **`addItem()` su un valore non ancora caricato non fa nulla, e non solleva.**
   Le label arrivano dal `load()` remoto, quindi per aggiungere una chip da
   codice — cioè nel riallineamento dalla textarea — serve `addOption({name})`
   **prima** di `addItem(name)`. Senza, la chip non compare e non c'è nessun
   errore da cui accorgersene.
2. **`load()` è ritardato di 300 ms** (`loadThrottle`): non è sincrono.

Il resto delle assunzioni regge: `create: true` + `createFilter`,
`remove_button`, `maxItems: 10`, e l'init dentro a un contenitore
`display:none` che si ridimensiona correttamente alla comparsa (960 px su un
viewport di 1024). Resta comunque valido il precedente del progetto —
`initCategorySelect()` in `ps-show-mov.html:527` rimanda l'init alla prima
apertura del pannello per il **posizionamento del dropdown**: nel pannello
filtri (§12) si fa così.

**Rifiuti espliciti**, con messaggio sotto il campo: nome non valido (charset o
lunghezza), undicesima label (P6), nota che supererebbe `MAX_NOTE_LENGTH`.
`MAX_NOTE_LENGTH` oggi vive in `mcp_server.py:116` e vale solo per il canale
MCP: va spostata in `conf.py` e usata **anche** come `maxlength` della textarea,
altrimenti il limite esiste solo per Alexa e la UI può scrivere note che il
canale vocale non potrebbe.

**Degrado se il CDN non risponde**: `TomSelect` non è definito, il campo resta
un `<select>` inerte — ma la nota è la fonte di verità, quindi la textarea
continua a funzionare e il server registra comunque le label dal testo.
`ps-labels.js` deve quindi: verificare `typeof TomSelect`, e in sua assenza
nascondere il campo e **non** andare in errore (nessuna eccezione in console,
nessun blocco del submit).

---

## 10. API del form: nulla di nuovo

`POST /api/movements` ([app.py:863](../pyspendless/app.py)) continua a ricevere
`note` e nient'altro di nuovo. Il payload non guadagna un campo `labels`: le
label sono nel testo, e aggiungerle a parte creerebbe due fonti da conciliare.
Lo stesso vale per `/api/recurrent-movements`.

---

## 11. Chip in elenco e ricerca

Un unico renderer, `PsLabels.decorate(root)`, cerca gli elementi
`[data-ps-note]`, legge il **testo** del nodo e sostituisce le label con
`<a class="ps-label-chip" href="/movements?label=coop">#coop</a>`.

- Costruzione con nodi DOM e `textContent`, **mai** `innerHTML` concatenato:
  la nota è testo utente (una nota `<script>#coop</script>` non deve diventare
  markup). Il progetto ha già `escHtml` in `ps-show-mov.html:602` per le card.
- Punti di aggancio: `ps-show-mov.html:218` (cella della tabella), il renderer
  delle card mobile (`ps-show-mov.html:619`), e le due viste equivalenti di
  `ps-search-mov.html`.
- **DataTables ridisegna le celle** a ogni cambio pagina e ordinamento: il
  `decorate` va richiamato su `draw.dt`, non solo al `DOMContentLoaded`. Il
  testo visibile resta `#coop`, quindi la ricerca client di DataTables continua
  a funzionare.
- L'infinite scroll delle card (`/api/search-movements`) chiama `decorate` sul
  frammento appena appeso.
- Stile: nuova classe `.ps-label-chip` in `ps-tailwind.src.css`, derivata da
  `.ps-badge-neutral` (già presente, riga 551) con `cursor: pointer` e stato
  hover. **Ricordarsi `./tools/build-css.sh`.**

---

## 12. Filtro per label in `/movements`

Query string `?label=coop&label=buoni`, **AND** fra le label (semantica Jira:
ogni label restringe). È una scelta diversa da quella dei `keywords`, che sono
in OR (`repository.py:720`): va scritta nell'etichetta del filtro ("tutte le
label selezionate").

`_parse_movement_filters()` ([app.py:~500](../pyspendless/app.py)) guadagna
`labels: [...]` (validate con `is_valid`, le non valide si **ignorano in
silenzio**: è input non fidato) e `active_count` +1 se presenti. Essendo lo
stesso parser, il filtro arriva gratis all'export CSV e alla correzione massiva.

Il predicato SQL è il punto delicato di D1. `note LIKE '%#coop%'` prenderebbe
anche `#coopx`: serve il confine di parola, che SQLite non ha. Soluzione:
funzione SQL custom registrata sulla connessione, che chiama **lo stesso
parser Python**.

```python
# conf.py, accanto a get_db_engine()
@event.listens_for(_engine, "connect")
def _register_sqlite_functions(dbapi_conn, _rec):
    from labels import has_label
    fn = lambda note, name: 1 if (note and has_label(note, name)) else 0
    try:
        dbapi_conn.create_function("ps_has_label", 2, fn, deterministic=True)
    except TypeError:       # sqlite3 < 3.8.3: niente deterministic
        dbapi_conn.create_function("ps_has_label", 2, fn)
```

```python
for name in labels:
    query = query.filter(func.ps_has_label(Movement.note, name) == 1)
```

Vantaggio: una sola definizione di "la nota contiene questa label", condivisa
da filtro, rinomina ed eliminazione — impossibile che divergano.
Limiti, da scrivere nel codice:

- **vincola il progetto a SQLite** (`conf.py:61`: lo è già, anche in
  produzione). Un cambio di DBMS richiederebbe di riscrivere questo predicato
  (con `REGEXP`, o introducendo l'indice `MovementLabel` di D1).
- è una **scansione** delle righe che superano gli altri filtri (data, wallet,
  categoria), quindi il filtro per label va sempre applicato **dopo** gli altri
  nella stessa `WHERE`. Su volumi familiari (migliaia di movimenti) è
  irrilevante; è anche la prima cosa che si rompe se il DB cresce di ordini di
  grandezza, ed è lì che l'indice tornerebbe in discussione.

UI: un Tom Select multi-selezione nel pannello filtri già esistente, con le
stesse attenzioni delle categorie (init rimandato alla prima apertura del
pannello: inizializzarlo mentre il contenitore è `display:none` sbaglia
larghezze e dropdown, `ps-show-mov.html:527`).

---

## 13. Pagina `Impostazioni → Labels`

- Rotta `/settings/labels` (`settings_labels`), template `ps-setting-labels.html`,
  modellato su `ps-setting-categories.html`.
- Voce di nav dopo "Categorie", icona `bi-hash`. Aggiungere `/settings/labels`
  a `NAV_LINKS_ORDER` in `test_task19_0.py:276` e aggiornare il commento delle
  "13 destinazioni" in testa a `ps-nav.html`: il test ignora i link che non
  conosce, quindi senza questo passo la nuova voce non è coperta da nulla.
- Tabella: label, numero di movimenti, azioni.
- **Rinomina** (modal `PsModal`): mostra quanti movimenti verranno riscritti.
  Se la nuova grafia coincide (case-insensitive) con una label esistente, il
  modal lo dice esplicitamente — "#coop esiste già: i 12 movimenti di #coopp
  verranno uniti" — e la conferma esegue il **merge**: `rename_label` su tutte
  le note (deduplicando dove entrambe erano presenti), poi `DELETE` della riga
  sorgente.
- **Elimina**: conferma con il conteggio e la frase "la label verrà rimossa dal
  testo delle note di N movimenti". È un'operazione **irreversibile** sul testo
  degli utenti: la conferma non è una formalità.
- Nessuna creazione di label da questa pagina: una label nasce usandola.

---

## 14. Casi limite

| # | Caso | Comportamento atteso |
|---|---|---|
| 1 | `#coop` due volte nella stessa nota | una sola chip; la `×` rimuove entrambe le occorrenze |
| 2 | `##coop`, `email#coop`, `#coop#buoni` | §3: nessuna label, nessuna label, solo `coop` |
| 3 | `#città`, `#però` | nessuna label, e **nessun troncamento** a `#cit` |
| 4 | `#a` | non valida: resta testo, nessuna riga in `LABEL` |
| 5 | `#1234` | valida |
| 6 | Nota che resta vuota dopo la rimozione | `note` vuota/`NULL`: è già `nullable` |
| 7 | `#Coop` digitata, `#coop` in registro | al salvataggio la nota diventa `#coop` (D4) |
| 8 | Due membri creano `#nuova` insieme | `IntegrityError` → retry → riuso della riga esistente (§7) |
| 9 | Rinomina `#coopp` → `#coop` esistente | merge, con dedup nelle note che avevano entrambe |
| 10 | Rinomina con nome non valido | 400, **nessuna** nota riscritta |
| 11 | Elimina label con 0 movimenti | sparisce solo la riga del registro |
| 12 | Label su una spesa ricorrente | la nota copiata porta le label: nessuna logica aggiuntiva |
| 13 | Aggiunta che sforerebbe `MAX_NOTE_LENGTH` o la 10ª label | rifiuto con messaggio, nota invariata |
| 14 | `note IS NULL` | `ps_has_label` → 0; `extract(None)` → `[]` |
| 15 | CDN Tom Select irraggiungibile | campo nascosto, textarea funzionante, nessun errore in console (§9) |
| 16 | `?label=` con valore non valido o inesistente | ignorato / zero risultati, mai un 500 |
| 17 | Nota con `<script>#coop</script>` in elenco | chip rese come nodi DOM, nessuna esecuzione (§11) |
| 18 | Import CSV con `#x` nelle note | label registrate dall'hook del repository (§7), senza UI |
| 19 | Movimento salvato da MCP/Alexa con `#x` nel testo | idem |
| 20 | Export CSV | invariato: le label viaggiano dentro la colonna della nota |

---

## 15. Fuori perimetro (e i rischi che restano aperti)

| # | Cosa resta fuori | Rischio / nota |
|---|---|---|
| **R1** | **Correzione massiva** (`/api/movements/bulk-update`, task21-0): sostituisce integralmente la nota, quindi **cancella le label** dei movimenti filtrati. | Non lo risolviamo qui. Non nasce incoerenza (il registro non si svuota, e la nuova nota viene comunque parsata), ma l'utente perde le chip senza un avviso. Se dà fastidio nell'uso: voce `MB-NNN` con un'opzione "conserva le label esistenti". **Da dire nella pagina**, non da scoprire. |
| **R2** | Sintassi vocale per le label su MCP/Alexa. | Dettare "cancelletto coop" non è praticabile e inventare una sintassi vocale è un task a sé. Le label scritte nel testo funzionano già (§7). |
| **R3** | Statistiche e report **per label**. | Candidato naturale a task successivo; è anche il caso d'uso che giustificherebbe l'indice `MovementLabel` di D1. |
| **R4** | Colonna `labels` dedicata nell'export/import CSV. | Oggi viaggiano nella nota: nessuna perdita di informazione. |
| **R5** | Localizzazione delle stringhe nuove. | Il task25-0 è `PIANIFICATO`, non fatto: qui le stringhe si scrivono **in italiano**, come il resto dell'app. Se il task25-0 arriva prima, le stringhe di `ps-setting-labels.html`, del campo labels e dei messaggi delle API vanno avvolte in `_()` e il conteggio di `tools/check-i18n.py` va aggiornato. |

---

## 16. File toccati

**Già scritti (Fase 0)**

| File | Contenuto |
|---|---|
| `pyspendless/test/test_task26_0.py` | il metro, quattro sezioni (§18) |
| `pyspendless/test/fixtures/labels_cases.json` | 112 casi condivisi Python/JS (§5) |
| `tools/probe-labels.html` | sonda JS + verifica delle assunzioni Tom Select (§5, §9) |
| `sql/sqllite/create_label.sql`, `sql/sqllite/NEXT_RELEASE/create_label.sql` | DDL, idempotente (§4) |
| `.claude/agents/ps-labels-py.md` | profilo dell'agente per le fasi 1-3 |
| `.claude/launch.json` | configurazione `probe` (server statico per la sonda) |
| `sql/sqllite/create_all.sql` | aggiunta la nuova tabella (e `RecurrentMovement`, che mancava) |

**Da scrivere**

| File | Contenuto | Fase |
|---|---|---|
| `pyspendless/labels.py` | parser e manipolazione del testo (§5) | 1 |
| `migrations/backfill_labels.py` | backfill del registro (§4) | 2 |
| `pyspendless/static/js/ps-labels.js` | gemello JS + campo a chip + `decorate` (§5, §9, §11) | 4 |
| `pyspendless/templates/ps-setting-labels.html` | scheletro in Fase 3, pagina vera in Fase 7 (§13) | 3, 7 |

**Modificati**

| File | Che cosa |
|---|---|
| `pyspendless/models.py` | `Label`, `Account.labels` |
| `pyspendless/repository.py` | `LabelRepository`; hook `sync_from_note` in `MovementRepository` (create/update/bulk) e `RecurrentMovementRepository`; filtro `labels` in `get_movements`/`search_movements` |
| `pyspendless/conf.py` | `ps_has_label` sulla connessione (§12); `MAX_NOTE_LENGTH` e `MAX_LABELS_PER_MOVEMENT` |
| `pyspendless/mcp_server.py` | `MAX_NOTE_LENGTH` importata da `conf.py` invece che definita qui |
| `pyspendless/app.py` | `/api/labels` (GET/PUT/DELETE), `/settings/labels`, `labels` in `_parse_movement_filters`, bump `_APP_VERSION` |
| `pyspendless/templates/ps-add-mov.html` | campo labels + script Tom Select/`ps-labels.js` |
| `pyspendless/templates/ps-recurrent-mov.html` | idem |
| `pyspendless/templates/ps-show-mov.html` | chip nelle note (tabella + card), filtro label nel pannello filtri |
| `pyspendless/templates/ps-search-mov.html` | chip nelle note (tabella + card) |
| `pyspendless/templates/ps-nav.html` | voce "Labels" in Impostazioni |
| `pyspendless/static/css/ps-tailwind.src.css` | `.ps-label-chip` (+ `./tools/build-css.sh`) |
| `pyspendless/test/test_task19_0.py` | `/settings/labels` in `NAV_LINKS_ORDER` |
| `backlog/features.md` | riga del task (fatto) |
| `pyspendless/test/test_task19_0.py` | `/settings/labels` in `NAV_LINKS_ORDER` (Fase 7) |

---

## 17. Fasi e delega

Metodo del task19-0 e del task25-0: il grosso delegato a **subagent su haiku**,
ogni fase delegata con un criterio di "fatto" che è un **exit code**, non un
giudizio. L'app resta funzionante alla fine di ogni fase, e ogni fase si chiude
con un commit (un subagent in worktree parte da `HEAD`).

Le istruzioni operative sono in `fasi/fase-N.md`: qui c'è solo la mappa.

| Fase | Contenuto | Chi | "Fatto" = |
|---|---|---|---|
| **0** ✅ | Fixture (112 casi), `test_task26_0.py`, `tools/probe-labels.html`, DDL, profilo agente | **principale** | fatta il 2026-11-08: il test gira ed è rosso (0/17) |
| **1** ✅ | `labels.py` — solo funzioni pure | `ps-labels-py` (haiku) | fatta: `parser` → exit 0 (12 controlli) |
| **2** ✅ | `models.Label`, `conf.register_sqlite_functions`, `LabelRepository`, hook nei repository, filtro, backfill | `ps-labels-py` | fatta: `repo` → exit 0 (30 controlli) |
| **3** ✅ | `/api/labels` (GET/PUT/DELETE), `?label=` nei filtri, rotta `/settings/labels` | `ps-labels-py` | fatta: `api` → exit 0 (19 controlli) |
| **4** ✅ | `ps-labels.js`: Tom Select, sync con la textarea, `decorate` | `ps-component` | fatta: `node tools/check-labels-js.mjs` → exit 0 (10 gruppi) e sonda 23/23 nel browser |
| **5** ✅ | Campo labels in `ps-add-mov.html` e `ps-recurrent-mov.html` | `ps-markup` (due invocazioni, in parallelo) | fatta: `contract` verde sui due form, `test_task19_0.py` exit 0 |
| **6** ✅ | Chip read-only in `ps-show-mov.html` e `ps-search-mov.html`, filtro nel pannello | `ps-markup` (due invocazioni, in parallelo) | fatta: `contract` verde sui due elenchi, `test_task19_0.py` exit 0 |
| **7** ✅ | Pagina `Impostazioni → Labels`, voce nav, `NAV_LINKS_ORDER` | `ps-markup` | fatta: `contract` 20/20, `api` e `test_task19_0.py` exit 0 |
| **8** 🔶 | `./tools/build-css.sh` ✅, verifica visiva light/dark e mobile ✅ (end-to-end sul DB reale di sviluppo), bump versione e rilascio **in attesa della UAT dell'utente** | **principale** | tutte le sezioni verdi, build deterministica |

Dipendenze: 1 → 2 → 3 → 4 → (5, 6, 7) → 8. Le fasi 5, 6 e 7 toccano file
disgiunti: parallelizzabili, se eseguite su worktree separati.

Le fasi 0, 4 (verifica) e 8 **non si delegano**: la prima scrive il metro di
misura delle altre, le altre due richiedono il browser.

---

## 18. Test

Il progetto **non usa pytest né unittest**: `test_task22_0.py` e
`test_task23_0.py` sono script con una classe `Checker` e `sys.exit()`.
`pyspendless/test/test_task26_0.py` segue quella convenzione, su SQLite
in-memory, con **quattro sezioni selezionabili** da riga di comando:

```bash
cd pyspendless
.venv/bin/python test/test_task26_0.py parser     # Fase 1
.venv/bin/python test/test_task26_0.py repo       # Fase 2
.venv/bin/python test/test_task26_0.py api        # Fase 3
.venv/bin/python test/test_task26_0.py contract   # Fasi 4-7
.venv/bin/python test/test_task26_0.py            # tutte
```

- **`parser`** — i 112 casi delle fixture, più tre vincoli strutturali
  (`labels.py` senza dipendenze, costanti, idempotenza).
- **`repo`** — `sync_from_note` crea/riusa/canonicalizza; l'hook scatta da
  `create_movement`, `update_movement`, `bulk_update_movements` e dalle
  ricorrenti; `ps_has_label` distingue `#coop` da `#coopx`; filtro in AND;
  `get_movements_stats` coerente; rinomina, merge, eliminazione, conteggi;
  **corsa fra due sessioni** sul vincolo `UNIQUE`; backfill idempotente e
  deterministico.
- **`api`** — 401 senza sessione; **404 su label di un altro account** (il caso
  del task24-0); 400 su nome non valido; rinomina con note riscritte;
  eliminazione; `?label=` che filtra, in AND, anche su export; `?label=` non
  valida ignorata senza 500; `POST /api/movements` che registra la label **senza
  campo `labels` nel payload**; `/settings/labels` a 200.
- **`contract`** — `ps-labels.js` espone il contratto e non usa lookbehind;
  `data-ps-labels` nei due form; `data-ps-note` nei due elenchi; `draw.dt`;
  voce di nav e `NAV_LINKS_ORDER`; `MAX_NOTE_LENGTH` solo in `conf.py`; e
  `.ps-label-chip` presente **sia** nel `.src.css` **sia** nel `ps-tailwind.css`
  compilato — il controllo che cattura la build del CSS dimenticata.

Le sezioni sono indipendenti: una fase può lavorare con la propria rossa e le
precedenti verdi. Finché una fase non esiste, la sua sezione fallisce con **una**
riga che dice cosa manca.

Fuori dallo script, due metri per il lato JavaScript:

- `node tools/check-labels-js.mjs` — i 112 casi contro `window.PsLabels`, exit
  code. **Node è uno strumento locale**, come `tools/tailwindcss`: il progetto
  non ne dipende, sul server non c'è, e nulla nel repo lo richiede a runtime.
  Perché funzioni, `ps-labels.js` deve poter essere caricato **senza DOM** — lo
  stesso vincolo che gli serve per degradare quando il CDN non risponde.
- `tools/probe-labels.html` — la metà di UI (campo a chip, `decorate`, le
  assunzioni su Tom Select), da aprire nel browser.

Più la verifica visiva della Fase 8.

---

## 19. Rilascio

Oltre alla procedura standard di `CLAUDE.md` (build CSS → bump `_APP_VERSION` →
commit → tag → push → `git pull` + Reload sul server), questo task ha **due
passi di schema** sul server, da eseguire nella console Bash di PythonAnywhere
dopo il `git pull` e **prima** del Reload:

```
sqlite3 /home/tabuto/data/pyspendless3.db < sql/sqllite/NEXT_RELEASE/create_label.sql
python migrations/backfill_labels.py
```

Nessuna nuova dipendenza Python: niente `pip install`, nessun rischio di quota
disco (il nodo che ha reso il task25-0 un gate non si ripresenta qui).

Se si dimentica il `CREATE TABLE`: ogni salvataggio di movimento va in errore —
fallimento **rotto**, non degradato. Se si dimentica solo il backfill: le label
storiche non compaiono nell'autocompletamento finché i movimenti non vengono
risalvati — fallimento **degradato**.

### Passo facoltativo: le parole-tag dello storico

Prima del task26-0 le etichette si scrivevano senza cancelletto
(`"Parcheggio tirana balcani2025"`): per la grammatica non sono label, quindi
quei movimenti non si filtrano. `migrations/add_labels_from_words.py` appende
`#parola` in fondo alle note che contengono una delle parole di un elenco
approvato — ricavato con un'euristica (parola in fondo alla nota, che si
ripete, che taglia più categorie, concentrata nel tempo) e **rivisto a mano
dall'utente** il 09/11/2026: 10 voci, 194 movimenti sul database di sviluppo.
Fra queste `sudafrica` → `#sudafrica2026`, perché quelle spese appartengono a
un viaggio già etichettato con un altro nome.

Lo script **non riscrive la parola nuda**, aggiunge solo il tag in coda: in una
migrazione a senso unico si tocca il minimo indispensabile. Gira in **sola
simulazione** per default, chiede conferma con `--apply`, ed è idempotente.
**Non è reversibile**: prima va fatta una copia del database.

Va eseguito **sia** in locale **sia** sul server, altrimenti i due archivi
divergono.
