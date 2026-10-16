# Fase 3 — Pagine semplici

**Agente**: `ps-markup`, **una invocazione per pagina** (4 subagent)
**Stima**: 1-2 gg
**Dipende da**: Fase 2 verde.

Ordine: `ps-maintenance.html` → `ps-login.html` → `ps-onboarding.html` →
`ps-home.html`.

Perché queste per prime: nessun JS complesso, coprono **entrambe** le shell
(auth e nav), e `ps-login` è la porta d'ingresso — un errore qui è
immediatamente visibile invece di restare nascosto in una pagina interna.

## Parallelizzazione

Le 4 pagine sono indipendenti: 4 subagent `ps-markup` in `isolation: worktree`,
in parallelo.

⚠️ **Nessuno dei 4 apre il browser.** Flask gira dal checkout principale, non
dai worktree: un subagent che verificasse nel browser guarderebbe il codice
sbagliato. La verifica visiva la fa l'agente principale **dopo il merge**.

## Lavoro per pagina

Ognuna cambia `{% extends %}` verso la shell `-tw` e riscrive il markup.

### `ps-maintenance.html` → `ps-auth-tw.html`

Resa dal `before_request` con status **503**. Da preservare: il testo, il
bottone "Riprova" con `window.location.reload()`.
Icone `fas fa-tools` / `fas fa-sync-alt` → **P2**: Font Awesome non è caricato,
oggi quelle icone non si vedono. Sostituire con `bi bi-*` se D10 è approvata.
`.login-box-msg` è una classe AdminLTE (P6): va sostituita.

### `ps-login.html` → `ps-auth-tw.html`

Da preservare: `id="login-google-btn"`, `href="/auth/login"`, il testo
"Login with Google", l'icona `bi bi-google`.

### `ps-onboarding.html` → `ps-auth-tw.html`

Da preservare: form `method="POST" action="/onboarding"`, i campi
`account_name` e `wallet_name` con `required` e `maxlength="100"`, i rispettivi
`form-text`, il blocco `get_flashed_messages(with_categories=true)` con gli
alert dismissible.

### `ps-home.html` → `ps-nav-tw.html`

Da preservare: i 6 link (`create`, `movements`, e i 4 di impostazioni),
l'alert di login con `user_email`, il testo italiano.

## Criteri di accettazione

Validi per **ogni** pagina della fase. Un subagent rilascia il proprio task
solo quando tutti i suoi sono soddisfatti.

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A3.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |
| A3.2 | Il template estende la shell `-tw` | grep `{% extends %}` |
| A3.3 | Nessuna occorrenza di `bootstrap`, `adminlte`, `btn btn-`, `card-body`, `col-md-`, `d-md-` nel file | grep |
| A3.4 | Tutti gli `id=` presenti prima lo sono ancora | diff degli id estratti da `git show HEAD:<file>` e dal file corrente |
| A3.5 | Tutti i `name=` e gli `{{ url_for }}` preservati | stesso metodo |
| A3.6 | Blocchi Jinja preservati: stesso numero di `{% if %}`, `{% for %}`, `{{ }}` | conteggio prima/dopo |
| A3.7 | Testo visibile italiano invariato | diff del testo con i tag rimossi |
| A3.8 | Il file è stato rimosso da `whitelist_non_migrati` in `test_task19_0.py` | grep |

### Verificabili solo dall'agente principale (Chrome, dopo il merge)

| # | Criterio |
|---|---|
| A3.9 | Percorso completo login → onboarding → home percorribile end-to-end |
| A3.10 | Nessun overflow orizzontale a 375 px su nessuna delle 4 pagine |
| A3.11 | Le 4 pagine rese correttamente in light **e** in dark |
| A3.12 | La pagina di manutenzione risponde ancora **503** con `MAINTENANCE_MODE=1` |
| A3.13 | I flash message dell'onboarding compaiono e si chiudono |
| A3.14 | Screenshot after archiviati in `docs/ui-after/` e confrontati con la baseline |

## Definition of done

Le 4 pagine girano su Tailwind, il contratto è verde, e il login funziona da
mobile e da desktop nei due temi.

La pagina di prova della Fase 2 si può cancellare qui.
