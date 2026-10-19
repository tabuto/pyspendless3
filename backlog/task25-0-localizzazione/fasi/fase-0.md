# Fase 0 — Gate di installabilità e inventario

**Chi**: l'**utente** per il gate (serve una console sul server, l'assistente
non ha accesso a PythonAnywhere) + 1 × `ps-i18n-audit` per l'inventario.
**Durata**: mezza giornata, il gate sono dieci minuti.
**Dipende da**: niente. **Blocca tutto il resto.**
**Nessun file dell'applicazione viene modificato in questa fase.**

---

## 0.1 Il gate: le dipendenze stanno sul server?

`Flask-Babel` e `Babel` sono le prime dipendenze nuove dal task18-0. Il deploy
è un `git pull`: **non installa niente**. Se non entrano, il primo rilascio del
task mette in produzione un'app che non importa — `ImportError` su ogni pagina.

### Comandi, da una console **Bash** su PythonAnywhere

```bash
# 1. Quanto spazio è rimasto? (free = 512 MB)
du -sh ~/.virtualenvs/* 2>/dev/null; df -h ~ | tail -1

# 2. Che Python fa girare la web app? (serve per i pin)
cd /home/tabuto/pyspendless3
python3 --version
# e nella tab Web, la riga "Python version" della web app

# 3. Prova di installazione, nel virtualenv della web app
pip install Flask-Babel

# 4. Verifica che importi e che versione è arrivata
python -c "import flask_babel, babel; print('flask-babel', flask_babel.__version__, '| babel', babel.__version__)"

# 5. Quanto è costato in disco
du -sh $(python -c "import babel, os; print(os.path.dirname(babel.__file__))")
df -h ~ | tail -1
```

### Esiti

| Esito | Cosa si scrive qui sotto | Conseguenza |
|---|---|---|
| **Verde** | versioni di `flask_babel` e `babel`, versione di Python della web app, spazio residuo | Si procede con D1 (Flask-Babel). I pin vanno in `requirements.txt` alla Fase 1 **con le versioni che hanno funzionato qui**, non con le ultime di PyPI. |
| **Rosso per quota** | quanti MB mancano | **Piano B**: `gettext` di stdlib + estensione i18n di Jinja2 a mano, `pybabel` solo in locale, mesi e formati scritti a mano per due lingue. Cambiano `i18n.py` e `requirements.txt`; **fasi, criteri e brief dei subagent restano identici**. |
| **Rosso per Python troppo vecchio** | la versione | Si pinna una `Flask-Babel` più vecchia compatibile, oppure piano B. |

> Se il gate è verde, **disinstallare** (`pip uninstall Flask-Babel`) non serve
> e non conviene: lasciarlo installato anticipa il passo manuale del rilascio
> (§9 del piano) e non ha effetti sull'app finché nessuno lo importa.

### Esito registrato

```
Data:                      ____________
Python della web app:      ____________
flask-babel:               ____________
babel:                     ____________
Spazio residuo prima/dopo: ____________
Esito:                     VERDE / ROSSO → piano B
```

---

## 0.2 Quale virtualenv, in locale

Nel repo ce ne sono **due**: `.venv/` nella root e `pyspendless/.venv/`.
`test_task22_0.py` usa il secondo, `.claude/settings.local.json` registra il
primo, e `tools/worktree-bootstrap.sh` sceglie quello che ha Flask installato.

Va **fissato qui** quale si usa, così i sedici subagent delle fasi successive
non devono indovinare:

```bash
cd /Users/fradidio/Sviluppo/pyspendless3
.venv/bin/python -c "import flask, sqlalchemy; print('root ok')"
pyspendless/.venv/bin/python -c "import flask, sqlalchemy; print('pyspendless ok')"
```

```
Virtualenv da usare nei brief:  ____________________
```

---

## 0.3 Inventario esatto delle stringhe

**Agente**: 1 × `ps-i18n-audit` (sola lettura, haiku).

Le cifre di `task25-spec.md` §2.2 (~433 testi + ~40 attributi + ~173 stringhe
JS nei template, ~700-900 msgid in totale) sono **euristiche**. Qui si misurano
per davvero, perché da quel numero dipende come si spezzano le slice della
Fase 4 e quanto dura la Fase 9.

L'audit produce `backlog/task25-0-localizzazione/inventario.md` con:

| Colonna | Contenuto |
|---|---|
| file | il template o il modulo Python |
| testi | stringhe di testo visibile |
| attributi | `placeholder`, `title`, `aria-label`, `alt` |
| JS inline | stringhe-frase nei blocchi `<script>` |
| interpolate | stringhe con `{{ }}` / f-string dentro: candidate a `{% trans %}` / `ngettext` |
| plurali | stringhe con un conteggio: candidate a `ngettext` |
| fase | in quale fase di questo piano il file viene lavorato |

E, separatamente, due elenchi che servono subito:

1. **Le f-string nei messaggi utente** di `app.py`, `repository.py`,
   `oauth_server.py`, con numero di riga. Sono il lavoro più delicato della
   Fase 4 e vanno conosciute prima di spezzare le slice. Note già oggi:
   `app.py:1526`, `app.py:1997`, `app.py:2004`.
2. **Le stringhe di log** (`logger.*`) negli stessi file: vanno **escluse**,
   e l'elenco serve a non confonderle con i messaggi utente.

### Cosa l'audit NON fa

Non propone traduzioni, non modifica file, non esegue `pybabel` (non è ancora
installato in locale). Conta e classifica.

---

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A0.1 | Il gate §0.1 ha un esito scritto in questo file | lettura |
| A0.2 | Le versioni che andranno nei pin sono quelle **verificate sul server**, non le ultime di PyPI | lettura |
| A0.3 | Il virtualenv locale da usare è fissato in §0.2 | lettura |
| A0.4 | `inventario.md` esiste e copre **tutti** i 22 template e i 6 moduli Python | conteggio righe della tabella |
| A0.5 | L'inventario elenca `ps-oauth-consent.html` | grep — è il template reso dal blueprint `oauth_server.py`, quello che è sfuggito alla pianificazione del task19-0 fino alla Fase 9 |
| A0.6 | L'elenco delle f-string nei messaggi utente è completo e distinto da quello dei log | ispezione a campione su `app.py:1526` e `app.py:2741` |
| A0.7 | `git status` mostra **solo** file dentro `backlog/` | `git status --short` |

## Definition of done

Si sa se Flask-Babel si può usare, si sa con che versioni, si sa quante
stringhe sono e dove stanno. Nessuna riga di codice dell'applicazione è
cambiata.
