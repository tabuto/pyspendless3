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

Le 4 pagine sono indipendenti: 4 subagent `ps-markup` in `isolation: worktree`
(è nel frontmatter della definizione, vale sempre), in parallelo.

⚠️ **Nessuno dei 4 apre il browser.** Flask gira dal checkout principale, non
dai worktree: un subagent che verificasse nel browser guarderebbe il codice
sbagliato. La verifica visiva la fa l'agente principale **dopo il merge**.

### Primo comando dentro il worktree

Un worktree contiene solo i file **tracciati**, quindi non ha `.venv/` né
`pyspendless/.env`. Senza quest'ultimo l'import dell'app fallisce, e il test di
contratto — che è il criterio di rilascio — non parte nemmeno.

Non è un passo manuale: `tools/worktree-bootstrap.sh` è versionato, quindi
esiste già dentro ogni worktree appena creato. Il subagent lo esegue come
**prima** cosa:

```bash
./tools/worktree-bootstrap.sh
```

Collega `.env`, individua il virtualenv giusto fra i due presenti nel repo, e
stampa il comando esatto del test. Nel checkout principale è un no-op, quindi
si può eseguire sempre senza pensarci.

Per prepararlo ed eseguire subito il contratto:

```bash
./tools/worktree-bootstrap.sh --test
```

Dettagli in `RUNBOOK.md` §4.1.

## Lavoro per pagina

Ognuna cambia `{% extends %}` verso la shell `-tw` e riscrive il markup.

### `ps-maintenance.html` → `ps-auth-tw.html`

Resa dal `before_request` con status **503**. Da preservare: il testo, il
bottone "Riprova" con `window.location.reload()`.
Icone `fas fa-tools` / `fas fa-sync-alt` / `fa-4x`: Font Awesome non è
caricato, oggi quelle icone **non si vedono**. **D10, decisa il 2026-10-17: si
rimuovono**, nessun glifo sostitutivo — oggi lì non c'è niente e dopo non ci
sarà niente, che è la scelta isofunzionale. Cancellare l'elemento `<i>` per
intero, non solo le classi: un `<i>` vuoto resterebbe nel DOM senza scopo.
`fa-4x` è l'icona grande al centro: togliendola il blocco si accorcia, ed è
l'unico punto in cui la rimozione si nota nel layout. È accettabile.
`.login-box-msg` è una classe del layout AdminLTE: va sostituita (la nuova
shell `ps-auth-tw.html` ha già il contenitore equivalente).

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
| A3.8 | Il file supera i `DYNAMIC_CLASS_PATTERNS` del contratto | comando nel brief (vedi nota) |

> **Nota su A3.8.** La formulazione originale era "il file è stato rimosso da
> `whitelist_non_migrati` in `test_task19_0.py`". Con quattro subagent in
> altrettanti worktree, quattro modifiche da una riga allo **stesso** file
> producono conflitti certi al rientro. Quindi: i subagent **non toccano il
> file di test**; verificano il proprio file con il comando dato nel brief, e
> la whitelist la sfoltisce l'agente principale dopo il merge, in un colpo
> solo. Il controllo è lo stesso, cambia solo chi lo esegue e quando.

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
