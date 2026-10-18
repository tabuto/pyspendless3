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

## Stato: CHIUSO — 2026-10-18

Tutte e dieci le fasi (0-9) sono completate. Bootstrap e AdminLTE non esistono
più nel progetto: **18 template** su tre shell Tailwind, tema light/dark
persistente, −33% di peso su `/movements`.

Il criterio che dà senso all'intero task, **A9.11**, è verde e dimostrato:
sull'intero branch `git diff --name-only main...HEAD` non tocca
`app.py`, `models.py`, `repository.py`, `conf.py`, `report_*.py` né
`oauth_server.py`. «Abbiamo cambiato solo la presentazione» è misurato, non
asserito.

Restano aperti, e **non** fanno parte di questo task:

| Cosa | Dove |
|---|---|
| Il subset delle icone (216,6 KB per 59 glifi su 2.078) | voce `MB-NNN` da aprire — vedi "Misura finale" |
| Verifica A9.6-A9.9 nei due temi su tre larghezze | richiede prima di estendere `ui-shots.py`, oggi bloccato su `THEME = "light"` |
| Il rilascio | vedi D14 |
| I due strumenti tautologici | vedi "Due strumenti di verifica sono diventati tautologici" |

### Stato di partenza (per memoria)

Stack: **AdminLTE 4 + Bootstrap 5.3**, CSS AdminLTE locale
(`pyspendless/static/css/adminlte.css`), tutto il resto da CDN — Bootstrap JS,
Bootstrap Icons, OverlayScrollbars, Chart.js, jQuery + DataTables, Tom Select,
font Source Sans 3.

16 template renderizzati da `app.py`, su due layout (`ps-nav.html` per l'area
autenticata, `ps-auth.html` per login/onboarding/manutenzione), più 9 template
morti mai referenziati da `render_template`.

> **Questo inventario era incompleto, e lo si è scoperto solo in Fase 9: i
> template resi sono 18, non 16.** Mancavano `ps-maintenance.html` e, più
> seriamente, `ps-oauth-consent.html` — che non è reso da `app.py` ma da
> `oauth_server.py:158`, un blueprint registrato a parte. Cercare
> `render_template` nel solo `app.py` dà un inventario incompleto: quel
> template non era assegnato a nessuna fase, estendeva ancora la vecchia shell,
> ed era l'ultimo file vivo con classi Bootstrap. Cancellare `ps-auth.html`
> senza convertirlo prima lo avrebbe rotto. Nota aggiunta anche a `CLAUDE.md`.

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
| D10 | Difetti preesistenti P1-P6: le icone **Font Awesome si rimuovono** (non sono mai state visibili, FA non è caricato — la rimozione è la scelta isofunzionale). **Precisazione 2026-10-18**: vale per le icone *decorative*, quelle accanto a un testo. Dove l'icona è l'**unico contenuto** di un bottone — cioè è l'etichetta, non un ornamento — si usa il `bi bi-*` corrispondente: rimuoverla lascerebbe un bottone vuoto identificabile solo dal tooltip. P6 è **reale**: vedi "Verifiche empiriche" |
| D12 | Sidebar mobile: **drawer off-canvas**, come oggi |
| D14 | Versione di rilascio: ~~`0.2.0`~~ → **`0.3.0`**. **Corretta in Fase 9**: `_APP_VERSION` era già `0.2.2` (il branch contiene il task23 OAuth) e i tag `v0.2.0` e `v0.2.1` **esistono già**. Rilasciare come 0.2.0 sarebbe stato un downgrade su un tag occupato. Scelto il bump minor: il rifacimento di 18 pagine è un cambiamento di livello feature, pur isofunzionale |

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

**P6: smentito su `/movements`, CONFERMATO sulle impostazioni.**

La prima misura era stata fatta solo su `/movements`, dove Bootstrap è davvero
caricato una volta sola: le due righe sospette di `ps-show-mov.html` sono gli
adattatori DataTables (`dataTables.bootstrap5.min.js:312` e
`responsive.bootstrap5.min.js:314`), che sono file diversi.

**Sei pagine di impostazioni**, però, caricano in fondo un secondo Bootstrap, in
una versione diversa da quella della shell — `wallet`, `import-export`,
`admin`, `categories`, `group`, `profile`:

```
ps-base.html:98   bootstrap@5.3.2/dist/js/bootstrap.min.js
<pagina>:NNN      bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js
```

A runtime vince il **secondo**, cioè il più vecchio, che sovrascrive il primo:
su `/settings/wallets` `bootstrap.Modal.VERSION` risponde `5.3.0`. Il difetto è
reale e si chiude in Fase 5 (criterio A5.9).

Lezione di metodo: una misura su una pagina sola non dimostra niente su
diciassette. Un difetto si smentisce sull'insieme dei file, non su un campione
scelto perché comodo.

### Misura finale (Fase 9, attività 9.7) — 2026-10-18

Stessa rotta, stesso strumento, stesse condizioni: `tools/ui-measure.py
/movements`, cache fredda, 1440x900, utente autenticato.

| | Fase 0 | Fase 9 | Δ |
|---|---|---|---|
| **richieste** | 22 | **16** | −6 (−27%) |
| **peso** | 882,7 KB | **593,1 KB** | **−289,6 KB (−33%)** |

Per origine, dove si vede lo scambio fatto dalle decisioni D6 e D9 — meno CDN,
più roba servita in locale:

| Origine | Fase 0 | Fase 9 |
|---|---|---|
| `localhost:5000` | 3 req / 515,2 KB | 7 req / 432,4 KB |
| `cdn.jsdelivr.net` | 11 req / 295,5 KB | 3 req / 90,3 KB |
| `cdn.datatables.net` | 7 req / 42,0 KB | 5 req / 40,4 KB |
| `code.jquery.com` | 1 req / 30,0 KB | 1 req / 30,0 KB |

`adminlte.css`, che da solo valeva 354,1 KB e il 40% della pagina, non esiste
più. Al suo posto `ps-tailwind.css` pesa **52,6 KB**: un settimo.

**Quello che resta da guadagnare, ed era già previsto in Fase 0.** La risorsa
più pesante della pagina ora è il set di icone, e non è il framework:

| Risorsa | KB | % della pagina |
|---|---|---|
| `ps-icons.woff2` | 131,3 | 22,1% |
| `ps-icons.css` | 85,3 | 14,4% |
| **totale icone** | **216,6** | **36,5%** |

D9 ha self-ostato Bootstrap Icons ma **non ne ha fatto un subset**. Contati:
`ps-icons.css` definisce **2.078 glifi**, i template e il JS ne usano **59**.
Si carica il 97% di un set per non usarlo.

La misura di Fase 0 aveva individuato il difetto ma ne aveva sbagliato la
taglia (*«set completo per una dozzina di glifi»*): dodici erano le icone
visibili allora, non quelle referenziate — e D10 ne ha poi aggiunte,
sostituendo le Font Awesome mai rese con i `bi bi-*` corrispondenti. Il
difetto resta, con un numeratore quattro volte più grande.
È il prossimo guadagno grosso, ma la stima va fatta sul serio prima di
prometterla: 59 glifi su 2.078 non significa 59/2078 del peso, perché un
`woff2` ha tabelle condivise che non scalano col numero di glifi. Un subset si
misura generandolo. È comunque un intervento a sé, non parte del restyling:
va aperta una voce `MB-NNN`.

### Due strumenti di verifica sono diventati tautologici

Emerso verificando la Fase 9, e va scritto perché non si creda che siano due
criteri superati:

- **`tools/check-nav-parity.py` (criterio A2.3)** confronta la nav «vecchia»
  letta da `/home` con la «nuova» letta da `ps-home.html`. Dalla Fase 3 `/home`
  **rende proprio `ps-home.html`**: confronta lo stesso template con se stesso,
  per due vie di rendering diverse. Vacuo da sei fasi.
- **`tools/check-conversion-table.py` (criterio A1.4)** salta i template già
  migrati. Dalla Fase 9 lo sono tutti e 21: esamina **0 classi** e riporta
  copertura completa.

Entrambi avevano come termine di paragone il *prima*, che ora non esiste più
nel working tree. Tornano significativi solo prendendolo da git, per esempio
`git show v0.2.2:pyspendless/templates/ps-nav.html`. Finché restano così,
il loro verde non è evidenza.

## Note

- **Branch**: il lavoro sta su `feature/task-19-FE-refactoring`, già attivo —
  da cui la numerazione `19-0`.
- **`backlog/features.md`: aggiornato in Fase 9**, dopo aver verificato la
  riserva che era scritta qui. La riserva diceva che aggiungere una riga
  «creerebbe quasi certamente un conflitto al merge», perché i task 19-23
  sarebbero stati numerati altrove. Misurato: `git diff main...HEAD --
  backlog/features.md` è **vuoto**, cioè il file su questo branch è
  **identico a `main`**, e già elenca task20-0, task21-0 e task22-0. Su un
  file identico a main, aggiungere una riga **in coda** è l'edit meno
  conflittuale possibile. La riga c'è, con stato `DONE`.

  Resta vero che il backlog di `task23-0-oauth-alexa.md` non ha una riga in
  `features.md`: è un buco preesistente, non di questo task.
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
