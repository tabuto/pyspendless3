# Fase 1 — Infrastruttura e gate automatici

**Chi**: **agente principale** (opus/sonnet). **Non si delega.**
**Durata**: 1 giorno.
**Dipende da**: Fase 0 verde (o piano B scelto).
**Vincolo cardine della fase**: **nessuna stringa viene estratta.** Alla fine
l'app è identica a oggi, con l'infrastruttura di traduzione in piedi e un
catalogo vuoto che compila.

Perché non si delega: qui si scrive il **metro di misura** delle otto fasi
successive (`check-i18n.py`, `test_task25_0.py`). Delegare a haiku la scrittura
del proprio criterio di valutazione è il modo più diretto di ottenere criteri
che passano sempre.

---

## 1.1 Dipendenze

`pyspendless/requirements.txt`: aggiungere `Flask-Babel` e `Babel` **pinnati
alle versioni verificate sul server** in Fase 0 §0.1. Non `>=`, non liberi: il
server non ha una fase di build che risolva i conflitti, e un'installazione
riuscita in locale non è una prova.

In locale, installarli nel virtualenv fissato in Fase 0 §0.2.

## 1.2 `pyspendless/conf.py`

```python
# ===== LOCALIZZAZIONE (task25-0) =====
# Unica fonte di verità per le lingue supportate. Il <select> del profilo e la
# whitelist di validazione dell'API leggono da qui: una lingua in più si
# aggiunge in un punto solo.
DEFAULT_LOCALE = os.getenv('DEFAULT_LOCALE', 'it')
SUPPORTED_LOCALES = ('it', 'en_GB')
```

## 1.3 `pyspendless/i18n.py` (nuovo)

Il modulo che risolve le tre trappole di `en_GB` (specifica §5.7). Espone:

| Funzione | Cosa fa |
|---|---|
| `init_app(app)` | Inizializza `Babel(app, locale_selector=select_locale)`. Da chiamare in `app.py` subito dopo `app.secret_key`. |
| `select_locale()` | I cinque livelli della specifica §4.2, nell'ordine: `?lang=` → `session['locale']` → `User.locale` → `Accept-Language` → `DEFAULT_LOCALE`. |
| `normalize_locale(raw)` | `en`, `en-US`, `en-gb`, `en_GB` → `'en_GB'`; `it`, `it-IT` → `'it'`; tutto il resto → `None`. **Unico punto** in cui si converte fra la grafia dei browser e quella di Babel. |
| `locale_bcp47()` | `en_GB` → `en-GB`, per l'attributo `lang` dell'HTML. |
| `dt_locale()` | `en_GB` → `en-GB`, `it` → `it-IT`, per il nome del JSON di DataTables (Fase 5). |
| `locale_label(code)` | L'etichetta da mostrare nel `<select>`: `it` → "Italiano", `en_GB` → "English (UK)". |

Due vincoli non negoziabili:

1. **`select_locale()` non deve toccare il database** quando la sessione ha già
   `locale`, e **non deve toccarlo mai** se la richiesta è in manutenzione o su
   una pagina senza utente (specifica §5.5). In manutenzione il DB può essere
   indisponibile: una query lì trasforma la pagina di cortesia in un 500.
2. **Un `?lang=` non valido si ignora in silenzio.** Non si fa `abort(400)`,
   non si rimanda in pagina il valore ricevuto: è input non fidato e finirebbe
   in `<html lang>`.

## 1.4 `pyspendless/app.py` — tre punti, nient'altro

| Dove | Cosa |
|---|---|
| dopo `app.secret_key` (riga ~39) | `i18n.init_app(app)` |
| `inject_admin_status` (riga 93) | aggiungere `current_locale` (BCP-47), `current_locale_babel`, `dt_locale`, `supported_locales` al dizionario restituito |
| — | **niente altro.** I messaggi `flash`/`jsonify` sono Fase 4. |

## 1.5 `pyspendless/templates/ps-base.html`

Riga 35: `<html lang="it">` → `<html lang="{{ current_locale }}">`.

Solo questa. Le due stringhe di testo del footer e i `<meta>` descrittivi
arrivano in Fase 3.

## 1.6 `pyspendless/babel.cfg` (nuovo)

```ini
[python: **.py]
[jinja2: **/templates/**.html]
```

Pattern, **non elenchi di file**: un elenco scritto a mano dimenticherebbe
`ps-oauth-consent.html`, reso dal blueprint `oauth_server.py` registrato in
`app.py:64`. È esattamente l'errore che il task19-0 ha scoperto in Fase 9.

Da escludere: `templates/_styleguide.html` (pagina di sviluppo).

## 1.7 `tools/build-i18n.sh` (nuovo)

Sul modello di `tools/build-css.sh`, e con la stessa ragione d'essere: **sul
server non c'è una fase di build, quindi l'output compilato è versionato.**

```bash
pybabel extract -F pyspendless/babel.cfg -o pyspendless/translations/messages.pot pyspendless
pybabel update  -i pyspendless/translations/messages.pot -d pyspendless/translations
pybabel compile -d pyspendless/translations --statistics
```

Deve **fallire** se:

- `pybabel` non è nel virtualenv;
- un `.mo` non viene prodotto, o è più vecchio del `.po` corrispondente;
- git **ignora** i `.mo` (lo stesso controllo che `build-css.sh` fa sul CSS);
- `pybabel compile` segnala msgid fuzzy (sono traduzioni indovinate: in
  produzione sono peggio dell'italiano, perché sembrano giuste).

E deve **stampare le statistiche**: quante msgid tradotte su quante totali. È
l'unico modo di accorgersi di un catalogo incompleto prima del commit.

## 1.8 `tools/check-i18n.py` (nuovo) — il gate dei subagent

Due modalità.

**`--file <path>`** (quella che usano i subagent, sul proprio file e basta):

| Controllo | Fallisce quando |
|---|---|
| testo non avvolto | un template ha testo visibile fuori da `_()` / `{% trans %}` |
| f-string | c'è `_(f"..."` o una concatenazione dentro `_()` |
| placeholder | un placeholder è posizionale (`%s`) invece che nominale (`%(nome)s`) |
| igiene del msgid | spazi iniziali/finali, o tag HTML dentro il msgid |
| contenuto utente | `_()` avvolge un'espressione Jinja (`_(category.name)`) invece di un letterale |

**senza `--file`** (solo agente principale): tutto quanto sopra su tutto il
repo, più i controlli di catalogo — `.pot` allineato a un `extract` fresco,
msgid non tradotte per lingua con soglia, `.mo` non più vecchio del `.po`,
placeholder coerenti fra msgid e msgstr (un `%(num)d` perso in traduzione è un
`KeyError` in produzione).

Serve una **whitelist dei file non ancora lavorati**, sul modello di
`whitelist_non_migrati` di `test_task19_0.py`: all'inizio contiene tutti i
template, e l'**agente principale** la sfoltisce dopo il merge di ogni fase.
I subagent **non la toccano** — sedici modifiche da una riga allo stesso file
sono sedici conflitti (lezione A3.8 del task19-0).

## 1.9 `pyspendless/test/test_task25_0.py` (nuovo, gusci)

Struttura e convenzioni di `test_task23_0.py` (SQLite in-memory + Flask test
client + `session_transaction()`). In questa fase i test che possono già
passare:

- `normalize_locale` sui casi di §1.3, compresi `en-US` e un valore inventato;
- `locale_bcp47` e `dt_locale`;
- `<html lang>` = `it` di default;
- il catalogo vuoto compila e `gettext('Qualsiasi cosa')` restituisce il msgid;
- **i formati macchina**: l'export CSV ha l'header italiano e le date ISO. Va
  scritto **ora**, mentre è ancora verde per costruzione: è il criterio A6, e
  un test scritto dopo la rottura è un test scritto per passare.

Il resto (resolver completo, API della preferenza) arriva in Fase 2.

---

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A1.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce **0** | exit code — il contratto DOM non si muove |
| A1.2 | `.venv/bin/python -m pyspendless.test.test_task25_0` esce **0** | exit code |
| A1.3 | `./tools/build-i18n.sh` esce 0 e produce `translations/en_GB/LC_MESSAGES/messages.mo` | exit code + `ls` |
| A1.4 | `pybabel extract` trova **0 msgid** (nessuna stringa ancora avvolta) | statistiche della build |
| A1.5 | `tools/check-i18n.py` (modo completo) esce 0 con tutti i template in whitelist | exit code |
| A1.6 | `build-i18n.sh` **fallisce** se si cancella a mano un `.mo` | prova negativa: il gate deve mordere |
| A1.7 | `git check-ignore pyspendless/translations/en_GB/LC_MESSAGES/messages.mo` non trova nulla | i `.mo` sono versionabili |
| A1.8 | `/home`, `/movements`, `/settings/profile` rese identiche a prima | agente principale, Chrome |
| A1.9 | `<html lang="it">` nel sorgente reso; con `?lang=en_GB` diventa `en-GB` | `curl` + grep |
| A1.10 | `?lang=sconosciuto` non cambia nulla e non compare in pagina | `curl` + grep |
| A1.11 | Con `MAINTENANCE_MODE=1` la pagina di manutenzione risponde **503** e non fa query | agente principale |
| A1.12 | `git diff --stat` resta nell'elenco della Fase 1 (§6.4 del piano) | ispezione |

## Definition of done

L'infrastruttura c'è, i tre gate automatici mordono, e **l'app è identica a
oggi**. Il commit di questa fase è il prerequisito di tutte le altre: i
worktree dei subagent vedono solo file tracciati.
