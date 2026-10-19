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
| MB-004 | evolutiva | Gestione del wallet preferito (`order_index = 0` riservato, unico, impostabile solo dall'azione dedicata) | media | RISOLTA |
| MB-005 | evolutiva | Il server MCP usa il wallet preferito quando la chiamata non ne specifica uno (dipende da MB-004) | bassa | RISOLTA |
| MB-006 | bug | La tabella movimenti ordina le date per giorno del mese: DataTables confronta `gg/mm/aaaa` come stringa | media | RISOLTA |
| MB-007 | bug | Una categoria cambia colore fra la dashboard mensile e quella annuale: la palette è assegnata per posizione | bassa | RISOLTA |
| MB-008 | evolutiva | Subset di Bootstrap Icons: 59 glifi su 2.078, da 221 KB a 8 KB (font + CSS) | media | RISOLTA |
| MB-009 | evolutiva | Icone: togliere il fallback `.woff` (180 KB, mai scaricato) e aggiungere lo script che rigenera il subset | bassa | APERTA |

## Aperte

### MB-009 — Icone: fallback `.woff` residuo e script di rigenerazione del subset

- **Tipo**: evolutiva
- **Priorità**: bassa
- **Dove**: `pyspendless/static/fonts/ps-icons.woff`,
  `pyspendless/static/css/ps-icons.css` (clausola `src:`), `tools/` (nuovo script).
- **Origine**: strascico di MB-008.

**Problema** — due cose rimaste fuori da MB-008, volutamente:

1. `ps-icons.woff` pesa ancora **180.288 byte** ed è il set completo (2.078
   glifi). Nessun browser attuale lo scarica, perché tutti supportano `woff2`,
   ma resta nel repo, e il `src:` del CSS continua a citarlo.
2. Il subset è stato generato a mano. Il `.woff2` e il CSS contengono solo i 59
   glifi usati: **aggiungere un'icona `bi-*` non presente nel subset la mostra
   vuota**, senza errori in console né 404. Chi aggiunge un'icona non ha alcun
   segnale.

**Proposta**

1. Cancellare `ps-icons.woff` e togliere `,url("../fonts/ps-icons.woff") format("woff")`
   dal `src:` di `ps-icons.css`.
2. Script `tools/build-icons.sh` (o `.py`) che: censisce le classi `bi-*`
   usate in `templates/`, `static/js/` e nei `.py`; le mappa ai codepoint;
   genera `ps-icons.woff2` con `pyftsubset` e riscrive `ps-icons.css`, sul
   modello di `tools/build-css.sh`. Come in `build-css.sh`, deve **fallire**
   se una classe usata non esiste nel set completo, o se l'output è
   anormalmente piccolo.
3. Decidere dove vive il font completo, fonte dello script: oggi sta solo nella
   cronologia git (fino al commit `726cd6f`, versione Bootstrap Icons 1.13.1).
   Alternative: scaricarlo da npm (`bootstrap-icons@1.13.1`) dentro lo script,
   oppure versionarlo fuori da `static/` (~134 KB, non servito).
4. Eventuale controllo in `pyspendless/test/`: ogni classe `bi-*` referenziata
   nei template è definita in `ps-icons.css`.

**Note / casi limite**

- Il controllo del punto 4 è quello che chiude davvero il rischio del punto 2:
  lo script rigenera, il test avvisa se ci si è dimenticati di lanciarlo.
- `bi-chevron-right` / `bi-chevron-down` compaiono in `ps-nav.html` anche come
  stringhe passate a `classList.add/remove`, non solo in `class="..."`: il
  censimento deve cercare `bi-[a-z0-9-]+` ovunque, non solo negli attributi.

### MB-008 — Subset di Bootstrap Icons · risolta il 2026-10-18

- **Tipo**: evolutiva
- **Priorità**: media
- **Dove**: `pyspendless/static/fonts/ps-icons.woff2`,
  `pyspendless/static/css/ps-icons.css`.
- **Origine**: indicata in `task19-0.md` ("Misura finale") come il primo
  guadagno di peso rimasto dopo il restyling.

**Problema** — D9 del task19-0 aveva self-ostato Bootstrap Icons 1.13.1 **senza
farne un subset**: `ps-icons.css` definiva 2.078 glifi, i template e il JS ne
usano 59. La pagina caricava il 97% di un set senza usarlo, e le icone erano
la risorsa più pesante: 36,5% del peso, più del framework CSS.

**Soluzione applicata** — subset a 59 glifi, generato con `pyftsubset`
(fonttools) a partire dal `woff2` completo:

- Censimento delle classi `bi-*` in `templates/`, `static/js/` e nei `.py`:
  **59**, tutte presenti nel set. Nessuna composta a runtime (le sole
  manipolazioni dinamiche sono `chevron-right`/`chevron-down` in `ps-nav.html`).
- Font: `--unicodes=<59 codepoint> --flavor=woff2 --layout-features='' --no-hinting
  --desubroutinize`. Senza ligature e senza hinting, che un font di icone non usa.
- CSS: regola base `.bi::before` e le sole 59 regole `.bi-xxx::before`.

| File | Prima | Dopo |
|---|---|---|
| `ps-icons.woff2` | 134.044 B | **5.220 B** |
| `ps-icons.css` | 86.934 B | **2.951 B** |
| **totale** | **220.978 B** | **8.171 B** (-96%) |

**Verifica**

- Contorni e larghezze dei 59 glifi **identici** all'originale (confronto con
  `RecordingPen`: 0 differenze su 59); `unitsPerEm` e ascent invariati, quindi
  nessuno spostamento verticale delle icone.
- Ogni classe usata è definita nel CSS, ogni codepoint del CSS esiste nel font.
- Nel browser: font caricato a 5.220 byte, 59 icone renderizzate, nessun 404.
  Non sono state riaperte le 18 pagine dietro login.

**Note / casi limite**

- **Aggiungere un'icona richiede di rigenerare il subset**: una `bi-*` fuori
  dai 59 si vede vuota, senza errori. Vedi MB-009.
- `ps-icons.woff` (180 KB, set completo) **non è stato toccato**: nessun
  browser attuale lo scarica. Vedi MB-009.
- Il **guadagno arriva solo dopo il bump di `_APP_VERSION`**: il CSS è
  referenziato con `?v={{ app_version }}`, e finché la versione non cambia i
  browser con la cache calda continuano a usare CSS e font vecchi. Sono
  comunque coerenti fra loro, quindi nessun glifo si rompe.
- Il CSS compilato di Tailwind non è coinvolto: `build-css.sh` non serve.

### MB-007 — Colori delle categorie incoerenti fra le dashboard · risolta il 2026-10-18

- **Tipo**: bug
- **Priorità**: bassa
- **Dove**: `pyspendless/templates/ps-dashboard-monthly.html` e
  `ps-dashboard-yearly.html`, funzione `psCategoryColor()`.
- **Trovata**: misurando la baseline dei grafici prima della conversione della
  Fase 8 del task19-0.

**Problema** — il colore di una fetta veniva scelto con
`COLORS[i % COLORS.length]`, dove `i` è la **posizione** dell'etichetta
nell'array. Le due dashboard ordinano le categorie per importo, e gli importi
di un mese non sono quelli di un anno: la stessa categoria finiva quindi in
posizioni diverse, e cambiava colore passando da un grafico all'altro.

Misurato sul DB di sviluppo: su **17 categorie presenti in entrambe le
dashboard, 13 avevano un colore diverso**.

| Categoria | mensile | annuale |
|---|---|---|
| Altro | `#FF6384` | `#FFCE56` |
| Food And Drink | `#9966FF` | `#4BC0C0` |
| Household | `#C9CBCF` | `#36A2EB` |

Confrontare la torta mensile con quella annuale era fuorviante: due fette
dello stesso colore non erano la stessa categoria.

**Soluzione applicata** — il colore dipende dal **nome** della categoria:

```js
function psCategoryColor(nome) {
  var h = 0;
  for (var i = 0; i < nome.length; i++) h = (h * 31 + nome.charCodeAt(i)) >>> 0;
  return COLORS[h % COLORS.length];
}
```

Stessa funzione nei due file, quindi la mappa categoria → colore è identica
ovunque, e stabile anche fra un mese e l'altro. Dopo la correzione le
discordanze sono **0 su 17**.

**Note / casi limite**

- La palette ha **7 tinte distinte in 10 posizioni** (le posizioni 0 e 6, 3 e
  8, 5 e 9 sono uguali), quindi con 17 o 27 categorie **le collisioni dentro
  lo stesso grafico restano inevitabili**. Misurate prima di applicare: da 10
  a 11 collisioni sul grafico mensile, da 20 a 21 sull'annuale. La correzione
  non peggiora la distinguibilità interna in modo apprezzabile, e in cambio
  rende il colore stabile fra i grafici. Se un giorno si vorranno fette tutte
  distinte, serve una palette più ampia — è un intervento diverso.
- I **totali dei nove grafici sono invariati**: la correzione tocca solo la
  scelta del colore.
- Tenuta **separata dalla Fase 8** di proposito: è una correzione di
  comportamento, non di presentazione. Se qualcosa si rompe nei grafici, i due
  commit restano distinguibili.

### MB-006 — Ordinamento per data della tabella movimenti · risolta il 2026-10-17

- **Tipo**: bug
- **Priorità**: media
- **Dove**: `pyspendless/templates/ps-show-mov.html:194` (cella della colonna
  "Data"); configurazione DataTables alla riga 323 dello stesso file.
- **Trovata**: verifica empirica 0.4 della Fase 0 del task19-0.

**Problema** — la colonna "Data" è renderizzata `gg/mm/aaaa`. DataTables ne
rileva il tipo automaticamente, il plugin `date-eu` non è caricato e
`Date.parse("13/09/2026")` dà `NaN`: il tipo ricade quindi su `string` e
`order: [[0, 'desc']]` produce un **confronto lessicografico**, cioè un
ordinamento per giorno del mese, poi mese, poi anno.

Il difetto è rimasto invisibile perché la vista di default filtra il **mese
corrente**, e dentro un singolo mese l'ordine per giorno coincide con quello
cronologico. Si manifesta appena si allarga l'intervallo:

| Intervallo | Prime righe a video | Corretto? |
|---|---|---|
| solo settembre 2026 | 30/09, 30/09, 29/09, 29/09, 28/09 … | sì, per caso |
| ago-ott 2026 | **31/08**, 31/08, 31/08, 30/09, 30/09, **30/08**, 29/09 … | no |
| 2025-2026 | **31/10/2025**, 31/10/2025, **31/08/2026**, 31/08/2025 … | no |

Su due anni di dati 247 righe su 257 risultavano fuori posto. Il server
ordina già correttamente (`move_date DESC`, `repository.py:611`): il
riordino sbagliato è interamente client-side, quindi la card-list mobile —
renderizzata da Jinja senza DataTables — non ne era affetta.

**Soluzione applicata** — attributo `data-order` con la data in formato ISO
sulla cella, che DataTables usa come dato di ordinamento al posto del testo
visualizzato:

```jinja
<td data-order="{{ mov.move_date.isoformat() }}">{{ mov.move_date.strftime('%d/%m/%Y') }}</td>
```

Una riga, nessuna dipendenza aggiunta, nessun plugin da caricare. Dopo la
modifica il tipo rilevato da DataTables passa da `string` a `date` e l'ordine
a video coincide esattamente con quello del server su tutti e tre gli
intervalli di prova.

**Note / casi limite**

- Le colonne "Entrata" e "Uscita" rendono `€ 1234.56` e **non** hanno il
  problema: DataTables le rileva come `num-fmt,` e le ordina correttamente.
  Verificato ordinando per "Uscita" e confrontando con `ORDER BY expense DESC`.
- Il formato visualizzato non cambia: resta `gg/mm/aaaa`.
- `data-order` va conservato dalla Fase 6 del task19-0, che riscrive questa
  tabella. È il motivo per cui la correzione è stata tenuta **separata** dal
  restyling invece di esserne assorbita.

### MB-004 — Gestione del wallet preferito · risolta il 2026-09-12, integrata il 2026-09-14

- **Tipo**: evolutiva
- **File toccati**: `pyspendless/repository.py` (`WalletRepository`),
  `pyspendless/app.py` (`api_get_wallets`, `api_create_wallet`, `api_update_wallet`,
  `api_set_preferred_wallet`, `api_unset_preferred_wallet`, `create`),
  `pyspendless/templates/ps-setting-wallet.html`, `pyspendless/templates/ps-add-mov.html`

**Problema**
Non esisteva il concetto di wallet preferito. Il "default" era implicito e
posizionale: `get_wallets_for_account` ordina per `order_index` poi per nome, e
chi consumava la lista trattava il primo elemento come predefinito. Per cambiare
wallet di default bisognava riordinare gli altri, e l'intenzione ("questo è
quello che uso quasi sempre") non era espressa da nessuna parte.

**Soluzione**
Preferenza resa esplicita **senza toccare lo schema**, come da proposta.

- `WalletRepository.PREFERRED_ORDER_INDEX = 0` più `get_preferred_wallet()` e
  `set_preferred_wallet()`: sono l'**unico punto del codice che conosce la
  convenzione**. `get_preferred_wallet` ordina per `order_index` poi per nome, così
  resta deterministico anche con più wallet a indice 0 per dati storici, e
  restituisce `None` se l'account non ha wallet. `set_preferred_wallet` porta il
  wallet scelto a 0 e ricompatta gli altri da 1 conservandone l'ordine relativo.
- Nuova API `PUT /api/wallets/<id>/preferred`, con i controlli di appartenenza
  all'account già usati dalle altre rotte wallet.
- `GET /api/accounts/<id>/wallets` espone `is_preferred`; in
  `ps-setting-wallet.html` badge "Preferito" e pulsante "Imposta come preferito"
  (nascosto sulla card già preferita).
- `create()` passa `preferred_wallet_id` a `ps-add-mov.html`, che rende
  `selected` l'option corrispondente.

**Requisiti aggiuntivi recepiti il 2026-09-14**

Lo 0 diventa un indice **riservato**, non un semplice "primo della lista":

1. l'utente **non può impostare `order_index = 0`** da nessuna UI o API di
   modifica: la validazione lo rifiuta;
2. lo 0 è assegnato **solo** dall'azione "imposta come preferito";
3. **unicità garantita**: promuovere un wallet declassa quello che era preferito,
   non possono esistere due wallet a 0;
4. **togliere la preferenza** porta il wallet a `order_index = 1`.

Implementazione:

- `WalletRepository.MIN_USER_ORDER_INDEX = 1` e `validate_order_index()`, che
  solleva `ValueError` sotto quella soglia. È invocata da `update_wallet()` e da
  `create_wallet()`; `api_update_wallet` / `api_create_wallet` traducono
  l'eccezione in **400** con il messaggio.
- `get_preferred_wallet()` **riscritta**: filtra `order_index == 0` e ritorna
  `None` se non c'è. Non ripiega più sul primo della lista, perché ora "nessun
  preferito" è uno stato che deve essere distinguibile.
- `set_preferred_wallet()` declassa a 1 il preferito uscente (e gli eventuali
  duplicati storici a 0) prima di promuovere il nuovo: l'unicità è garantita
  dall'operazione stessa. Non ricompatta più tutti gli indici.
- Nuova `unset_preferred_wallet()` + `DELETE /api/wallets/<id>/preferred`, con
  pulsante "Rimuovi preferito" sulla card del preferito.
- `create_wallet()`: il primo wallet di un account parte da **1**, non più da 0
  (prima un account nuovo si ritrovava un preferito senza averlo mai scelto).
- Modale di modifica: `min="1"`, testo esplicativo sullo 0 riservato, e sul
  wallet preferito il campo Ordine è disabilitato e l'`order_index` non viene
  nemmeno inviato.

**Decisioni prese sugli attriti segnalati**

- **Conflitto con "ultimo wallet usato" — decisione ribaltata il 2026-09-14.**
  Nella prima stesura la preselezione da `localStorage['ps_last_wallet_id']` era
  stata **rimossa**, perché con la vecchia convenzione un preferito esisteva
  sempre e i due default si sarebbero sempre contesi la select. Con lo 0
  riservato, "nessun preferito" è ora rappresentabile, quindi i due meccanismi
  non competono più: sono una **catena di ripiego**. La preselezione è stata
  quindi **ripristinata**, subordinata al preferito. Ordine dei default nel form:
  1) wallet del movimento sorgente (modifica/ripeti), 2) wallet preferito,
  3) ultimo wallet usato su quel browser. Il punto 3 si applica solo se non
  esiste un preferito; la scrittura su `localStorage` avviene sempre, così il
  ripiego è pronto se in seguito la preferenza viene rimossa.
- **Ordine visualizzato**: invariato. Promuovere un wallet cambia solo l'indice
  del promosso e del declassato, quindi filtri di "Vedi Movimenti" ed elenco
  wallet non si riordinano oltre il voluto. Nota: il declassato va a 1 e può
  quindi pareggiare con un altro wallet già a 1 — i pari merito restano ordinati
  per nome, come già faceva `get_wallets_for_account`. Solo lo 0 è unico.
- **Colonna dedicata (`Wallet.is_default`)**: non introdotta, avrebbe richiesto
  `ALTER TABLE` e migrazione sul server, promuovendo la voce a task. Se servirà,
  è sufficiente riscrivere il blocco "preferito" del repository.
- **Dati storici**: gli account esistenti hanno già un wallet a `order_index = 0`
  (era il default di `create_wallet`), che con le nuove regole risulta preferito.
  È una migrazione implicita benigna e reversibile con "Rimuovi preferito".

### MB-005 — Il server MCP usa il wallet preferito se non specificato · risolta il 2026-09-12

- **Tipo**: evolutiva
- **Dipendeva da**: MB-004 (implementata prima, nella stessa sessione)
- **File toccati**: `pyspendless/mcp_server.py` (`resolve_wallet`,
  `_tool_add_movement`, `_tool_list_categories`), `pyspendless/dev_mcp_check.py`

**Problema**
Il tool `add_movement` ha il parametro `wallet` opzionale. Quando mancava,
`resolve_wallet()` ripiegava sul **primo wallet della lista** (`wallets[0]`):
una scelta posizionale, non la preferenza dell'utente. Registrando una spesa a
voce senza nominare il wallet, il movimento poteva finire su quello sbagliato.

**Soluzione**
`resolve_wallet(wallets, requested, preferred=None)`: con `requested` vuoto
ritorna il preferito, con ripiego su `wallets[0]` se il preferito non è
disponibile. `_tool_add_movement()` lo recupera con
`WalletRepository.get_preferred_wallet(account_id)`. `_tool_list_categories()`
marca `is_default` confrontando l'id con il preferito invece di usare l'indice 0,
sia nel testo sia in `structuredContent`, così l'elenco restituito a Claude dice
il vero. Aggiornata la `description` del parametro `wallet` nello schema del tool.

**Decisioni prese sugli attriti segnalati**

- **Wallet indicato esplicitamente**: semantica invariata, la risoluzione per
  nome/codice resta prioritaria sul preferito.
- **Account senza wallet**: continua a produrre l'errore di tool `no_wallet`
  (`get_preferred_wallet` ritorna `None` e la lista è vuota), non un'eccezione.
- **Account con wallet ma senza preferito** (stato possibile dopo i requisiti del
  2026-09-14): `resolve_wallet` ripiega su `wallets[0]`, cioè il minore per
  `order_index`. In più `list_categories` lo dichiara esplicitamente
  («Nessun wallet preferito impostato: se non ne indichi uno viene usato X»),
  così il modello può avvisare l'utente invece di scegliere in silenzio.
- **`dev_mcp_check.py`**: il controllo su `list_categories` non verifica più che
  sia preferito l'elemento in posizione 0, ma che i wallet marcati preferiti
  siano **al massimo uno** (zero è legittimo); il preferito rilevato viene
  stampato a video.

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
