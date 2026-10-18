# CLAUDE.md — Istruzioni di progetto per PySpendless

Guida operativa per l'assistente. Va letta a inizio sessione e rispettata in
tutte le attività su questo repo.

## Regole non negoziabili

- **Mai `git commit` e mai `git push` se non esplicitamente richiesto
  dall'utente.** Fare le modifiche ai file e fermarsi lì; il versionamento lo
  decide l'utente.
- **Mai creare tag git** di propria iniziativa (vedi "Rilascio / Deploy").
- Non toccare `.env`, `.env_pa`, `*.db`: sono ignorati da git e contengono
  dati locali/segreti.
- I segreti restano fuori dal repo (GitHub Actions secrets / file `.env`
  ignorati), mai hardcodati nel codice o nei workflow.

## Struttura dell'applicazione

```
pyspendless/
├── app.py           # entry point + quasi tutte le rotte (pagine e API /api/...)
├── oauth_server.py  # blueprint OAuth2: /oauth/authorize rende ps-oauth-consent.html
├── models.py        # tabelle SQLAlchemy
├── conf.py          # configurazione e costanti (legge .env via python-dotenv)
├── repository.py    # CRUD / logica di accesso dati
├── templates/       # Jinja2, base = ps-base.html
├── static/css/      # ps-tailwind.src.css (sorgente) -> ps-tailwind.css (versionato)
├── static/js/       # ps-ui.js (modal/drawer/tab), ps-theme.js (light/dark)
└── .env / .env_pa   # variabili d'ambiente (NON versionati)

tools/               # build-css.sh, sonde di verifica UI
```

> **`app.py` non ha tutte le rotte.** `oauth_server.py` è un blueprint
> registrato in `app.py:64` e rende un template per conto suo. Cercare
> `render_template` nel solo `app.py` dà un inventario incompleto — è
> esattamente così che `ps-oauth-consent.html` è sfuggito alla pianificazione
> del task19-0, e si è scoperto solo in Fase 9.

Deploy: PythonAnywhere `tabuto.pythonanywhere.com`, working copy server
`/home/tabuto/pyspendless3`.

## File `.md` di progetto e ordine di lettura

Non c'è caricamento automatico oltre a questo file. Quando l'utente chiede di
**implementare un task o un bugfix**, l'ordine è:

1. **Il file indicato dall'utente**:
   - `backlog/taskN-0.md` — task strutturato (obiettivo, analisi, implementazione,
     casi limite, "File toccati", test).
   - `backlog/00-task-minor-bugfix.md` — registro permanente delle evolutive/bug
     minori; leggere la voce `MB-NNN` indicata **e** la sezione "Convenzioni" in
     testa al file.
2. **I file sorgente elencati** nella sezione "File toccati" / "Dove" della voce,
   ai riferimenti puntuali (`app.py:NNN`, `templates/....html`).
3. **Altri `.md` solo se la voce li richiama** (es. aggiornare
   `backlog/features.md`).

Riferimento (letti solo se servono a un vincolo specifico):

| File | Contenuto |
|---|---|
| `backlog/features.md` | backlog features, tabella Task/Descrizione/Stato |
| `backlog/00-task-minor-bugfix.md` | registro evolutive/bug minori (`MB-NNN`) |
| `backlog/bugfix.md` | note bugfix storiche |
| `pyspendless/SPECS.md` | specifiche funzionali originali |
| `pyspendless/README.md` | setup ambiente, deploy |
| `pyspendless/migrations/*.md` | procedura di migrazione dati |
| `prompt.md` | prompt iniziale di generazione del progetto (storico) |

## Convenzioni di backlog

- Task grande (modello dati, migrazione, > 2-3 file) → nuovo `backlog/taskN-0.md`
  con numerazione progressiva (ultimo: `task23-0-oauth-alexa.md`).
- Intervento piccolo → voce `MB-NNN` in `backlog/00-task-minor-bugfix.md`
  (ID progressivo, mai riusato; stato `APERTA → IN CORSO → RISOLTA/SCARTATA`;
  alla chiusura spostare il blocco in "Risolte" con data e file toccati).
- Le nuove feature/task vanno registrate anche in `backlog/features.md`.

## Rilascio / Deploy

> **Il deploy è MANUALE.** La GitHub Action `.github/workflows/deploy.yml` è
> **disabilitata**: l'account PythonAnywhere è gratuito e non consente l'uso delle
> API (`consoles/send_input`, `webapps/reload`), su cui il workflow si basa
> interamente. È questa la causa del run fallito sul tag `v0.1.7`. Il file del
> workflow resta in repo come riferimento per un'eventuale riattivazione su un
> piano a pagamento; descrizione originale in `backlog/task18-0.md`.

Il tag `vX.Y.Z` resta la convenzione per marcare le release, ma **non innesca
nulla**: dopo il push va eseguito a mano l'aggiornamento sul server.

**Procedura di rilascio (solo su richiesta esplicita dell'utente):**

0. **Compilare il CSS**: `./tools/build-css.sh`, poi verificare che
   `pyspendless/static/css/ps-tailwind.css` sia aggiornato e **staged**.
   Vedi "CSS: il passo che si dimentica" qui sotto.
1. Bump di `_APP_VERSION` in `pyspendless/app.py` (semver) — vedi voce MB-003.
2. `git commit` delle modifiche.
3. `git tag vX.Y.Z` con la stessa versione di `_APP_VERSION`.
4. `git push && git push --tags`.
5. **Passo manuale sul server** (non automatizzabile da qui): console Bash su
   PythonAnywhere → `cd /home/tabuto/pyspendless3` → `git pull` (o
   `git checkout vX.Y.Z`) → poi **Reload** della web app dalla tab *Web*.
6. Verifica: `GET https://tabuto.pythonanywhere.com/version` deve riportare la
   versione appena rilasciata.

### CSS: il passo che si dimentica

Dal task19-0 la presentazione gira su **Tailwind**, compilato da
`pyspendless/static/css/ps-tailwind.src.css` a `ps-tailwind.css`. Sul server
non c'è Node e non c'è una fase di build: **l'output compilato è versionato**,
esattamente come lo era `adminlte.css` prima.

Quindi, ogni volta che si tocca un `class="..."` in un template o una regola
nel `.src.css`:

```bash
./tools/build-css.sh
```

Il binario è `tools/tailwindcss` (CLI standalone, nessun `package.json`); lo
script fallisce apposta se l'output scende sotto i 5 KB o se git lo ignora.

**Se ci si dimentica**, in produzione finisce il CSS vecchio: le classi nuove
non hanno stile, ma **l'app funziona** — fallimento degradato, non rotto. Il
modo di accorgersene prima è che `git status` resti pulito dopo una build:
se la build cambia il file, il commit era incompleto.

L'assistente esegue questi passi **solo** se l'utente lo chiede esplicitamente.
Al termine di un task, se le modifiche sembrano da rilasciare, **proporre** la
procedura e attendere conferma — non eseguirla d'iniziativa.
