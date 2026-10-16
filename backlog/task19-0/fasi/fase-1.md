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

Questa sezione è l'input di `ps-markup` per tutte le fasi successive. Va
compilata **qui**, perché la qualità delle conversioni dipende da quanto è
completa. Ogni riga: pattern Bootstrap → classe `.ps-*` o utility Tailwind.

| Bootstrap | Target | Note |
|---|---|---|
| `card` / `card-header` / `card-body` / `card-footer` | `ps-card` / `ps-card-header` / `ps-card-body` / `ps-card-footer` | |
| `btn btn-primary` | `ps-btn-primary` | idem per secondary, success, danger, info, warning |
| `btn-outline-*` | `ps-btn-outline-*` | |
| `btn-sm` / `btn-lg` | `ps-btn-sm` / `ps-btn-lg` | touch target ≥44px su mobile |
| `form-control` / `form-select` | `ps-input` / `ps-select` | |
| `form-label` / `form-text` | `ps-label` / `ps-help` | |
| `table table-striped table-hover` | `ps-table` | |
| `badge bg-success` | `ps-badge-income` | semantica, non colore |
| `alert alert-danger` | `ps-alert-danger` | |
| `spinner-border` | `ps-spinner` | |
| `d-md-none` | `md:hidden` | **768px, non negoziabile** |
| `d-none d-md-block` | `hidden md:block` | idem |
| `row` / `col-md-6` | `grid` / `md:col-span-6` o flex | valutare caso per caso |
| `visually-hidden` | `sr-only` | |
| `text-muted` | `ps-muted` | |

Completala leggendo i template: 775 occorrenze su 26 file, i pattern ricorrenti
sono una trentina. **Se un pattern non è in tabella, `ps-markup` deve fermarsi
e chiedere** — è scritto nella sua definizione.

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
