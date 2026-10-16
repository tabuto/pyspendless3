# Fase 4 — Pagine form

**Agente**: `ps-markup`, una invocazione per pagina (2 subagent)
**Stima**: 2-3 gg
**Dipende da**: Fase 3 verde.

`ps-add-mov.html` e `ps-recurrent-mov.html`. Entrambe estendono `ps-nav-tw.html`.

## `ps-add-mov.html` — la più delicata delle due

Il JS di questa pagina (righe 108-336) **non si tocca**. Solo markup.

Il form serve **tre modalità** distinte, decise server-side, e tutte e tre
vanno riprovate dopo la conversione:

1. **nuovo** — `/create`
2. **modifica** — `/create?movement_id=<id>`
3. **ripeti** — `/create?repeat_from=<id>`, con data odierna e alert informativo

Contratto specifico, oltre agli id: gli attributi `data-*` sulle `<option>`.
Le categorie hanno `data-type` (usato da `filterCategories()` per filtrare in
base al tipo movimento); le spese ricorrenti hanno `data-movement-type`,
`data-category-id`, `data-wallet-id`, `data-amount`, `data-note`, letti dal
listener su `#recurrent_template` per precompilare il form. Se uno sparisce,
la precompilazione smette di funzionare **in silenzio**.

Attenzione a `showAlert()` (righe 290-334): fa `scrollIntoView`, `focus()`,
auto-hide a 5s **sospeso finché l'alert ha il focus**, e in modalità "Ripeti"
usa `behavior:'auto'` per non perdere il redirect a 1s. Resta dov'è, invariata.

`localStorage['ps_last_wallet_id']`: preseleziona l'ultimo wallet usato, solo
in creazione. Non è markup, ma è comportamento osservabile da verificare.

## `ps-recurrent-mov.html`

Form crea/modifica + tabella + modal di conferma eliminazione.

Il markup delle righe è **anche** generato in JS (6 `innerHTML`): applica la
regola sulle classi dinamiche — ogni ramo di un ternario produce la classe
intera, meglio se una `.ps-*`.

I bottoni riga passano parametri inline a `editRecurrent(...)` e
`confirmDelete(...)` con `|e` sui valori: la forma delle chiamate va
preservata esattamente.

## Criteri di accettazione

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A4.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |
| A4.2 | Il template estende `ps-nav-tw.html` | grep |
| A4.3 | Nessuna classe Bootstrap residua | grep su `btn btn-`, `card-`, `col-md-`, `form-control`, `d-md-`, `mb-3` |
| A4.4 | Tutti gli `id=` preservati | diff con `git show HEAD:<file>` |
| A4.5 | **Tutti i `data-*` sulle `<option>` preservati** | grep: `data-type`, `data-movement-type`, `data-category-id`, `data-wallet-id`, `data-amount`, `data-note` |
| A4.6 | Il blocco `<script>` è **byte-identico** a prima | `diff <(git show HEAD:<file> \| sed -n '/<script>/,/<\/script>/p') <(sed -n '/<script>/,/<\/script>/p' <file>)` — tranne le stringhe di classe autorizzate |
| A4.7 | Nessuna classe CSS costruita per concatenazione | `IgieneTemplate` nel test, dopo aver tolto il file dalla whitelist |
| A4.8 | Le chiamate inline `editRecurrent(...)` / `confirmDelete(...)` hanno gli stessi argomenti | grep + confronto |
| A4.9 | Campi `required`, `min`, `step`, `maxlength`, `rows` preservati | grep degli attributi di validazione |

A4.6 è il criterio più importante di questa fase: se il JS cambia, la
conversione ha sconfinato.

### Verificabili solo dall'agente principale (Chrome)

| # | Criterio |
|---|---|
| A4.10 | **Creazione**: salva, mostra l'alert di successo, resetta il form, ripristina data odierna e tipo "Uscita" |
| A4.11 | **Modifica**: `?movement_id=` precompila tutto, salva, **non** resetta |
| A4.12 | **Ripeti**: `?repeat_from=` precompila con data odierna, mostra l'alert informativo, dopo il salvataggio redirige a `/movements` dopo 1s |
| A4.13 | Il selettore spesa ricorrente precompila tipo, categoria, wallet, importo, nota — **e non tocca la data** |
| A4.14 | Cambiando "Tipo Movimento" le categorie si filtrano per tipo |
| A4.15 | `ps_last_wallet_id`: il wallet dell'ultimo salvataggio è preselezionato alla creazione successiva |
| A4.16 | L'alert di esito entra nella viewport (scroll automatico) e non sparisce mentre ha il focus |
| A4.17 | Ricorrenti: crea, modifica, annulla, elimina con modal di conferma |
| A4.18 | Entrambe le pagine senza overflow a 375 px, in light e dark |

## Definition of done

Le tre modalità di `/create` funzionano identiche a prima, il CRUD delle
ricorrenti è completo, e il blocco `<script>` di `ps-add-mov.html` è rimasto
quello che era.
