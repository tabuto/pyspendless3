# Fase 5 — Il campo labels nei due form

**Chi**: subagent **`ps-markup`** (profilo del task19-0: conversione meccanica
e isofunzionale, una pagina per invocazione).
**Dipende da**: Fase 4 verde.
**Fatto quando**: `.venv/bin/python test/test_task26_0.py contract` non segnala
più i due template, **e** `.venv/bin/python test/test_task19_0.py` resta verde
(contratto DOM del restyling).
**File**: `pyspendless/templates/ps-add-mov.html`,
`pyspendless/templates/ps-recurrent-mov.html`. Una invocazione per file.

## Il mandato

Sotto la textarea della nota, un campo:

```html
<div class="mb-3" data-ps-labels-wrap>
  <label for="labels" class="ps-label">Labels</label>
  <select id="labels" name="labels" multiple
          data-ps-labels
          data-ps-labels-target="#note"
          data-ps-note-max="{{ max_note_length }}"
          data-ps-labels-max="{{ max_labels_per_movement }}"></select>
  <p class="ps-help" data-ps-labels-message hidden></p>
  <p class="ps-help">Le label finiscono nella nota, scritte con #.</p>
</div>
```

I due `data-*` dei limiti **non sono decorativi**: `MAX_NOTE_LENGTH` e
`MAX_LABELS_PER_MOVEMENT` vivono in `conf.py` (il canale MCP usa il primo), e
questo è il modo di non duplicarli nel JavaScript. `ps-labels.js` li legge dal
markup e tiene i propri valori solo come ripiego: se il template non li passa,
cambiare `conf.py` smette di avere effetto sul campo. Le due variabili vanno
quindi aggiunte al `render_template` delle due pagine — ed è **l'unico
intervento su `app.py`** consentito in questa fase.

`data-ps-labels-wrap` e `[data-ps-labels-message]` sono le due convenzioni che
`ps-labels.js` cerca: il wrapper è quello che viene nascosto se il CDN di Tom
Select non risponde (nascondere il solo `<select>` lascerebbe l'etichetta
orfana), e il paragrafo è dove finiscono i messaggi di rifiuto. Se non li
fornisci, il componente crea il contenitore da sé e nasconde solo il campo:
funziona, ma peggio.

Sotto e non sopra: l'effetto di una chip aggiunta è un testo che cambia, e va
visto.

Più, nel block degli script della pagina, il `<link>` e il `<script>` di Tom
Select dal CDN (**le stesse versioni** già usate in `ps-show-mov.html:18,329`,
non versioni nuove) e `ps-labels.js`, con l'init dentro al
`DOMContentLoaded` esistente.

## I vincoli

1. **Il payload dell'API non cambia.** `POST /api/movements` continua a mandare
   `note` e nient'altro di nuovo: le label sono dentro il testo. Se ti viene da
   aggiungere `labels: [...]` al `formData`, fermati — sono due fonti di verità
   e la specifica (§10) ne vuole una.
2. **`form.reset()`**: in creazione il form si resetta dopo il salvataggio
   (`ps-add-mov.html`, ramo `if (!movId)`). Il campo a chip **non** si svuota
   da solo: va svuotato a mano insieme al reset, o la seconda spesa nasce con
   le label della prima.
3. **Modalità modifica e "Ripeti"**: la nota arriva già valorizzata dal server,
   quindi le chip devono comparire al caricamento — cioè l'init legge la
   textarea, non parte vuoto.
4. **Il selettore di spesa ricorrente** (`#recurrent_template`) riscrive
   `#note` da JavaScript: dopo quella riscrittura le chip vanno riallineate.
   È il caso che si dimentica più facilmente, perché non passa dall'evento
   `input` dell'utente.
5. ~~`ps-recurrent-mov.html` usa un modal per creare/modificare la ricorrente:
   l'init del campo va fatto all'apertura del modal.~~ **Sbagliato, verificato
   in Fase 5**: in quella pagina il form è **inline** e sempre visibile
   (`<form id="recurrent-form">`, riga 20); l'unico `<dialog class="ps-modal">`
   è la conferma di eliminazione. Quindi niente contenitore nascosto e niente
   init rimandato: vale l'attivazione automatica su `DOMContentLoaded`. Resta
   invece vero il resto: `resetForm()` chiama `form.reset()` (quindi le chip si
   svuotano da sole, il componente ascolta `reset`), e `editRecurrent()`
   riempie `#rm_note` da JavaScript — lì l'evento `input` va emesso a mano.
