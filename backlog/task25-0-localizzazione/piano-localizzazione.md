# Piano di dettaglio — Localizzazione (task 25-0)

**Data**: 2026-10-19
**Specifica di riferimento**: `task25-spec.md` (in questa cartella). Le decisioni
sono là; qui c'è **chi fa cosa, in che ordine, e come si verifica**.
**Versione app di partenza**: `_APP_VERSION = "0.3.1"`
**Metodo**: dieci fasi, l'app funzionante alla fine di ognuna, il grosso del
lavoro delegato a subagent su **haiku**.

---

## 1. Le tre decisioni che hanno chiuso la pianificazione

| # | Decisione | Effetto sul piano |
|---|---|---|
| **P2** | L'inglese è **`en_GB`** | Date `19/10/2026`, importi `1,234.56`. Tre trappole tecniche (due grafie del codice, `Accept-Language`, whitelist) in `task25-spec.md` §5.7: tutte e tre si risolvono in `i18n.py`, Fase 1. |
| **P3** | DataTables **self-hostato** | Due JSON (~2 KB) in `static/js/i18n/`, scaricati dall'agente principale in Fase 5. Un subagent in worktree non ha rete utile: il download **non** si delega. |
| **P1** | Installabilità su PythonAnywhere = **gate bloccante** | È la Fase 0. Nessuna riga di codice prima che sia verde o che sia stato scelto il piano B. |

E una quarta, che riguarda il metodo:

| **Delega** | Lo sviluppo va a **subagent, preferibilmente haiku**. Questo piano è scritto per renderlo possibile: ogni fase delegata ha un criterio di "fatto" che è un **exit code**, non un giudizio. Vedi §4. |

---

## 2. Il gate (Fase 0) — perché viene prima di tutto

`Flask-Babel` e `Babel` sono **le prime dipendenze Python nuove dal task18-0**.
Il deploy è un `git pull` + Reload: non installa niente. Quindi:

- se le dipendenze non si possono installare sul server, l'app **non parte più**
  al primo deploy del task — `ImportError` su ogni pagina, fallimento **rotto**,
  non degradato;
- l'ostacolo più probabile **non è la rete** (da una console PythonAnywhere
  `pip` raggiunge PyPI anche sul piano gratuito) ma la **quota disco**: 512 MB
  su un virtualenv che ha già `matplotlib`, `fpdf2`, `SQLAlchemy` e `Authlib`.
  `Babel` porta i dati CLDR e non è piccolo.

Il gate ha due esiti, entrambi previsti:

- **verde** → si procede con Flask-Babel (D1 della specifica);
- **rosso** → si passa al **piano B**: `gettext` della standard library +
  estensione i18n di Jinja2 configurata a mano, `pybabel` solo come strumento
  locale, nomi dei mesi e formati scritti a mano per due lingue. **Il resto del
  piano non cambia**: cambiano `i18n.py` e `requirements.txt`, non le fasi, non
  i criteri, non i brief dei subagent. Il lavoro meccanico su 900 stringhe è
  identico nei due casi — ed è per questo che il gate può stare davanti a tutto
  senza bloccare la pianificazione.

Dettaglio operativo e comandi: `fasi/fase-0.md`. **Il gate lo esegue l'utente**
su una console PythonAnywhere: l'assistente non ha accesso al server.

---

## 3. Allocazione agenti e modelli

| Fase | Chi | Modello | Perché |
|---|---|---|---|
| 0 | utente (gate) + `ps-i18n-audit` (inventario) | **haiku** | Il gate è sul server. L'inventario è estrazione e conteggio in sola lettura. |
| 1 | **agente principale** | opus / sonnet | Qui si **progetta**: resolver, normalizzazione dei locale, script di build, test. È il lavoro che definisce i criteri di tutte le fasi dopo. Non si delega ciò che scrive il metro di misura. |
| 2 | 1 subagent | **sonnet** | Modello dati + API + sessione: tocca `app.py`, `models.py`, `repository.py` e i tre punti di login. Poche righe ma con il finding del task24-0 sul mass assignment da rispettare. |
| 3, 5, 6, 7 | 4+3+3+7 = **17 × `ps-i18n-template`** | **haiku** | È il cuore della delega: avvolgere ~650 stringhe in `_()` su 21 template. Lavoro meccanico, molto volume, criterio di fatto = exit code. |
| 4 | 6 × `ps-i18n-python` | **haiku**, con riserva | Avvolgere i messaggi di `app.py`/`repository.py`/`oauth_server.py` e convertire le f-string. Più delicato: le slice sono piccole e il gate è stretto (§4.3). Se una slice torna imprecisa, **si rilancia quella slice su sonnet** — non si riscrive la definizione. |
| 8 | 1 subagent | **sonnet** | Formati data/numero/valuta: il criterio "non ho toccato i formati macchina" è un test, ma la scelta di *quale* helper applicare *dove* richiede giudizio. |
| 9 | `ps-i18n-translate` + principale | **haiku** per la prima passata, revisione del principale | Tradurre 900 msgid con un glossario fisso (§8) è lavoro di volume; la coerenza terminologica la verifica il principale. |

**Regola di allocazione, ereditata dal RUNBOOK del task19-0 e qui ancora
valida**: haiku va bene quando *il criterio di "fatto" è un exit code*. Dove il
criterio è "sembra giusto", serve un modello più grande, o l'utente.

### Le tre definizioni di agente

Scritte direttamente in `.claude/agents/` (a differenza del task19-0, dove
andarono prima in `backlog/` e poi spostate a mano: la cartella è scrivibile):

| File | Agente | Tools | Modello |
|---|---|---|---|
| `.claude/agents/ps-i18n-template.md` | `ps-i18n-template` | Read, Edit, Grep, Glob, Bash | haiku |
| `.claude/agents/ps-i18n-python.md` | `ps-i18n-python` | Read, Edit, Grep, Glob, Bash | haiku |
| `.claude/agents/ps-i18n-audit.md` | `ps-i18n-audit` | Read, Grep, Glob | haiku |

`ps-i18n-audit` dichiara **solo tool di lettura**: come agente registrato *non
può* scrivere, ed è una garanzia utile in Fase 0 e in Fase 9, quando il suo
compito è dire la verità su cosa manca, non aggiustarlo.

Per la Fase 9 si riusa `ps-i18n-template` con un brief di traduzione, oppure si
aggiunge `ps-i18n-translate`: lo si decide alla Fase 9, quando si sa quante
msgid sono davvero (§8 del piano dipende dall'inventario della Fase 0).

---

## 4. Perché haiku può fare questo lavoro: i tre gate automatici

La delega sta in piedi solo se un subagent può **sapere da sé** di aver finito.
Tre meccanismi, tutti costruiti in Fase 1 **prima** che parta la prima delega.

### 4.1 Il contratto DOM del task19-0, riusato tale e quale

`pyspendless/test/test_task19_0.py` congela id, `name` dei form, `href` e
alcune **stringhe letterali** di ogni pagina. Normalmente un refactoring di i18n
lo romperebbe — ma qui no, e per una ragione precisa: **i msgid sono in
italiano** (D2) e `it` è la lingua di default, quindi senza catalogo `gettext`
restituisce il msgid e la pagina resa in italiano è **carattere per carattere
quella di prima**.

Il contratto diventa così la prova dell'isofunzionalità (criterio A1) a costo
zero. Vale però solo se i test girano con `it`: in Fase 1 va fissato
`DEFAULT_LOCALE = 'it'` e verificato che il test client non erediti un
`Accept-Language` diverso.

> Corollario operativo: **un subagent non modifica mai `test_task19_0.py`.** Se
> il contratto si rompe, ha cambiato il testo reso — cioè ha sbagliato il
> wrapping (spazi dentro il msgid, stringa spezzata, apostrofo mangiato).

### 4.2 `tools/check-i18n.py --file <path>`

Scritto in Fase 1. Dato **un** file, esce 0 se:

- nessun testo visibile fuori da `_()` / `{% trans %}` (per i template);
- nessuna f-string e nessuna concatenazione dentro una chiamata a `_()`;
- i placeholder sono nominali (`%(nome)s`), non posizionali;
- ogni msgid è "pulito": niente spazi iniziali/finali, niente tag HTML dentro.

È il metro che il subagent usa sul **proprio** file, senza sapere nulla del
resto del repo. Senza `--file` controlla tutto e aggiunge i controlli di
catalogo (§4.4), e quello lo esegue solo l'agente principale.

### 4.3 `pyspendless/test/test_task25_0.py`

Scritto in Fase 1 (gusci) e completato in Fase 2. Copre il resolver, l'API della
preferenza, `<html lang>`, e soprattutto i **formati macchina** (criterio A6:
header CSV e date ISO invariati anche con `en_GB` attivo). Per le fasi 4 e 8 è
il gate principale.

### 4.4 Quello che i subagent NON eseguono

| Comando | Perché solo il principale |
|---|---|
| `./tools/build-i18n.sh` | Scrive in `translations/`: un file condiviso. Diciassette subagent in parallelo che lo rigenerano = diciassette conflitti certi. **`translations/` ha un solo scrittore: l'agente principale, dopo il merge di ogni fase.** È la stessa lezione di A3.8 del task19-0 (la whitelist del test la sfoltiva il principale, non i quattro subagent). |
| `tools/check-i18n.py` senza `--file` | Controlla i cataloghi, che il subagent non ha rigenerato: fallirebbe per colpa di altri. |
| Qualsiasi apertura del browser | Flask gira dal checkout principale, non dai worktree. Un subagent che verificasse in Chrome guarderebbe il codice sbagliato. |
| `git commit`, `git tag`, `git push` | Regola non negoziabile di `CLAUDE.md`. Vale per tutti, subagent compresi. |

---

## 5. Le regole di wrapping (il contenuto meccanico della delega)

Sono la parte che finisce nelle definizioni degli agenti. Qui per riferimento
umano.

```jinja
Testo semplice        <h5>Profilo</h5>            →  <h5>{{ _('Profilo') }}</h5>
Attributo             placeholder="Es. Casa"      →  placeholder="{{ _('Es. Casa') }}"
Con interpolazione    Trovati {{ n }} movimenti   →  {% trans n=n %}Trovati {{ n }} movimenti{% endtrans %}
Con markup interno    Serve <strong>un wallet</strong> →  {% trans %}...{% endtrans %} (trimmed)
Nel JS inline         const l = ['Entrate',...]   →  const l = ['{{ _('Entrate') }}', ...]
```

Cinque divieti, ognuno nato da un modo concreto di sbagliare:

1. **Gli spazi stanno fuori dal msgid.** `{{ _(' Salva ') }}` crea un msgid con
   gli spazi dentro: due msgid diversi per la stessa parola, e il traduttore ne
   perde uno. Si scrive `{{ _('Salva') }}` e lo spazio resta nel markup.
2. **Niente tag HTML dentro `_()`.** Un `<br>` nel msgid finisce nel catalogo e
   il traduttore può cancellarlo. Si spezza la stringa, o si usa `{% trans %}`.
3. **Niente f-string, niente concatenazione.** `_(f'...')` cerca nel catalogo la
   stringa *già interpolata*: non la trova mai. Placeholder **nominali**.
4. **Non si traduce il contenuto dell'utente.** Nessun `_()` attorno a
   `{{ category.name }}`, `{{ mov.note }}`, `{{ wallet.name }}`.
5. **Non si traduce, si avvolge.** L'inglese arriva in Fase 9, dal catalogo. Un
   subagent che scrive testo inglese nel template ha fatto un danno che il
   contratto DOM becca subito (il testo reso in `it` è cambiato).

E una cosa che **non** va toccata, mai: i messaggi di `logger.*`. Non sono
interfaccia.

---

## 6. Orchestrazione

Le regole del `RUNBOOK.md` del task19-0 valgono, **comprese le correzioni** che
quel task ha pagato per imparare. Le tre che contano qui:

### 6.1 L'isolamento si passa all'invocazione

`isolation: worktree` nel frontmatter della definizione **non basta** — nel
task19-0 quattro `ps-markup` che lo dichiaravano hanno scritto tutti nel
checkout principale. Va passato **a ogni chiamata**, agente per agente.

### 6.2 Quindi: un commit per fase è obbligatorio, non consigliato

Un `git worktree` contiene solo i file **tracciati**. Se la Fase 1 non è
committata, i diciassette subagent delle fasi 3-7 non vedono `i18n.py`, non vedono
`babel.cfg`, e `tools/check-i18n.py` non esiste: il loro criterio di rilascio
non parte nemmeno. Chiude il punto P5 della specifica: **la granularità è per
fase**, e il commit è un prerequisito della fase successiva, non una scelta
stilistica.

> Resta fermo che il commit **lo chiede l'utente** (`CLAUDE.md`). L'assistente
> arriva alla fine della fase, mostra il diff, e si ferma.

E il primo comando di ogni subagent in worktree resta:

```bash
./tools/worktree-bootstrap.sh --test
```

che collega `pyspendless/.env` (non tracciato, quindi assente dal worktree),
sceglie fra i due virtualenv del repo quello che ha Flask, ed esegue il
contratto. Nel checkout principale è un no-op.

### 6.3 File disgiunti, o niente parallelismo

Nelle fasi 3, 5, 6, 7 i subagent lavorano **un template per invocazione**, e i
template sono disgiunti per costruzione. Nella Fase 4 le slice di `app.py` sono
**intervalli di righe dello stesso file**: lì il parallelismo è pericoloso
(l'editing di una slice sposta le righe delle altre) e le invocazioni vanno
**in sequenza**, rileggendo il file ogni volta. È la differenza più importante
fra la Fase 4 e tutte le altre.

### 6.4 Gate sul diff, a ogni fase

```bash
git diff --stat
```

| Fase | Può toccare |
|---|---|
| 1 | `requirements.txt`, `babel.cfg`, `i18n.py`, `conf.py`, `app.py` (solo init + context processor), `templates/ps-base.html`, `translations/**`, `tools/**`, `test/**` |
| 2 | `models.py`, `repository.py`, `app.py`, `templates/ps-setting-profile.html`, `templates/ps-nav.html`, `sql/sqllite/NEXT_RELEASE/**`, `test/**` |
| 3, 5, 6, 7 | **solo** `pyspendless/templates/**` (+ `static/js/i18n/**` nella 5) |
| 4 | **solo** `pyspendless/app.py`, `repository.py`, `oauth_server.py` |
| 8 | `i18n.py`, `report_pdf.py`, `report_charts.py`, `repository.py`, `templates/**` |
| 9 | `translations/**`, `docs/**`, `backlog/**`, `CLAUDE.md`, `README.md`, `.gitignore` |

Se nelle fasi 3-7 compare un file fuori elenco → **stop**. In particolare: un
subagent `ps-i18n-template` che ha toccato `translations/` ha violato la regola
del singolo scrittore (§4.4), e il merge della fase va rifatto.

### 6.5 Un solo Chrome, e lo guida il principale

La verifica visiva è **sempre seriale** e sempre dell'agente principale, dopo
il merge. Mai `isolation: "remote"`: un subagent su un'altra macchina non vede
né il `localhost` né il repo in lavorazione.

---

## 7. Fasi e dipendenze

```
Fase 0  gate + inventario          (nessun codice)
   │
Fase 1  infrastruttura + gate automatici      ← principale, non delegata
   │                                            commit obbligatorio
   ├── Fase 2  preferenza utente    (1 × sonnet)
   │      │
   │      └── Fase 3  shell e accesso          (4 × haiku, parallelo)
   │             │
   │             ├── Fase 5  movimenti         (3 × haiku, parallelo)
   │             ├── Fase 6  dashboard/report  (3 × haiku, parallelo)
   │             └── Fase 7  impostazioni      (7 × haiku, parallelo)
   │
   └── Fase 4  messaggi Python      (6 × haiku, SEQUENZIALI)   ← indipendente da 2
          │
       Fase 8  formati e PDF        (1 × sonnet)
          │
       Fase 9  traduzione en_GB + QA + docs
```

La Fase 4 non dipende dalla 2 né dalla 3: tocca solo Python. Può girare **in
parallelo alla 3**, purché il gate sul diff (§6.4) tenga separati gli insiemi
di file — ed è il modo più efficace di accorciare il calendario.

Le fasi 5, 6 e 7 dipendono dalla 3 solo perché la 3 è il collaudo del metodo:
se quattro haiku su otto template semplici tornano con lavoro pulito, le
tredici invocazioni successive sono prevedibili. Se tornano sporche, si corregge
la definizione dell'agente **prima** di moltiplicarla per tredici.

---

## 8. Glossario terminologico `it → en_GB` (bozza, punto P7)

Da confermare prima della Fase 9. Vive in `translations/GLOSSARIO.md` e viene
citato nel brief dell'agente di traduzione.

| Italiano | `en_GB` | Nota |
|---|---|---|
| movimento | **transaction** | Non "movement": in un'app di spese inglese la parola è *transaction*. |
| entrata | **income** | |
| uscita / spesa | **expense** | Una sola parola inglese per le due italiane: coerenza > letteralità. |
| wallet | **wallet** | Resta: è già inglese nell'originale e nel modello dati. |
| categoria | **category** | |
| ricorrente | **recurring** | Non "recurrent". |
| wallet preferito | **default wallet** | "Preferred" in inglese suona come un gusto; qui è il wallet proposto per primo. |
| gruppo | **group** | |
| invito | **invitation** | |
| impostazioni | **settings** | |
| profilo | **profile** | |
| riepilogo | **summary** | |
| saldo | **balance** | |
| importo | **amount** | |
| nota | **note** | |
| token personale | **personal token** | |
| connessione (OAuth) | **connection** | |
| manutenzione | **maintenance** | |
| Genera | **Generate** | |
| Salva / Annulla / Elimina | **Save / Cancel / Delete** | Mai "Remove" per Elimina: l'azione è distruttiva. |

Regola generale: **sentence case** nei bottoni e nei titoli (`Add transaction`,
non `Add Transaction`), coerente con l'italiano attuale.

---

## 9. Rilascio

Alla fine della Fase 9, se l'utente lo chiede, la procedura di `CLAUDE.md` con
**due passi in più**:

- **0-bis**, in locale, accanto a `./tools/build-css.sh`:

  ```bash
  ./tools/build-i18n.sh
  ```

  e verifica che i `.mo` siano aggiornati e **staged**. Se dopo la build
  `git status` non è pulito, il commit era incompleto — identico al CSS.

- **nel passo 5**, sul server, **una volta sola** e **prima** del Reload:

  ```bash
  cd /home/tabuto/pyspendless3
  pip install -r pyspendless/requirements.txt
  ```

  Senza questo, il Reload mette in produzione un'app che non importa.

Versione: il task vale un **minor** (`0.4.0`): aggiunge una colonna, una rotta
e una preferenza utente. Il bump lo decide l'utente.

---

## 10. Come avviare la sessione

**Dall'app desktop sul Mac**, non dal telefono: i file locali e il browser
passano da lì. Modello della sessione principale: **opus** o **sonnet** — è
l'unica che vede il risultato visivo e decide sui punti aperti.

Prerequisiti, oltre a quelli del `RUNBOOK.md` del task19-0 (app su
`localhost:5000`, login Google già fatto in Chrome, Mac sveglio, DB di sviluppo
popolato):

- **il gate della Fase 0 eseguito**, con l'esito scritto in `fasi/fase-0.md`;
- le tre definizioni in `.claude/agents/` visibili come tipi di agente in una
  sessione nuova (`ps-i18n-template`, `ps-i18n-python`, `ps-i18n-audit`).

Prompt di avvio:

```
Leggi backlog/task25-0-localizzazione/task25-spec.md e
backlog/task25-0-localizzazione/piano-localizzazione.md.
Il gate della Fase 0 è verde (vedi fasi/fase-0.md).
Partiamo dalla Fase 1: fasi/fase-1.md. La Fase 1 la fai tu, non delegarla.
L'app gira su http://localhost:5000, sono già loggato in Chrome.
Non passare alla fase successiva senza avermi mostrato i criteri di
accettazione soddisfatti e il diff.
```
