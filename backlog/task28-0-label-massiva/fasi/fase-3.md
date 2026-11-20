# Fase 3 — Il campo a chip nella modale

**Chi**: subagent **`ps-ui`** (haiku).
**Dipende da**: Fase 2 (`api` verde: la rotta accetta `add_labels` e la pagina
riceve i due limiti).
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task28_0.py contract`
esce con **exit code 0**, `repo` e `api` restano verdi, e
`node tools/check-labels-js.mjs` esce `0` (la grammatica JS deve restare
allineata a `labels.py`).
**File che puoi toccare**: `pyspendless/static/js/ps-labels.js`,
`pyspendless/templates/ps-show-mov.html`,
`pyspendless/templates/ps-setting-labels.html`. **Nient'altro** — non il
Python, non il CSS compilato (la ricompilazione è della Fase 4), non il test.

## Il mandato

### 1. `ps-labels.js` — modalità standalone di `initField`

Oggi `initField(el)` ([ps-labels.js:272](../../../pyspendless/static/js/ps-labels.js))
pretende una textarea:

```js
var textarea = targetSel ? document.querySelector(targetSel) : null;
if (!textarea) return; // markup incompleto: niente da sincronizzare
```

Il campo della correzione massiva **non ha** una textarea da sincronizzare: le
label non si scrivono in un testo unico, le aggiunge il server a ciascuna nota.
Quindi: quando `data-ps-labels-target` **manca** (campo marcato
`data-ps-labels-standalone`), il campo è la fonte di verità di sé stesso.

Cosa cambia in quel ramo, e **solo** in quel ramo:

| Elemento | Standalone |
|---|---|
| Tom Select | stessa configurazione di oggi: `remove_button`, `valueField/labelField/searchField: "name"`, `create: true`, `persist: false`, `shouldLoad >= 1`, `load` su `/api/labels` |
| `createFilter` | `isValid(input)` **+** il limite `labelsMax`, con gli stessi due messaggi di oggi. **Niente** controllo su `noteMax`: non c'è una nota da misurare, il limite lo applica il server per movimento (`task28-spec.md` §6) |
| sincronizzazione | **nessuna**: niente `resyncFromTextarea`, niente listener `input`/`reset`, niente `item_add`/`item_remove` che scrivono altrove |
| ritorno | `initField` restituisce l'istanza Tom Select (anche nel ramo con textarea: un `return ts` in fondo serve a entrambi) |

Il degrado resta quello di oggi, invariato: se `TomSelect` non è definito (CDN
giù) si nasconde `[data-ps-labels-wrap]` e si esce — criterio A11, e il resto
della modale continua a funzionare.

Due vincoli del file che non vanno persi:

- **deve caricarsi senza DOM**: `tools/check-labels-js.mjs` lo importa in Node.
  Niente accesso a `document` fuori dalle funzioni;
- **la grammatica (parte 1 del file) non si tocca.** Se ti sembra che manchi
  qualcosa lì, fermati e dillo: quelle funzioni sono il gemello di `labels.py`
  e hanno 112 casi condivisi.

### 2. `ps-show-mov.html` — il campo nella modale

Dopo il blocco "Nuova descrizione"
([ps-show-mov.html:293](../../../pyspendless/templates/ps-show-mov.html)), dentro
`#bulkEditModal`:

```html
<div class="mb-3" data-ps-labels-wrap>
  <label for="bulk-labels" class="ps-label">Aggiungi label</label>
  <select id="bulk-labels" multiple
          data-ps-labels-standalone
          data-ps-labels-max="{{ max_labels_per_movement }}"></select>
  <p class="ps-help" data-ps-labels-message hidden></p>
  <p class="ps-help">
    Le label si <strong>aggiungono</strong> alla nota di ogni movimento: il
    testo esistente non si perde.
  </p>
</div>
```

**`data-ps-labels-standalone`, e non `data-ps-labels`**: l'auto-attivazione in
fondo a `ps-labels.js` ([ps-labels.js:471](../../../pyspendless/static/js/ps-labels.js))
cerca `[data-ps-labels]` al `DOMContentLoaded`, quando il `<dialog>` è chiuso e
quindi `display:none`. Tom Select costruito in un contenitore nascosto calcola
larghezza e posizione del dropdown sbagliate: è la stessa trappola per cui il
multi-select delle categorie e quello delle label dei filtri aspettano
`shown.bs.collapse` ([ps-show-mov.html:634](../../../pyspendless/templates/ps-show-mov.html)).

Quindi l'init si lega all'apertura della modale, dentro il blocco
`── Correzione massiva ──` ([ps-show-mov.html:493](../../../pyspendless/templates/ps-show-mov.html)):

```js
let tsBulkLabels = null;
document.getElementById('bulkEditModal').addEventListener('shown.bs.modal', function () {
  if (tsBulkLabels || typeof PsLabels === 'undefined') return;
  tsBulkLabels = PsLabels.initField(document.getElementById('bulk-labels'));
  if (tsBulkLabels) {
    tsBulkLabels.on('change', updateApplyState);
  }
}, { once: false });
```

`shown.bs.modal` è emesso da `ps-ui.js`
([ps-ui.js:171](../../../pyspendless/static/js/ps-ui.js)) a fine animazione, con
il pannello già visibile: è il momento giusto. La guardia `if (tsBulkLabels)`
serve perché la modale si apre più volte e `once: true` sull'ascoltatore
sarebbe fragile se un giorno l'init fallisse al primo giro.

### 3. `ps-show-mov.html` — Applica, payload, esito

| Punto | Cosa cambia |
|---|---|
| `updateApplyState` | si abilita con categoria **o** nota **o** almeno una chip: `const hasLabels = tsBulkLabels && tsBulkLabels.items.length > 0;` |
| `confirm(...)` | nomina le label scelte quando ce ne sono: l'utente deve leggere *che cosa* sta per aggiungere prima di confermare (R5 della specifica) |
| payload | `if (hasLabels) body.add_labels = tsBulkLabels.items.slice();` |
| risposta | se `result.skipped > 0`, un `alert` prima del reload: `'Aggiornati N movimenti. M lasciati intatti: nota troppo lunga o troppe label.'` Poi `window.location.reload()` come oggi |

Il ramo d'errore resta identico (messaggio da `result.error`, `applyBtn`
riabilitato): non riscriverlo.

### 4. `ps-setting-labels.html` — l'avviso

[Riga 13](../../../pyspendless/templates/ps-setting-labels.html) oggi dice che la
correzione massiva "sostituisce integralmente la nota, quindi rimuove tutte le
label dei movimenti filtrati". Resta vero **della sostituzione della nota**, e
non è più tutta la verità. Riscrivilo in due frasi: il campo "Aggiungi label"
aggiunge senza perdere niente; il campo "Nuova descrizione" sostituisce la nota
e quindi rimuove le label dei movimenti filtrati.

Non cambiare la classe dell'avviso (`ps-alert ps-alert-warning`) e non
spostarlo: è markup che esiste già e il CSS compilato lo copre.

## Vincoli di presentazione

- **Classi Tailwind già in uso**, nessuna classe inventata: `mb-3`, `ps-label`,
  `ps-help`, `ps-alert*` sono tutte presenti nella pagina. Se finisci per
  scriverne una nuova, **dillo nel riepilogo**: significa che la Fase 4 deve
  ricompilare il CSS (`./tools/build-css.sh`), e quel passo non è tuo.
- **Dark mode**: il campo a chip di Tom Select nella pagina `/movements` è già
  stilato (i `<link>` del tema e lo skin stanno in testa al template). Non
  aggiungere colori inline: è esattamente così che è nato `MB-012` (il campo
  labels scriveva scuro su scuro).
- **Niente `bootstrap.`**: il conteggio in `ps-show-mov.html` è **0** e deve
  restare 0. Lo shim in `ps-ui.js` è debito tenuto in vita per i call site da
  migrare, non un'API da usare.

Se un caso del metro ti sembra sbagliato, **fermati e dillo**: non si modifica
il test.
