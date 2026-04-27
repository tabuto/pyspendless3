# Task 12.0: Visualizzazione Movimenti Responsive con Card e Scroll Infinito

## Problema

In `/movements` la tabella DataTables con layout responsive nasconde le colonne Entrata/Uscita sugli schermi piccoli, richiedendo un click per espandere la riga. L'importo — informazione primaria — non è visibile immediatamente su mobile.

## Approccio

Dual-layout:
- **Desktop (≥md):** tabella DataTables esistente invariata
- **Mobile (<md):** lista di card Bootstrap con importo prominente + infinite scroll JS puro

Per l'infinite scroll serve un endpoint API paginato. La route HTML continua a servire solo i filtri e le statistiche (no movimenti nel template render), il caricamento lista avviene via fetch JS.

---

## Tutti i componenti da toccare

| Componente | Tipo | Modifica |
|---|---|---|
| `pyspendless/app.py` | Modifica | Aggiungere `GET /api/movements` paginato |
| `pyspendless/templates/ps-show-mov.html` | Modifica | Aggiungere card list mobile + infinite scroll JS; tabella desktop invariata |

---

## Dettaglio

### 1. Nuovo endpoint `GET /api/movements`

**Route:** `GET /api/movements`  
**Auth:** sessione richiesta  
**Query params:**
- `year` (int, default: mese corrente)
- `month` (int, default: mese corrente)
- `wallet_id` (int, optional)
- `category_type` (str, optional: `income`/`expense`)
- `category_id` (int, optional)
- `page` (int, default: 1)
- `per_page` (int, default: 20, max: 50)

**Response:**
```json
{
  "movements": [
    {
      "id": 42,
      "move_date": "2025-04-15",
      "category": "Spesa",
      "wallet": "Conto Corrente",
      "income": null,
      "expense": 35.50,
      "note": "Supermercato",
      "user": "mario"
    }
  ],
  "page": 1,
  "per_page": 20,
  "has_more": true
}
```

Riutilizza `movement_repo.get_movements_for_account()` già esistente, con aggiunta di `offset`/`limit` alla query (o slice Python se il metodo non supporta paginazione nativa).

### 2. Modifiche `ps-show-mov.html`

#### Struttura HTML

```
<!-- Visibile solo su mobile -->
<div id="movements-card-list" class="d-md-none">
  <!-- Cards iniettate da JS -->
  <div id="cards-container"></div>
  <div id="load-more-trigger"></div>  <!-- sentinella IntersectionObserver -->
  <div id="cards-spinner" class="text-center py-3 d-none">
    <div class="spinner-border text-primary"></div>
  </div>
  <div id="no-more-msg" class="text-center text-muted py-3 d-none">
    Nessun altro movimento
  </div>
</div>

<!-- Visibile solo su desktop — tabella DataTables esistente -->
<div class="d-none d-md-block">
  <table id="movementsTable" ...>...</table>
</div>
```

#### Struttura di ogni card

```html
<div class="card mb-2 movement-card">
  <div class="card-body py-2 px-3">
    <div class="d-flex justify-content-between align-items-center">
      <div>
        <span class="fw-semibold">{{ categoria }}</span>
        <span class="text-muted small ms-1">· {{ wallet }}</span>
      </div>
      <span class="fw-bold fs-5 text-{danger|success}">
        € {{ importo }}
      </span>
    </div>
    <div class="d-flex justify-content-between mt-1">
      <span class="text-muted small">{{ data }}</span>
      <span class="text-muted small fst-italic text-truncate ms-2" style="max-width:140px">
        {{ nota }}
      </span>
    </div>
    <div class="mt-1 text-end">
      <a href="/create?movement_id={{ id }}" class="btn btn-sm btn-outline-primary py-0 px-2">
        <i class="bi bi-pencil"></i>
      </a>
      <button onclick="deleteMovement('{{ id }}')" class="btn btn-sm btn-outline-danger py-0 px-2">
        <i class="bi bi-trash"></i>
      </button>
    </div>
  </div>
</div>
```

#### Logica JS (infinite scroll)

```javascript
// Stato paginazione
let currentPage = 0;
let isLoading = false;
let hasMore = true;

// IntersectionObserver sulla sentinella
const trigger = document.getElementById('load-more-trigger');
const observer = new IntersectionObserver(entries => {
  if (entries[0].isIntersecting && !isLoading && hasMore) {
    loadMoreMovements();
  }
}, { threshold: 0.1 });
observer.observe(trigger);

async function loadMoreMovements() {
  isLoading = true;
  // mostra spinner
  const params = new URLSearchParams(window.location.search);
  params.set('page', ++currentPage);
  params.set('per_page', 20);

  const res = await fetch(`/api/movements?${params}`);
  const data = await res.json();

  renderCards(data.movements);
  hasMore = data.has_more;
  isLoading = false;
  // nascondi spinner
}

function renderCards(movements) {
  const container = document.getElementById('cards-container');
  movements.forEach(mov => {
    const isExpense = mov.expense !== null;
    const amount = isExpense ? mov.expense : mov.income;
    const colorClass = isExpense ? 'text-danger' : 'text-success';
    const sign = isExpense ? '-' : '+';
    const note = mov.note || '';

    const card = document.createElement('div');
    card.className = 'card mb-2 movement-card';
    card.innerHTML = `
      <div class="card-body py-2 px-3">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <span class="fw-semibold">${mov.category}</span>
            <span class="text-muted small ms-1">· ${mov.wallet}</span>
          </div>
          <span class="fw-bold fs-5 ${colorClass}">${sign} € ${parseFloat(amount).toFixed(2)}</span>
        </div>
        <div class="d-flex justify-content-between mt-1">
          <span class="text-muted small">${mov.move_date}</span>
          <span class="text-muted small fst-italic text-truncate ms-2" style="max-width:140px">${note}</span>
        </div>
        <div class="mt-1 text-end">
          <a href="/create?movement_id=${mov.id}" class="btn btn-sm btn-outline-primary py-0 px-2">
            <i class="bi bi-pencil"></i>
          </a>
          <button onclick="deleteMovement('${mov.id}')" class="btn btn-sm btn-outline-danger py-0 px-2">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>`;
    container.appendChild(card);
  });
}
```

#### Reset al cambio filtri

Il form filtri su submit ricarica la pagina (GET), quindi lo stato del paginatore viene resettato naturalmente.

---

## Note tecniche

- La tabella DataTables (desktop) continua a ricevere i movimenti dal template Jinja (invariato), per non rompere il comportamento esistente su desktop.
- Sul mobile la tabella è nascosta con `d-none d-md-block` e i dati arrivano via API.
- `IntersectionObserver` è supportato da tutti i browser moderni; nessuna libreria esterna aggiuntiva.
- Il nuovo endpoint riutilizza la logica di filtraggio già esistente in `MovementRepository`.

---

## Criteri di accettazione

- [ ] Su mobile (<768px), l'elenco movimenti mostra card con importo prominente (visibile senza click).
- [ ] La card mostra: data, categoria, wallet, importo colorato (rosso/verde), nota troncata, azioni (modifica/elimina).
- [ ] Scorrendo verso il basso vengono caricati automaticamente altri movimenti (infinite scroll).
- [ ] Al termine dei movimenti compare il messaggio "Nessun altro movimento".
- [ ] I filtri (anno, mese, wallet, tipo, categoria) vengono applicati correttamente anche alla lista card.
- [ ] Su desktop (≥768px) la tabella DataTables esistente rimane invariata.
- [ ] L'endpoint `GET /api/movements` risponde con JSON paginato e richiede autenticazione.
- [ ] L'eliminazione di un movimento dalla card funziona correttamente (reload della lista).
