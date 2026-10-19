# Fase 1 — Infrastruttura Tailwind

**Agente**: `ps-component`
**Stima**: 2-3 gg
**Nessun template esistente viene toccato.** `ps-base.html` resta identico,
l'app continua a girare su Bootstrap. Alla fine di questa fase l'aspetto
dell'applicazione non è cambiato di un pixel.

## Attività

### 1.1 — Toolchain

`tools/build-css.sh`: scarica il binario Tailwind CLI standalone se manca, poi
compila.

```bash
./tools/tailwindcss \
  -i pyspendless/static/css/ps-tailwind.src.css \
  -o pyspendless/static/css/ps-tailwind.css \
  --minify
```

`.gitignore`: aggiungi `tools/tailwindcss*` (il binario, ~40 MB, non va
versionato) e **verifica esplicitamente** che `ps-tailwind.css` non finisca
ignorato da una regola esistente. Il CSS compilato **deve** essere versionato:
il deploy è un `git pull`, non c'è build sul server.

### 1.2 — Sorgente e token

`pyspendless/static/css/ps-tailwind.src.css`. Bozza completa al §2.3 del piano.
Struttura:

```css
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
@source "../../templates/**/*.html";
@source "../js/*.js";

@theme { /* palette grezza, font, radius */ }

@layer base {
  :root { /* token semantici light */ }
  .dark { /* token semantici dark */ }
}

@layer components { /* .ps-card, .ps-btn, .ps-input, … */ }
```

I token semantici e la palette stanno al §3.2 del piano. **Il vincolo che non
si negozia**: verde = entrate, rosso = uscite, info/warning = bilancio
positivo/negativo. Cambiare la tinta è ammesso, scambiare i ruoli no.

### 1.3 — Tabella di conversione

**Questa sezione è l'input di `ps-markup` per tutte le fasi successive.** Non è
una bozza: è stata compilata estraendo tutti gli `class="…"` dai 18 template
renderizzati più i 3 layout — **1.022 attributi, 295 classi distinte** — e
classificandoli uno per uno. Se `ps-markup` incontra un pattern che non è qui,
si ferma e segnala, come prescrive la sua definizione.

> Copertura: ogni classe Bootstrap/AdminLTE trovata nei template appartiene a
> una delle famiglie qui sotto. I conteggi fra parentesi sono le occorrenze
> reali, e servono a dare la scala: `btn` compare 89 volte, `btn-info` una.

#### Componenti — diventano classi `.ps-*` in `@layer components`

| Bootstrap | Target | Note |
|---|---|---|
| `card` (42) | `ps-card` | |
| `card-header` (32) / `card-body` (44) / `card-footer` (2) | `ps-card-header` / `ps-card-body` / `ps-card-footer` | |
| `card-title` (39) | `ps-card-title` | |
| `card-text` (4) | nessuna classe, è solo un paragrafo | |
| `card-primary` (3) / `card-outline` (1) | `ps-card-accent` | header colorato di marca |
| `card-header-tabs` (1) | `ps-card-header-tabs` | solo `ps-setting-categories.html` |
| `btn` (89) | `ps-btn` | base, mai da sola nel markup finale |
| `btn-primary` (28) | `ps-btn-primary` | |
| `btn-secondary` (16) | `ps-btn-secondary` | |
| `btn-danger` (13) | `ps-btn-danger` | |
| `btn-warning` (3) | `ps-btn-warning` | |
| `btn-success` (1) | `ps-btn-success` | |
| `btn-info` (1) | `ps-btn-info` | |
| `btn-light` (1) | `ps-btn-light` | |
| `btn-outline-secondary` (13) | `ps-btn-outline-secondary` | |
| `btn-outline-primary` (5) | `ps-btn-outline-primary` | |
| `btn-outline-danger` (5) | `ps-btn-outline-danger` | |
| `btn-outline-warning` (1) | `ps-btn-outline-warning` | |
| `btn-outline-success` (1) | `ps-btn-outline-success` | |
| `btn-link` (1) | `ps-btn-link` | |
| `btn-sm` (36) / `btn-lg` (2) | `ps-btn-sm` / `ps-btn-lg` | **target touch ≥ 44 px su mobile** |
| `btn-close` (22) / `btn-close-white` (2) | `ps-btn-close` / `ps-btn-close-light` | la X dei modal e degli alert |
| `btn-group-vertical` (1) | `flex flex-col` | caso unico, `ps-home.html` |
| `form-control` (31) / `form-control-sm` (1) | `ps-input` / `ps-input-sm` | |
| `form-select` (19) | `ps-select` | |
| `form-label` (46) | `ps-label` | la classe più frequente dei form |
| `form-text` (12) | `ps-help` | |
| `form-group` (1) | `mb-3` → `ps-field` | residuo Bootstrap 4, una sola occorrenza |
| `input-group` (3) | `ps-input-group` | |
| `table` (9) + `table-striped` (9) + `table-hover` (3) | `ps-table` | le tre insieme sono il pattern reale |
| `table-bordered` (1) | `ps-table-bordered` | |
| `table-responsive` (5) | `overflow-x-auto` | |
| `modal` (13) / `modal-dialog` / `modal-content` | `<dialog class="ps-modal">` + `ps-modal-panel` | vedi 1.4: il markup cambia struttura |
| `modal-header` / `modal-title` / `modal-body` / `modal-footer` (13 ciascuna) | `ps-modal-header` / `-title` / `-body` / `-footer` | |
| `alert` (15) | `ps-alert` | |
| `alert-success` (4) | `ps-alert-success` | |
| `alert-danger` (4) | `ps-alert-danger` | |
| `alert-info` (3) | `ps-alert-info` | |
| `alert-warning` (3) | `ps-alert-warning` | |
| `alert-dismissible` (1) / `alert-heading` (1) | `ps-alert-dismissible` / `ps-alert-heading` | |
| `badge` (9) | `ps-badge` + modificatore semantico | **mai `bg-*`**, vedi sotto |
| `spinner-border` (7) / `spinner-border-sm` (5) | `ps-spinner` / `ps-spinner-sm` | |
| `progress` / `progress-bar` / `progress-bar-striped` / `progress-bar-animated` (1 ciascuna) | `ps-progress` / `ps-progress-bar` / `ps-progress-striped` / `ps-progress-animated` | solo import/export |
| `list-group` (3) / `list-group-flush` (3) / `list-group-item` (11) | `ps-list` / `ps-list-flush` / `ps-list-item` | membri e inviti in `ps-setting-group.html` |
| `nav-tabs` (1) / `nav-item` (21) / `nav-link` (21) | `ps-tabs` / `ps-tab` / `ps-tab-btn` | |
| `nav` (4) | contesto: `ps-tabs` sui tab, struttura della sidebar altrove | da sola non ha stile proprio |
| `tab-content` (1) / `tab-pane` (2) | `ps-tabpanels` / `ps-tabpanel` | |
| `pagination` / `page-item` (5) / `page-link` (5) | `ps-pagination` / `ps-page-item` / `ps-page-link` | solo `ps-search-mov.html` |

#### Utility — diventano utility Tailwind, nessuna classe nuova

| Bootstrap | Tailwind | Note |
|---|---|---|
| `row` (33) | `grid grid-cols-12 gap-4` o `flex` | caso per caso |
| `col-md-6` (18) / `col-md-4` (8) / `col-md-3` (5) / `col-md-8` (3) / `col-md-2` (3) / `col-md-12` (2) / `col-md-10` (1) / `col-md-5` (1) | `md:col-span-6` … | |
| `col-12` (15) / `col-6` (2) / `col` (3) | `col-span-12` / `col-span-6` / `flex-1` | |
| `col-sm-6` (3) / `col-lg-6` (1) / `col-lg-8` (1) | `sm:col-span-6` / `lg:col-span-6` / `lg:col-span-8` | |
| `row-cols-1` (1) / `row-cols-md-3` (1) | `grid-cols-1` / `md:grid-cols-3` | |
| `container` (4) / `container-fluid` (17) | `mx-auto max-w-7xl px-4` / `w-full px-4` | |
| `g-3` (4) | `gap-4` | |
| `mb-3` (45) / `mb-4` (24) / `mb-0` (30) / `mt-4` (18) / `mt-3` (9) / `me-2` (19) / `me-1` (11) … | `mb-3` / `mb-4` / `mb-0` / `mt-4` / `mt-3` / `mr-2` / `mr-1` | **attenzione**: `me-*`/`ms-*` sono logici → `mr-*`/`ml-*` (Tailwind ha `me-*`/`ms-*`, ma con semantica RTL: qui l'app è solo in italiano, usare `mr`/`ml` evita ambiguità) |
| `p-0` (5) / `py-3` (8) / `py-2` (4) / `py-0` (6) / `px-3` (4) / `px-2` (6) | identici | |
| `mt-auto` (4) / `ms-auto` (1) | `mt-auto` / `ml-auto` | |
| `d-flex` (28) | `flex` | |
| `flex-column` (6) / `flex-wrap` (4) / `flex-sm-row` (2) | `flex-col` / `flex-wrap` / `sm:flex-row` | |
| `align-items-center` (14) | `items-center` | |
| `align-items-start` (4) | `items-start` | |
| `align-items-end` (4) | `items-end` | |
| `align-items-sm-center` (2) | `sm:items-center` | |
| `justify-content-between` (14) | `justify-between` | |
| `justify-content-center` (6) | `justify-center` | |
| `justify-content-end` (1) | `justify-end` | |
| `align-middle` (2) | `align-middle` | |
| `gap-2` (8) / `gap-1` (1) | `gap-2` / `gap-1` | |
| `d-none` (11) | `hidden` | |
| `d-md-none` (2) | `md:hidden` | **768 px, non negoziabile** |
| `d-md-block` (2) | `md:block` | idem (nel pattern `d-none d-md-block` → `hidden md:block`) |
| `d-grid` (1) | `grid` | |
| `w-100` (6) / `h-100` (3) | `w-full` / `h-full` | |
| `text-center` (25) / `text-end` (16) / `text-start` (3) | `text-center` / `text-right` / `text-left` | |
| `text-truncate` (4) | `truncate` | |
| `text-nowrap` (4) | `whitespace-nowrap` | |
| `text-decoration-none` (1) | `no-underline` | |
| `small` (11) | `text-sm` | |
| `fs-5` (2) | `text-lg` | |
| `h5` (1) | `text-xl font-medium` | usata come **classe** su uno `<span>`, `ps-show-mov.html:16` |
| `fw-bold` (2) / `fw-semibold` (5) / `fw-light` (1) | `font-bold` / `font-semibold` / `font-light` | |
| `fst-italic` (2) | `italic` | |
| `font-monospace` (1) | `font-mono` | token MCP in `ps-setting-profile.html` |
| `border-0` (2) / `shadow-sm` (2) / `shadow` (1) / `opacity-75` (1) | `border-0` / `shadow-sm` / `shadow` / `opacity-75` | |
| `bg-transparent` (2) | `bg-transparent` | |
| `visually-hidden` (2) | `sr-only` | |
| `fade` (16) / `show` (2) / `collapse` | gestite da `ps-ui.js` | non sono stile: sono stato |

#### Colori — qui si passa dal colore alla semantica

Il vincolo del §3.1 del piano: **verde = entrate, rosso = uscite**. Le classi
di colore Bootstrap vanno tradotte nel **ruolo**, non nella tinta.

| Bootstrap | Target | Ruolo |
|---|---|---|
| `text-success` (3) / `bg-success` (3) | `ps-amount-income` / `ps-badge-income` | entrata |
| `text-danger` (13) / `bg-danger` (6) | `ps-amount-expense` / `ps-badge-expense` | uscita |
| `text-primary` (13) / `bg-primary` (5) | `text-[var(--ps-brand)]` / `ps-badge-brand` | marca |
| `bg-info` (2) | `ps-balance-positive` | bilancio ≥ 0 (`ps-show-mov.html:110`) |
| `bg-warning` (1) | `ps-balance-negative` | bilancio < 0 (stessa riga) |
| `text-muted` (34) | `ps-muted` | |
| `text-secondary` (2) / `bg-secondary` (1) | `ps-muted` / `ps-badge-neutral` | |
| `text-white` (11) | `text-white` | solo su fondi pieni |
| `text-info` (1) / `text-warning` (1) | `text-[var(--ps-info)]` / `text-[var(--ps-warning)]` | |
| `bg-light` (2) / `bg-body` (1) / `bg-body-secondary` (2) / `bg-body-tertiary` (1) | `bg-[var(--ps-surface-2)]` | **non** grigi fissi: devono seguire il tema |
| `border-danger` (2) | `border-[var(--ps-expense)]` | zona pericolosa |

#### Icone

| Oggi | Target | Note |
|---|---|---|
| `bi bi-*` (220 occorrenze, 56 glifi) | **invariate** | decisione D9: Bootstrap Icons self-hosted, le classi non cambiano |
| `fas fa-*` (23 occorrenze, 10 classi) | **rimuovere** se decorative, `bi bi-*` se sono l'etichetta (D10) | vedi sotto |

> **Font Awesome non è caricato da nessuna parte**, quindi queste 23
> occorrenze — tutte in `ps-maintenance.html` (`fa-tools`, `fa-sync-alt`,
> `fa-4x`) e `ps-search-mov.html` (`fa-edit`, `fa-trash`, `fa-redo`, `fa-undo`,
> `fa-search`, `fa-info-circle`) — **oggi non mostrano nulla**: è il difetto
> preesistente P1.
>
> **Decisione D10, presa il 2026-10-17: si rimuovono.** Niente glifo
> sostitutivo. Oggi al loro posto non c'è niente, e dopo la conversione non ci
> sarà niente: è la scelta isofunzionale. Tradurle in `bi-*` avrebbe fatto
> comparire icone che l'utente non ha mai visto — un miglioramento, ma un
> cambiamento visibile introdotto di straforo dentro un restyling che si
> impegna a non cambiare comportamento.
>
> **Precisazione del 2026-10-18.** La rimozione vale per le icone
> **decorative**, quelle che stanno accanto a un testo: togliendole resta
> l'etichetta, e l'utente non perde niente (è il caso di `ps-maintenance.html`,
> e di `fa-search`/`fa-undo`/`fa-info-circle` su `ps-search-mov.html`).
>
> Dove invece l'icona è l'**unico contenuto di un bottone** — `fa-edit`,
> `fa-redo`, `fa-trash` nelle righe di tabella e nelle card — non è
> decorazione: **è l'etichetta**. Rimuoverla lascerebbe un bottone colorato
> vuoto, riconoscibile solo dal `title`. Lì si usa il `bi bi-*`
> corrispondente, che è anche ciò che `/movements` già mostra per gli stessi
> tre bottoni: `bi-pencil`, `bi-arrow-repeat`, `bi-trash`.

> Operativamente, per `ps-markup`: **cancellare l'intero elemento** che porta
> `fas fa-*` (di norma un `<i class="fas fa-xxx"></i>`), non solo le classi —
> un `<i>` vuoto resterebbe nel DOM senza scopo. Se l'icona è dentro un
> bottone o un titolo, il testo accanto resta invariato. Attenzione a
> `ps-maintenance.html`, dove `fa-4x` è l'icona grande al centro della pagina:
> rimuovendola il blocco si accorcia, ed è l'unico punto in cui la rimozione
> si nota nel layout. È accettabile — quello spazio oggi è vuoto comunque.

#### Classi custom dell'applicazione — non sono Bootstrap

Tre classi sono definite in un `<style>` dentro `ps-show-mov.html` (righe
288-302) e generate dal suo JS. Non hanno un equivalente Bootstrap: vanno
portate in Tailwind in **Fase 6**, insieme alla pagina.

| Classe | Dove | Cosa fa | Nota |
|---|---|---|---|
| `filters-toggle` (1) | `ps-show-mov.html:10`, stile a :290 | toglie l'aspetto "link" (blu/sottolineato) al toggle dei filtri | nata con MB-002 |
| `filters-chevron` (1) | `ps-show-mov.html:22`, stile a :296 | la freccia che ruota: `.filters-toggle[aria-expanded="true"] .filters-chevron` | **la rotazione dipende da `aria-expanded`**: `ps-ui.js` deve continuare a impostarlo |
| `no-results` (1) | generata dal JS, `ps-show-mov.html:509` | messaggio "Nessun risultato" della card-list | |
| `footer` (1) | `ps-base.html:74` | appartiene alla shell, riscritta in Fase 2 | |

#### Shell AdminLTE — non si traduce, si riscrive

`app-wrapper`, `app-header`, `app-sidebar`, `app-main`, `app-content`,
`app-content-header`, `layout-fixed`, `sidebar-*`, `brand-*`, `navbar-*`,
`nav-icon`, `nav-arrow`, `nav-treeview` (circa 40 occorrenze) non hanno un
corrispettivo uno-a-uno: sono la struttura di AdminLTE. Vengono **ricostruite**
in Fase 2 dentro `ps-base-tw.html` / `ps-nav-tw.html` / `ps-auth-tw.html`,
drawer off-canvas compreso (D12). `ps-markup` non le incontra mai, perché le
pagine ereditano la shell.

Stessa sorte per `login-box`, `login-page`, `login-card-body`, `login-box-msg`
(`ps-auth.html`, `ps-maintenance.html`), che appartengono al layout di
autenticazione.

#### ⚠️ Classi assemblate: due casi da correggere durante la conversione

Lo scanner di Tailwind vede solo **stringhe letterali complete**. Questi due
punti costruiscono il nome della classe a pezzi, quindi la classe finirebbe
**assente dal CSS compilato** (rischio R1):

| Dove | Oggi | Da fare |
|---|---|---|
| `ps-onboarding.html:17` | `class="alert alert-{{ category }} …"` | mappare `category` a una classe intera con un `{% if %}` per ramo, o una macro |
| `ps-setting-admin.html:72` | `class="badge bg-{{ 'primary' if user.role == 'owner' else 'secondary' }}"` | `{% if %}ps-badge-brand{% else %}ps-badge-neutral{% endif %}` |

Gli altri quattro usi di Jinja dentro `class="…"` (`ps-search-mov.html:117,138`,
`ps-show-mov.html:25,110`) sono **sicuri**: ogni ramo produce già la classe
intera. Non vanno "corretti".

Sul lato JavaScript il problema esiste in 4 punti vivi
(`ps-show-mov.html:580`, `ps-search-mov.html:282`, `ps-setting-group.html:384`,
`ps-setting-wallet.html:166`): lì la regola è usare `ps-amount-income` /
`ps-amount-expense` e simili, dichiarate in `@layer components`, così la classe
esiste nel CSS a prescindere da cosa fa il JS. Il test di contratto sorveglia
entrambe le forme (vedi `DYNAMIC_CLASS_PATTERNS`).

### 1.4 — `ps-ui.js`

Modal, collapse, tab, alert dismiss, drawer sidebar. Più lo shim
`window.bootstrap.Modal`. Dettagli e vincoli nella definizione di
`ps-component` e in `analisi-decisioni-D4-D5.md`.

Costruisci il modal su `<dialog>` nativo: backdrop, focus trap, Esc e
`aria-modal` li dà il browser.

### 1.5 — `ps-theme.js`

Tre stati `light` / `dark` / `system`, default `system`. Persistenza in
`localStorage['ps_theme']`. Lo script anti-FOUC è **inline nel `<head>`**, non
in questo file, e non è `async` né `defer`: deve girare prima del primo paint.
Codice al §4.2 del piano.

Emette `ps:themechange` su `document`, che serve a Chart.js in Fase 8.

### 1.6 — Font self-hosted

Source Sans 3 in `pyspendless/static/fonts/`, con `@font-face` nel sorgente
CSS. Stesso font di oggi: nessun cambio percepito nella "voce" del testo, una
dipendenza CDN in meno, niente flash del font.

### 1.7 — Styleguide

`pyspendless/templates/_styleguide.html`, **non instradata** (nessuna route in
`app.py`: il gate sul diff vieta di toccarlo). La si apre come file statico o
dietro un flag di debug.

Mostra tutti i componenti della tabella 1.3 nei due temi. È qui che si giudica
il design system, non sulle pagine vere: se un componente è sbagliato, lo si
scopre adesso e non dopo averlo replicato su 16 pagine.

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A1.1 | `./tools/build-css.sh` compila senza errori e produce `ps-tailwind.css` non vuoto | exit code + dimensione file > 5 KB |
| A1.2 | `ps-tailwind.css` **non** è ignorato da git | `git check-ignore pyspendless/static/css/ps-tailwind.css` non trova nulla |
| A1.3 | Il binario Tailwind **è** ignorato | `git check-ignore tools/tailwindcss` lo trova |
| A1.4 | Tabella di conversione completa: copre tutti i pattern Bootstrap presenti nei 16 template renderizzati | grep dei `class="` nei template, ogni pattern ha una riga |
| A1.5 | Styleguide: ogni componente della tabella è presente e reso in light **e** dark | ispezione visiva, agente principale |
| A1.6 | Toggle tema: light → dark → system, persiste al reload, **nessun flash** | reload ripetuti in Chrome nei 3 stati |
| A1.7 | `ps-ui.js` espone `window.bootstrap.Modal` con `show`/`hide`/`getInstance`/`getOrCreateInstance` | prova in console sulla styleguide |
| A1.8 | Modal: apre, chiude con X / Annulla / Esc / click backdrop; il focus torna al trigger | prova manuale sulla styleguide |
| A1.9 | **Nessun template esistente modificato** | `git diff --name-only` non elenca file in `templates/` tranne `_styleguide.html` |
| A1.10 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |

## Definition of done

La styleguide mostra il design system completo nei due temi, il toggle funziona
senza flash, `ps-ui.js` replica i comportamenti Bootstrap che servono — e
l'applicazione vera è **ancora identica a prima**, perché nessuna pagina è stata
toccata.
