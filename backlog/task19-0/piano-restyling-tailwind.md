# Piano implementativo — Rifacimento grafico PySpendless con Tailwind CSS

**Stato**: proposta di piano (sola analisi, nessun file del repo modificato)
**Data**: 2026-09-10
**Versione app analizzata**: `_APP_VERSION = "0.1.8"` (`pyspendless/app.py:32`)
**Vincolo cardine**: **ISOFUNZIONALITÀ** — nessuna funzionalità aggiunta, rimossa o
modificata nel comportamento. Cambia solo la presentazione.

> Unica eccezione consapevole e richiesta: il **selettore di tema dark/light**, che
> introduce un controllo UI nuovo. È l'unico elemento non presente oggi; tutto il
> resto deve avere corrispondenza 1:1 con l'attuale.

---

## 0. Sintesi esecutiva

| Voce | Decisione proposta |
|---|---|
| Stack CSS attuale | AdminLTE 4 + Bootstrap 5.3 (CSS locale + JS da CDN) |
| Stack CSS target | Tailwind CSS v4, output compilato e **committato** in `static/css/` |
| Build | Tailwind CLI **standalone** (binario, zero Node runtime su PythonAnywhere) |
| Strategia di migrazione | **Strangler per template**: due base coesistenti, mai due framework CSS sulla stessa pagina |
| Sostituto JS Bootstrap | `static/js/ps-ui.js` vanilla (modal, collapse, tab, alert dismiss) |
| Tema | `class="dark"` su `<html>` + `localStorage` + script inline anti-FOUC |
| Impatto deploy | **Nullo** sul workflow GitHub Actions (nessuno step nuovo) |
| Fasi | 9 fasi incrementali, ciascuna con checkpoint verificabile |
| Task da registrare | `backlog/task19-0.md` + riga in `backlog/features.md` |

---

## 1. Inventario del progetto

### 1.1 Stack front-end attuale

Da `pyspendless/templates/ps-base.html`:

| Dipendenza | Versione | Provenienza | Ruolo |
|---|---|---|---|
| AdminLTE | 4.x | **locale** `static/css/adminlte.css` (~ + `.map`, rtl, min) + `static/js/adminlte.js` | Layout app-shell, sidebar, temi |
| Bootstrap | 5.3.2 (base) / 5.3.0 (bundle in 6 pagine) | CDN jsdelivr | Grid, componenti, utility |
| Popper.js | 2.11.8 | CDN | Dipendenza Bootstrap |
| Bootstrap Icons | 1.13.1 | CDN | Icone (`bi bi-*`) |
| OverlayScrollbars | 2.11.0 | CDN | Solo scrollbar della `.sidebar-wrapper` |
| Fontsource Source Sans 3 | 5.0.12 | CDN | Font |
| Chart.js | 4.4.0 | CDN | 3 pagine (movimenti, dashboard mensile/annuale) |
| chartjs-plugin-datalabels | 2.2.0 | CDN | Dashboard |
| jQuery | 3.7.1 | CDN | Solo dipendenza DataTables |
| DataTables + Responsive | 1.13.7 / 2.5.0, tema `bootstrap5` | CDN | Solo `ps-show-mov.html` |
| Tom Select | 2.3.1, tema `bootstrap5` | CDN | Solo `ps-show-mov.html` (multi-select categorie) |

**Osservazione critica**: Bootstrap JS viene caricato **due volte** su 6 pagine
(`ps-base.html` carica `bootstrap.min.js`, poi i blocchi `{% block scripts %}` di
`ps-setting-*.html` e `ps-recurrent-mov.html` caricano `bootstrap.bundle.min.js`).
Non è un bug bloccante ma va tenuto presente: la rimozione di Bootstrap va fatta
**in entrambi i punti**.

### 1.2 Template — inventario completo

#### Layout / partial (2)

| File | Ruolo | Note |
|---|---|---|
| `ps-base.html` | `<html>`, `<head>`, asset globali, header/footer di fallback, footer con `app_version` | Da sostituire con `ps-base-tw.html` |
| `ps-nav.html` | App-shell AdminLTE: navbar + sidebar + `<main>`; espone `{% block nav_content %}`; JS inline `toggleSettingsMenu` / `toggleDashboardMenu` | Cuore del restyling |
| `ps-auth.html` | Shell pagine non autenticate | **Rotto**: il markup `.login-box` è fuori da qualsiasi `{% block %}` in un template figlio → Jinja lo scarta. Di fatto rende solo `{% block auth_content %}` dentro il `content` di `ps-base.html` |

#### Pagine effettivamente renderizzate da `app.py` (16)

| Template | Route / endpoint | Estende | Complessità |
|---|---|---|---|
| `ps-maintenance.html` | `before_request` → 503 | `ps-auth` | ⬤ bassa |
| `ps-login.html` | `GET /login` → `login` | `ps-auth` | ⬤ bassa |
| `ps-onboarding.html` | `GET /onboarding` → `onboarding` | `ps-auth` | ⬤ bassa |
| `ps-home.html` | `GET /home` → `home` | `ps-nav` | ⬤ bassa |
| `ps-add-mov.html` | `GET /create` → `create` | `ps-nav` | ⬤⬤ media |
| `ps-recurrent-mov.html` | `GET /recurrent-movements` → `recurrent_movements_page` | `ps-nav` | ⬤⬤ media |
| `ps-setting-wallet.html` | `GET /settings/wallets` → `settings_wallets` | `ps-nav` | ⬤⬤ media |
| `ps-setting-categories.html` | `GET /settings/categories` → `settings_categories` | `ps-nav` | ⬤⬤⬤ alta |
| `ps-setting-group.html` | `GET /settings/group` → `settings_group` | `ps-nav` | ⬤⬤⬤ alta |
| `ps-setting-import-export.html` | `GET /settings/import-export` → `settings_import_export` | `ps-nav` | ⬤⬤ media |
| `ps-setting-admin.html` | `GET /settings/admin` → `settings_admin` | `ps-nav` | ⬤⬤ media |
| `ps-show-mov.html` | `GET /movements` → `movements` | `ps-nav` | ⬤⬤⬤⬤ **massima** |
| `ps-search-mov.html` | `GET /ps-search-mov` → `search_movements` | `ps-nav` | ⬤⬤⬤ alta |
| `ps-dashboard-monthly.html` | `GET /dashboard/monthly` → `dashboard_monthly` | `ps-nav` | ⬤⬤⬤ alta |
| `ps-dashboard-yearly.html` | `GET /dashboard/yearly` → `dashboard_yearly` | `ps-nav` | ⬤⬤⬤ alta |
| `ps-reports.html` | `GET /reports` → `reports_page` | `ps-nav` | ⬤⬤ media |

#### Template morti — non referenziati da nessun `render_template` (9)

`base.html`, `index.html`, `login.html`, `login_old.html`, `loginv2.html`,
`cards.html`, `forms.html`, `tables.html`, `ps-setting-categories-old.html`.

`cards.html`, `forms.html`, `tables.html` sono demo AdminLTE da ~1000 righe ciascuna.
→ **Punto aperto D7**: cancellare o lasciare.

### 1.3 Componenti UI ricorrenti da ricostruire

Elenco derivato dalla scansione dei template (775 occorrenze di classi Bootstrap
su 26 file). Ogni voce diventa una **macro Jinja** o un pattern documentato.

| # | Componente | Dove compare | Note di migrazione |
|---|---|---|---|
| C01 | **App shell**: header + sidebar + main | `ps-nav.html` | Da AdminLTE a layout Tailwind mobile-first: drawer off-canvas `<lg`, sidebar fissa `≥lg` |
| C02 | **Sidebar menu + treeview** (2 sottomenu: Dashboard, Impostazioni) | `ps-nav.html` | Il toggle JS attuale manipola `style.display` e classi `bi-chevron-*`: riscrivere in `ps-ui.js`, comportamento identico (chiuso di default) |
| C03 | **Card** (header / body / footer) | 14 template | Variante `card-primary`, e header colorati `bg-primary`/`bg-success`/`bg-danger`/`bg-info`/`bg-warning text-white` |
| C04 | **Bottoni**: `btn-primary/secondary/success/danger/info/warning`, `-outline-*`, `btn-sm`, `btn-lg`, `btn-link`, `btn-group-vertical`, `w-100`, `d-grid` | ovunque | ~8 varianti × 3 taglie |
| C05 | **Form control**: `input[text/number/date/email/file]`, `select`, `select multiple`, `textarea`, `form-label`, `form-text`, `input-group` | 11 template | Servono anche gli stati `required`, `disabled`, `readonly` |
| C06 | **Modal** (12 istanze) | categorie ×3, wallet ×2, group ×3, admin ×1, ricorrenti ×1 | Sostituire `data-bs-toggle="modal"` / `data-bs-dismiss` con equivalenti `data-ps-*` in `ps-ui.js`; mantenere gli **stessi id** |
| C07 | **Tabella** `table-striped/-bordered/-hover`, `table-responsive` | 6 template | Su mobile molte sono già nascoste (`d-none d-md-block`) |
| C08 | **Nav tabs** (`data-bs-toggle="tab"`) | `ps-setting-categories.html` | Uscite / Entrate |
| C09 | **Collapse** (`data-bs-toggle="collapse"`) | `ps-show-mov.html` pannello filtri | Include il chevron che ruota e il badge conteggio filtri attivi |
| C10 | **Alert** (statici + generati da JS, dismissible, auto-hide 5 s con gestione del focus) | 10 template | `showAlert()` è duplicata in ~8 file con firme leggermente diverse: **candidata a unificazione in `ps-ui.js` a parità di comportamento** |
| C11 | **Badge** (`bg-primary/success/danger/secondary/info`) | movimenti, ricorrenti, admin | |
| C12 | **KPI card colorate** (Entrate verde / Uscite rossa / Bilancio info-o-warning) | `ps-show-mov.html` | Il colore del Bilancio dipende dal segno: logica da preservare |
| C13 | **Card-list mobile** generata in JS con infinite scroll (IntersectionObserver) | `ps-show-mov.html`, `ps-search-mov.html` | ⚠️ Le classi sono costruite per **concatenazione di stringhe** → incompatibile con lo scanner Tailwind (vedi §2.4) |
| C14 | **Paginazione** (`.pagination`, `.page-item`, `.page-link`) | `ps-search-mov.html` | |
| C15 | **Spinner** (`spinner-border`, `spinner-border-sm`) | movimenti, ricerca, reports | |
| C16 | **Progress bar** striped animated | `ps-setting-import-export.html` | |
| C17 | **List group flush** | `ps-setting-group.html` (membri, inviti), `ps-reports.html` | |
| C18 | **Canvas Chart.js** dentro card | `ps-show-mov` ×1, `ps-dashboard-monthly` ×4, `ps-dashboard-yearly` ×5 | Colori assi/legende da rendere theme-aware |
| C19 | **DataTables** (tema bootstrap5, i18n it-IT, `pageLength 25`, `responsivePriority`) | `ps-show-mov.html` | Vedi punto aperto D5 |
| C20 | **Tom Select** multi-select (plugin `remove_button`, `checkbox_options`) + link "Seleziona tutto / Deseleziona" | `ps-show-mov.html` | Tema bootstrap5 da sostituire |
| C21 | **Footer** con `© 2026 PySpendless · v{{ app_version }}` | `ps-base.html` | Da preservare identico |
| C22 | **Shell pagine auth** (login / onboarding / manutenzione) | `ps-auth.html` | Layout centrato, card |
| C23 | **Zona pericolosa** (bordo rosso, conferma digitando "ELIMINA") | `ps-setting-group.html` | Logica `disabled` del bottone da preservare |

### 1.4 Difetti preesistenti rilevati (da NON correggere silenziosamente)

| ID | Difetto | Dove |
|---|---|---|
| P1 | Icone Font Awesome (`fas fa-search`, `fa-edit`, `fa-redo`, `fa-trash`, `fa-undo`) usate ma **FA non è caricato** → icone invisibili | `ps-search-mov.html` (5×) |
| P2 | Idem: `fas fa-tools fa-4x`, `fas fa-sync-alt` | `ps-maintenance.html` |
| P3 | Markup `.login-box` fuori da ogni block → scartato da Jinja | `ps-auth.html:5-15` |
| P4 | `<title>` e `<meta viewport>` duplicati | `ps-base.html:6/10`, `:5/12` |
| P5 | Bootstrap JS caricato due volte | 6 template |
| P6 | `.login-box-msg` referenziata ma è una classe AdminLTE | `ps-maintenance.html:13` |

→ **Punto aperto D10**: in un rifacimento isofunzionale, "icona invisibile → icona
visibile" è un cambiamento *visivo*, non funzionale. Proposta: correggere P1/P2/P3/P4/P6
come parte del rifacimento (sono difetti di presentazione) e documentarli nel task;
P5 si risolve da sé rimuovendo Bootstrap.

---

## 2. Integrazione di Tailwind

### 2.1 La domanda decisiva: CDN o build step?

| Opzione | Pro | Contro | Verdetto |
|---|---|---|---|
| **A. CDN browser** (`@tailwindcss/browser@4`) | zero setup | Compila nel browser a ogni page load; ~400 KB JS; FOUC garantito; nessun purge; sconsigliato ufficialmente in produzione | ❌ |
| **B. Tailwind CLI standalone** (binario, nessun `node_modules`) | Nessuna dipendenza Node runtime; CSS finale ~15-30 KB; build locale, output committato; **deploy invariato** | Richiede di ricordarsi di rilanciare la build; binario ~40 MB da scaricare (non committato) | ✅ **scelta** |
| **C. npm + build in GitHub Actions** | build riproducibile in CI | Il workflow attuale fa `git pull` **sul server PA**: un artefatto costruito in CI dovrebbe essere ri-committato e ri-pushato dal bot → loop di tag, complessità, permessi di scrittura sul repo | ❌ |
| **D. build sul server PythonAnywhere** | — | PA free/hobby non ha Node garantito; aggiunge uno step fragile a un deploy oggi affidabile | ❌ |

**Perché B è obbligata dall'architettura di deploy esistente**: `.github/workflows/deploy.yml`
invia `git pull` a una console PA e poi chiama l'API di reload. Non esiste una fase di
build. Quindi **il CSS compilato deve essere versionato**, esattamente come lo è oggi
`static/css/adminlte.css`. C'è già il precedente.

### 2.2 Struttura file proposta

```
pyspendless/
├── static/
│   ├── css/
│   │   ├── ps-tailwind.src.css      ← SORGENTE (versionato): @import + @theme + @layer
│   │   ├── ps-tailwind.css          ← OUTPUT compilato (VERSIONATO, non ignorato)
│   │   └── adminlte.*               ← rimosso solo in Fase 8
│   └── js/
│       ├── ps-theme.js              ← toggle tema (il pre-set anti-FOUC resta inline)
│       ├── ps-ui.js                 ← modal / collapse / tab / alert / drawer
│       └── adminlte.*               ← rimosso solo in Fase 8
├── templates/
│   ├── ps-base-tw.html              ← nuova base
│   ├── ps-nav-tw.html               ← nuova app-shell
│   ├── ps-auth-tw.html              ← nuova shell auth
│   └── _components/                 ← macro Jinja (card, btn, field, modal, alert…)
└── tailwind.config.js               ← solo se si sceglie v3 (v4 = config in CSS)
tools/
└── build-css.sh                     ← wrapper: scarica il binario se manca, poi build
```

`.gitignore`: aggiungere `tools/tailwindcss*` (il binario) e **verificare esplicitamente
che `ps-tailwind.css` NON sia ignorato**.

### 2.3 Sorgente Tailwind v4 (CSS-first) — bozza

```css
/* pyspendless/static/css/ps-tailwind.src.css */
@import "tailwindcss";

/* dark mode a classe invece che a media-query (default di v4) */
@custom-variant dark (&:where(.dark, .dark *));

/* Tailwind v4 scansiona automaticamente, ma da CLI conviene essere espliciti */
@source "../../templates/**/*.html";
@source "../js/*.js";

@theme {
  /* --- palette grezza --- */
  --color-brand-50:  #eef2ff;
  --color-brand-500: #6366f1;
  --color-brand-600: #4f46e5;
  --color-brand-700: #4338ca;
  --color-brand-400: #818cf8;
  /* … scala completa in §3 … */

  --font-sans: "Source Sans 3", ui-sans-serif, system-ui, sans-serif;
  --radius-card: 0.75rem;
  --shadow-card: 0 1px 2px rgb(0 0 0 / .05), 0 1px 3px rgb(0 0 0 / .08);
}

/* --- token semantici: stesso nome, valore diverso per tema --- */
@layer base {
  :root {
    --ps-bg:        #f8fafc;
    --ps-surface:   #ffffff;
    --ps-surface-2: #f1f5f9;
    --ps-border:    #e2e8f0;
    --ps-text:      #0f172a;
    --ps-text-muted:#64748b;
    --ps-brand:     #4f46e5;
    --ps-income:    #059669;
    --ps-expense:   #e11d48;
    --ps-info:      #0284c7;
    --ps-warning:   #d97706;
  }
  .dark {
    --ps-bg:        #0b1120;
    --ps-surface:   #111827;
    --ps-surface-2: #1e293b;
    --ps-border:    #334155;
    --ps-text:      #e2e8f0;
    --ps-text-muted:#94a3b8;
    --ps-brand:     #818cf8;
    --ps-income:    #34d399;
    --ps-expense:   #fb7185;
    --ps-info:      #38bdf8;
    --ps-warning:   #fbbf24;
  }
  html { color-scheme: light; }
  html.dark { color-scheme: dark; }
  body { background: var(--ps-bg); color: var(--ps-text); }
}

/* --- classi di componente: cambiano look senza toccare 26 template --- */
@layer components {
  .ps-card   { @apply rounded-xl border bg-[var(--ps-surface)] border-[var(--ps-border)] shadow-sm; }
  .ps-btn    { @apply inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2
                      text-sm font-medium transition focus-visible:outline-none
                      focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50
                      disabled:pointer-events-none; }
  .ps-btn-primary { @apply ps-btn bg-brand-600 text-white hover:bg-brand-700; }
  .ps-input  { @apply w-full rounded-lg border border-[var(--ps-border)]
                      bg-[var(--ps-surface)] px-3 py-2 text-[var(--ps-text)]
                      placeholder:text-[var(--ps-text-muted)]
                      focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30; }
  /* … */
}
```

**Perché classi di componente e non utility sparse ovunque**: con 26 template e ~775
punti di intervento, le utility inline renderebbero ogni futura modifica un
find-and-replace di massa. Le classi `.ps-*` in `@layer components` danno lo stesso
risultato visivo, tengono i template leggibili e — soprattutto — rendono il diff
before/after **ispezionabile**, requisito per verificare l'isofunzionalità.

### 2.4 ⚠️ Trappola: classi costruite dinamicamente in JS

`ps-show-mov.html:450-482` e `ps-search-mov.html` fanno:

```js
const colorClass = isExpense ? 'text-danger' : 'text-success';
card.innerHTML = '<span class="fw-bold fs-5 ' + colorClass + ' text-nowrap">' …
```

Lo scanner di Tailwind cerca **stringhe letterali complete**. Un frammento concatenato
non viene rilevato e la classe finisce **assente dal CSS compilato**. Regola operativa
da mettere nel task:

```js
// ❌ const c = 'text-' + (isExpense ? 'danger' : 'success');
// ✅
const c = isExpense ? 'text-[var(--ps-expense)]' : 'text-[var(--ps-income)]';
```

Ogni ternario deve produrre la **classe intera**. Alternativa più robusta: usare classi
`.ps-amount-expense` / `.ps-amount-income` definite in `@layer components`, che compaiono
comunque nel CSS sorgente. **Raccomandato**.

### 2.5 Comando di build

```bash
# tools/build-css.sh
./tools/tailwindcss \
  -i pyspendless/static/css/ps-tailwind.src.css \
  -o pyspendless/static/css/ps-tailwind.css \
  --minify
# watch in sviluppo:
# ./tools/tailwindcss -i … -o … --watch
```

### 2.6 Impatto sul deploy PythonAnywhere — **nessuno**

| Aspetto | Prima | Dopo |
|---|---|---|
| Trigger | push tag `v*` | invariato |
| Step CI | `send_input` "git pull" + reload API | invariato |
| Node/npm sul server | non richiesto | **non richiesto** |
| Nuovi secrets | — | nessuno |
| Nuovi file serviti | `static/css/adminlte.css` | `static/css/ps-tailwind.css` (+ `ps-ui.js`, `ps-theme.js`) |

**Unica accortezza — cache busting.** Il reload PA non invalida la cache del browser.
Oggi il link è `url_for('static', filename='css/adminlte.css')` senza versione: dopo un
rilascio l'utente può restare con il CSS vecchio. Poiché `app_version` è già iniettata
in tutti i template dal context processor (`app.py:75-78`):

```jinja
<link rel="stylesheet"
      href="{{ url_for('static', filename='css/ps-tailwind.css') }}?v={{ app_version }}">
```

Nessuna modifica a `app.py`, solo al template. Stessa cosa per `ps-ui.js` e `ps-theme.js`.

**Nuovo passo nella procedura di rilascio** (da aggiungere a `CLAUDE.md` → "Rilascio / Deploy"):

> 0. `./tools/build-css.sh` e verificare che `ps-tailwind.css` sia aggiornato e staged.

Se ci si dimentica, in produzione va il CSS vecchio ma **l'app funziona**: fallimento
degradato, non rotto. Mitigazione opzionale: un check in CI che ricompila e confronta
l'hash, fallendo il deploy se differisce (job aggiuntivo in `deploy.yml`, non bloccante
per la Fase 1 — vedi punto aperto D3).

---

## 3. Design system

### 3.1 Vincolo semantico non negoziabile

I colori dell'app **veicolano significato** e vanno preservati nella semantica:

| Semantica | Uso attuale | Token target |
|---|---|---|
| Entrata / positivo | `text-success`, `bg-success`, `badge bg-success`, rgba(25,135,84) nei chart | `--ps-income` |
| Uscita / negativo | `text-danger`, `bg-danger`, rgba(220,53,69) nei chart | `--ps-expense` |
| Bilancio ≥ 0 | `bg-info` | `--ps-info` |
| Bilancio < 0 | `bg-warning` | `--ps-warning` |
| Azione primaria | `btn-primary`, `card-primary` | `--ps-brand` |
| Distruttivo | `btn-danger`, `border-danger`, "Zona Pericolosa" | `--ps-expense` |

Cambiare la *tinta* è ammesso; scambiare i ruoli no.

### 3.2 Palette

**Brand (indigo)** — professionale, neutro rispetto a verde/rosso già impegnati.

| Token | Light | Dark | Uso |
|---|---|---|---|
| `brand-600` / `brand-400` | `#4f46e5` | `#818cf8` | bottoni primari, link, focus ring |
| `brand-700` | `#4338ca` | `#6366f1` | hover |
| `brand-50` | `#eef2ff` | `#312e81` | sfondi tenui, stato attivo sidebar |

**Semantici**

| Ruolo | Light | Dark | Contrasto su surface |
|---|---|---|---|
| income | `#059669` (emerald-600) | `#34d399` (emerald-400) | AA ✓ |
| expense | `#e11d48` (rose-600) | `#fb7185` (rose-400) | AA ✓ |
| info | `#0284c7` (sky-600) | `#38bdf8` (sky-400) | AA ✓ |
| warning | `#d97706` (amber-600) | `#fbbf24` (amber-400) | AA ✓ |

**Neutri / superfici**

| Token | Light | Dark |
|---|---|---|
| `--ps-bg` (sfondo pagina) | `#f8fafc` | `#0b1120` |
| `--ps-surface` (card, modal) | `#ffffff` | `#111827` |
| `--ps-surface-2` (sidebar, header tabella, hover) | `#f1f5f9` | `#1e293b` |
| `--ps-border` | `#e2e8f0` | `#334155` |
| `--ps-text` | `#0f172a` | `#e2e8f0` |
| `--ps-text-muted` | `#64748b` | `#94a3b8` |

> ⚠️ In dark mode i "solid header" attuali (`bg-danger text-white`, `bg-success text-white`,
> `bg-warning`) diventano troppo carichi. Proposta: header di card **tinted** —
> sfondo `color-mix(in srgb, var(--ps-expense) 12%, var(--ps-surface))` con testo del
> colore semantico pieno. Preserva il significato, migliora la leggibilità.
> `bg-warning` senza `text-white` (import/export, `ps-setting-import-export.html:78`) è
> già un problema di contrasto oggi.

### 3.3 Tipografia

Mantenere **Source Sans 3** (già in uso) → nessun cambio percepito di "voce" del testo,
un rischio in meno. **Self-hostare** i woff2 in `static/fonts/` invece del CDN: elimina
una dipendenza esterna e il flash del font. (Punto aperto D6 se si preferisce Inter.)

| Ruolo | Classe | Size / line-height / weight |
|---|---|---|
| Display (h1 pagina) | `.ps-h1` | 1.5rem/2rem 600 → `sm:1.875rem` |
| Section (h3 card-title) | `.ps-h2` | 1.125rem/1.75rem 600 |
| Card title (h5) | `.ps-h3` | 1rem/1.5rem 600 |
| Body | default | 0.9375rem/1.5rem 400 |
| Small / muted | `.ps-muted` | 0.8125rem/1.25rem 400, `--ps-text-muted` |
| KPI numerico | `.ps-kpi` | 1.75rem/2.25rem 700, `tabular-nums` |
| Importi in tabella | `.ps-amount` | `tabular-nums text-right` |

`tabular-nums` è un miglioramento gratuito e invisibile a livello funzionale: gli importi
in colonna si allineano.

### 3.4 Spaziature, raggi, ombre, breakpoint

- **Spacing**: scala Tailwind di default (base 4 px). Ritmo verticale delle sezioni: `gap-4` mobile → `gap-6` da `md`.
- **Radius**: `--radius-card: 0.75rem` (card, modal), `0.5rem` (input, bottoni), `9999px` (badge).
- **Shadow**: `shadow-sm` per le card in light; in dark le ombre non si vedono → **il bordo diventa il separatore primario** (`border-[var(--ps-border)]` sempre presente).
- **Breakpoint**: quelli di default Tailwind (`sm 640 / md 768 / lg 1024 / xl 1280`).
  ⚠️ Oggi il codice usa i breakpoint Bootstrap. `md` coincide (768 px) — ed è quello che
  conta, perché `ps-show-mov.html:258` fa `matchMedia('(min-width: 768px)')` per
  inizializzare DataTables solo su desktop, in accordo con `d-md-none` / `d-none d-md-block`.
  **`md = 768px` va mantenuto**, altrimenti la lista card e la tabella possono comparire
  entrambe o nessuna delle due → regressione funzionale.
  `lg` invece differisce (BS 992 vs TW 1024): riguarda solo `sidebar-expand-lg`, effetto
  puramente visivo, accettabile.
- **Touch target**: minimo 44×44 px per ogni azione su mobile. Oggi i bottoni azione della
  card-list sono `btn-sm py-0 px-2` → sotto soglia. Correggerlo è un miglioramento di
  presentazione, non funzionale.

### 3.5 Focus e accessibilità

Ring di focus unico e visibile: `focus-visible:ring-2 ring-brand-500 ring-offset-2
ring-offset-[var(--ps-bg)]`. Da preservare: `aria-live="polite"` / `aria-atomic="true"`
sui contenitori alert, `role="navigation"` + `aria-label` sulla sidebar, `aria-expanded`
sul toggle filtri (`ps-show-mov.html:14`), `visually-hidden` sugli spinner
(→ `sr-only` in Tailwind).

---

## 4. Meccanismo di switch tema

### 4.1 Modello

Tre stati: **`light` / `dark` / `system`**. Default `system` (rispetta `prefers-color-scheme`,
coerente con i `<meta name="theme-color" media="(prefers-color-scheme: …)">` già presenti
in `ps-base.html:14-15`).

Persistenza: `localStorage['ps_theme']`. Precedente esistente nel progetto:
`localStorage['ps_last_wallet_id']` (`ps-add-mov.html:122`). Nessuna modifica a DB,
modello o sessione → **nessun impatto funzionale server-side**.

### 4.2 Anti-flash (FOUC): script inline bloccante nel `<head>`

Deve stare **prima** del `<link>` al CSS e non essere `async`/`defer`, altrimenti il
primo paint avviene in light e poi salta a dark.

```html
<script>
  (function () {
    try {
      var t = localStorage.getItem('ps_theme') || 'system';
      var dark = t === 'dark' ||
                 (t === 'system' &&
                  window.matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.classList.toggle('dark', dark);
      document.documentElement.dataset.psTheme = t;
    } catch (e) { /* localStorage negato: resta light */ }
  })();
</script>
```

### 4.3 Toggle (`ps-theme.js`)

Posizione: navbar in alto a destra, accanto alla voce Account già presente
(`ps-nav.html:18-31`) — l'unico punto dove aggiungere un controllo non disturba la
struttura esistente.

```js
window.psTheme = {
  set(mode) {                       // 'light' | 'dark' | 'system'
    localStorage.setItem('ps_theme', mode);
    this.apply(mode);
  },
  apply(mode) {
    const dark = mode === 'dark' ||
      (mode === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', dark);
    document.documentElement.dataset.psTheme = mode;
    document.querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', dark ? '#0b1120' : '#4f46e5');
    document.dispatchEvent(new CustomEvent('ps:themechange', { detail: { dark } }));
  }
};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if ((localStorage.getItem('ps_theme') || 'system') === 'system')
    psTheme.apply('system');
});
```

### 4.4 Il punto delicato: Chart.js e i temi

I 10 canvas Chart.js hanno colori **hardcoded** (palette `COLORS`, `rgba(25,135,84,.7)`,
tick e griglie di default grigio scuro). In dark mode diventano illeggibili.

Soluzione:

```js
function psChartTheme() {
  const s = getComputedStyle(document.documentElement);
  Chart.defaults.color       = s.getPropertyValue('--ps-text-muted').trim();
  Chart.defaults.borderColor = s.getPropertyValue('--ps-border').trim();
}
psChartTheme();
document.addEventListener('ps:themechange', () => {
  psChartTheme();
  Chart.instances && Object.values(Chart.instances).forEach(c => c.update());
});
```

I colori **semantici** dei dataset (entrate verde / uscite rosso) devono leggere
`--ps-income` / `--ps-expense`. La palette categoriale a 10 colori delle dashboard va
sostituita con una palette che funzioni su entrambi i fondi (saturazione media, luminanza
40-65 %) — **stesso ordine e stesso numero di colori**, così le categorie mantengono la
stessa associazione cromatica tra un grafico e l'altro.

Analogo per **DataTables** e **Tom Select**: i temi `*.bootstrap5.min.css` vanno sostituiti
dal tema neutro + uno skin Tailwind (`ps-datatables.css`, `ps-tomselect.css` in `@layer components`).

---

## 5. Strategia di migrazione: strangler per template

### 5.1 Il problema del "big bang" e quello della coesistenza

Caricare Tailwind **accanto** a Bootstrap sulla stessa pagina è la scelta peggiore:
il Preflight di Tailwind e il Reboot di Bootstrap resettano gli stessi elementi in modo
diverso, e le utility hanno collisioni di nome (`.hidden`, `.border`, `.shadow`, `.fixed`,
`.text-center`…). Il risultato è ingovernabile e rende impossibile dire se una differenza
visiva è voluta o accidentale.

Un big bang su 16 pagine in un colpo solo, d'altra parte, rende non verificabile
l'isofunzionalità: se qualcosa si rompe, la superficie di ricerca è l'intera app.

### 5.2 La soluzione

**Due gerarchie di base che convivono; ogni pagina appartiene a una sola.**

```
ps-base.html    ← Bootstrap + AdminLTE     ps-base-tw.html  ← solo Tailwind
     │                                            │
ps-nav.html                                  ps-nav-tw.html
ps-auth.html                                 ps-auth-tw.html
     │                                            │
 pagine non ancora migrate                 pagine migrate
```

Migrare una pagina = cambiare **una riga**: `{% extends 'ps-nav.html' %}` →
`{% extends 'ps-nav-tw.html' %}`, più la riscrittura del suo markup.

Proprietà che rendono questa strategia adatta al vincolo:

- **Nessuna pagina carica mai due framework** → zero conflitti CSS.
- **Rollback atomico per pagina**: rimettere `ps-nav.html` ripristina lo stato precedente.
- **Verifica localizzata**: dopo ogni fase l'app è integralmente funzionante, in parte vecchia e in parte nuova.
- Costo: durante la transizione la nav ha due look. Accettabile — è temporaneo e, poiché la nav è ricostruita in Fase 2 con **gli stessi identici link nello stesso ordine**, la navigazione non cambia.

---

## 6. Fasi di lavorazione

Ogni fase ha un **checkpoint verificabile**. Nessuna fase parte se il checkpoint della
precedente non è verde.

### Fase 0 — Baseline (nessuna modifica al codice)

1. Avviare l'app locale con un DB di test popolato (movimenti su ≥2 anni, ≥2 wallet, categorie entrata+uscita, ≥1 spesa ricorrente, ≥1 invito pendente, utente admin).
2. **Screenshot before** di tutte le 16 pagine × 3 viewport (375 / 768 / 1440) → `docs/ui-baseline/`.
   Includere gli stati non di default: modal aperti (12), tab Entrate, pannello filtri aperto con badge, card-list mobile dopo scroll, alert di successo, progress bar import, "Zona pericolosa" con bottone abilitato.
3. Compilare la **matrice di isofunzionalità** (§7.1) partendo dal codice.
4. Scrivere gli **smoke test** di §7.3 e verificarli verdi *prima* di toccare qualsiasi cosa.

✅ *Checkpoint*: baseline archiviata, test verdi sul codice attuale.
📦 *Deliverable*: `docs/ui-baseline/`, `tests/test_ui_contract.py`.

---

### Fase 1 — Infrastruttura Tailwind (nessuna pagina cambia aspetto)

1. `tools/build-css.sh` + binario Tailwind CLI standalone (in `.gitignore`).
2. `static/css/ps-tailwind.src.css` con `@theme`, token light/dark, `@layer components` con i pattern C01-C23.
3. `static/js/ps-theme.js`, `static/js/ps-ui.js`.
4. Font self-hostato in `static/fonts/`.
5. Una **pagina vetrina non instradata** — `templates/_styleguide.html` renderizzata solo in debug o aperta come file statico — che mostra tutti i componenti C01-C23 in light e dark.

⚠️ Nessun template esistente viene toccato. `ps-base.html` resta identico.

✅ *Checkpoint*: `ps-tailwind.css` compila; la styleguide mostra tutti i componenti nei due temi; il toggle funziona senza flash; `git diff` non tocca alcuna pagina esistente né `app.py`.
📦 2-3 giornate.

---

### Fase 2 — Nuova app-shell

1. `ps-base-tw.html`: head (meta, script anti-FOUC, CSS+JS con `?v={{ app_version }}`), footer identico con `app_version`, blocchi `title`/`head`/`content`/`scripts` **con gli stessi nomi** di `ps-base.html`.
2. `ps-nav-tw.html`: header + sidebar drawer + `<main>`, blocco `{% block nav_content %}` **con lo stesso nome**.
   - Voci di menu: le **stesse 8 + 2 sottomenu**, stesso ordine, stessi `url_for`, stesse icone.
   - Toggle Dashboard/Impostazioni: comportamento identico (chiuso di default, chevron che ruota, `menu-open`).
   - Voce Account in alto a destra con la stessa logica `session.user_email.split('@')[0] || session.user_name || 'User'`.
   - Voce Admin condizionata a `{% if is_admin %}`.
   - **Nuovo**: il toggle tema.
3. `ps-auth-tw.html` (e correzione strutturale di P3).

✅ *Checkpoint*: una pagina di prova che estende `ps-nav-tw.html` mostra la shell completa; tutti i `url_for` risolvono; il diff dei link estratti dalla nav vecchia e nuova è vuoto.
📦 2-3 giornate.

---

### Fase 3 — Pagine semplici (4)

`ps-maintenance.html` → `ps-login.html` → `ps-onboarding.html` → `ps-home.html`

Perché prima: nessun JS complesso, coprono la shell auth *e* la shell nav, e `ps-login`
è la porta d'ingresso — un errore qui è immediatamente evidente.

Da preservare: `id="login-google-btn"`, `href="/auth/login"`, form POST `/onboarding` con
i campi `account_name` / `wallet_name` (`required`, `maxlength=100`), il blocco
`get_flashed_messages(with_categories=true)`, i 3 link card della home.

✅ *Checkpoint*: login → onboarding → home percorribile end-to-end; screenshot diff rivisti.
📦 1-2 giornate.

---

### Fase 4 — Pagine form (2)

`ps-add-mov.html`, `ps-recurrent-mov.html`

Il template più delicato del gruppo è `ps-add-mov`: **niente cambia nel JS**, solo il
markup. Contratto da rispettare alla lettera (§7.2).

Attenzione a `showAlert()` in `ps-add-mov.html:290-334`: fa `scrollIntoView`, `focus()`,
auto-hide 5 s **rimandato se l'alert ha il focus**, e in modalità "Ripeti" usa
`behavior:'auto'` per non perdere il redirect a 1 s. Va riportato **identico** nella
versione `ps-ui.js`, oppure lasciato in-page.

✅ *Checkpoint*: creazione, modifica, ripetizione, precompilazione da spesa ricorrente, filtro categorie per tipo, `ps_last_wallet_id`, reset dopo creazione, redirect dopo "Ripeti" — tutti verificati manualmente. CRUD ricorrenti completo.
📦 2-3 giornate.

---

### Fase 5 — Pagine impostazioni con modal (5)

`ps-setting-wallet` → `ps-setting-import-export` → `ps-setting-admin` → `ps-setting-categories` → `ps-setting-group`

Ordine per complessità crescente. Qui si mette alla prova il modal di `ps-ui.js` (12 istanze).

Punti di attenzione:
- `ps-setting-categories.html:186` usa `{{ session.account_id }}` inline → mantenere.
- Il markup delle righe tabella è generato in JS (11 `innerHTML`) → applicare la regola §2.4.
- `ps-setting-group.html`: 24 `innerHTML`, list-group membri/inviti, Web Share API, clipboard, e la conferma "digita ELIMINA" con `disabled` dinamico.
- `ps-setting-import-export.html`: `<input type="file">` — il file input stilizzato in Tailwind (`file:` variant) non deve alterare `accept=".csv"` né l'id `csvFile`.

✅ *Checkpoint*: tutti i CRUD della matrice §7.1 eseguiti a mano; ogni modal apre, chiude con X / bottone Annulla / Esc / click sul backdrop (verificare quali di questi funzionano **oggi** e replicare esattamente quelli).
📦 4-5 giornate.

---

### Fase 6 — `ps-show-mov.html` (la pagina critica)

Da sola perché concentra: pannello filtri collassabile, 3 KPI card, Chart.js, DataTables +
jQuery, Tom Select, card-list mobile con IntersectionObserver, export CSV, delete.

Sotto-passi:
1. Layout + KPI card + card grafico (senza toccare il JS).
2. Pannello filtri collassabile su `ps-ui.js` — preservare `aria-expanded` derivato da `filters.active_count`, il badge, e la rotazione del chevron.
3. Tom Select: cambio stylesheet + skin. ⚠️ L'inizializzazione è **rimandata a `shown.bs.collapse`** (`ps-show-mov.html:398-404`); `ps-ui.js` deve emettere un evento equivalente (`ps:collapse:shown`) e la logica `if (già aperto) init() else on(shown, init, {once:true})` va replicata — è ciò che evita il dropdown mal dimensionato.
4. DataTables: tema neutro + skin (o D5).
5. Card-list mobile: riscrittura delle stringhe di classe secondo §2.4, `IntersectionObserver` invariato.
6. Chart.js theme-aware.

✅ *Checkpoint*: filtri (date, wallet, tipo, multi-categoria, keyword) producono la **stessa querystring** di prima; DataTables ordina/pagina/cerca in it-IT; infinite scroll a 375 px carica pagina 2, 3…; "Seleziona tutto/Deseleziona"; export CSV con i filtri correnti; delete con `confirm()`. A 767 px si vede **solo** la card-list, a 768 px **solo** la tabella.
📦 3-4 giornate.

---

### Fase 7 — Ricerca (1)

`ps-search-mov.html`: tabella server-side + paginazione + card-list mobile + le icone FA morte (P1).

✅ *Checkpoint*: querystring `?search=…&page=N` invariata; "Trovati N movimenti"; stati disabled di Precedente/Successivo.
📦 1-2 giornate.

---

### Fase 8 — Dashboard e report (3)

`ps-dashboard-monthly`, `ps-dashboard-yearly`, `ps-reports`

Il grosso è il tema dei grafici (§4.4): 9 canvas, plugin datalabels, palette categoriale,
`createPieChart` / `createLineChart`.

✅ *Checkpoint*: ogni grafico rende gli **stessi dati** in light e dark, leggibile in entrambi; filtri anno/mese; download PDF del report annuale (il PDF è generato server-side da `report_pdf.py`/`report_charts.py` e **non va toccato**: resta identico).
📦 2-3 giornate.

---

### Fase 9 — Pulizia e rilascio

1. Rimuovere `static/css/adminlte.*` (8 file) e `static/js/adminlte.*` (4 file).
2. Rimuovere `ps-base.html`, `ps-nav.html`, `ps-auth.html`.
3. Rinominare `ps-*-tw.html` → `ps-*.html` (un solo commit di rename + aggiornamento degli `extends`).
4. Rimuovere OverlayScrollbars, Popper, Bootstrap JS/CSS da tutti i template.
5. Template morti (§1.2) → **decisione D7**.
6. Immagini AdminLTE inutilizzate in `static/img/` → verificare i riferimenti prima.
7. Aggiornare `CLAUDE.md` (§2.6, passo 0 del rilascio) e `pyspendless/README.md`.
8. Chiudere `backlog/task19-0.md`, aggiornare `backlog/features.md`.
9. **Proporre** il rilascio: bump `_APP_VERSION` → `0.2.0` (breaking a livello di presentazione), commit, tag, push — **solo su richiesta esplicita dell'utente**, come da `CLAUDE.md`.

✅ *Checkpoint*: nessuna occorrenza di `bootstrap`, `adminlte`, `overlayscrollbars`, `class="btn `, `class="card`, `col-md-` nei template; suite di test verde; screenshot after completi.
📦 1-2 giornate.

**Totale stimato: 18-26 giornate**, molto sensibile alle decisioni D4/D5.

---

## 7. Strategia di verifica dell'isofunzionalità

Tre livelli: **contratto** (automatico), **comportamento** (manuale), **aspetto** (visivo).

### 7.1 Matrice route / azioni — checklist manuale

Il rifacimento non deve toccare `app.py`, quindi le route sono invarianti per costruzione.
Ciò che va verificato è che **l'UI continui a raggiungerle tutte**.

**Pagine (17 endpoint di rendering)**

| Endpoint | Verifica |
|---|---|
| `login` | bottone Google → `/auth/login` |
| `auth_login` / `auth_callback` / `logout` | flusso OAuth completo; link Logout in sidebar |
| `onboarding` (GET/POST) | form crea account + wallet, flash |
| `home` | 6 link (crea, movimenti, 4 impostazioni) |
| `create` | 3 modalità: nuovo / `?movement_id=` / `?repeat_from=` |
| `movements` | filtri, KPI, chart, tabella, card-list, export, delete |
| `search_movements` | ricerca + paginazione |
| `recurrent_movements_page` | CRUD completo |
| `settings_categories` | tab, ordinamento, add/edit/delete-con-spostamento |
| `settings_wallets` | CRUD |
| `settings_group` | rinomina account, invita, link, inviti pendenti, elimina account |
| `settings_import_export` | export CSV, import CSV + progress + risultati |
| `settings_admin` | whitelist add/remove, elenco utenti, delete utente |
| `dashboard_monthly` / `dashboard_yearly` | filtri + 4/5 grafici |
| `reports_page` | select anno + download PDF |
| `generate_link_callback` | accettazione invito |
| `version` / manutenzione | footer versione; pagina 503 |

**Chiamate API raggiunte dall'UI (34)** — ognuna deve restare invocabile dal punto di
partenza attuale:

`GET/POST /api/movements` · `DELETE /api/movements/<id>` · `GET /api/movements/export` ·
`GET /api/categories` · `POST /api/accounts/<id>/categories` · `PUT/DELETE /api/categories/<id>` ·
`GET/POST /api/accounts/<id>/wallets` · `PUT/DELETE /api/wallets/<id>` ·
`GET/POST/PUT/DELETE /api/recurrent-movements[/<id>]` · `GET /api/search-movements` ·
`GET /api/groups/<id>/members` · `POST /api/groups/<id>/invite` ·
`GET/PUT /api/accounts/<id>` · `GET /api/accounts/<id>/users` ·
`POST /api/export/movements` · `POST /api/import/movements` · `POST /api/generate-link` ·
`GET/DELETE /api/pending-invites[/<uuid>]` · `DELETE /api/user/delete-account` ·
`GET /api/stats/monthly|yearly|category-trend` · `GET /api/filters/years` ·
`GET /api/reports/annual` · `POST /admin/whitelist` · `DELETE /admin/whitelist/<email>` ·
`GET /admin/users` · `DELETE /admin/users/<id>`

### 7.2 Contratto DOM — l'ancora dell'isofunzionalità

Il JS di pagina non va riscritto, quindi **ogni id, name e attributo che il JS legge deve
sopravvivere invariato**. Questo è l'elenco da congelare (estratto dal codice) e da
verificare automaticamente.

**`ps-add-mov.html`** — id: `movement-form`, `movement_id`, `is_repeat`,
`recurrent_movement_id`, `recurrent_template`, `recurrent-template-block`, `move_date`,
`movement_type`, `category`, `wallet`, `amount`, `note`, `submit-btn`, `alert-container`.
Attributi: `option[data-type]` sulle categorie; `option[data-movement-type|data-category-id|data-wallet-id|data-amount|data-note]` sulle ricorrenti. Storage: `ps_last_wallet_id`.

**`ps-show-mov.html`** — form GET su `url_for('movements')` con i `name`:
`date_from`, `date_to`, `wallet_id`, `category_type`, `category_id` (multiplo), `keywords`.
Id: `filters-collapse`, `movementsTable`, `category_id`, `cat-select-all`,
`cat-deselect-all`, `export-csv-btn`, `movements-card-list`, `cards-container`,
`load-more-trigger`, `cards-spinner`, `no-more-msg`, `expensesChart`.
Classi strutturali: `.d-md-none` / `.d-none.d-md-block` → equivalenti Tailwind con **breakpoint 768 px**.

**`ps-search-mov.html`** — `name="search"`, `?page=`, id `cards-container`,
`load-more-trigger`, `cards-spinner`, `no-more-msg`, `no-results-msg`, `alert-container`.

**`ps-setting-categories.html`** — `expenseCategoriesTableBody`, `incomeCategoriesTableBody`,
`addCategoryModal`, `editCategoryModal`, `deleteCategoryModal`, `categoryName`,
`categoryType`, `categoryOrderIndex`, `editCategoryId`, `editCategoryOldName`,
`editCategoryName`, `editCategoryOrderIndex`, `deleteCategoryId`, `deleteCategoryType`,
`deleteCategoryName`, `deleteMovementsCount`, `targetCategorySelect`, `btnToggleSort`,
`alertContainer`, `#expense`/`#income` (tab pane).

**`ps-setting-wallet.html`** — `walletsContainer`, `addWalletModal`, `editWalletModal`,
`walletName`, `walletCurrency`, `editWalletId`, `editWalletName`, `editWalletCurrency`,
`editWalletOrder`, `alertContainer`.

**`ps-setting-group.html`** — `membersTable`, `pendingInvitesTable`, `noPendingMessage`,
`accountName`, `accountNameInput`, `editAccountModal`, `inviteModal`, `inviteEmail`,
`generatedLinkContainer`, `generatedLink`, `shareButton`, `generateLinkBtn`,
`deleteAccountModal`, `deletionDetails`, `sharedAccountNote`, `fullDeletionNote`,
`confirmDeleteText`, `confirmDeleteBtn`, `alertContainer`.

**`ps-setting-admin.html`** — `whitelistTable(Body)`, `usersTable(Body)`,
`addWhitelistModal`, `whitelistEmail`, `whitelistNote`, `tr[data-email]`, `tr[data-user-id]`.

**`ps-setting-import-export.html`** — `csvFile`, `importProgress`, `importResults`,
`importedCount`, `errorsContainer`, `errorsList`, `alertContainer`.

**`ps-recurrent-mov.html`** — `recurrent-form`, `rm_id`, `rm_name`, `rm_movement_type`,
`rm_category`, `rm_wallet`, `rm_amount`, `rm_note`, `submit-btn`, `cancel-btn`,
`form-title`, `recurrent-tbody`, `row-<id>`, `empty-row`, `deleteModal`, `delete-name`,
`confirm-delete-btn`, `alertContainer`.

**Dashboard/report** — `filterYear`, `filterMonth`, `btnUpdate`, `chartIncomeExpense`,
`chartExpenseByCategory`, `chartExpenseByWallet`, `chartIncomeByWallet`, `reportYear`,
`btnDownload`, `statusArea`, `loadingMsg`, `successMsg`, `errorMsg`, `errorDetail`.

**`ps-onboarding.html`** — POST `/onboarding`, `account_name`, `wallet_name`.

### 7.3 Test automatici — `tests/test_ui_contract.py`

Scritti in **Fase 0** contro il codice attuale, devono restare verdi a ogni fase. Sono
la rete di sicurezza che rende la migrazione incrementale sostenibile.

```python
# pseudo-struttura
CONTRACT = {
    "/create":   {"ids": ["movement-form","move_date","movement_type","category",
                          "wallet","amount","note","submit-btn","alert-container"],
                  "forms": [{"id":"movement-form"}]},
    "/movements":{"ids": ["filters-collapse","movementsTable","export-csv-btn",
                          "cards-container","expensesChart"],
                  "form_fields": ["date_from","date_to","wallet_id",
                                  "category_type","category_id","keywords"]},
    # … una voce per rotta …
}

def test_ids_presenti(client, route, spec):       # ogni id esiste, esattamente 1 volta
def test_campi_form(client, route, spec):         # name/method/action invariati
def test_link_url_for(client, route):             # insieme degli href == baseline
def test_status_200(client, route):               # nessuna rotta rotta
def test_nessun_bootstrap(route):                 # da Fase 9: asserisce l'assenza
```

Test aggiuntivi consigliati:

- **`test_link_nav`**: la nav espone esattamente 11 destinazioni, nello stesso ordine.
- **`test_classi_dinamiche`**: grep dei template per `class="…' +` / `` `…${ `` dentro stringhe di classe → fallisce se ricompare il pattern di §2.4.
- **`test_css_aggiornato`** (CI): ricompila e confronta l'hash con il file committato.
- **`test_versione_footer`**: `v{{ app_version }}` presente in ogni pagina autenticata.

### 7.4 Screenshot before/after

Script Playwright: login con sessione fittizia → per ogni rotta e per ogni stato
(§ Fase 0 punto 2) → 375 / 768 / 1440 px, light e dark → `docs/ui-after/`.
Il confronto **non** è un pixel-diff (il look cambia per definizione): è una **review
affiancata** con una griglia di controllo per screenshot:

> tutti i testi presenti? tutti i bottoni presenti? stessa quantità di righe/card?
> stessi colori semantici (verde=entrate, rosso=uscite)? niente overflow orizzontale?
> touch target ≥44 px? contrasto leggibile in dark?

### 7.5 Gate sul diff

Regola meccanica da applicare a ogni commit del task:

```bash
git diff --stat  # deve toccare SOLO:
#   pyspendless/templates/**, pyspendless/static/**, tools/**,
#   tests/**, docs/**, backlog/**, CLAUDE.md, README.md
# Se compare pyspendless/{app,models,repository,conf,report_*}.py → STOP.
```

Unica eccezione ammessa e da giustificare per iscritto: nessuna prevista.

---

## 8. Rischi

| # | Rischio | Impatto | Probabilità | Mitigazione |
|---|---|---|---|---|
| R1 | Classi Tailwind costruite dinamicamente in JS spariscono dal CSS compilato | alto | **alta** | §2.4 + test `test_classi_dinamiche` + classi `.ps-*` invece di utility nei ternari |
| R2 | `ps-ui.js` non replica esattamente un comportamento Bootstrap (evento `shown`, focus trap, chiusura con Esc, backdrop) | alto | media | Censire prima **cosa fa oggi** ogni interazione, non cosa dovrebbe fare; test manuale per ognuna delle 12 modal |
| R3 | Breakpoint `md` disallineato → card-list e tabella entrambe visibili o nessuna | alto | bassa | `md = 768px` è identico in BS5 e TW; verifica esplicita a 767/768 px in Fase 6 |
| R4 | DataTables / Tom Select senza tema bootstrap5 risultano visivamente rotti | medio | **alta** | Budget dedicato in Fase 6; skin `@layer components`; fallback = tenere il CSS bootstrap5 del solo plugin, isolato |
| R5 | Chart.js illeggibile in dark | medio | alta | §4.4, evento `ps:themechange` |
| R6 | Dimenticare `build-css.sh` prima del tag → produzione con CSS vecchio | medio | media | Passo 0 in `CLAUDE.md` + check hash in CI (D3) |
| R7 | Cache browser del CSS dopo il reload PA | medio | alta | `?v={{ app_version }}` |
| R8 | Duplicazione di `showAlert()` in 8 file: unificandola si cambia sottilmente il comportamento (auto-hide, focus, scroll) | medio | media | O si unifica **replicando la variante più ricca** (`ps-add-mov`) e verificandola su tutte le pagine, o si lascia ogni copia dov'è. Default proposto: **lasciare** in Fase 4-8, unificare solo se D-approvato |
| R9 | La sidebar drawer mobile scritta da zero introduce trap di focus / scroll-lock assenti prima | basso | media | Comportamento di riferimento: quello attuale di AdminLTE |
| R10 | Scope creep: "già che ci siamo" → nuove feature | alto | **alta** | Gate §7.5 + questo documento come contratto |
| R11 | 12 modal × ricostruzione = superficie di regressione più ampia dell'intero resto | medio | media | Modal come **unica macro Jinja** riusata 12 volte, non 12 markup indipendenti |
| R12 | Il PDF del report (`report_pdf.py`, `matplotlib`) non riflette il nuovo look | basso | certa | **Fuori scope**: è server-side, non è il rifacimento della web app. Da esplicitare |

---

## 9. Punti aperti — richiedono una decisione

| ID | Domanda | Opzioni | Proposta |
|---|---|---|---|
| **D1** | Tailwind v4 (config in CSS) o v3 (`tailwind.config.js`)? | v4 / v3 | **v4**: `@theme` + `@custom-variant dark` è più pulito e non aggiunge un file JS di config |
| **D2** | Toolchain di build | binario standalone / npm+node_modules | **standalone**: nessun `package.json`, nessun `node_modules`, coerente con un repo Python |
| **D3** | Check in CI che il CSS committato sia aggiornato? | sì (job in `deploy.yml`) / no (solo disciplina) | **sì, ma non bloccante in Fase 1**; da valutare a fine Fase 9 |
| **D4** | Sostituto del JS Bootstrap | `ps-ui.js` vanilla (~150 righe) / **Alpine.js** (15 KB) / Flowbite | **`ps-ui.js` vanilla**: zero dipendenze nuove, controllo totale sul comportamento da replicare. Alpine sarebbe più veloce da scrivere ma introduce una dipendenza CDN e uno stile dichiarativo estraneo al resto del codice |
| **D5** | DataTables | tenere (tema neutro + skin) / **sostituire** con sort+paging vanilla | **tenere**. Sostituirlo significa riscrivere ordinamento, paginazione, ricerca, i18n it-IT e il responsive collapse → è esattamente il tipo di riscrittura che mette a rischio l'isofunzionalità. Anche jQuery resta, solo per DataTables |
| **D6** | Font | Source Sans 3 self-hosted / Inter / system stack | **Source Sans 3 self-hosted**: stesso testo di oggi, una dipendenza CDN in meno |
| **D7** | 9 template morti (~3000 righe) | cancellare in Fase 9 / lasciare | **cancellare**, ma è una modifica al repo che va approvata: sono demo AdminLTE e versioni `_old` |
| **D8** | Persistenza del tema | `localStorage` / anche server-side per utente | **`localStorage`**: server-side richiederebbe una colonna DB + migrazione + endpoint → sarebbe una funzionalità nuova, contro il vincolo |
| **D9** | Icone | Bootstrap Icons (CDN, invariate) / self-hosted / SVG inline (Lucide) | **Bootstrap Icons self-hosted**: le classi `bi bi-*` restano identiche in ~120 punti → zero rischio, e si toglie un CDN |
| **D10** | Difetti P1-P6 (icone FA invisibili, markup scartato, meta duplicati) | correggere durante il rework / lasciare identici | **correggere**, documentandoli uno per uno nel task: sono difetti di *presentazione*, e il rework è per definizione un cambio di presentazione. Ma è una scelta dell'utente |
| **D11** | Header di card "solid colored" in dark mode | mantenere `bg-danger text-white` / passare a tinted | **tinted**: il solid in dark è visivamente aggressivo. Cambio estetico, semantica invariata |
| **D12** | Aspetto della sidebar su mobile | drawer off-canvas (come oggi) / bottom tab bar | **drawer**: la bottom bar sarebbe un pattern di navigazione nuovo → cambio funzionale |
| **D13** | Unificare le 8 copie di `showAlert()`? | sì / no | **no per default** (R8). Se sì, va fatta come sotto-fase a sé con verifica su tutte le pagine |
| **D14** | Versione del rilascio finale | `0.1.9` / `0.2.0` | **`0.2.0`** — cambio di presentazione di tutta l'app |
| **D15** | Registrazione a backlog | `backlog/task19-0.md` (task grande) | **sì**: >2-3 file, ampiamente sopra la soglia di `MB-NNN`. Più una riga in `backlog/features.md`. **Da creare solo su via libera** (questo è un task di sola analisi) |

---

## 10. Prossimi passi

1. Rispondere ai punti aperti, in particolare **D4** e **D5** (determinano la stima).
2. Su approvazione, creare `backlog/task19-0.md` con questo piano come corpo e la riga in `backlog/features.md`.
3. Partire dalla **Fase 0**: la baseline e i test di contratto vanno scritti *prima* che una riga di markup cambi. È la differenza tra "abbiamo rifatto la grafica" e "abbiamo rifatto la grafica e possiamo dimostrare che non abbiamo rotto niente".

---

### Appendice — file di riferimento

| File | Righe rilevanti |
|---|---|
| `pyspendless/app.py` | `:32` versione · `:75-78` context processor · `:81-108` manutenzione · 62 route |
| `pyspendless/templates/ps-base.html` | `:32-59` CSS · `:62` body class · `:74-82` footer · `:84-126` JS |
| `pyspendless/templates/ps-nav.html` | `:6-34` header · `:37-161` sidebar · `:167-213` toggle sottomenu |
| `pyspendless/templates/ps-show-mov.html` | `:7-89` filtri · `:92-117` KPI · `:255-522` JS |
| `.github/workflows/deploy.yml` | `:3-6` trigger tag · `:35` git pull · `:67-73` reload |
| `CLAUDE.md` | "Rilascio / Deploy", "Convenzioni di backlog" |
