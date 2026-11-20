# Task 28.0 — Aggiunta di una label nella correzione massiva

**Stato**: **PIANIFICATO** — specifica scritta, nessuna riga di codice.
**Data**: 2026-11-20 (specifica)
**Piano per fase**: `fasi/fase-0.md` … `fasi/fase-4.md` in questa cartella. La
specifica dice *cosa e perché*, i file di fase dicono *chi fa cosa e come si
verifica*.
**Versione app di partenza**: `_APP_VERSION = "0.4.1"` ([app.py:38](../../pyspendless/app.py))
**Repo**: `tabuto/pyspendless3`, branch `main`.
**Dipende da**: task26-0 (labels), **implementato**: `labels.py`,
`LabelRepository`, `ps-labels.js` e il registro `LABEL` ci sono già. Questo task
non li ridisegna, li usa.
**Interferisce con**: task25-0 (localizzazione, `PIANIFICATO`): introduce 4
stringhe nuove in 2 template. Vedi §10 R3.
**Nuove dipendenze**: **nessuna**. Nessuna migrazione, nessuna colonna nuova.
**Vincolo di ambiente**: il virtualenv del progetto è **Python 3.9**
(`pyspendless/.venv`): niente `match`, niente `str | None` nelle annotazioni.

---

## 1. Obiettivo

Permettere di **aggiungere una o più label** a tutti i movimenti che soddisfano
i filtri correnti di `/movements`, dalla stessa modale della correzione massiva
che oggi cambia categoria e descrizione.

Il vincolo che decide tutto il resto:

> **Aggiungere non è sostituire: la nota di ogni movimento resta la sua.**

Oggi l'unico modo di mettere una label in blocco è riscrivere la nota — che è
esattamente il rischio R1 del task26-0 (`task26-spec.md` §15): la correzione
massiva sostituisce integralmente la nota e **cancella** le label dei movimenti
filtrati. Per questo l'operazione nuova non può passare dal campo "Nuova
descrizione": non esiste un testo unico da applicare a N movimenti con N note
diverse. L'append avviene **per movimento**, lato server, con la stessa funzione
pura che usa il form del singolo movimento (`labels.add_label`).

### Criteri di accettazione

| # | Criterio |
|---|---|
| A1 | Con 3 movimenti filtrati che hanno note diverse, aggiungere `#casa` lascia a ciascuno il suo testo e gli aggiunge ` #casa` in coda. |
| A2 | Un movimento senza nota (`NULL` o `''`) diventa `#casa`. |
| A3 | L'operazione è idempotente: rilanciarla non raddoppia la label, e un movimento che ha già `#CASA` non viene riscritto (la grafia esistente non si tocca). |
| A4 | Si possono aggiungere più label in una sola operazione, nell'ordine in cui sono state scelte. |
| A5 | Le label nuove finiscono nel registro `LABEL` dell'account (una riga per label, grafia canonica) e quelle esistenti riusano la grafia del registro. Il registro si interroga **una volta per operazione**, non una volta per movimento. |
| A6 | Un movimento la cui nota supererebbe `MAX_NOTE_LENGTH`, o che ha già `MAX_LABELS_PER_MOVEMENT` label, viene **saltato** e non modificato; la risposta dice quanti sono stati saltati e l'interfaccia lo riporta. |
| A7 | Un nome di label non valido nel payload è un **400**, non un'omissione silenziosa. |
| A8 | Aggiungere label **non** richiede il filtro per tipo (Entrata/Uscita): quel vincolo riguarda il cambio di categoria e resta solo lì. |
| A9 | La risposta conserva il campo `updated` con il significato di oggi; `skipped` e `labels` si aggiungono. Nessun chiamante esistente cambia comportamento. |
| A10 | Il campo a chip della modale ha la stessa grammatica e gli stessi rifiuti del form movimento (riuso di `ps-labels.js`, non una seconda implementazione). |
| A11 | Senza JavaScript o con il CDN di Tom Select giù, la modale continua a fare quello che fa oggi (categoria + descrizione): il campo label si nasconde, non blocca l'Applica. |
| A12 | Isolamento per account (task24-0): i filtri restano quelli della sessione, la label viene registrata solo nell'account chiamante, e i movimenti di altri account non si toccano. |

---

## 2. Che cosa c'è già (ricognizione del 2026-11-20)

Cinque fatti del codice attuale su cui si appoggia tutto. Nessuno va cambiato.

| Dove | Fatto |
|---|---|
| [app.py:932](../../pyspendless/app.py) | `POST /api/movements/bulk-update` legge `category_id` e `note` dal JSON, prende i filtri dalla **query string** con `_parse_movement_filters()` ([app.py:493](../../pyspendless/app.py)) e risponde `{'updated': N}`. È l'unico punto da estendere lato rotte. |
| [repository.py:1095](../../pyspendless/repository.py) | `MovementRepository.bulk_update_movements(account_id, filters, category, category_id, note)` rilegge i movimenti con `get_movements_for_account(**filters)`, assegna gli stessi valori a tutti e fa **un solo** `commit()`. L'unico chiamante è la rotta sopra. |
| [repository.py:682](../../pyspendless/repository.py) | `LabelRepository.sync_from_note(account_id, note)` estrae le label da un testo, crea o riusa le righe `LABEL` (con savepoint sul vincolo UNIQUE) e **ritorna la nota canonicalizzata**. Costa da 1 a N query: va chiamata una volta, non per movimento. |
| [labels.py](../../pyspendless/labels.py) | `add_label(note, name)` è già esattamente la semantica che serve: append in coda, idempotente case-insensitive, `None`/`''` → `#name`. Non va scritta, va usata. |
| [ps-labels.js:272](../../pyspendless/static/js/ps-labels.js) | `initField(el)` costruisce il campo a chip su Tom Select con la grammatica del server, la ricerca su `/api/labels`, la creazione al volo e i rifiuti con messaggio sotto il campo. **Pretende** una textarea (`data-ps-labels-target`) e, se non la trova, esce senza fare nulla. È il solo punto del componente da estendere. |

E un sesto fatto, che è il motivo per cui questo task esiste:
[ps-setting-labels.html:13](../../pyspendless/templates/ps-setting-labels.html)
avvisa l'utente che la correzione massiva **cancella** le label. Dopo questo
task l'avviso va riscritto: resta vero per la sostituzione della nota, non è più
tutta la verità.

---

## 3. Il contratto dell'API

`POST /api/movements/bulk-update?<filtri>` — un campo nuovo nel body:

```json
{
  "category_id": 3,
  "note": "testo nuovo",
  "add_labels": ["casa", "Bollette"]
}
```

| Campo | Regola |
|---|---|
| `add_labels` | lista di stringhe, 1..`MAX_LABELS_PER_MOVEMENT` elementi. Un `#` iniziale si accetta e si toglie. Ogni nome passa per `labels.is_valid`. |
| validazione | serve **almeno uno** fra `category_id`, `note`, `add_labels` (oggi: almeno uno fra i primi due). |
| non una lista | `400` `{'error': 'add_labels deve essere una lista di nomi'}`. |
| nome non valido | `400` `{'error': 'Label non valida: <nome>'}` — e **nessun** movimento viene scritto. |
| troppi nomi | `400` con il limite nel messaggio. |

Risposta `200`:

```json
{"updated": 42, "skipped": 2, "labels": ["casa", "bollette"]}
```

- `updated`: movimenti che soddisfano i filtri e sono stati scritti — **lo
  stesso significato di oggi**;
- `skipped`: movimenti lasciati intatti per i limiti di §6;
- `labels`: le grafie **canoniche** applicate (quelle del registro, che possono
  differire da quelle digitate). Serve all'interfaccia per dire *che cosa* ha
  aggiunto, e al test per verificare il riuso del registro.

Il vincolo "per cambiare categoria filtra prima per tipo"
([app.py:960](../../pyspendless/app.py)) **non** si estende alle label: resta
legato alla presenza di `category_id` (A8).

---

## 4. La regola, per movimento

Nel repository, un parametro in più e un solo punto che decide:

```python
def bulk_update_movements(self, account_id, filters, category=None,
                          category_id=None, note=None, add_labels=None):
```

Per ogni movimento che soddisfa i filtri, **in quest'ordine**:

1. `category_id` → `m.category_id`, `m.category` (come oggi);
2. `note` → `m.note = <nota canonicalizzata>`, identica per tutti (come oggi);
3. `add_labels` → `m.note = reduce(add_label, nomi_canonici, m.note)`, diversa
   per ciascuno.

L'ordine non è arbitrario: con `note` **e** `add_labels` nella stessa richiesta,
le label si aggiungono al testo nuovo. L'inverso (label aggiunte e poi
cancellate dalla sostituzione) sarebbe un'operazione che annulla metà di sé.
Resta vero che la sostituzione della nota cancella le label *preesistenti*: è
R1, non si risolve qui (§10).

---

## 5. Il registro si interroga una volta

```python
canon_note = label_repo.sync_from_note(account_id, ' '.join('#' + n for n in add_labels))
canon_names = labels.extract(canon_note)
```

Una chiamata sola costruisce le righe `LABEL` mancanti e restituisce le grafie
canoniche; il resto del lavoro è manipolazione di stringhe in memoria.

Chiamare `sync_from_note` per movimento darebbe lo stesso risultato facendo da
1 a N query **per ciascuno** dei 2000 movimenti di un filtro annuale. È la
differenza fra un'operazione e un timeout, ed è il controllo 7 di §9.

Due conseguenze volute:

- **Con zero movimenti filtrati non si registra niente.** La risoluzione del
  registro avviene solo se c'è almeno un movimento da scrivere: altrimenti
  un filtro sbagliato lascerebbe nel registro label mai usate, che l'utente
  dovrebbe poi cancellare a mano dalla pagina Impostazioni.
- **Le grafie già scritte nelle note non si riscrivono.** `add_label` è
  idempotente case-insensitive: un movimento con `#COOP` resta `#COOP` anche se
  il registro dice `#coop`. Uniformare le grafie è il lavoro di
  `LabelRepository.rename_label`, che ha una sua UI e un suo conteggio.

---

## 6. Casi limite: quando un movimento si salta

Due limiti vivono in `conf.py` ([conf.py:98](../../pyspendless/conf.py)):
`MAX_NOTE_LENGTH = 500` e `MAX_LABELS_PER_MOVEMENT = 10`. Il form del singolo
movimento li fa rispettare rifiutando l'input; qui l'input è uno e i movimenti
sono N, quindi la decisione è **per movimento**:

| Situazione | Esito |
|---|---|
| `len(nota + ' #label') > MAX_NOTE_LENGTH` | movimento **saltato**, nota invariata, `skipped += 1` |
| il movimento ha già `MAX_LABELS_PER_MOVEMENT` label distinte e la nuova non è fra quelle | movimento **saltato**, `skipped += 1` |
| il movimento ha già `MAX_LABELS_PER_MOVEMENT` label **fra cui** quella richiesta | **non** è un salto: `add_label` è un no-op e il movimento conta fra gli `updated` |
| più label richieste e solo una sfora | le precedenti restano applicate, il movimento conta fra gli `updated` **e** fra gli `skipped`; il conteggio è "quanti movimenti non hanno ricevuto tutto", ed è questo che il messaggio dice |

Le alternative sono peggiori: troncare la nota perde testo scritto
dall'utente, e far fallire tutta l'operazione per un movimento su cinquecento
la rende inutilizzabile proprio sui filtri larghi, che sono il suo caso d'uso.

---

## 7. L'interfaccia

Nella modale `#bulkEditModal` ([ps-show-mov.html:260](../../pyspendless/templates/ps-show-mov.html)),
un terzo campo dopo "Nuova descrizione":

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

Tre cose che non sono dettagli:

1. **`data-ps-labels-standalone`, non `data-ps-labels`.** L'auto-attivazione di
   `ps-labels.js` ([ps-labels.js:471](../../pyspendless/static/js/ps-labels.js))
   gira al `DOMContentLoaded`, quando il `<dialog>` è chiuso e quindi
   `display:none`: Tom Select inizializzato lì calcola larghezze e posizione del
   dropdown sbagliate. È la stessa trappola per cui il multi-select delle
   categorie aspetta `shown.bs.collapse`
   ([ps-show-mov.html:634](../../pyspendless/templates/ps-show-mov.html)). Qui
   l'init si lega a `shown.bs.modal`, emesso da `ps-ui.js`, `{ once: true }`.
2. **Modalità standalone del componente**, non un secondo campo a chip. Senza
   `data-ps-labels-target` oggi `initField` esce subito; dopo questo task,
   quando il target manca, il campo è la fonte di verità di sé stesso: niente
   sincronizzazione con una textarea, niente controllo su `MAX_NOTE_LENGTH`
   (non c'è una nota da misurare: la misura la fa il server, per movimento), e
   `createFilter` conserva grammatica e limite sul numero di chip. Il valore si
   legge da `el.tomselect.items`.
3. **Il campo non rende il tipo obbligatorio.** L'Applica si abilita se c'è una
   categoria **o** una nota **o** almeno una chip; la conferma e il messaggio
   finale nominano le label scelte e, se `skipped > 0`, dicono quanti movimenti
   sono stati lasciati intatti e perché.

`max_labels_per_movement` e `max_note_length` oggi non arrivano al template di
`/movements` (il `render_template` di [app.py:620](../../pyspendless/app.py) non
li passa, a differenza di quello del form): è un passo della Fase 2, non della
Fase 3 — `app.py` è di `ps-py`.

---

## 8. Decisioni

| # | Decisione | Perché |
|---|---|---|
| **D1** | Il payload porta `add_labels` (lista), non un campo singolo. | Il campo a chip è già multiplo e il costo è identico: una label sola è il caso con un elemento. Un campo singolo si sarebbe dovuto allargare al primo uso reale. |
| **D2** | `add_labels` **aggiunge**, non sostituisce. | È il punto del task: oggi la sola strada per mettere una label in blocco cancella le note (R1 del task26-0). |
| **D3** | L'append è per movimento, lato server, con `labels.add_label`. | N note diverse non hanno un testo comune da applicare. E la funzione esiste già, con 112 casi di test alle spalle. |
| **D4** | Il registro `LABEL` si interroga una volta per operazione. | Vedi §5: la differenza fra un'operazione e un timeout su un filtro annuale. |
| **D5** | Le grafie già presenti nelle note non si riscrivono. | Uniformare le grafie è `rename_label`, con la sua UI e il suo conteggio: farlo di nascosto dentro un'altra operazione sorprenderebbe. |
| **D6** | Movimento che sforerebbe i limiti → saltato e contato. | Troncare perde testo dell'utente; fallire tutto rende inutile la funzione sui filtri larghi (§6). |
| **D7** | Nome non valido → `400`. Nel filtro per label si ignora in silenzio ([app.py:530](../../pyspendless/app.py)). | La query string è input non fidato di una navigazione; qui è un'azione deliberata su N movimenti, e il silenzio sarebbe una modifica mancata senza spiegazione. |
| **D8** | Init del campo a chip alla prima apertura della modale. | Tom Select in un contenitore `display:none` sbaglia le misure: trappola già pagata nel task26-0. |
| **D9** | `updated` conserva il significato di oggi; `skipped` e `labels` si aggiungono. | Il JS esistente legge `updated`: cambiargli significato romperebbe un contratto per un dettaglio di presentazione. |
| **D10** | Nessuna colonna, nessuna migrazione, nessuna dipendenza. | Le label vivono in `Movement.note` e nel registro che esiste già: il deploy resta `git pull` + Reload. |
| **D11** | La modale **non** guadagna una casella "conserva le label esistenti" per la sostituzione della nota. | È R1, un problema diverso (sottrattivo, non additivo) con una sua decisione da prendere. Mescolarlo qui raddoppierebbe i casi di test e la superficie dell'operazione. Resta `MB-NNN` se darà fastidio nell'uso. |

---

## 9. I casi di test

Il metro è `pyspendless/test/test_task28_0.py`, tre sezioni indipendenti
(`repo`, `api`, `contract`), SQLite **in-memory**, convenzione di
`test_task26_0.py`. Si scrive in Fase 0, prima di qualunque riga di
implementazione.

### Sezione `repo` (Fase 1)

| # | Caso | Atteso |
|---|---|---|
| 1 | 3 movimenti con note `'pane'`, `'latte #spesa'`, `None` + `add_labels=['casa']` | `'pane #casa'`, `'latte #spesa #casa'`, `'#casa'` |
| 2 | rilancio della stessa chiamata | note invariate (idempotenza) |
| 3 | movimento con `'spesa #CASA'` + `add_labels=['casa']` | invariato: la grafia esistente non si riscrive (D5) |
| 4 | `add_labels=['casa', 'auto']` | append nell'ordine passato: `'pane #casa #auto'` |
| 5 | registro: `#Casa` digitata con `#casa` già in `LABEL` | nelle note finisce `#casa` (grafia canonica), e `LABEL` non guadagna una seconda riga |
| 6 | registro: label nuova | una riga sola in `LABEL`, grafia come digitata |
| 7 | spia su `LabelRepository.sync_from_note` con 5 movimenti filtrati | chiamata **una volta sola** (D4) |
| 8 | `note='rifatta'` + `add_labels=['casa']` | tutte le note diventano `'rifatta #casa'` |
| 9 | `category_id` + `add_labels` nella stessa chiamata | categoria cambiata **e** label aggiunta |
| 10 | nota di 497 caratteri + `['casa']` (`+5`) | movimento saltato, nota invariata, `skipped == 1` |
| 11 | movimento con 10 label + `['undicesima']` | saltato, `skipped == 1` |
| 12 | movimento con 10 label fra cui `#casa` + `['casa']` | **non** saltato, nota invariata, conta fra gli `updated` |
| 13 | `filters` che selezionano 2 movimenti su 5 | solo quei 2 cambiano |
| 14 | zero movimenti filtrati | `updated == 0`, `skipped == 0`, **nessuna riga nuova** in `LABEL` (§5) |
| 15 | isolamento: account B con gli stessi filtri | i movimenti di A non si toccano, e `LABEL` di B non vede la label di A |
| 16 | `add_labels=None` (chiamata vecchia stile) | comportamento identico a oggi: è la prova di non-regressione del contratto del repository |

### Sezione `api` (Fase 2)

| # | Caso | Atteso |
|---|---|---|
| 1 | `{"add_labels": ["casa"]}` | `200`, `{'updated': N, 'skipped': 0, 'labels': ['casa']}` |
| 2 | `{"add_labels": ["#casa"]}` | `200`: il `#` si accetta e si toglie |
| 3 | `{"add_labels": ["a"]}`, `["ciao!"]`, `["x"*31]`, `["-x-"]` | `400`, e **nessun** movimento modificato |
| 4 | `{"add_labels": "casa"}` (stringa) | `400` |
| 5 | `{}` e `{"add_labels": []}` | `400` "Specificare almeno…" |
| 6 | 11 nomi | `400` con il limite nel messaggio |
| 7 | solo `add_labels`, **senza** `category_type` nei filtri | `200` (A8) |
| 8 | `category_id` di un altro account | `404` (comportamento di oggi, da non rompere) |
| 9 | senza sessione | `401` |
| 10 | `GET /movements` reso dal test client | la pagina contiene `data-ps-labels-max="10"`: il contesto del `render_template` non è stato dimenticato (§7) |

### Sezione `contract` (Fase 3)

Controlli **statici** su template e JS (lettura del file + regex), convenzione
di `test_task19_0.py`: non aprono un browser.

| Controllo | Perché |
|---|---|
| `ps-show-mov.html` ha `id="bulk-labels"` con `multiple`, `data-ps-labels-standalone`, `data-ps-labels-max` | è il campo nuovo |
| lo stesso `<select>` **non** ha `data-ps-labels` | altrimenti l'auto-init al `DOMContentLoaded` lo costruirebbe nel `<dialog>` chiuso (D8) |
| il JS della modale cita `shown.bs.modal` e `#bulkEditModal` con `once` | l'init rimandato è il contratto, non un'ottimizzazione |
| il payload del `fetch` di `bulk-edit-apply-btn` contiene `add_labels` | altrimenti il campo si vede e non fa niente |
| il JS legge `skipped` dalla risposta | A6: il salto va detto, non nascosto |
| `ps-labels.js` cita `data-ps-labels-standalone` e `initField` restituisce l'istanza | la modalità standalone esiste e il chiamante può leggere le chip |
| `ps-setting-labels.html` non afferma più che la correzione massiva "rimuove tutte le label" come unica verità, e cita l'aggiunta | §2, sesto fatto |
| il conteggio di `bootstrap.` in `ps-show-mov.html` resta **0** | il task19-0 ha rimosso Bootstrap: lo shim di `ps-ui.js` non va allungato |
| `node tools/check-labels-js.mjs` esce `0` se `node` c'è, altrimenti il controllo si salta dichiarandolo | la grammatica JS deve restare allineata a `labels.py` dopo la modifica al file |

---

## 10. Rischi e cose fuori perimetro

| # | Rischio / limite | Trattamento |
|---|---|---|
| **R1** | La sostituzione della nota continua a cancellare le label preesistenti (R1 del task26-0). | **Fuori perimetro** (D11). L'avviso in `ps-setting-labels.html` va aggiornato, non rimosso: resta vero per la sostituzione. |
| **R2** | La rotta `bulk-update` **non** valida oggi la lunghezza di `note` contro `MAX_NOTE_LENGTH`, mentre il percorso nuovo rispetta il limite per movimento. | Incoerenza preesistente, non introdotta qui. Si apre una voce `MB-NNN` in `backlog/00-task-minor-bugfix.md` e **non** si corregge in questo task (nessun refactoring collaterale). |
| **R3** | 4 stringhe nuove in 2 template, mentre task25-0 (localizzazione) è `PIANIFICATO`. | Si scrivono in italiano come il resto: quando il task25-0 passerà, le avvolgerà con tutte le altre. Nessun `_()` anticipato. |
| **R4** | `updated` conta i movimenti scritti, non quelli *cambiati*: con una label già presente su tutti, `updated == N` e nulla è cambiato. | È il significato di oggi (D9) e il messaggio dell'interfaccia dice "aggiornati", non "modificati". Un conteggio dei soli movimenti realmente cambiati sarebbe un dato in più da far quadrare con `skipped`: non lo si introduce. |
| **R5** | L'operazione resta non reversibile, e ora può toccare le note anche quando l'utente non ha scritto niente nel campo descrizione. | L'avviso rosso già presente nella modale resta, e la conferma nomina le label: l'utente deve poter leggere *che cosa* sta per aggiungere prima di confermare. |
| **R6** | Il filtro per label (`?label=...`) combinato con l'aggiunta della stessa label è un no-op completo (tutti i movimenti filtrati l'hanno già). | Nessun errore: `updated == N`, note invariate. Vale la pena che il caso 2 di §9 lo copra, non che il codice lo impedisca. |

---

## 11. Fasi

| Fase | Chi | Perimetro | Fatto quando |
|---|---|---|---|
| **0** | agente principale, **non si delega** | `test/test_task28_0.py` | le tre sezioni girano e falliscono con una riga per controllo |
| **1** | `ps-py` (haiku) | `repository.py` | `test_task28_0.py repo` esce `0` |
| **2** | `ps-py` (haiku) | `app.py` | `test_task28_0.py api` esce `0`, `repo` resta verde |
| **3** | `ps-ui` (haiku) | `ps-labels.js`, `ps-show-mov.html`, `ps-setting-labels.html` | `test_task28_0.py contract` esce `0` |
| **4** | agente principale | verifica visiva, CSS, regressione | le 4 suite di `CLAUDE.md` verdi, `git status` pulito dopo `./tools/build-css.sh`, prova manuale in light e dark |

Dettaglio in `fasi/fase-0.md` … `fasi/fase-4.md`.

---

## 12. File toccati

| File | Fase | Che cosa |
|---|---|---|
| `pyspendless/test/test_task28_0.py` | 0 | **nuovo** — il metro, 3 sezioni |
| `pyspendless/repository.py` | 1 | `bulk_update_movements`: parametro `add_labels`, append per movimento, conteggio dei salti |
| `pyspendless/app.py` | 2 | `api_bulk_update_movements`: validazione di `add_labels`, risposta con `skipped`/`labels`; `render_template('ps-show-mov.html')`: `max_labels_per_movement`, `max_note_length` |
| `pyspendless/static/js/ps-labels.js` | 3 | `initField`: modalità standalone senza textarea, ritorno dell'istanza |
| `pyspendless/templates/ps-show-mov.html` | 3 | campo `#bulk-labels` nella modale, init su `shown.bs.modal`, payload e messaggio finale |
| `pyspendless/templates/ps-setting-labels.html` | 3 | avviso riscritto (sostituzione ≠ aggiunta) |
| `pyspendless/static/css/ps-tailwind.css` | 4 | ricompilato **solo se** la Fase 3 ha introdotto classi nuove |
| `backlog/features.md` | — | riga del task28-0 |
| `backlog/00-task-minor-bugfix.md` | 4 | voce `MB-NNN` per R2 |
