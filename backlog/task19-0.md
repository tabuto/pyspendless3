# Task 19-0: Rifacimento grafico con Tailwind CSS (mobile first, dark/light)

## Obiettivo

Rifare la presentazione di PySpendless con **Tailwind CSS**: mobile first,
responsive, look moderno, tema **dark/light** selezionabile e persistente.

Il vincolo che governa tutto il task è l'**isofunzionalità**: nessuna
funzionalità aggiunta, rimossa o modificata nel comportamento. Cambia solo
la presentazione.

> Unica eccezione, voluta: il **selettore di tema**, che introduce un controllo
> UI nuovo. Tutto il resto ha corrispondenza 1:1 con l'attuale.

Documenti di supporto, da leggere prima di iniziare:

| File | Contenuto |
|---|---|
| `backlog/task19-0/piano-restyling-tailwind.md` | Piano completo: inventario, design system, 9 fasi, strategia di verifica, rischi |
| `backlog/task19-0/analisi-decisioni-D4-D5.md` | Perché `ps-ui.js` vanilla e perché DataTables resta |
| `backlog/task19-0/RUNBOOK.md` | Come si avvia la sessione, allocazione modelli, regole di orchestrazione |
| `backlog/task19-0/fasi/fase-N.md` | Un file per fase: obiettivo, input, criteri di accettazione |
| `.claude/agents/ps-{markup,contract,component}.md` | Definizioni dei subagent, con il modello nel frontmatter (vedi RUNBOOK §1.1) |

## Stato attuale

Stack: **AdminLTE 4 + Bootstrap 5.3**, CSS AdminLTE locale
(`pyspendless/static/css/adminlte.css`), tutto il resto da CDN — Bootstrap JS,
Bootstrap Icons, OverlayScrollbars, Chart.js, jQuery + DataTables, Tom Select,
font Source Sans 3.

16 template renderizzati da `app.py`, su due layout (`ps-nav.html` per l'area
autenticata, `ps-auth.html` per login/onboarding/manutenzione), più 9 template
morti mai referenziati da `render_template`.

### Decisioni prese

| ID | Decisione |
|---|---|
| D1 | Tailwind **v4**, configurazione CSS-first (`@theme`, `@custom-variant dark`) |
| D2 | Build con **Tailwind CLI standalone** (binario, nessun `package.json`, nessun Node runtime) |
| D4 | Sostituto del JS Bootstrap: **`ps-ui.js` vanilla** con shim `window.bootstrap.Modal` |
| D5 | **DataTables resta**, con tema neutro + skin Tailwind. Sostituzione rimandata a un task autonomo |
| D6 | Font **Source Sans 3 self-hosted** |
| D8 | Tema persistito in **`localStorage`**, nessuna modifica a DB o sessione |
| D9 | **Bootstrap Icons self-hosted**: le classi `bi bi-*` restano identiche |
| D10 | Difetti preesistenti P1-P6: le icone **Font Awesome si rimuovono** (non sono mai state visibili, FA non è caricato — la rimozione è la scelta isofunzionale). P6 è risultato **inesistente**: Bootstrap JS è caricato una volta sola, vedi "Verifiche empiriche" |
| D12 | Sidebar mobile: **drawer off-canvas**, come oggi |
| D14 | Versione di rilascio: **`0.2.0`** |

Le decisioni ancora aperte (D3, D7, D10, D11, D13) sono elencate nel piano al
§9 e **non bloccano** l'avvio: si decidono alla fase in cui servono.

### Perché il deploy non cambia

Il deploy è manuale (vedi `CLAUDE.md` → "Rilascio / Deploy"): console PA →
`git pull` → Reload. Non esiste una fase di build, quindi il **CSS compilato va
versionato**, esattamente come lo è oggi `adminlte.css`. Nessuno step nuovo,
nessun secret nuovo, nessun Node sul server.

Unica aggiunta alla procedura di rilascio, da inserire come passo 0:

> 0. `./tools/build-css.sh` e verificare che `pyspendless/static/css/ps-tailwind.css`
>    sia aggiornato e staged.

Se ci si dimentica, in produzione va il CSS vecchio ma **l'app funziona**:
fallimento degradato, non rotto.

## Strategia: strangler per template

Caricare Tailwind **accanto** a Bootstrap sulla stessa pagina è la scelta
peggiore — Preflight e Reboot resettano gli stessi elementi in modo diverso, e
le utility hanno nomi in collisione (`.hidden`, `.border`, `.shadow`,
`.text-center`). Un big bang su 16 pagine, d'altro canto, rende impossibile
verificare l'isofunzionalità: se qualcosa si rompe, la superficie di ricerca è
l'intera app.

Quindi: **due gerarchie di base che convivono, ogni pagina appartiene a una
sola.**

```
ps-base.html   ← Bootstrap + AdminLTE      ps-base-tw.html  ← solo Tailwind
     │                                            │
ps-nav.html                                  ps-nav-tw.html
ps-auth.html                                 ps-auth-tw.html
     │                                            │
 pagine non ancora migrate                 pagine migrate
```

Migrare una pagina = cambiare una riga `{% extends %}` più il suo markup.
Nessuna pagina carica mai due framework; il rollback è per pagina.

## Fasi

| Fase | Contenuto | Agente | File |
|---|---|---|---|
| 0 | Baseline, DB di test, contratto DOM, screenshot before | `ps-contract` + principale | `fasi/fase-0.md` |
| 1 | Infrastruttura Tailwind, token, `ps-ui.js`, `ps-theme.js`, styleguide | `ps-component` | `fasi/fase-1.md` |
| 2 | Nuova app-shell (`ps-base-tw`, `ps-nav-tw`, `ps-auth-tw`) + toggle tema | `ps-component` | `fasi/fase-2.md` |
| 3 | Pagine semplici: manutenzione, login, onboarding, home | `ps-markup` ×4 | `fasi/fase-3.md` |
| 4 | Pagine form: add-mov, recurrent-mov | `ps-markup` ×2 | `fasi/fase-4.md` |
| 5 | Impostazioni con modal: wallet, import-export, admin, categorie, group | `ps-markup` ×5 | `fasi/fase-5.md` |
| 6 | `ps-show-mov.html` — la pagina critica | `ps-component` | `fasi/fase-6.md` |
| 7 | `ps-search-mov.html` | `ps-markup` | `fasi/fase-7.md` |
| 8 | Dashboard e report, tema dei grafici | `ps-component` | `fasi/fase-8.md` |
| 9 | Pulizia, rimozione Bootstrap/AdminLTE, rilascio | principale | `fasi/fase-9.md` |

Nessuna fase parte se il checkpoint della precedente non è verde.
Stima complessiva: **19-23 giornate**.

## Il contratto DOM è l'ancora

Il JS di pagina **non va riscritto**. Quindi ogni `id`, ogni `name` di campo
form e ogni `data-*` che il JS legge deve sopravvivere invariato al restyling.

Questo è congelato in `pyspendless/test/test_task19_0.py`, che va eseguito
**verde sul codice attuale prima che una riga di markup cambi**, e deve restare
verde a ogni fase:

```bash
.venv/bin/python -m pyspendless.test.test_task19_0
```

Exit code 0 = contratto rispettato. È il criterio di rilascio che ogni subagent
deve soddisfare prima di dichiarare chiuso il proprio task.

## Gate sul diff

Regola meccanica da applicare a ogni commit del task:

```bash
git diff --stat   # deve toccare SOLO:
#   pyspendless/templates/**, pyspendless/static/**, pyspendless/test/**,
#   tools/**, docs/**, backlog/**, .claude/agents/**, CLAUDE.md, README.md
# Se compare pyspendless/{app,models,repository,conf,report_*}.py → STOP.
```

Nessuna eccezione prevista. Se una sembra necessaria, è un segnale che la
conversione sta sconfinando dalla presentazione al comportamento.

## File toccati

**Nuovi**

- `pyspendless/static/css/ps-tailwind.src.css` — sorgente (token, `@theme`, `@layer components`)
- `pyspendless/static/css/ps-tailwind.css` — output compilato, **versionato**
- `pyspendless/static/js/ps-ui.js` — modal, collapse, tab, alert, drawer + shim Bootstrap
- `pyspendless/static/js/ps-theme.js` — toggle tema
- `pyspendless/static/fonts/` — Source Sans 3 self-hosted
- `pyspendless/templates/ps-base-tw.html`, `ps-nav-tw.html`, `ps-auth-tw.html`
- `pyspendless/templates/_components/` — macro Jinja
- `pyspendless/templates/_styleguide.html` — vetrina componenti, non instradata
- `pyspendless/test/test_task19_0.py` — contratto DOM ✅ *già creato*
- `.claude/agents/ps-markup.md`, `ps-contract.md`, `ps-component.md` —
  definizioni dei subagent ✅ *già create, da spostare in `.claude/agents/`
  con il comando in RUNBOOK §1.1*
- `tools/build-css.sh` — wrapper della build
- `tools/worktree-bootstrap.sh` — prepara un worktree (collega `.env`, trova il
  venv giusto) ✅ *già creato*
- `docs/ui-baseline/`, `docs/ui-after/` — screenshot

**Modificati**

- I 16 template renderizzati — markup, una fase per volta
- `pyspendless/templates/ps-base.html`, `ps-nav.html`, `ps-auth.html` — **rimossi** in Fase 9
- `pyspendless/static/{css,js}/adminlte.*` — **rimossi** in Fase 9
- `.gitignore` — aggiungere `tools/tailwindcss*`; verificare che `ps-tailwind.css` **non** sia ignorato
- `CLAUDE.md` — passo 0 della procedura di rilascio
- `pyspendless/README.md` — come si compila il CSS
- `backlog/features.md` — riga di backlog

Nessuna modifica al codice applicativo (`app.py`, `models.py`, `repository.py`,
`conf.py`, `report_*.py`), nessuna migrazione DB, nessun file `.env` coinvolto.

## Test

### Automatici

- **Contratto DOM** — `.venv/bin/python -m pyspendless.test.test_task19_0`.
  Verde sul codice attuale in Fase 0, verde a ogni fase successiva.
- **Ordine della nav** — stesse 13 destinazioni, stesso ordine (incluso nel test).
- **Versione nel footer** — presente su ogni pagina autenticata (incluso nel test).
- **Igiene template** — nessuna classe CSS costruita per concatenazione nei file
  già migrati (incluso nel test, con whitelist dei non ancora migrati).
- **Fase 9** — `PS_FASE9=1` fa fallire il test se un template referenzia ancora
  Bootstrap o AdminLTE.

### Manuali nel browser (agente principale, Chrome)

Per ogni fase, i criteri sono elencati nel rispettivo `fasi/fase-N.md`. I tre
trasversali:

- **767 vs 768 px** su `/movements`: sotto si vede **solo** la card-list, sopra
  **solo** la tabella. Mai entrambe, mai nessuna.
- **Nessun flash di tema** al caricamento, in light e in dark.
- **Nessun overflow orizzontale** a 375 px su nessuna pagina.

### Verifiche empiriche (Fase 0) — chiuse il 2026-10-17

**Ordinamento per data della tabella movimenti: CONFERMATO.** Il server ordina
per `move_date DESC` (`repository.py:611`), poi DataTables riordina
client-side la colonna 0 renderizzata `gg/mm/aaaa`. Il plugin `date-eu` non e'
caricato, `Date.parse("13/09/2026")` da' `NaN`, il tipo ricade su `string` e
`order: [[0, 'desc']]` (`ps-show-mov.html:323`) produce un confronto
lessicografico: per giorno del mese, poi mese, poi anno.

> **Il test proposto in `fasi/fase-0.md` §0.4 non lo avrebbe rivelato.**
> Dentro un singolo mese l'ordine per giorno coincide con quello cronologico,
> e la vista di default filtra proprio il mese corrente. Serve un intervallo
> su **piu' mesi**. E' il motivo per cui il difetto e' rimasto invisibile.

Misurato sul DataTables reale (Playwright, `tools/ui-shots.py` e sonde):

| Intervallo | tipo rilevato | prime righe a video | corretto |
|---|---|---|---|
| settembre 2026 (67 righe) | `string` | 30/09, 30/09, 29/09, 29/09, 28/09 | si', per caso |
| ago-ott 2026 (257 righe) | `string` | **31/08**, 31/08, 31/08, 30/09, **30/08** | no |
| 2025-2026 (1.395 righe) | `string` | **31/10/2025**, 31/10/2025, **31/08/2026** | no |

Corretto con `data-order` sulla cella — voce **MB-006**, chiusa lo stesso
giorno, separata dal restyling. Dopo la correzione il tipo rilevato e' `date`
e l'ordine coincide con quello del server su tutti e tre gli intervalli.
Le colonne importo **non** hanno il problema: sono rilevate `num-fmt,` e
ordinano bene (verificato contro `ORDER BY expense DESC`).

**Peso reale degli asset su `/movements`** — cache fredda, 1440x900, utente
autenticato. Nessuna risposta >= 400, **nessuna risorsa richiesta due volte**.
Rimisurabile con `tools/ui-measure.py [rotta]`.

**Totale: 22 richieste, 882,7 KB**

| Origine | Richieste | KB | % |
|---|---|---|---|
| `localhost:5000` | 3 | 515,2 | 58,4% |
| `cdn.jsdelivr.net` | 11 | 295,5 | 33,5% |
| `cdn.datatables.net` | 7 | 42,0 | 4,8% |
| `code.jquery.com` | 1 | 30,0 | 3,4% |

| Tipo | Richieste | KB | % |
|---|---|---|---|
| stylesheet | 7 | 379,8 | 43,0% |
| script | 11 | 239,3 | 27,1% |
| font | 2 | 146,8 | 16,6% |
| document | 1 | 114,1 | 12,9% |
| xhr | 1 | 2,8 | 0,3% |

Le voci che dominano: **`adminlte.css` 354,1 KB** (40% della pagina, sparisce
in Fase 9), **`bootstrap-icons.woff2` 131,6 KB** (set completo per una dozzina
di glifi: con il self-hosting di D9 c'e' spazio per un subset), il documento
114,1 KB, `chart.umd.min.js` 69,5 KB, `adminlte.js` 47,0 KB.

**P6 e' smentito.** Il piano elencava fra i difetti preesistenti "Bootstrap JS
caricato due volte": non risulta. Bootstrap e' caricato una volta sola
(`ps-base.html:98`); le due righe di `ps-show-mov.html` che lo fanno sospettare
sono gli adattatori DataTables (`dataTables.bootstrap5.min.js:312` e
`responsive.bootstrap5.min.js:314`), che sono file diversi. Il controllo sui
duplicati di rete lo conferma.

## Note

- **Branch**: il lavoro sta su `feature/task-19-FE-refactoring`, già attivo —
  da cui la numerazione `19-0`.
- **`backlog/features.md` non è stato aggiornato di proposito.** Su questo
  branch il backlog si ferma a `task18-0.md`, ma in `pyspendless/test/`
  esistono `test_task22_0.py` (wallet preferito per utente) e
  `test_task23_0.py` (OAuth2 su `/mcp-oauth2`): i task 19-23 sono stati
  numerati altrove e le loro voci di backlog non sono su questo branch.
  Aggiungere qui una riga a `features.md` creerebbe quasi certamente un
  conflitto al merge. Da fare dopo l'allineamento con `main`, decidendo quale
  versione del file tenere.
- `/settings/admin` **non è nel `CONTRACT`** del test: richiede che l'utente
  della sessione finta sia l'`ADMIN_USER_ID`. I suoi criteri di accettazione
  (Fase 5) restano manuali. Se vuoi coprirla, va aggiunta una fixture che
  inietti l'id admin.
- I difetti preesistenti P1-P6 (icone Font Awesome invisibili perché FA non è
  caricato, markup di `ps-auth.html` scartato da Jinja, `<title>` duplicato,
  Bootstrap JS caricato due volte) sono elencati al §1.4 del piano. Sono difetti
  di **presentazione**: la proposta è correggerli durante il rework
  documentandoli, ma è la decisione aperta **D10**.
- Il PDF del report (`report_pdf.py`, matplotlib) è server-side e **fuori
  scope**: non riflette il nuovo look, e va bene così.
