# Fase 5 — Movimenti (il percorso principale)

**Chi**: **3 × `ps-i18n-template`** su **haiku**, in worktree, in parallelo
+ l'**agente principale** per il self-hosting di DataTables (§5.4).
**Durata**: 1 giorno.
**Dipende da**: Fase 3 verde e committata (è il collaudo del metodo).

---

## Le tre invocazioni

| # | File | Stringhe attese |
|---|---|---|
| 5.A | `ps-add-mov.html` | 15 testi + 8 nel JS |
| 5.B | `ps-search-mov.html` | 19 testi + 5 attributi + 9 nel JS |
| 5.C | `ps-show-mov.html` | 48 testi + 7 attributi + 14 nel JS |

File disgiunti, parallelismo sicuro. Nessuno apre il browser.

---

## Note per file

### `ps-add-mov.html` (5.A)

Riga 19: `Stai ripetendo il movimento del {{ repeat_source.move_date.strftime('%d/%m/%Y') }}:`
è una stringa **con interpolazione**: va a `{% trans %}`, non a `_()`.
Il formato della data **non si tocca qui** — i formati sono la Fase 8.

Riga 57: il `value` dell'`<input type="date">` è `%Y-%m-%d`. È un **formato
macchina** imposto dall'HTML: non si avvolge, non si localizza, non si tocca.
Mai (criterio A6 della specifica).

### `ps-search-mov.html` (5.B)

Riga 47 `Nessun movimento trovato` e riga 160
`Nessun movimento trovato per la ricerca "{{ search_text }}"`: la seconda è
interpolata → `{% trans %}`. Attenzione a non avvolgere `{{ search_text }}`:
è testo scritto dall'utente.

Le due frasi sono **diverse** e vanno tenute distinte: in un'altra lingua
potrebbero divergere più che in italiano.

### `ps-show-mov.html` (5.C)

Il template più denso del progetto, e quello con più JS. Tre punti d'attenzione:

1. **Riga 215**: `data-order="{{ mov.move_date.isoformat() }}"` è ciò che
   DataTables usa per **ordinare**. È un formato macchina: **non si tocca**. Il
   `{{ mov.move_date.strftime('%d/%m/%Y') }}` accanto è la vista, e lo localizza
   la Fase 8.
2. **Riga 542**: `return '<div class="no-results">Nessun risultato</div>';` —
   stringa italiana **dentro** una stringa HTML, nel JS. Si avvolge solo il
   testo: `'<div class="no-results">' + '{{ _('Nessun risultato') }}' + '</div>'`
   oppure, meglio, si estrae il testo in una costante avvolta e si lascia il
   markup intatto. **Il markup non entra nel msgid** (divieto 2 di §5 del piano).
3. **Riga 337**: la localizzazione di DataTables — §5.4 qui sotto, **non è
   lavoro del subagent**.

Le etichette dei grafici Chart.js in coda al file si avvolgono come normali
stringhe JS.

---

## 5.4 DataTables self-hostato — lo fa l'agente principale

Oggi (`ps-show-mov.html:337`):

```js
language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/it-IT.json' }
```

**Decisione P3, chiusa il 2026-10-19: si self-hosta.** Non è lavoro delegabile:
un subagent in worktree non ha una rete utile, e scaricare un file da internet
è un'azione che vuole l'approvazione dell'utente.

L'agente principale:

1. scarica i due file della **versione 1.13.7** — la stessa che la pagina
   carica, non l'ultima:

   ```bash
   cd /Users/fradidio/Sviluppo/pyspendless3/pyspendless/static/js/i18n
   curl -fsSLo datatables-it-IT.json https://cdn.datatables.net/plug-ins/1.13.7/i18n/it-IT.json
   curl -fsSLo datatables-en-GB.json https://cdn.datatables.net/plug-ins/1.13.7/i18n/en-GB.json
   ```

2. li versiona (sono ~2 KB l'uno) e verifica che siano JSON validi;
3. cambia la riga 337 in:

   ```js
   language: { url: '{{ url_for("static", filename="js/i18n/datatables-" ~ dt_locale ~ ".json") }}?v={{ app_version }}' }
   ```

   dove `dt_locale` arriva dal context processor (Fase 1 §1.4) e vale `it-IT`
   o `en-GB`.

Due cose da non sbagliare: il `?v={{ app_version }}` (cache-busting, come per
CSS e JS del progetto), e il fatto che `dt_locale` usa il **trattino** mentre
Babel usa l'underscore — la conversione sta in `i18n.py`, non qui.

---

## Criteri di accettazione

### Verificabili dal subagent

| # | Criterio | Come si verifica |
|---|---|---|
| A5.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code |
| A5.2 | `tools/check-i18n.py --file <file assegnato>` esce **0** | exit code |
| A5.3 | `data-order`, `isoformat()` e il `value` degli input date **invariati** | grep + diff |
| A5.4 | Nessun tag HTML dentro un msgid | coperto da A5.2 |
| A5.5 | `{{ search_text }}`, `{{ mov.note }}`, `{{ category.name }}` non avvolti | grep |
| A5.6 | Stesso numero di `$('#...')` e di selettori nel JS | diff — il JS non si rifattorizza |
| A5.7 | `git status --short` mostra solo i file assegnati, niente `translations/` | ispezione |

### Verificabili solo dall'agente principale

| # | Criterio |
|---|---|
| A5.8 | DataTables si inizializza senza errori in console, con il JSON **locale** (verificabile in rete: nessuna richiesta a `cdn.datatables.net`) |
| A5.9 | Ordinamento per data ancora corretto (è il `data-order`: se si è rotto, le date si ordinano alfabeticamente e si vede subito) |
| A5.10 | Filtri, ricerca e paginazione funzionanti; il messaggio "nessun risultato" compare |
| A5.11 | I grafici si rendono in light e in dark |
| A5.12 | Creazione, modifica e ripetizione di un movimento funzionanti end-to-end |
| A5.13 | Export CSV: header italiano e date ISO (criterio A6) |
| A5.14 | `git diff --stat` tocca solo `templates/**` e `static/js/i18n/**` |

## Definition of done

Il percorso che la gente usa ogni giorno — aggiungi, cerca, guarda — è
avvolto, DataTables è localizzato senza CDN, e gli ordinamenti e gli export non
si sono accorti di niente.
