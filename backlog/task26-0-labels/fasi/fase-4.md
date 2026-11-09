# Fase 4 — `ps-labels.js` (il componente)

**Chi**: subagent **`ps-component`** (il profilo del task19-0: replica
comportamenti esistenti, non ne inventa).
**Dipende da**: Fase 3 verde (il componente chiama `/api/labels`).
**Fatto quando**: due criteri, uno per metà.

1. **La grammatica**, da riga di comando, exit code:

```bash
node tools/check-labels-js.mjs
```

I 112 casi delle fixture contro `window.PsLabels`, gli stessi del lato Python.
Node **non** è una dipendenza del progetto — sul server non c'è e nulla nel
repo lo richiede a runtime: è uno strumento locale come `tools/tailwindcss`.
Perché funzioni, `ps-labels.js` deve poter essere **caricato in un ambiente
senza DOM**: all'import non tocca `document` e non assume `TomSelect`. È lo
stesso vincolo che gli serve in produzione per degradare quando il CDN non
risponde (§4.4).

2. **La UI** (campo a chip, sincronizzazione, `decorate`), nel browser:
`tools/probe-labels.html` tutto verde e console pulita. La sonda la apre
**l'agente principale**, non tu:

```bash
# configurazione "probe" di .claude/launch.json
# poi http://localhost:8765/tools/probe-labels.html
```

**File che puoi toccare**: `pyspendless/static/js/ps-labels.js` (nuovo),
`pyspendless/static/css/ps-tailwind.src.css` (solo `.ps-label-chip`).

## 4.1 Le funzioni, gemelle di `labels.py`

`window.PsLabels` espone, in camelCase, le stesse funzioni del modulo Python —
`isValid`, `extract`, `extractNorm`, `hasLabel`, `addLabel`, `removeLabel`,
`renameLabel`, `canonicalize`, `normalizeSpace` — con lo **stesso** contratto
(la tabella è in `fase-1.md`, i casi sono in
`pyspendless/test/fixtures/labels_cases.json`, e la sonda li esegue tutti).

**Senza lookbehind**: Safari lo supporta solo da 16.4 e l'app è mobile-first.

```javascript
const LABEL_RE = /(^|[^\p{L}\p{N}_#-])#([0-9A-Za-z_-]{2,30})(?![\p{L}\p{N}_-])/gu;
// gruppo 1 = il carattere di contesto consumato, gruppo 2 = il nome
```

Il contesto consumato non crea problemi fra due label consecutive (`#a #bb`):
condividono un solo carattere delimitatore, che serve alla seconda e non alla
prima. Ma attenzione a **dove inizia la label**: `m.index` punta al carattere
di contesto, non al `#`. La posizione del `#` è `m.index + m[1].length`, e la
fine è quella posizione più `1 + nome.length`. Conviene che una funzione
interna restituisca la lista dei match come `{start, end, name}` e che
`removeLabel`, `renameLabel` e `canonicalize` ricostruiscano la stringa a
pezzi da quelle posizioni: è l'unico punto in cui il lato JS è più scomodo del
Python, e sbagliarlo mangia il carattere prima della label.

Verificato in Fase 4: con questo schema i 112 casi passano in JS senza
lookbehind.

## 4.2 Il campo a chip

`PsLabels.initField(el)` su ogni `[data-ps-labels]`, con
`data-ps-labels-target="#note"` che punta alla textarea.

```javascript
new TomSelect(select, {
  plugins: ['remove_button'],
  valueField: 'name', labelField: 'name', searchField: 'name',
  create: true, createFilter: PsLabels.isValid, persist: false,
  shouldLoad: (q) => q.length >= 1,
  maxItems: 10, maxOptions: 10,
  load: (q, cb) => { /* GET /api/labels?q= */ }
});
```

Sincronizzazione, nei due versi:

| Evento | Azione |
|---|---|
| `item_add` | `textarea.value = PsLabels.addLabel(textarea.value, name)` |
| `item_remove` | `textarea.value = PsLabels.removeLabel(textarea.value, name)` |
| `input` sulla textarea (debounce **150 ms**) | ricalcola le chip da `PsLabels.extract(textarea.value)` |

Il riallineamento dalla textarea è il punto delicato: **sospendi i listener**
mentre riscrivi le chip, o `item_add` rimette mano alla textarea e parte un
ciclo.

## 4.3 Le due trappole di Tom Select (misurate in Fase 0, non supposte)

1. **`addItem()` su un valore non ancora caricato non fa nulla, e non solleva.**
   Le label arrivano dal `load()` remoto, quindi nel riallineamento serve
   `addOption({name})` **prima** di `addItem(name)`. Senza, la chip non compare
   e non c'è nessun errore da cui accorgersene.
2. **`load()` è ritardato di 300 ms** (`loadThrottle`). Non scrivere logica che
   assume una risposta sincrona.

E una terza, ereditata dal progetto: nel pannello filtri di `/movements`
(Fase 6) l'init va **rimandato alla prima apertura** del pannello, come
`initCategorySelect()` in `ps-show-mov.html:527`. Nella sonda, con un viewport
reale, il campo inizializzato dentro a un contenitore `display:none` si
ridimensiona correttamente quando il contenitore compare (960 px su 1024) — ma
il posizionamento del dropdown resta il motivo per cui il progetto rimanda
l'init, e quel precedente si rispetta.

## 4.4 Degrado se il CDN non risponde

```javascript
if (typeof TomSelect === 'undefined') { /* nascondi il campo, esci */ }
```

Nessuna eccezione in console, nessun blocco del submit: la nota è la fonte di
verità, quindi la textarea resta usabile e il server registra comunque le label
dal testo. Il test `contract` verifica che la stringa `typeof TomSelect`
compaia nel file.

## 4.5 I rifiuti, con messaggio

Tre casi, con un messaggio sotto il campo (non un `alert()`): grafia non valida
("solo lettere, numeri, `_` e `-`, da 2 a 30 caratteri"), undicesima label,
nota che supererebbe `MAX_NOTE_LENGTH` (500).

## 4.6 `PsLabels.decorate(root)`

Cerca `[data-ps-note]`, legge il **testo** del nodo e lo sostituisce con una
sequenza di nodi: testo normale + `<a class="ps-label-chip" href="/movements?label=coop">#coop</a>`.

**Nodi DOM e `textContent`, mai `innerHTML` concatenato**: la nota è testo
utente, e una nota `<script>#coop</script>` non deve diventare markup. La sonda
lo verifica con una nota ostile.

`.ps-label-chip` in `ps-tailwind.src.css`: derivata da `.ps-badge-neutral`
(riga ~551) più `cursor: pointer` e uno stato hover. **La build del CSS non è
tua**: la fa l'agente principale in Fase 8 (`./tools/build-css.sh`). Tu tocchi
solo il `.src.css`.
