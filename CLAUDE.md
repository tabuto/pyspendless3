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
├── app.py         # entry point + tutte le rotte (pagine e API /api/...)
├── models.py      # tabelle SQLAlchemy
├── conf.py        # configurazione e costanti (legge .env via python-dotenv)
├── repository.py  # CRUD / logica di accesso dati
├── templates/     # Jinja2, base = ps-base.html
└── .env / .env_pa # variabili d'ambiente (NON versionati)
```

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
  con numerazione progressiva (ultimo: `task18-0.md`).
- Intervento piccolo → voce `MB-NNN` in `backlog/00-task-minor-bugfix.md`
  (ID progressivo, mai riusato; stato `APERTA → IN CORSO → RISOLTA/SCARTATA`;
  alla chiusura spostare il blocco in "Risolte" con data e file toccati).
- Le nuove feature/task vanno registrate anche in `backlog/features.md`.

## Rilascio / Deploy

Il deploy su PythonAnywhere è automatico via **GitHub Actions**
(`.github/workflows/deploy.yml`), trigger: **push di un tag `vX.Y.Z`**
(`on: push: tags: ['v*']`). Il workflow fa `git pull`/checkout del tag sul
server PA e reload della web app tramite API token (secrets
`PA_USER` / `PA_TOKEN` / `PA_DOMAIN` / `PA_REPO_PATH`). Dettagli in
`backlog/task18-0.md`.

**Procedura di rilascio (solo su richiesta esplicita dell'utente):**

1. Bump di `_APP_VERSION` in `pyspendless/app.py` (semver) — vedi voce MB-003.
2. `git commit` delle modifiche.
3. `git tag vX.Y.Z` con la stessa versione di `_APP_VERSION`.
4. `git push && git push --tags`  ← è il push del tag che avvia il deploy.

L'assistente esegue questi passi **solo** se l'utente lo chiede esplicitamente.
Al termine di un task, se le modifiche sembrano da rilasciare, **proporre** la
procedura e attendere conferma — non eseguirla d'iniziativa.
