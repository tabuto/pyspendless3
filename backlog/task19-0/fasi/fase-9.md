# Fase 9 — Pulizia e rilascio

**Agente**: principale (non delegare: qui si cancellano file)
**Stima**: 1-2 gg
**Dipende da**: Fase 8 verde.

A questo punto tutte e 16 le pagine girano su Tailwind e la vecchia gerarchia
non serve più a nessuno.

## Attività

### 9.1 — Rimozione degli asset

- `pyspendless/static/css/adminlte.*` (8 file: css, min, rtl, rtl.min e i 4 `.map`)
- `pyspendless/static/js/adminlte.*` (4 file)
- `pyspendless/static/img/` — verificare **prima** quali immagini AdminLTE
  (`AdminLTEFullLogo.png`, `AdminLTELogo.png`, `boxed-bg.*`, `default-150x150.png`,
  `icons.png`) non sono più referenziate, poi rimuovere solo quelle

### 9.2 — Rimozione della vecchia gerarchia

`ps-base.html`, `ps-nav.html`, `ps-auth.html`.

### 9.3 — Rename

`ps-*-tw.html` → `ps-*.html`, con aggiornamento degli `{% extends %}` nelle 16
pagine. Conviene come **commit separato e isolato**: un rename puro è facile da
rivedere, un rename mescolato ad altro no.

### 9.4 — Rimozione dei CDN residui

OverlayScrollbars, Popper, Bootstrap JS e CSS da tutti i template, inclusi i
secondi caricamenti nei `{% block scripts %}` (difetto **P5**, si risolve da sé
qui).

Restano, legittimamente: Chart.js, chartjs-plugin-datalabels, jQuery,
DataTables, Tom Select.

### 9.5 — Template morti

I 9 mai referenziati da `render_template`: `base.html`, `index.html`,
`login.html`, `login_old.html`, `loginv2.html`, `cards.html`, `forms.html`,
`tables.html`, `ps-setting-categories-old.html`. Circa 3000 righe, per lo più
demo AdminLTE.

**Decisione D7**: da confermare prima di cancellare.

### 9.6 — Documentazione

- `CLAUDE.md` → "Rilascio / Deploy": inserire il passo 0
  (`./tools/build-css.sh`, verificare che il CSS sia staged)
- `pyspendless/README.md` → come si compila il CSS, dove sta il binario, cosa
  succede se ci si dimentica
- `backlog/features.md` → aggiornare la riga a DONE
- Chiudere `backlog/task19-0.md`

### 9.7 — Misura finale

Ripetere la misura 0.5 su `/movements` e confrontare con la baseline. È il
numero che dice se il lavoro ha anche alleggerito l'app, oltre a rifarla.

### 9.8 — Proporre il rilascio

Bump `_APP_VERSION` a **`0.2.0`**, commit, tag `v0.2.0`, push, poi i passi
manuali sul server PA (console → `git pull` → Reload dalla tab Web), infine
verifica su `https://tabuto.pythonanywhere.com/version`.

⚠️ **Solo su richiesta esplicita dell'utente**, come da `CLAUDE.md`. Proporre
e attendere conferma, non eseguire d'iniziativa.

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A9.1 | `PS_FASE9=1 .venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | il test fallisce se un template referenzia ancora Bootstrap o AdminLTE |
| A9.2 | Nessuna occorrenza di `bootstrap`, `adminlte`, `overlayscrollbars`, `popper` nei template | grep ricorsivo |
| A9.3 | Nessuna occorrenza di `class="btn `, `class="card`, `col-md-`, `d-md-`, `form-control` | grep ricorsivo |
| A9.4 | `whitelist_non_migrati` nel test è vuota (o contiene solo i template morti, se non cancellati) | lettura del file |
| A9.5 | Tutte e 16 le rotte rendono 200 | incluso nel test |
| A9.6 | Nessun 404 sugli asset statici su nessuna pagina | `read_console_messages` + `read_network_requests`, Chrome |
| A9.7 | Nessun errore in console su nessuna delle 16 pagine, light e dark | `read_console_messages` |
| A9.8 | Giro completo manuale: login → crea → visualizza → cerca → ricorrenti → dashboard → report → impostazioni → logout | percorso end-to-end in Chrome |
| A9.9 | `docs/ui-after/` completo e confrontato con `docs/ui-baseline/` | review affiancata |
| A9.10 | Misura finale registrata accanto a quella di Fase 0 | tabella comparativa nel task |
| A9.11 | Il gate sul diff ha retto: nessuna modifica a `app.py`, `models.py`, `repository.py`, `conf.py`, `report_*.py` | `git diff --stat` su tutto il branch |

A9.11 è il criterio che dà senso all'intero task: se è verde, l'affermazione
"abbiamo cambiato solo la presentazione" è dimostrata, non asserita.

## Definition of done

Bootstrap e AdminLTE non esistono più nel progetto, il giro completo funziona
nei due temi su tre larghezze, il codice applicativo non è stato toccato, e il
rilascio è **proposto** all'utente con la procedura manuale scritta.
