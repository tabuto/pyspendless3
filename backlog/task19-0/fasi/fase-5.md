# Fase 5 — Pagine impostazioni con modal

**Agente**: `ps-markup`, una invocazione per pagina (6 subagent)
**Stima**: 4-5 gg
**Dipende da**: Fase 4 verde.

Ordine per complessità crescente: `ps-setting-wallet` →
`ps-setting-import-export` → `ps-setting-profile` → `ps-setting-admin` →
`ps-setting-categories` → `ps-setting-group`.

È la fase che mette alla prova `ps-ui.js`: **12 modal**, tutti qui tranne quello
delle ricorrenti.

> **Correzione al piano (2026-10-17): le pagine sono SEI, non cinque.**
> `ps-setting-profile.html` — token MCP e connessioni OAuth — non era assegnata
> a **nessuna** fase: compariva solo di sfuggita nella tabella di conversione.
> È una pagina di impostazioni come le altre, ha 2 modal (`addTokenModal`,
> `showTokenModal`) e carica il bundle Bootstrap duplicato di A5.9. Lasciarla
> fuori significherebbe arrivare in Fase 9 con una pagina ancora su Bootstrap e
> non poterlo rimuovere. Entra qui.
>
> Da cui anche: i modal diventano **12**, e le sei interazioni A5.10-A5.15 si
> applicano a tutti e dodici.

## Il vincolo che governa la fase

Il JS di queste pagine chiama l'**API imperativa** di Bootstrap:
`new bootstrap.Modal(el).show()`, `bootstrap.Modal.getInstance(el).hide()`.
Quel JS **non si tocca**: funziona grazie allo shim in `ps-ui.js` scritto in
Fase 1. Se un modal non si apre, il problema è nello shim, non nel markup —
segnalalo invece di aggirarlo modificando la pagina.

Il markup del modal deve conservare gli stessi `id` e gli stessi
`data-bs-toggle="modal"` / `data-bs-dismiss="modal"` **oppure** i loro
equivalenti `data-ps-*`, coerentemente con quanto implementato in `ps-ui.js`.
Decidi una volta in Fase 1 e sii coerente su tutte e 10.

## Note per pagina

### `ps-setting-wallet.html`
2 modal. Le card dei wallet sono generate in JS (5 `innerHTML`): regola sulle
classi dinamiche.
Il blocco a `:198-205` rimuove a mano il backdrop Bootstrap — con `<dialog>`
diventa innocuo. **Lascialo**, e annotalo.

### `ps-setting-import-export.html`
Nessun modal. `<input type="file">` stilizzato con la variante `file:` di
Tailwind: **non** alterare `accept=".csv"` né l'id `csvFile`.
Progress bar striped animated. `bg-warning` senza `text-white` è già oggi un
problema di contrasto: con i token tinted si risolve.

### `ps-setting-admin.html`
1 modal. Due tabelle server-rendered con `tr[data-email]` e `tr[data-user-id]`:
il JS li usa per rimuovere la riga dopo la cancellazione. Preservarli.

### `ps-setting-categories.html`
3 modal **più** i tab Uscite/Entrate (`data-bs-toggle="tab"`, gli unici tab
dell'app) e il toggle di ordinamento alfabetico.
`{{ session.account_id }}` inline nel JS a riga 186: **mantenere**.
11 `innerHTML`: regola sulle classi dinamiche.
Il modal di eliminazione ha una meccanica a sé: se la categoria ha movimenti,
chiede la categoria di destinazione prima di cancellare.

### `ps-setting-profile.html`

2 modal (`addTokenModal`, `showTokenModal`). Mostra l'URL del server MCP in un
campo readonly (`#mcpUrl`, classe `font-monospace` → `font-mono`) con un
bottone che chiama `copyValue('mcpUrl')`: la **forma della chiamata inline** va
preservata. Due tbody popolati da JS — `#tokensContainer` e
`#oauthConnectionsContainer` — quindi vale la regola sulle classi dinamiche.
`#newTokenValue` mostra il token appena creato: è l'unico momento in cui è
visibile, quindi il markup di quel modal non va semplificato.

### `ps-setting-group.html` — la più complessa
3 modal, 24 `innerHTML`, list-group per membri e inviti, Web Share API,
clipboard, e la "Zona pericolosa" con conferma digitando `ELIMINA`.

⚠️ **Il punto critico dell'intera fase**: il listener `show.bs.modal` su
`#deleteAccountModal` (riga 264) chiama `checkAccountSharing()`, che decide
quali voci mostrare in `#deletionDetails` — cioè cosa l'utente legge su *che
cosa sta per cancellare*. Se l'evento non arriva prima che il modal sia
visibile, l'utente vede per un istante informazioni sbagliate su una
cancellazione irreversibile. Va provato per primo.

Gli altri tre listener (`hidden.bs.modal` a 230, 239, 258) resettano i form
alla chiusura: vanno verificati uno per uno.

## Criteri di accettazione

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A5.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |
| A5.2 | Estende `ps-nav-tw.html`, nessuna classe Bootstrap residua | grep |
| A5.3 | Tutti gli `id=` preservati, modal inclusi | diff con `git show HEAD:<file>` |
| A5.4 | Il blocco `<script>` invariato, salvo le stringhe di classe autorizzate | diff |
| A5.5 | Nessuna classe costruita per concatenazione | `IgieneTemplate`, file tolto dalla whitelist |
| A5.6 | Gli attributi `data-email` / `data-user-id` sulle `<tr>` preservati (admin) | grep |
| A5.7 | `accept=".csv"` e id `csvFile` preservati (import-export) | grep |
| A5.8 | `{{ session.account_id }}` ancora presente (categorie) | grep |
| A5.9 | Il secondo `<script src=...bootstrap.bundle...>` rimosso dal `{% block scripts %}` | grep |

### Verificabili solo dall'agente principale (Chrome)

Per **ognuno dei 10 modal**, sei interazioni:

| # | Criterio |
|---|---|
| A5.10 | Apre dal trigger `data-bs-toggle` |
| A5.11 | Apre da JS (`new bootstrap.Modal(...).show()`) |
| A5.12 | Chiude con la X |
| A5.13 | Chiude con "Annulla" / "Chiudi" |
| A5.14 | Chiude con Esc |
| A5.15 | Chiude con click sul backdrop |

Più, al netto dei modal:

| # | Criterio |
|---|---|
| A5.16 | **`show.bs.modal` su `deleteAccountModal` arriva prima che il modal sia visibile**: `#deletionDetails` è già corretto alla comparsa |
| A5.17 | I tre `hidden.bs.modal` resettano i rispettivi form alla chiusura |
| A5.18 | Dopo la chiusura: nessun backdrop fantasma, scroll del body ripristinato |
| A5.19 | CRUD wallet completo: crea, modifica (nome, valuta, ordine), elimina |
| A5.20 | CRUD categorie: crea, rinomina, cambia ordine, elimina **con spostamento movimenti**, merge su rinomina a nome esistente |
| A5.21 | Tab Uscite/Entrate e toggle ordinamento alfabetico |
| A5.22 | Group: rinomina account, genera link di invito, copia, condividi, elimina invito pendente |
| A5.23 | Zona pericolosa: il bottone si abilita **solo** digitando esattamente `ELIMINA` |
| A5.24 | Admin: aggiungi/rimuovi whitelist, elimina utente; il proprio utente non è eliminabile |
| A5.25 | Import/export: scarica CSV, importa CSV con progress e riepilogo errori |
| A5.26 | Le 5 pagine senza overflow a 375 px, in light e dark |

## Definition of done

Tutti i CRUD delle impostazioni funzionano come prima, i 10 modal superano le
sei interazioni, e nessun backdrop resta appeso.
