# Fase 7 — Ricerca movimenti

**Agente**: `ps-markup`
**Stima**: 1-2 gg
**Dipende da**: Fase 6 verde.

`ps-search-mov.html`. Struttura ibrida: tabella **server-side** con paginazione
classica su desktop, card-list con **infinite scroll** su mobile — due
meccaniche di paginazione diverse nella stessa pagina.

## Note

- Le icone sono `fas fa-*` (search, edit, redo, trash, undo) ma Font Awesome
  **non è caricato**: oggi non si vedono (difetto **P1**). Sostituire con i
  corrispondenti `bi bi-*`, coerenti con il resto dell'app, se D10 è approvata.
  I corrispettivi usati altrove: `bi-search`, `bi-pencil`, `bi-arrow-repeat`,
  `bi-trash`, `bi-arrow-counterclockwise`.
- La card-list condivide gli stessi id di `ps-show-mov.html`
  (`cards-container`, `load-more-trigger`, `cards-spinner`, `no-more-msg`) più
  `no-results-msg`. Riusa lo stesso pattern di classi `.ps-*` definito in
  Fase 6: le due liste devono apparire identiche.
- La paginazione server-side (`.pagination`, `.page-item`, `.page-link`) è
  l'unica dell'app. Gli stati `disabled` su Precedente/Successivo e
  `tabindex="-1"` / `aria-disabled` vanno preservati.
- Regola sulle classi dinamiche: 5 `innerHTML`.

## Criteri di accettazione

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A7.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |
| A7.2 | Estende `ps-nav-tw.html`, nessuna classe Bootstrap residua | grep |
| A7.3 | `name="search"` e i 6 id preservati | incluso nel test |
| A7.4 | Nessuna classe costruita per concatenazione | `IgieneTemplate`, file tolto dalla whitelist |
| A7.5 | Nessuna classe `fa`/`fas`/`far` residua | grep |
| A7.6 | Il blocco `<script>` invariato salvo le stringhe di classe | diff |
| A7.7 | Gli `href` della paginazione conservano `?search={{ search_text }}&page=N` | grep |

### Verificabili solo dall'agente principale (Chrome)

| # | Criterio |
|---|---|
| A7.8 | La ricerca produce la stessa querystring `?search=…&page=N` |
| A7.9 | "Trovati N movimenti" con il numero corretto |
| A7.10 | Paginazione: Precedente disabilitato a pagina 1, Successivo disabilitato all'ultima |
| A7.11 | Reset riporta alla pagina vuota |
| A7.12 | A 375 px: card-list con infinite scroll; "Nessun movimento trovato" se la ricerca non dà risultati |
| A7.13 | A 768 px: tabella con paginazione server-side |
| A7.14 | Le icone azione (modifica, ripeti, elimina) sono **visibili** e portano dove devono |
| A7.15 | Le card qui e quelle di `/movements` hanno lo stesso aspetto |
| A7.16 | Nessun overflow a 375 px, light e dark |

A7.14 riguarda solo i **tre bottoni d'azione**, dove l'icona è l'etichetta.
È una verifica che la baseline non può confermare — oggi quei bottoni sono
vuoti — ed è un miglioramento dichiarato, non una regressione. Le tre icone
decorative, invece, spariscono e basta: lì la baseline resta il riferimento.

## Definition of done

Ricerca e paginazione invariate nel comportamento, card-list coerente con
`/movements`, e le icone che prima erano invisibili ora ci sono.
