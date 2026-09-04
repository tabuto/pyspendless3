# Task 17-0: Funzione "Ripeti" movimento

## Obiettivo
Aggiungere nell'elenco movimenti un pulsante **Ripeti** che porta alla pagina di
creazione movimento con il form già pre-compilato con tutti i campi del movimento
di riferimento, **tranne la data che è quella odierna**. Il salvataggio resta a
carico dell'utente, che può correggere i campi prima di confermare.

> **Nota sul requisito (revisione).** La prima stesura prevedeva un endpoint
> `POST /api/movements/<id>/repeat` che creava direttamente il clone. Il requisito
> è stato poi cambiato in "porta alla pagina di creazione pre-compilata": vince
> quindi la variante descritta in origine come alternativa. L'endpoint e il metodo
> `duplicate_movement()` **non fanno più parte dell'implementazione**.

## Analisi del codice esistente

| Elemento | Dove | Note |
|---|---|---|
| Modello `Movement` | `pyspendless/models.py:114` | PK `id` Text (uuid), campi legacy stringa (`category`, `wallet`, `user`) + FK (`category_id`, `wallet_id`, `user_id`, `recurrent_movement_id`) |
| CRUD | `pyspendless/repository.py:559` `MovementRepository` | `get_movement_by_id(id, account_id)` filtra già per account |
| Form crea/modifica | `pyspendless/app.py:371` `create()` | route GET che passa `movement` al template quando c'è `movement_id` |
| API create/update | `pyspendless/app.py:717` `api_create_movement` | riusata così com'è: il form ripetuto è a tutti gli effetti una creazione |
| Template form | `templates/ps-add-mov.html` | binding dei valori su `movement`; JS imposta data odierna e wallet da `localStorage` quando `movement_id` è vuoto |
| Lista movimenti (desktop) | `templates/ps-show-mov.html:181` | colonna "Azioni", icone **Bootstrap Icons** (`bi-`) |
| Lista movimenti (mobile) | `templates/ps-show-mov.html:416` | card generate in JS da `/api/movements` |
| Ricerca movimenti | `templates/ps-search-mov.html:95` e `:266` | stesse azioni ma icone **FontAwesome** (`fas fa-`) |

Nessuna modifica al modello e nessuna migrazione DB: la funzione non introduce
scritture nuove, riusa il percorso di creazione esistente.

## Implementazione

### 1. `app.py` — route `create()`

Nuovo parametro di query string `repeat_from`:

```python
repeat_from = request.args.get('repeat_from')
...
# Se repeat_from è presente (e non siamo in modifica), recupera il
# movimento da usare come sorgente per pre-compilare il form.
# Il filtro su account_id impedisce di leggere movimenti di altri account.
repeat_source = None
if repeat_from and not movement:
    repeat_source = movement_repo.get_movement_by_id(repeat_from, account_id)
    if not repeat_source:
        flash('Movimento da ripetere non trovato', 'error')
        return redirect(url_for('movements'))
```

Il template riceve `repeat_source` e `today=_date.today()`.
`movement_id` ha la precedenza su `repeat_from`: se entrambi sono presenti si
resta in modifica, così la modalità del form non è mai ambigua.

La data odierna è calcolata **lato server** (`date.today()`), coerentemente con
`_parse_movement_filters` (`app.py:423`) e `api_get_movements`: il campo data è
già valorizzato nell'HTML, senza dipendere dall'orologio del dispositivo e senza
sfarfallii se il JS è lento o disattivato.

### 2. `ps-add-mov.html` — pre-compilazione

Il template distingue ora tre modalità, tenendo separati "chi fornisce i valori"
da "che tipo di operazione è":

```jinja
{% set src = movement or repeat_source %}
```

- `src` alimenta i binding dei valori: tipo movimento, categoria, wallet, importo, nota.
- `movement` continua a governare la **semantica di modifica**: titolo della card,
  hidden `movement_id` (vuoto in ripetizione → l'API fa INSERT, non UPDATE),
  visibilità del blocco "Spesa Ricorrente".
- `repeat_source` governa solo la data (`today`), il titolo "Ripeti Movimento" e
  un banner informativo che indica la data del movimento di origine.

Il `{% set %}` è **dentro** `{% block nav_content %}`: le variabili definite fuori
dal block non sarebbero visibili al suo interno (scoping Jinja).

Campi ereditati: categoria, wallet, tipo movimento, importo, nota e
`recurrent_movement_id` (pre-selezionato anche nel select delle spese ricorrenti,
così hidden field e UI restano coerenti).

Adattamenti JS necessari:

- hidden `is_repeat` → `const isRepeat`. Il blocco che imposta data odierna e
  wallet da `localStorage` gira solo `if (!movementId && !isRepeat)`: senza questo
  guard la preselezione "ultimo wallet usato" **sovrascriverebbe** il wallet del
  movimento da ripetere.
- Al salvataggio riuscito in modalità ripeti si torna a `/movements` invece di
  resettare il form: `form.reset()` ripristinerebbe i *default* del DOM, cioè
  proprio i valori pre-compilati della sorgente, lasciando la pagina in uno stato
  ibrido con il banner "stai ripetendo" ancora visibile.

### 3. UI — pulsante

Semplice link, nessun JavaScript dedicato:

```html
<!-- ps-show-mov.html, colonna Azioni -->
<a href="/create?repeat_from={{ mov.id }}" class="btn btn-sm btn-secondary" title="Ripeti oggi">
  <i class="bi bi-arrow-repeat"></i>
</a>
```

Quattro punti di inserimento:

- `ps-show-mov.html` — riga della tabella desktop e card mobile in `renderCards()`
  (`mov.id` è già nel payload di `/api/movements`, `app.py:639`: nessuna modifica all'API GET);
- `ps-search-mov.html` — stessi due punti, ma con icona FontAwesome `fa-redo`,
  perché quel template non carica Bootstrap Icons.

Essendo una navigazione `GET` verso un form, il link è sicuro rispetto a prefetch,
refresh e doppio click: nessuna scrittura avviene prima del submit esplicito.

## Casi limite

1. **Isolamento account** — `repeat_from` arriva dalla query string ed è
   manipolabile: il recupero passa da `get_movement_by_id(id, account_id)`, mai da
   `get_movement(id)`. Id di un altro account → flash + redirect a `/movements`.
2. **Movimento inesistente o cancellato nel frattempo** — stesso trattamento
   (flash "Movimento da ripetere non trovato" + redirect), coerente con il ramo
   `movement_id` già esistente.
3. **Categoria o wallet eliminati dopo la creazione dell'originale** — l'`<option>`
   corrispondente non esiste più, quindi il select resta non selezionato e il
   `required` blocca il submit finché l'utente non sceglie un valore valido.
   È un vantaggio rispetto alla creazione diretta lato server, che avrebbe clonato
   silenziosamente FK ormai penzolanti.
4. **Movimenti importati da CSV con `category_id`/`wallet_id` NULL**
   (`api_import_movements` non valorizza gli id): il form si apre con i select
   vuoti e l'utente completa. Il movimento nuovo nasce quindi con le FK valorizzate,
   meglio dell'originale.
5. **Attribuzione utente** — non è più un problema da decidere: il salvataggio
   passa da `api_create_movement`, che usa `session['user_id']` e `user.email`.
   Il nuovo movimento è correttamente attribuito a chi lo crea, non all'autore
   dell'originale.
6. **Importi** — il valore arriva nel form come `src.income or src.expense` e
   viene rispedito come float dall'API, esattamente come per una creazione normale.
   Nessuna nuova casistica di arrotondamento.
7. **`repeat_from` + `movement_id` insieme** — vince `movement_id` (modifica),
   `repeat_source` resta `None`.
8. **Utente non autenticato** — la route `create()` fa già flash + redirect al login.
9. **Nessun rischio CSRF / doppia creazione** — il pulsante è un `GET` su un form;
   la scrittura avviene solo al submit, già coperto dal flusso esistente.

## File toccati

- `pyspendless/app.py` — `create()`: parametro `repeat_from`, `repeat_source`, `today`
- `pyspendless/templates/ps-add-mov.html` — modalità "ripeti": `src`, banner, titolo,
  data odierna server-side, hidden `is_repeat`, guard su localStorage, redirect post-salvataggio
- `pyspendless/templates/ps-show-mov.html` — link "Ripeti" (tabella + card mobile)
- `pyspendless/templates/ps-search-mov.html` — link "Ripeti" (tabella + card mobile)
- `backlog/features.md` — riga di backlog

Nessuna modifica a `repository.py`, nessuna nuova API, nessuna migrazione DB.

## Test

- Ripeti una spesa → il form si apre con categoria, wallet, tipo, importo e nota
  dell'originale e data odierna; al salvataggio nasce un nuovo movimento e si
  torna all'elenco.
- Ripeti un'entrata → `movement_type` = Entrata e le categorie filtrate sono quelle
  income (il `filterCategories()` iniziale deve mantenere la categoria pre-selezionata).
- Ripeti un movimento il cui wallet è diverso dall'ultimo usato → il wallet mostrato
  è quello del movimento, non quello in `localStorage`.
- Ripeti un movimento collegato a una spesa ricorrente → il select delle ricorrenti
  è pre-selezionato e il legame viene mantenuto sul nuovo movimento.
- `/create?repeat_from=<id-di-un-altro-account>` → redirect a `/movements` con flash.
- `/create?movement_id=<a>&repeat_from=<b>` → si apre la modifica di `<a>`.
- Apri il form da "Nuovo Movimento" → comportamento invariato (data odierna via JS,
  wallet dall'ultimo usato).
