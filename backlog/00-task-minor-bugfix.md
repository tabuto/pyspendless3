# 00 - Task Minor / Bugfix

Registro **permanente** delle piccole evolutive e dei bug minori: interventi
troppo piccoli per meritare un file `taskN-0.md` dedicato, ma che vanno comunque
tracciati. Il file non si chiude mai: le voci nascono in "Aperte" e si spostano
in "Risolte" una volta completate.

Se una voce cresce fino a richiedere modifiche al modello dati, una migrazione o
più di 2-3 file, va promossa a task autonomo (`taskN-0.md`) e qui si lascia solo
il rimando.

## Convenzioni

- **ID**: `MB-NNN`, progressivo, mai riusato anche dopo la risoluzione.
- **Tipo**: `bug` (comportamento sbagliato) oppure `evolutiva` (comportamento
  corretto ma migliorabile).
- **Priorità**: `alta` / `media` / `bassa`.
- **Stato**: `APERTA` → `IN CORSO` → `RISOLTA` (oppure `SCARTATA`, con motivazione).

### Come aggiungere una voce

1. Aggiungere una riga in fondo all'**Indice**, con il primo ID libero.
2. Aggiungere il blocco di dettaglio in fondo alla sezione **Aperte**, copiando
   il template qui sotto.
3. Alla risoluzione: aggiornare lo stato nell'indice e **spostare** il blocco in
   **Risolte**, aggiungendo data e file effettivamente toccati.

```markdown
### MB-NNN — Titolo breve

- **Tipo**: bug | evolutiva
- **Priorità**: alta | media | bassa
- **Dove**: `percorso/file.ext` (riferimenti puntuali)

**Problema** — cosa succede oggi e perché è un problema.

**Proposta** — intervento concreto, ancorato al codice esistente.

**Note / casi limite** — cosa non rompere.
```

## Indice

| ID | Tipo | Descrizione | Priorità | Stato |
|----|------|-------------|----------|-------|
| MB-001 | evolutiva | Al salvataggio di un movimento portare il focus sul messaggio di successo | media | APERTA |
| MB-002 | evolutiva | Pannello filtri di "Vedi Movimenti" collassabile e chiuso di default | media | APERTA |
| MB-003 | evolutiva | Versione applicativa: variabile privata in `app.py`, API `/version`, visibile nel footer | bassa | APERTA |

## Aperte

### MB-001 — Focus sul messaggio di esito al salvataggio movimento

- **Tipo**: evolutiva
- **Priorità**: media
- **Dove**: `pyspendless/templates/ps-add-mov.html` — `#alert-container` (riga 14),
  `showAlert()` (riga 290), chiamate nel submit handler (righe 245, 277, 281)

**Problema**
`showAlert()` inserisce l'alert in `#alert-container`, che sta in cima alla
pagina, sopra la card del form. Il pulsante "Salva Movimento" è invece in fondo
(`card-footer`): su mobile, e su desktop con form lungo, dopo il submit l'utente
resta con la viewport sul pulsante e **non vede alcun feedback**. L'alert per
giunta si auto-nasconde dopo 5 secondi, quindi può sparire senza essere mai
stato letto. Il dubbio "ha salvato o no?" porta a doppi salvataggi.

**Proposta**
In `showAlert()`, subito dopo `alertContainer.appendChild(alert)`:

- rendere l'alert focalizzabile via `alert.setAttribute('tabindex', '-1')`;
- `alert.scrollIntoView({ behavior: 'smooth', block: 'center' })`;
- `alert.focus({ preventScroll: true })` così il messaggio è annunciato anche
  dagli screen reader e diventa il punto di ripartenza per la tastiera;
- aggiungere `aria-live="polite"` (e `aria-atomic="true"`) sul div
  `#alert-container` nel markup, in modo che la sostituzione del contenuto sia
  notificata anche quando il focus non si sposta.

**Note / casi limite**

- In creazione il form viene resettato dopo il salvataggio per inserire subito
  un altro movimento: da decidere se, passato l'alert, rimandare il focus sul
  primo campo utile (importo o data) invece di lasciarlo sull'alert. Da valutare
  con l'uso reale.
- In modalità "Ripeti" c'è già un redirect a `/movements` dopo 1 secondo
  (task17-0): lo scroll deve avvenire comunque, ma senza `behavior: 'smooth'`
  rischia di non completarsi prima della navigazione — verificare, eventualmente
  allungare il timeout o usare scroll istantaneo in quel ramo.
- L'auto-hide a 5 secondi resta: valutare se sospenderlo quando l'alert ha il
  focus, per non far sparire il messaggio mentre lo si sta leggendo.
- La stessa funzione `showAlert()` è duplicata in
  `pyspendless/templates/ps-search-mov.html` (riga ~194): decidere se allineare
  anche quella o limitare l'intervento al form.

### MB-002 — Pannello filtri collassabile e chiuso di default in "Vedi Movimenti"

- **Tipo**: evolutiva
- **Priorità**: media
- **Dove**: `pyspendless/templates/ps-show-mov.html` — card "Filtri" (righe 6-72)

**Problema**
La card dei filtri è sempre espansa e occupa due righe di form (date, wallet,
tipo, multi-select categorie, keywords). Su mobile riempie l'intera prima
schermata: KPI, grafico ed elenco movimenti — cioè il contenuto che si va
effettivamente a consultare — finiscono sotto la piega e richiedono uno scroll
lungo a ogni caricamento.

**Proposta**
Trasformare la card in un pannello collassabile con Bootstrap 5 Collapse, chiuso
di default. Bootstrap JS è già caricato in `ps-base.html` (riga 95) e le
Bootstrap Icons sono disponibili (riga 54), quindi non servono dipendenze nuove.

- `card-header`: diventa il toggle, con
  `data-bs-toggle="collapse" data-bs-target="#filters-collapse"`,
  `aria-expanded="false"` e `aria-controls="filters-collapse"`; usare un
  `<button type="button">` (o un `<a>`) e non un semplice `<div>` per avere
  accessibilità da tastiera. Aggiungere un chevron (`bi-chevron-down`) che ruota
  in base allo stato.
- `card-body`: avvolgere in `<div class="collapse" id="filters-collapse">`.

**Note / casi limite**

- **Responsive**: usare la classe `collapse` "nuda". Evitare varianti tipo
  `collapse d-md-block`, che su desktop terrebbero il pannello sempre aperto
  rompendo il toggle: il requisito è "chiuso di default" a *tutte* le larghezze.
- **Tom Select**: `#category_id` viene inizializzato nel `DOMContentLoaded`
  (riga ~340 circa) mentre il contenitore sarà `display: none`. L'init funziona,
  ma larghezza del controllo e posizionamento del dropdown possono risultare
  errati finché il pannello non viene mostrato la prima volta. Se succede,
  agganciarsi all'evento `shown.bs.collapse` del pannello per un refresh
  (`tsCategories.sync()` o re-init lazy alla prima apertura).
- **Filtri attivi**: con il pannello chiuso non si vede quali filtri sono in uso.
  Aprire il pannello di default quando la query string contiene filtri diversi
  dai default (Jinja può aggiungere la classe `show` in base a `filters`) e/o
  mostrare nell'header un badge con il numero di filtri attivi. I default sono
  calcolati in `_parse_movement_filters()` (`pyspendless/app.py:418`): dal primo
  del mese a oggi, nessun wallet, nessun tipo, nessuna categoria, nessuna keyword.
- Lo stato aperto/chiuso non va persistito: a ogni submit la pagina ricarica, e
  un eventuale `localStorage` andrebbe coordinato con il punto precedente.
- Intervento analogo possibile su `ps-search-mov.html`: fuori scope qui, aprire
  una voce dedicata se serve.

### MB-003 — Versione applicativa: variabile privata, API `/version`, footer

- **Tipo**: evolutiva
- **Priorità**: bassa
- **Dove**: `pyspendless/app.py` (header modulo, ~riga 27; context processor
  `inject_admin_status` riga 70), `pyspendless/templates/ps-base.html` — footer
  (righe 73-78)

**Problema**
Non esiste un numero di versione dell'applicazione: non è possibile sapere quale
build è in esecuzione su PythonAnywhere né correlarla a un tag/commit. Il footer
mostra solo `© 2026 PySpendless`.

**Proposta**
Una sola fonte di verità, letta sia dall'API sia dal template.

1. **Variabile privata in `app.py`** — subito dopo il setup del logger
   (`logger = logging.getLogger(__name__)`, riga 27):
   ```python
   _APP_VERSION = "0.1.0"   # semver; bump manuale a ogni release/tag
   ```
   Nome con underscore iniziale = "privato di modulo" (convenzione Python),
   coerente con la richiesta. Nessun import da file esterni.

2. **API REST `/version`** — endpoint pubblico (nessun `session.get('user_id')`),
   accanto agli altri `@app.route(...)`:
   ```python
   @app.route("/version", methods=['GET'])
   def version():
       """Ritorna la versione dell'applicazione."""
       return jsonify({"version": _APP_VERSION})
   ```
   > Nota convenzione: tutte le altre API stanno sotto `/api/...`
   > (`api_get_categories`, `api_get_movements`, ...). La richiesta parla di
   > `/version`: implementare `/version`, valutando in fase di PR se aggiungere
   > anche l'alias `/api/version` per uniformità. `jsonify` è già importato
   > (`app.py:6`).

3. **Footer** — esporre la versione ai template via il context processor già
   presente (`inject_admin_status`, `app.py:70`), senza ri-hardcodarla
   nell'HTML:
   ```python
   return {'is_admin': is_admin(), 'app_version': _APP_VERSION}
   ```
   In `ps-base.html`, footer:
   ```html
   <span class="text-muted">&copy; 2026 PySpendless &middot; v{{ app_version }}</span>
   ```

**Note / casi limite**

- `/version` deve restare raggiungibile **senza login**: verificare che non ci
  siano `before_request` che la intercettano. C'è `check_maintenance_mode`
  (`app.py:75`): decidere se in manutenzione `/version` risponde comunque
  (utile per i check esterni) aggiungendola all'allowlist del maintenance, o se
  è accettabile che venga bloccata.
- Il footer `{% block footer %}` è sovrascritto in alcuni template figli:
  cercare `{% block footer %}` nelle altre `templates/*.html` e allineare, o
  spostare la versione in un punto ereditato da tutti.
- La pagina di login/manutenzione usa `ps-base.html`? Se sì il `app_version` nel
  context processor è sufficiente; se qualche pagina non passa dal context
  processor (render statico), passarla esplicitamente nel `render_template`.
- Bump manuale: la variabile va aggiornata a mano prima di creare il tag `vX.Y.Z`
  usato dal deploy (task18-0). Fuori scope qui automatizzarlo (es. derivarla da
  `git describe`).
- Nessuna dipendenza nuova, nessuna modifica a modello dati o migrazioni.

## Risolte

_Nessuna voce risolta._

<!--
Formato delle voci risolte:

### MB-NNN — Titolo breve  ·  risolta il AAAA-MM-GG

- **Tipo**: bug | evolutiva
- **File toccati**: `percorso/file.ext`, ...

**Problema** — ...

**Soluzione** — cosa è stato fatto davvero (se diverso dalla proposta iniziale, dirlo).
-->
