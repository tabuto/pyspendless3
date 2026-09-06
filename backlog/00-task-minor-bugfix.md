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
| MB-001 | evolutiva | Al salvataggio di un movimento portare il focus sul messaggio di successo | media | RISOLTA |
| MB-002 | evolutiva | Pannello filtri di "Vedi Movimenti" collassabile e chiuso di default | media | RISOLTA |
| MB-003 | evolutiva | Versione applicativa: variabile privata in `app.py`, API `/version`, visibile nel footer | bassa | RISOLTA |

## Aperte

_Nessuna voce aperta._

## Risolte

### MB-001 — Focus sul messaggio di esito al salvataggio movimento · risolta il 2026-09-05

- **Tipo**: evolutiva
- **File toccati**: `pyspendless/templates/ps-add-mov.html`,
  `pyspendless/templates/ps-search-mov.html`

**Problema**
`showAlert()` inserisce l'alert in `#alert-container`, che sta in cima alla
pagina, sopra la card del form. Il pulsante "Salva Movimento" è invece in fondo
(`card-footer`): su mobile, e su desktop con form lungo, dopo il submit l'utente
resta con la viewport sul pulsante e **non vede alcun feedback**. L'alert per
giunta si auto-nasconde dopo 5 secondi, quindi può sparire senza essere mai
stato letto. Il dubbio "ha salvato o no?" porta a doppi salvataggi.

**Soluzione**
In `showAlert()` di `ps-add-mov.html`, dopo `alertContainer.appendChild(alert)`:

- `alert.tabIndex = -1` (focalizzabile da script, non raggiungibile con Tab);
- `alert.scrollIntoView({ block: 'center' })` + `alert.focus({ preventScroll: true })`;
- `aria-live="polite"` e `aria-atomic="true"` sul div `#alert-container`.

**Decisioni prese sugli attriti segnalati**

- **Modalità "Ripeti"**: `behavior` è condizionato a `isRepeat` — scroll
  istantaneo (`'auto'`) quando è previsto il redirect a `/movements` dopo 1s,
  `'smooth'` altrimenti. Così l'animazione non viene troncata dalla navigazione.
- **Auto-hide a 5 secondi**: mantenuto, ma sospeso mentre l'alert ha il focus.
  Il timer, alla scadenza, controlla `document.activeElement === alert` e in tal
  caso rimanda la chiusura al `blur` (listener `{ once: true }`), così il
  messaggio non sparisce mentre lo si sta leggendo.
- **Focus dopo il reset del form in creazione**: lasciato sull'alert, non
  spostato sul primo campo. Spostarlo avrebbe fatto perdere il messaggio agli
  screen reader subito dopo averlo annunciato; da rivalutare con l'uso reale.
- **`showAlert()` duplicata in `ps-search-mov.html`**: allineata, senza il ramo
  `isRepeat` che lì non esiste. Le due copie restano duplicate: fattorizzarle in
  un JS condiviso è un intervento a sé.

### MB-002 — Pannello filtri collassabile e chiuso di default in "Vedi Movimenti" · risolta il 2026-09-05

- **Tipo**: evolutiva
- **File toccati**: `pyspendless/templates/ps-show-mov.html`, `pyspendless/app.py`
  (`_parse_movement_filters()`, `movements()`)

**Problema**
La card dei filtri è sempre espansa e occupa due righe di form (date, wallet,
tipo, multi-select categorie, keywords). Su mobile riempie l'intera prima
schermata: KPI, grafico ed elenco movimenti — cioè il contenuto che si va
effettivamente a consultare — finiscono sotto la piega e richiedono uno scroll
lungo a ogni caricamento.

**Soluzione**
Card trasformata in pannello Bootstrap 5 Collapse, chiuso di default. Nessuna
dipendenza nuova: Bootstrap JS e Bootstrap Icons erano già in `ps-base.html`.

- `card-header`: `<button type="button">` con `data-bs-toggle="collapse"`,
  `data-bs-target="#filters-collapse"`, `aria-expanded` e `aria-controls`
  (accessibile da tastiera), con chevron `bi-chevron-down` che ruota via CSS su
  `[aria-expanded="true"]`.
- `card-body` avvolto in `<div class="collapse" id="filters-collapse">`.

**Decisioni prese sugli attriti segnalati**

- **Responsive**: usata la classe `collapse` "nuda", nessun `d-md-block`. Il
  pannello è quindi chiuso a tutte le larghezze e il toggle funziona ovunque.
- **Tom Select**: risolto alla radice con **init lazy** invece che con un
  refresh a posteriori. `tsCategories` parte a `null` e viene creato al primo
  `shown.bs.collapse`, quando il contenitore è visibile e le misure sono
  corrette. Caso limite gestito: se il pannello è già aperto al caricamento
  (filtri attivi) l'evento non scatterebbe mai, quindi si controlla
  `classList.contains('show')` e si inizializza subito. I click su
  "Seleziona tutto"/"Deseleziona" hanno un guard `if (!tsCategories) return;`
  anche se sono raggiungibili solo a pannello aperto.
- **Filtri attivi**: implementati entrambi i rimedi. `_parse_movement_filters()`
  calcola `active_count`, cioè quanti gruppi di filtri si discostano dai default
  (periodo diverso da "primo del mese → oggi", wallet, tipo, categorie,
  keywords); `movements()` lo passa nel dict `filters`. Il template aggiunge
  `show` al collapse e un badge con il conteggio nell'header quando è > 0.
  `active_count` è calcolato dentro `_parse_movement_filters()`, quindi resta
  allineato ai default anche se cambiano; la route di export ignora la chiave.
- **Persistenza dello stato**: non implementata, come da nota.
- **`ps-search-mov.html`**: non toccato, resta fuori scope.

### MB-003 — Versione applicativa: variabile privata, API `/version`, footer · risolta il 2026-09-05

- **Tipo**: evolutiva
- **File toccati**: `pyspendless/app.py`, `pyspendless/templates/ps-base.html`

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

**Soluzione**
Implementata come da proposta: `_APP_VERSION = "0.1.0"` subito dopo il logger in
`app.py`, endpoint pubblico `GET /version` che ritorna `{"version": ...}`,
`app_version` aggiunto al context processor `inject_admin_status` e footer di
`ps-base.html` che mostra `© 2026 PySpendless · v{{ app_version }}`.

**Decisioni prese sugli attriti segnalati**

- **Manutenzione**: `/version` è stata aggiunta all'allowlist di
  `check_maintenance_mode` insieme a `/health`
  (`if request.path in ('/health', '/version')`). Sapere quale build è in
  esecuzione serve soprattutto quando l'app è ferma.
- **Override del footer**: verificato con una ricerca su `templates/*.html` —
  `{% block footer %}` è definito **solo** in `ps-base.html` e nessun template
  figlio lo sovrascrive. Nessun allineamento necessario.
- **Pagine fuori dal context processor**: il context processor è globale
  sull'app, quindi copre anche login e manutenzione. Per sicurezza il footer usa
  comunque `{% if app_version %}`, così un eventuale render senza contesto
  degrada al solo copyright invece di stampare una stringa vuota.
- **Alias `/api/version`**: non aggiunto. La richiesta parlava di `/version` e un
  secondo endpoint identico andrebbe mantenuto in due posti; da riaprire come
  voce dedicata se emerge l'esigenza di uniformità.
- **Bump manuale**: resta manuale prima del tag `vX.Y.Z` (task18-0), come da nota.

<!--
Formato delle voci risolte:

### MB-NNN — Titolo breve  ·  risolta il AAAA-MM-GG

- **Tipo**: bug | evolutiva
- **File toccati**: `percorso/file.ext`, ...

**Problema** — ...

**Soluzione** — cosa è stato fatto davvero (se diverso dalla proposta iniziale, dirlo).
-->
