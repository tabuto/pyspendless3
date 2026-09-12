# Analisi decisioni aperte D4 e D5

**Contesto**: rifacimento grafico isofunzionale di PySpendless con Tailwind CSS
(vedi `piano-restyling-tailwind.md`).
**Data**: 2026-09-10 · **Versione analizzata**: `_APP_VERSION = "0.1.8"`
**Natura**: sola analisi. Nessun file del repo modificato.

---

## Premessa: due rilevazioni che cambiano il quadro

Approfondendo il codice per questa analisi sono emersi due fatti che nel piano
iniziale non erano ancora a fuoco. Entrambi pesano sulla decisione.

### Rilevazione 1 — Il JS di pagina usa l'**API imperativa** di Bootstrap, non solo i `data-bs-*`

Non si tratta solo di attributi dichiarativi da rimpiazzare. In 12 punti il codice
chiama direttamente le classi JS di Bootstrap:

| File | Riga | Chiamata |
|---|---|---|
| `ps-setting-categories.html` | 350 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-setting-categories.html` | 365 | `new bootstrap.Modal(…)` + `.show()` |
| `ps-setting-categories.html` | 409 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-setting-categories.html` | 471 | `new bootstrap.Modal(…)` + `.show()` |
| `ps-setting-categories.html` | 499 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-setting-wallet.html` | 194-196 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-setting-wallet.html` | 220-221 | `new bootstrap.Modal(…)` + `.show()` |
| `ps-setting-wallet.html` | 249 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-setting-admin.html` | 179 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-setting-group.html` | 331-334 | `bootstrap.Modal.getInstance(…).hide()` |
| `ps-recurrent-mov.html` | 248 | `new bootstrap.Modal(…).show()` |
| `ps-recurrent-mov.html` | 253 | `bootstrap.Modal.getInstance(…)` |

Più 5 listener su **eventi custom Bootstrap**:

| File | Riga | Evento |
|---|---|---|
| `ps-setting-group.html` | 230 | `hidden.bs.modal` → reset `editAccountForm` |
| `ps-setting-group.html` | 239 | `hidden.bs.modal` → reset `inviteForm` + nasconde `generatedLinkContainer` |
| `ps-setting-group.html` | 258 | `hidden.bs.modal` → svuota `confirmDeleteText`, ri-disabilita `confirmDeleteBtn` |
| `ps-setting-group.html` | 264 | `show.bs.modal` → `checkAccountSharing()` (chiamata API!) |
| `ps-show-mov.html` | 403 | `shown.bs.collapse` → init differita di Tom Select |

**Conseguenza**: il vincolo "non riscrivere il JS di pagina" (che è l'ancora
dell'isofunzionalità) impone che il sostituto esponga una **superficie compatibile**
— `window.bootstrap.Modal` con `new`, `.show()`, `.hide()`, `getInstance()` — e
riemetta eventi con gli stessi nomi. Questo è possibile con un modulo imperativo.
Non lo è, se non riscrivendo i 17 call site, con un framework dichiarativo.

`show.bs.modal` su `deleteAccountModal` è il caso più insidioso: non è cosmetico,
**scatena una chiamata API** (`checkAccountSharing()`) che decide quali voci mostrare
in `#deletionDetails`. Se l'evento non viene riemesso al momento giusto, il modal si
apre con informazioni sbagliate su cosa verrà cancellato. In una pagina intitolata
"Zona Pericolosa".

### Rilevazione 2 — Nel repo esiste già un workaround per un bug del modal Bootstrap

`ps-setting-group.html:329-348` e `ps-setting-wallet.html:198-205` contengono lo
stesso identico blocco:

```js
// Forza la rimozione del backdrop e cleanup
setTimeout(() => {
  document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
  document.body.classList.remove('modal-open');
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
}, 300);
```

Qualcuno ha già combattuto con backdrop fantasma e scroll bloccato. Questo dice due
cose: (a) il modal Bootstrap in questa app **non è già oggi perfettamente affidabile**,
quindi la barra da eguagliare non è "impeccabile"; (b) quel workaround dipende da
dettagli implementativi di Bootstrap (`.modal-backdrop`, `.modal-open`,
`padding-right` per la scrollbar) che in un sostituto **non esisteranno** — il codice
diventerà innocuo ma resterà lì a mentire. Da annotare nel task.

### Correzione al piano

Il piano parlava di **12 modal**. Il conteggio corretto sui soli template vivi è **10**:

| File | Modal |
|---|---|
| `ps-setting-categories.html` | `deleteCategoryModal` (75), `addCategoryModal` (113), `editCategoryModal` (150) |
| `ps-setting-wallet.html` | `addWalletModal` (24), `editWalletModal` (56) |
| `ps-setting-group.html` | `editAccountModal` (107), `inviteModal` (133), `deleteAccountModal` (176) |
| `ps-setting-admin.html` | `addWhitelistModal` (93) |
| `ps-recurrent-mov.html` | `deleteModal` (128) |

Le altre 5 stanno in `ps-setting-categories-old.html`, template morto.

---

# D4 — Sostituto del JS di Bootstrap

## Superficie da coprire — censimento esatto

Comportamenti Bootstrap effettivamente usati nei template vivi:

| Comportamento | Occorrenze | File |
|---|---|---|
| `data-bs-toggle="modal"` (apertura dichiarativa) | 6 | `ps-setting-categories.html:30`, `ps-setting-wallet.html:12`, `ps-setting-group.html:17,40,97`, `ps-setting-admin.html:15` |
| `data-bs-dismiss="modal"` | 20 | i 5 file con modal (X di chiusura + bottoni "Annulla"/"Chiudi") |
| API imperativa `bootstrap.Modal` | 12 | vedi tabella sopra |
| Eventi `*.bs.modal` | 4 | `ps-setting-group.html:230,239,258,264` |
| `data-bs-toggle="tab"` | 2 | `ps-setting-categories.html:16,21` (Uscite / Entrate) |
| `data-bs-toggle="collapse"` | 1 | `ps-show-mov.html:12-13` (pannello filtri) |
| Evento `shown.bs.collapse` | 1 | `ps-show-mov.html:403` (init Tom Select differita) |
| `data-bs-dismiss="alert"` + `.fade .show` | 8 | `ps-add-mov.html:300`, `ps-search-mov.html:208`, `ps-onboarding.html:19`, `ps-recurrent-mov.html:284`, `ps-setting-categories.html:211`, `ps-setting-group.html:275`, `ps-setting-admin.html:129`, `ps-setting-import-export.html:104` |
| `data-lte-toggle="sidebar"` (AdminLTE, non BS) | 1 | `ps-nav.html:11` |
| `data-bs-theme="dark"` | 1 | `ps-nav.html:37` — **CSS-only**, sparisce col restyling |

**Non usati affatto**: dropdown, tooltip, popover, toast, offcanvas, carousel,
scrollspy. La superficie reale è quindi: **modal, tab, collapse, alert-dismiss**,
più il drawer della sidebar e i due treeview (`toggleSettingsMenu` /
`toggleDashboardMenu`, `ps-nav.html:167-213`, già vanilla oggi).

---

## Opzione D4-A — `ps-ui.js` vanilla

Modulo unico, ~350-450 righe, che implementa i 4 comportamenti + drawer, ed espone
uno **shim di compatibilità** `window.bootstrap.Modal`.

### Pro

- **Compatibilità con l'API imperativa esistente.** È l'unica opzione che permette di lasciare intatti i 12 call site e i 5 listener. Lo shim è ~30 righe:
  ```js
  window.bootstrap = window.bootstrap || {};
  window.bootstrap.Modal = class {
    constructor(el){ this.el = typeof el === 'string' ? document.querySelector(el) : el;
                     PsModal.registry.set(this.el, this); }
    show(){ PsModal.show(this.el); }   // emette show.bs.modal / shown.bs.modal
    hide(){ PsModal.hide(this.el); }   // emette hide.bs.modal / hidden.bs.modal
    static getInstance(el){ return PsModal.registry.get(el) || null; }
    static getOrCreateInstance(el){ return this.getInstance(el) || new this(el); }
  };
  ```
  Il vincolo "non tocco il JS di pagina" resta **letteralmente** rispettato: il diff su `ps-setting-*.html` riguarda solo il markup.
- **Superficie minima, sotto controllo totale.** Si implementa quello che serve e nulla più. Nessun comportamento emergente da un framework che non si conosce.
- **Zero dipendenze nuove.** Nessun CDN aggiuntivo, nessuna supply chain, nessuna versione da seguire. Coerente con un repo Python che oggi ha 10 righe di `requirements.txt` e zero `package.json`.
- **Debuggabilità.** Quando il modal fa una cosa strana, si apre un file di 400 righe scritto in casa, non si cerca su GitHub il comportamento di `x-show` con `x-transition` annidato.
- **Si sposa con l'approccio del resto del piano.** I template restano HTML+Jinja server-rendered, senza un secondo modello mentale reattivo sopra.
- **Nessun costo di apprendimento** per chi mantiene il progetto: è JS del DOM, quello che c'è già in tutti i template.

### Contro

- **Va scritto e, soprattutto, va scritto _bene_.** Un modal fatto seriamente non è "aggiungi una classe": serve backdrop, chiusura con Esc, click sul backdrop, **focus trap**, restituzione del focus all'elemento che ha aperto, `aria-hidden`/`aria-modal`, scroll-lock del body con compensazione della scrollbar, gestione di modal sovrapposti, e le transizioni. È il classico componente che sembra da 50 righe e ne vuole 200.
- **Rischio di accessibilità peggiore.** Bootstrap ha anni di rifiniture su focus e ARIA. Una prima versione casalinga quasi certamente non le eguaglia. Mitigabile: il pattern WAI-ARIA per il dialog è documentato e `<dialog>` nativo (supportato da tutti i browser da metà 2022) risolve gratis backdrop, focus trap ed Esc.
- **Nessuna manutenzione esterna.** Un bug su un browser nuovo lo si scopre e lo si corregge da soli.
- **Lo shim è una bugia utile che va documentata.** `window.bootstrap` che non è Bootstrap confonderà il prossimo lettore. Va messo un commento in testa e — meglio — pianificata la migrazione dei 12 call site a `psUI.modal(...)` in un task **successivo**, separato, con i test già in piedi.

### Peso e performance

| Voce | Raw | Gzip |
|---|---|---|
| `ps-ui.js` (stima) | ~10-14 KB | ~3-4 KB |
| **Rimosso**: `bootstrap.min.js` | ~60 KB | ~18 KB |
| **Rimosso**: `popper.min.js` | ~21 KB | ~7 KB |
| **Rimosso**: `bootstrap.bundle.min.js` (2° caricamento su 6 pagine) | ~80 KB | ~23 KB |
| **Rimosso**: `overlayscrollbars` js+css | ~50 KB | ~14 KB |

*Valori indicativi, da verificare in Fase 0 con misura reale.*

**Bilancio**: da ~130 KB gzip di JS di terze parti a ~4 KB propri. Su 6 pagine il
risparmio raddoppia (doppio caricamento di Bootstrap). Quattro richieste HTTP a CDN
esterni in meno per pagina — su rete mobile è il fattore che conta più dei KB.
Sul TTI l'impatto è modesto in assoluto ma va nella direzione giusta.

### Isofunzionalità e rischio di regressione

**Rischio: medio-basso.** Determinato dalla scelta dello shim.

- ✅ I 12 call site imperativi non si toccano → nessun rischio da riscrittura di logica.
- ✅ I 5 listener su eventi `.bs.*` continuano a funzionare **se** lo shim li riemette con lo stesso nome, nella stessa sequenza (`show` → `shown`, `hide` → `hidden`) e con lo stesso timing rispetto alla transizione.
- ⚠️ Punto di attenzione n.1: `show.bs.modal` su `deleteAccountModal` (`ps-setting-group.html:264`) deve essere emesso **prima** che il modal diventi visibile, come fa Bootstrap; altrimenti `checkAccountSharing()` popola `#deletionDetails` a modal già aperto e l'utente vede un flash di contenuto sbagliato.
- ⚠️ Punto di attenzione n.2: `shown.bs.collapse` (`ps-show-mov.html:403`) deve scattare a **transizione conclusa**, non all'inizio. È esattamente il motivo per cui l'init di Tom Select è differita (commento a `ps-show-mov.html:377-379`: inizializzarlo mentre il contenitore è `display:none` produce larghezze e dropdown sbagliati). Emetterlo troppo presto ricrea il bug che quel codice è lì per evitare.
- ⚠️ Punto di attenzione n.3: i due blocchi di cleanup del backdrop (Rilevazione 2) diventano no-op. Innocui, ma il `setTimeout(…, 300)` continua a esistere: se la transizione del nuovo modal dura diversamente, nessun effetto — il codice non fa più nulla di utile. Va lasciato (isofunzionalità) e annotato.
- ✅ Verificabile: ognuno dei 10 modal ha una checklist di 6 interazioni (apri da trigger, apri da JS, chiudi con X, chiudi con Annulla, chiudi con Esc, chiudi con backdrop) → 60 verifiche manuali, noiose ma deterministiche.

### Effort stimato

| Attività | gg |
|---|---|
| Modal su `<dialog>` nativo + shim `bootstrap.Modal` + eventi | 1.5 |
| Collapse + evento `shown` a fine transizione | 0.5 |
| Tab (2 istanze, `ps-setting-categories.html`) | 0.5 |
| Alert dismiss + `.fade .show` | 0.25 |
| Drawer sidebar mobile + treeview | 0.75 |
| Test manuali (10 modal × 6 interazioni, 2 tab, 1 collapse) | 1.0 |
| Buffer accessibilità / focus / edge case | 0.75 |
| **Totale** | **~5.25 gg** |

Distribuite: ~2 gg in Fase 1, il resto assorbito nelle Fasi 5-6 dove i componenti
vengono effettivamente esercitati.

### Manutenibilità a lungo termine

**Buona, con una riserva.** Il codice è piccolo, leggibile, senza dipendenze che
invecchiano. Nessun rischio di "Alpine 4 ha cambiato la sintassi". La riserva: se in
futuro servisse un componente che oggi non c'è (dropdown, toast, combobox), va scritto
— mentre con un framework sarebbe incluso. Guardando il repo, però, in 18 task non è
mai servito nulla oltre a modal/tab/collapse/alert: l'estrapolazione è ragionevole.

Debito tecnico esplicito da mettere a backlog: **rimuovere lo shim** e migrare i 12
call site a `psUI.*`, una volta che i test di contratto sono stabili.

### Pagine e file coinvolti

`ps-setting-categories.html`, `ps-setting-wallet.html`, `ps-setting-group.html`,
`ps-setting-admin.html`, `ps-recurrent-mov.html` (modal + tab), `ps-show-mov.html`
(collapse), `ps-add-mov.html`, `ps-search-mov.html`, `ps-onboarding.html`,
`ps-setting-import-export.html` (alert), `ps-nav.html` (drawer + treeview),
`ps-base.html` (rimozione script). Nuovo: `static/js/ps-ui.js`.

---

## Opzione D4-B — Alpine.js

Framework dichiarativo (~44 KB raw / ~16 KB gzip), attributi `x-data`, `x-show`,
`x-transition`, `@click`, `x-cloak`.

### Pro

- **I componenti si scrivono in una frazione del tempo.** Un modal è `x-data="{open:false}"` + `x-show` + `x-transition`. Collapse e tab sono ancora più brevi. La quantità di JS scritto a mano crolla.
- **Transizioni gratuite e di buona qualità** (`x-transition`), che è proprio la parte noiosa del modal fatto a mano.
- **Stato dichiarativo nel markup**: guardando il template si capisce cosa fa, senza inseguire un `addEventListener` in fondo al file. Su template lunghi come `ps-setting-group.html` (390+ righe) è un guadagno reale di leggibilità.
- **Accoppiata naturale con Tailwind**: è lo stack che la community usa di più, quindi esempi, pattern e risposte abbondano.
- **Manutenuto da terzi**, con una community grande; i bug di accessibilità li corregge qualcun altro.
- **Scala meglio se il progetto crescesse** verso UI più interattive (filtri live, form dinamici).

### Contro

- **⛔ Non copre l'API imperativa.** È il difetto decisivo in questo repo. `new bootstrap.Modal(el).show()` non ha traduzione Alpine: lo stato vive in `x-data`, non in un'istanza JS globale. Le strade sono due, entrambe costose:
  1. **Riscrivere i 17 call site** (12 imperativi + 5 listener) in `$dispatch('open-modal')` / `Alpine.store`. → viola il principio "non tocco il JS di pagina", che è l'ancora dell'isofunzionalità.
  2. **Scrivere comunque uno shim** `window.bootstrap.Modal` che pilota lo store Alpine. → si paga Alpine *e* si scrive lo shim, cioè il peggio dei due mondi.
- **I 5 listener su eventi `.bs.*` vanno comunque riscritti.** In particolare `show.bs.modal` → `checkAccountSharing()`: in Alpine diventa un `x-effect` o un `@open-modal.window`, con timing da riverificare.
- **Nuova dipendenza CDN**, con la stessa categoria di problemi che il piano sta cercando di ridurre (il piano self-hosta font e icone proprio per togliere CDN).
- **Secondo modello mentale.** Il repo oggi è Flask + Jinja + JS del DOM. Aggiungere reattività dichiarativa significa che chi legge deve conoscere due paradigmi. Su un progetto personale mantenuto da una persona, è un costo che si paga ogni volta che si rientra nel codice dopo mesi.
- **FOUC di Alpine.** Serve `x-cloak` + CSS dedicato, altrimenti i modal lampeggiano aperti al load. Un problema in più proprio mentre se ne sta risolvendo uno analogo per il tema.
- **Sovradimensionato.** Alpine è un framework di reattività completo; qui servono 4 comportamenti, nessuno dei quali richiede reattività.

### Peso e performance

| Voce | Raw | Gzip |
|---|---|---|
| Alpine.js 3.x | ~44 KB | ~16 KB |
| Shim di compatibilità (se si sceglie quella via) | ~4 KB | ~1.5 KB |
| **Rimosso**: Bootstrap JS + Popper (+ doppio su 6 pagine) | come sopra | come sopra |

**Bilancio**: ~16-18 KB gzip contro i ~4 KB di D4-A. In assoluto sono ~13 KB: non è
questo il criterio che decide. Va però notato che Alpine **esegue** al parse del DOM
(walker su tutto l'albero alla ricerca di `x-*`), costo assente in D4-A dove il JS
lavora solo sugli elementi che tocca. Su `ps-show-mov.html` con centinaia di righe di
tabella renderizzate server-side, il walk non è gratis.

### Isofunzionalità e rischio di regressione

**Rischio: alto.** È il punto dove le due opzioni divergono davvero.

- ⛔ La riscrittura di 17 call site è **codice comportamentale toccato**, non markup. Ogni riscrittura è un'occasione di regressione, e le regressioni qui riguardano: chiusura del modal dopo il salvataggio (categorie, wallet, admin, group), reset dei form alla chiusura, e la logica di `#deletionDetails` sull'eliminazione account.
- ⛔ La checklist di verifica si allarga: non basta più "il modal si apre e si chiude", bisogna riverificare **tutti i flussi CRUD** che attraversano un modal — cioè la maggior parte delle pagine impostazioni.
- ⚠️ `shown.bs.collapse` → in Alpine il momento "transizione conclusa" è `x-transition:after` o un `@transitionend`: replicabile, ma con più modi di sbagliarlo.
- ➕ In compenso, dove Alpine gestisce il componente per intero, il rischio di sbagliare backdrop/focus/Esc è **più basso** che scrivendoli a mano.

Il bilancio netto resta sfavorevole perché il rischio si concentra dove fa più male:
nella logica applicativa, non nella presentazione.

### Effort stimato

| Attività | gg |
|---|---|
| Setup, `x-cloak`, pattern condivisi | 0.5 |
| 10 modal in `x-data` | 1.25 |
| **Riscrittura 12 call site imperativi + 5 listener** | 1.5 |
| Tab, collapse, drawer | 0.75 |
| Alert dismiss | 0.25 |
| Test (flussi CRUD completi, non solo apri/chiudi) | 1.75 |
| Buffer (timing eventi, FOUC) | 1.0 |
| **Totale** | **~7 gg** |

Alpine fa risparmiare sui componenti (~1 gg) ma lo restituisce con gli interessi sulla
migrazione dei call site e sui test (~2.75 gg).

### Manutenibilità a lungo termine

**Buona in astratto, discutibile qui.** Alpine è stabile e ben mantenuto, e su una
codebase Tailwind è la scelta idiomatica. Ma introduce un paradigma che il resto del
progetto non usa, in un'app dove i 4 comportamenti richiesti sono noti e stabili da
18 task. Il beneficio "scala meglio in futuro" è reale solo se quel futuro arriva.

### Pagine e file coinvolti

Le stesse di D4-A, **più** la riscrittura dei blocchi `{% block scripts %}` di
`ps-setting-categories.html` (~350-500), `ps-setting-wallet.html` (~180-250),
`ps-setting-group.html` (~216-348), `ps-setting-admin.html` (~179),
`ps-recurrent-mov.html` (~248-253).

---

## Confronto sintetico D4

| Criterio | D4-A `ps-ui.js` | D4-B Alpine.js |
|---|---|---|
| Peso (gzip) | ~4 KB | ~16-18 KB |
| Dipendenze nuove | 0 | 1 (CDN o self-hosted) |
| JS di pagina da riscrivere | **0 call site** | **17 call site** |
| Rischio di regressione | medio-basso | **alto** |
| Effort | ~5.25 gg | ~7 gg |
| Facilità di scrittura componenti | bassa | **alta** |
| Accessibilità "out of the box" | da costruire (mitigata da `<dialog>`) | **buona** |
| Coerenza con lo stack esistente | **alta** | media |
| Manutenzione da terzi | no | **sì** |
| Adatto se il progetto cresce molto | meno | **più** |

## ✅ Raccomandazione D4: **`ps-ui.js` vanilla**

Non per purismo anti-framework, ma per una ragione strutturale specifica di questo repo:
**l'unico modo di rispettare il vincolo di isofunzionalità è esporre un'API imperativa
compatibile con `bootstrap.Modal`**, e Alpine per costruzione non può farlo senza
riscrivere 17 punti di logica applicativa. Nel momento in cui si riscrive quel codice,
l'affermazione "abbiamo cambiato solo la grafica" smette di essere vera, e la verifica
si allarga da "i modal funzionano" a "tutti i CRUD funzionano".

Le tre indicazioni operative che rendono la scelta solida:

1. **Costruire il modal su `<dialog>` nativo.** Backdrop, focus trap, Esc e `aria-modal` arrivano dal browser. Neutralizza gran parte del contro "l'accessibilità fatta a mano è peggiore" e taglia l'effort.
2. **Lo shim `window.bootstrap.Modal` è temporaneo per contratto.** Commento in testa che spiega perché esiste, più una voce `MB-NNN` a backlog per rimuoverlo migrando i 12 call site a `psUI.modal(...)` — dopo il restyling, con i test già verdi.
3. **Testare per primi i due eventi critici**: `show.bs.modal` su `deleteAccountModal` e `shown.bs.collapse` su `#filters-collapse`. Sono i due punti in cui un timing sbagliato produce un bug silenzioso invece di un errore visibile.

Alpine resterebbe la scelta giusta in uno scenario diverso: se si accettasse di
riscrivere il JS di pagina come parte del lavoro, o se il progetto stesse andando verso
UI molto più interattive. Nessuna delle due condizioni è vera oggi.

---

# D5 — DataTables: tenere o riscrivere

## Perimetro reale — una sola pagina

jQuery, DataTables, Responsive e Tom Select compaiono **esclusivamente** in
`ps-show-mov.html` (righe 243-253). Nessun altro template li usa. Il perimetro di D5 è
quindi **1 pagina su 16**, e precisamente la tabella `#movementsTable` (`:171-212`),
visibile **solo da ≥768 px** (`:169` `d-none d-md-block`); sotto quella soglia c'è la
card-list con infinite scroll, che non usa DataTables.

Configurazione attuale (`:259-276`):

```js
$('#movementsTable').DataTable({
  language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/it-IT.json' },
  order: [[0, 'desc']],
  pageLength: 25,
  responsive: true,
  columnDefs: [ /* responsivePriority su 8 colonne */ ]
});
```

Funzionalità effettivamente erogate: ordinamento su 8 colonne, paginazione a 25,
casella di ricerca globale, selettore "mostra N elementi", riga informativa
("Vista da 1 a 25 di N elementi"), traduzione it-IT, collasso responsive delle colonne
a bassa priorità con riga di dettaglio espandibile.

## ⚠️ Rilevazione: l'ordinamento per data è probabilmente già rotto

Tre fatti che si incastrano:

1. Il server restituisce già i movimenti ordinati: `repository.py:611` → `query.order_by(Movement.move_date.desc()).all()`.
2. La colonna 0 è renderizzata come `{{ mov.move_date.strftime('%d/%m/%Y') }}` (`ps-show-mov.html:187`), quindi **`gg/mm/aaaa`**.
3. `order: [[0,'desc']]` chiede a DataTables di riordinare quella colonna client-side.

DataTables 1.13 core rileva il tipo `date` tramite `Date.parse()`. Su `13/09/2026`
`Date.parse` restituisce `NaN` (in formato US il mese 13 non esiste), quindi il tipo
ricade su **stringa** e l'ordinamento diventa lessicografico: `31/01` finisce prima di
`01/02`. Cioè **ordina per giorno del mese**. Peggio: se in un dato filtro tutte le
date avessero giorno ≤ 12, verrebbero interpretate come `MM/DD` e l'ordinamento
sarebbe sbagliato in un altro modo ancora.

Il plugin di riconoscimento `date-eu` **non è caricato**.

→ **Da verificare empiricamente in Fase 0** (basta un mese con movimenti su giorni
>12 e confrontare l'ordine visualizzato con quello del server). Se confermato, è un
bug preesistente che pesa sulla decisione: D5-A lo conserva (isofunzionalità),
D5-B lo elimina per costruzione. In ogni caso **va registrato come `MB-NNN` separato**,
non corretto di soppiatto dentro il restyling.

---

## Opzione D5-A — Tenere DataTables (tema neutro + skin Tailwind)

Si sostituiscono `dataTables.bootstrap5.css` e `responsive.bootstrap5.css` con il tema
di default (`dataTables.dataTables.css`), e si scrive uno skin Tailwind per il "chrome"
generato dal plugin: casella di ricerca, select della lunghezza, riga info, paginazione.

### Pro

- **Isofunzionalità per costruzione.** Ordinamento, paginazione, ricerca, i18n e responsive-collapse restano *esattamente* quelli di oggi, bug del sort per data incluso. È la definizione operativa di "non ho cambiato il comportamento".
- **Effort basso e prevedibile.** Il lavoro è solo CSS, e il CSS è la cosa che questo task deve fare comunque.
- **Nessun rischio sulla logica.** Zero righe di JS comportamentale scritte.
- **Il collasso responsive continua a funzionare** nella fascia 768-1000 px, dove 8 colonne non ci stanno. Riscriverlo da zero è la parte più costosa di D5-B.
- **Traduzione it-IT già pronta e completa** (tutte le stringhe: ricerca, paginazione, info, "nessun dato disponibile", plurali).
- **Reversibile**: se lo skin non convince, si può cambiare senza toccare la pagina.

### Contro

- **Trascina jQuery.** ~30 KB gzip per una sola pagina e una sola funzione. È esteticamente sgradevole in un rework che punta a snellire, ed è una dipendenza che continuerà a essere caricata da CDN.
- **Lo skin del chrome DataTables non è banale.** Il plugin genera markup con classi proprie (`dt-search`, `dt-length`, `dt-info`, `dt-paging`, `.dataTables_wrapper` nella 1.13) su cui bisogna scrivere CSS "difensivo": è l'unica parte del rework in cui si stila markup non proprio. Da rifare se un giorno si aggiorna alla 2.x, che ha cambiato le classi.
- **Fetch runtime della lingua.** `language.url` fa una richiesta HTTP a `cdn.datatables.net` **a ogni caricamento** della pagina movimenti. Se il CDN è lento o irraggiungibile, la tabella si inizializza con le stringhe inglesi o resta in attesa. Mitigabile a costo zero: inlinare l'oggetto `language` invece di scaricarlo (ma è una micro-modifica al JS — da valutare se rientra nel perimetro).
- **Preserva un bug.** Se la Rilevazione sull'ordinamento è confermata, questa opzione lo mantiene. Corretto rispetto al vincolo, insoddisfacente rispetto al prodotto.
- **Doppia sorgente di verità sul tema dark.** DataTables 1.13 non ha supporto dark nativo; ogni superficie va ridichiarata nello skin.

### Peso e performance

| Voce | Raw ≈ | Gzip ≈ |
|---|---|---|
| jQuery 3.7.1 | 87 KB | 30 KB |
| DataTables core 1.13.7 | 85 KB | 28 KB |
| Responsive 2.5.0 (js) | 30 KB | 10 KB |
| Adapter bootstrap5 (js) | 5 KB | 2 KB |
| CSS (core + responsive) | 20 KB | 5 KB |
| `it-IT.json` | 1.5 KB | — (+1 richiesta HTTP) |
| **Totale** | **~230 KB** | **~75 KB** |

*Valori indicativi, da misurare in Fase 0.*

Con il tema neutro si risparmiano solo i ~2 adapter bootstrap5 (~3 KB gzip): il grosso
resta. Il costo è confinato a `/movements`, ma è la pagina che l'utente apre più spesso.
Nota: la tabella è **interamente renderizzata server-side senza paginazione** — il
filtro di default è il mese corrente, ma allargando l'intervallo a un anno il DOM può
arrivare a migliaia di `<tr>` che DataTables deve indicizzare al load. Con o senza
DataTables il problema esiste; DataTables lo rende più costoso.

### Isofunzionalità e rischio di regressione

**Rischio: basso.** Il comportamento non viene toccato. L'unico rischio è
**visivo**: uno skin incompleto lascia elementi del chrome non stilati (tipicamente il
select della lunghezza e i bottoni di paginazione), evidenti ma non funzionali.
Da verificare: search, ordinamento su tutte e 8 le colonne, paginazione, cambio
lunghezza, collasso responsive a 800 px, e la coesistenza con Tom Select nello stesso
pannello.

### Effort stimato

| Attività | gg |
|---|---|
| Sostituzione CSS + skin del chrome (search, length, info, paging) | 1.25 |
| Skin righe/header/hover/striped coerente col design system | 0.5 |
| Variante dark | 0.5 |
| Skin Responsive (child row, bottone `+`) | 0.5 |
| Test | 0.5 |
| **Totale** | **~3.25 gg** |

### Manutenibilità a lungo termine

**Media.** Il plugin è maturo e mantenuto, ma DataTables 2.x ha rinominato le classi
del wrapper: un futuro aggiornamento richiederà di rifare lo skin. E jQuery resta un
"passeggero" che vive solo per lui. Il verdetto onesto: è manutenibile, ma è debito che
prima o poi qualcuno vorrà chiudere.

### File coinvolti

`ps-show-mov.html` (`:243-249` link/script, `:255-277` init) e nuovo
`static/css/ps-datatables.css` (o un `@layer components` in `ps-tailwind.src.css`).

---

## Opzione D5-B — Riscrivere sort / paging / search / i18n a mano

Rimozione di jQuery + DataTables + Responsive, sostituiti da ~250-350 righe in
`ps-table.js`: ordinamento per colonna con tipizzazione, paginazione client, ricerca,
stringhe italiane hardcoded.

### Pro

- **Elimina l'ultima dipendenza jQuery del progetto.** ~75 KB gzip e 5 richieste CDN via dalla pagina più visitata. È il singolo intervento con il maggior impatto sul peso in tutto il rework.
- **Markup e classi interamente sotto controllo**, quindi Tailwind puro senza CSS difensivo, e dark mode che arriva gratis dai token del design system.
- **Occasione per correggere l'ordinamento per data** — con `data-order="{{ mov.move_date.isoformat() }}"` sul `<td>` il problema sparisce alla radice. (⚠️ è un **cambiamento di comportamento**: va scorporato in una voce `MB-NNN` a sé, non nascosto nel rework.)
- **Nessun chrome da stilare**: si genera solo ciò che serve, con la grafica giusta al primo colpo.
- **Coerenza**: la paginazione della tabella potrebbe riusare lo stesso componente di `ps-search-mov.html:113-140`, che oggi ha una paginazione server-side scritta a mano e stilata diversamente.

### Contro

- **⛔ È l'unico punto del piano in cui si riscrive logica, non presentazione.** Va contro il principio guida del task. Ordinamento, paginazione e ricerca sono *funzionalità*: rifarle significa che l'affermazione "isofunzionale" va dimostrata invece che garantita per costruzione.
- **Il collasso responsive è la parte cara e sottovalutata.** L'estensione Responsive nasconde le colonne a bassa priorità secondo lo spazio disponibile e le rende consultabili in una child row espandibile. Nella fascia 768-1000 px (tablet in verticale, finestre affiancate su desktop) è ciò che rende leggibile una tabella a 8 colonne. Riscriverlo bene vale da solo 1.5-2 gg; riscriverlo male è una regressione visibile.
- **Cento dettagli piccoli.** Tipizzazione per colonna (date, testo, valuta con simbolo € e trattini per i valori vuoti), stabilità dell'ordinamento, ricerca accent-insensitive, stato disabled dei bottoni di paginazione, messaggio "nessun risultato", plurali italiani, `aria-sort` sugli header. DataTables li ha già risolti tutti.
- **Effort più che raddoppiato**, con varianza alta: è il tipo di lavoro che si stima male.
- **Manutenzione a carico proprio**, su un componente non banale.

### Peso e performance

| Voce | Raw | Gzip |
|---|---|---|
| `ps-table.js` (stima) | ~12-16 KB | ~4-5 KB |
| **Rimosso** | ~230 KB | ~75 KB |

**Bilancio**: −70 KB gzip e −5 richieste CDN sulla pagina movimenti. Il TTI su rete
mobile migliora in modo percepibile, e sparisce il fetch bloccante di `it-IT.json`.
È il vantaggio più concreto di questa opzione, e non è piccolo.

### Isofunzionalità e rischio di regressione

**Rischio: alto** — il più alto dell'intero piano.

- ⛔ Ogni funzione della tabella va riverificata da zero: 8 colonne × 2 direzioni di ordinamento, paginazione ai bordi (prima/ultima pagina, N esatto multiplo di 25), ricerca su accenti e maiuscole, comportamento a 0 risultati.
- ⛔ Il collasso responsive è difficile da verificare "a occhio": funziona a 800 px ma non a 900? Serve un test a più larghezze.
- ⚠️ Interazione con l'export CSV e con `deleteMovement()`: il bottone Elimina sta dentro la tabella (`:205`) e dopo la cancellazione la pagina fa `location.reload()` — quindi nessuno stato da preservare, per fortuna. Ma se in futuro si volesse evitare il reload, la tabella custom dovrebbe gestire la rimozione della riga.
- ⚠️ Le decisioni "quale ordinamento è quello giusto" diventano scelte da fare, e ogni scelta è un potenziale scostamento dal comportamento attuale.

### Effort stimato

| Attività | gg (completo) | gg (ridotto\*) |
|---|---|---|
| Ordinamento tipizzato (data, testo, valuta) + `aria-sort` | 1.0 | 1.0 |
| Paginazione client + controlli | 0.75 | 0.75 |
| Ricerca globale | 0.5 | 0.5 |
| Selettore lunghezza + riga info + stringhe it-IT | 0.5 | 0.5 |
| **Collasso responsive + child row** | 1.75 | — |
| Integrazione, rimozione jQuery, verifica Tom Select | 0.5 | 0.5 |
| Test (8 colonne, bordi, larghezze) | 1.25 | 0.75 |
| Buffer (varianza alta) | 1.0 | 0.75 |
| **Totale** | **~7.25 gg** | **~4.75 gg** |

\* *Variante ridotta*: si rinuncia al collasso responsive accettando lo scroll
orizzontale nella fascia 768-1000 px (il `.table-responsive` esiste già a `:170`).
**È una regressione funzionale**, piccola ma reale, e va approvata esplicitamente.

### Manutenibilità a lungo termine

**Buona se fatto bene, altrimenti pessima.** Un componente tabella scritto in casa,
piccolo e con test, è ottimo da mantenere e non invecchia. Un componente tabella
scritto di fretta per chiudere una fase è la cosa che si rimpiange per anni. La
differenza la fa il tempo che gli si dedica — cioè esattamente ciò che un task di
restyling tende a comprimere.

### File coinvolti

`ps-show-mov.html` (`:168-214` tabella, `:242-249` script, `:255-277` init), nuovo
`static/js/ps-table.js`, eventualmente `ps-search-mov.html:113-140` per unificare la
paginazione.

---

## Confronto sintetico D5

| Criterio | D5-A tenere | D5-B riscrivere |
|---|---|---|
| Peso su `/movements` (gzip) | ~75 KB | **~5 KB** |
| Richieste CDN | 5 + 1 fetch i18n | **0** |
| jQuery nel progetto | resta | **eliminato** |
| Logica riscritta | **nessuna** | ordinamento, paging, ricerca, responsive |
| Rischio di regressione | **basso** | alto |
| Effort | **~3.25 gg** | ~7.25 gg (~4.75 ridotto, con regressione) |
| Collasso responsive 768-1000 px | **incluso** | da riscrivere o da sacrificare |
| i18n it-IT | **completa** | da scrivere |
| Bug ordinamento date | conservato | risolvibile |
| Qualità del dark mode | skin difensivo | **nativa** |
| Manutenibilità | media (skin da rifare su DT 2.x) | buona **se** fatto bene |

## ✅ Raccomandazione D5: **tenere DataTables** in questo task, con un percorso di uscita

La ragione è di sequenziamento, non di merito tecnico. D5-B è, nel merito, l'opzione
migliore per il prodotto: 70 KB gzip e cinque richieste CDN in meno sulla pagina più
visitata sono un guadagno reale, e jQuery caricato per una sola tabella è un residuo
che prima o poi va tolto.

Ma metterlo **dentro** il rework grafico significa infilare l'intervento a più alto
rischio di regressione dentro il task il cui vincolo cardine è "nessuna regressione",
e farlo nella pagina più complessa dell'app — quella che già concentra pannello filtri
collassabile, Tom Select con init differita, Chart.js, infinite scroll con
IntersectionObserver ed export CSV. Se dopo il rilascio l'utente segnala che "i
movimenti si vedono strani", con D5-A si sa che la causa è nel CSS; con D5-B lo spazio
di ricerca include l'intera logica della tabella.

C'è anche un argomento di verificabilità: il valore del piano sta nel poter dire, a
fine lavoro, "il comportamento è identico e lo dimostro". D5-A permette di dirlo.
D5-B costringe a dire "il comportamento dovrebbe essere identico, l'abbiamo testato" —
che è un'affermazione più debole.

**Percorso di uscita, da mettere a backlog subito:**

1. `MB-NNN` — *Verificare l'ordinamento per data della tabella movimenti*: confermare o smentire la Rilevazione, in Fase 0. Se confermato, correggerlo **subito e separatamente** con `data-order` sul `<td>` (`ps-show-mov.html:187`): è una modifica di 1 riga, indipendente dal restyling, e non ha senso portarsi dietro un bug di ordinamento per settimane.
2. `MB-NNN` — *Inlinare l'oggetto `language` di DataTables* al posto di `language.url` (`ps-show-mov.html:260-262`): elimina una richiesta CDN bloccante al load. Poche righe, rischio nullo.
3. `task20-0.md` — *Sostituzione di DataTables e rimozione di jQuery*: task autonomo, **da fare dopo** il restyling, quando i test di contratto di §7.3 del piano sono stabili e la tabella è già in markup Tailwind. A quel punto l'intervento è isolato, la rete di sicurezza c'è, e la stima di ~7 gg si può prendere per intero senza comprimere la qualità.

Se invece l'obiettivo prioritario fosse la performance della pagina movimenti — e si
accettasse un task più lungo e con più verifica — allora D5-B **variante completa**
(mai quella ridotta: sacrificare il collasso responsive è una regressione che si nota)
è difendibile. Ma andrebbe eseguita come **fase separata dopo la Fase 9**, non dentro
la Fase 6.

---

## Impatto combinato sulla stima del piano

| Scenario | D4 | D5 | Δ sulle 18-26 gg |
|---|---|---|---|
| **Raccomandato** | A (~5.25) | A (~3.25) | baseline, ~19-23 gg |
| Massima riduzione peso | A (~5.25) | B completo (~7.25) | **+4 gg**, ~23-27 gg, rischio ↑↑ |
| Massima velocità di scrittura | B (~7) | A (~3.25) | +1.75 gg, rischio ↑↑ |
| Peggiore combinazione | B (~7) | B (~7.25) | **+5.75 gg**, rischio ↑↑↑ |

---

## Sintesi in una riga

**D4 → `ps-ui.js` vanilla**, perché è l'unica opzione che non obbliga a riscrivere i
17 call site imperativi di Bootstrap presenti nel codice, e quindi l'unica compatibile
con il vincolo di isofunzionalità.

**D5 → tenere DataTables ora, sostituirlo in un task dedicato dopo**, perché il
guadagno (70 KB gzip, jQuery via) è reale ma non vale il rischio di infilare l'unica
riscrittura di logica del piano dentro la pagina più complessa dell'app, proprio nel
task in cui bisogna dimostrare che nulla è cambiato.
