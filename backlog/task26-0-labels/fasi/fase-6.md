# Fase 6 — Chip in elenco e ricerca, filtro nel pannello

**Chi**: subagent **`ps-markup`**.
**Dipende da**: Fase 4 verde (usa `PsLabels.decorate`) e Fase 3 verde (il
filtro lato server esiste già).
**Fatto quando**: la sezione `contract` non segnala più questi template, e
`test_task19_0.py` resta verde.
**File**: `pyspendless/templates/ps-show-mov.html`,
`pyspendless/templates/ps-search-mov.html`.

## 6.1 Le chip (sola lettura)

Marca con `data-ps-note` i quattro punti in cui una nota viene resa:

| Dove | Riferimento |
|---|---|
| cella della tabella desktop | `ps-show-mov.html:218` |
| renderer delle card mobile | `ps-show-mov.html:619` (dentro la stringa HTML costruita in JS) |
| tabella di `/ps-search-mov` | l'equivalente in `ps-search-mov.html` |
| card mobile di `/ps-search-mov` (infinite scroll) | idem |

Poi `PsLabels.decorate()` va richiamata in **tre** momenti, non uno:

1. al `DOMContentLoaded`;
2. su `draw.dt` — **DataTables ridisegna le celle** a ogni cambio pagina e
   ordinamento, e le chip sparirebbero dalla seconda pagina in poi (il test
   verifica la presenza di `draw.dt`);
3. sul frammento appena appeso dall'infinite scroll delle card.

Il testo visibile resta `#coop`, quindi la ricerca client di DataTables
continua a funzionare.

## 6.2 Il filtro

Nel pannello filtri già esistente (`filters-collapse`), un Tom Select
multi-selezione `name="label"`, popolato da `/api/labels`, con i valori
correnti pre-selezionati da `labels_raw`.

Tre cose da rispettare:

1. **Init rimandato alla prima apertura** del pannello, come
   `initCategorySelect()` (`ps-show-mov.html:527`): il pannello è collassato e
   inizializzare dentro a `display:none` sbaglia il posizionamento del
   dropdown. Riusa lo stesso schema, non inventarne un altro.
2. **L'etichetta dice la semantica**: "tutte le label selezionate" — il filtro
   è in **AND**, a differenza del campo keywords che è in OR. Un utente che si
   aspetta l'OR vede zero risultati e pensa a un bug.
3. Il badge con il **conteggio dei filtri attivi** arriva da `active_count`
   (Fase 3): se il filtro per label non lo incrementa, il pannello si richiude
   nascondendo un filtro attivo.

## 6.3 Click su una chip

`href="/movements?label=coop"` — la chip è un link, non un `onclick`: deve
funzionare con il tasto centrale e col copia-indirizzo. Lo costruisce
`PsLabels.decorate` (Fase 4), qui non si duplica la logica.
