# Task 9.0: Fix Responsive UI Issues

Questo task risolve tre problemi di layout responsive identificati nell'interfaccia di PySpendless.

---

## Issue #1 — Home Page: Spaziatura pulsante "Crea Movimento"

### Problema
In `ps-home.html`, il pulsante **Crea Movimento** non risulta visivamente distanziato dall'elemento `<h5>` sovrastante, a differenza del pulsante **Vedi Movimenti** che appare correttamente spaziato. In viewport stretti, le card impilate accentuano l'inconsistenza di altezza e posizionamento dei pulsanti.

### Analisi del Codice
```html
<!-- Card "Nuovo Movimento" (attuale) -->
<div class="card-body">
  <h5 class="card-title mb-3">...</h5>
  <a href="..." class="btn btn-primary">Crea Movimento</a>
</div>

<!-- Card "Visualizza Movimenti" (attuale) -->
<div class="card-body">
  <h5 class="card-title mb-3">...</h5>
  <a href="..." class="btn btn-info">Vedi Movimenti</a>
</div>
```

Le due card hanno HTML identico, ma la card "Impostazioni" contiene un `btn-group-vertical` più alto che — su alcune risoluzioni — causa un'altezza diversa. Il risultato visivo è un pulsante che sembra "incollato" al testo se la card adiacente è più alta.

### Soluzione
Uniformare tutte le card usando **flexbox** su `.card` e `.card-body` con `mt-auto` sul pulsante (o gruppo di pulsanti), così il pulsante è sempre ancorato in fondo alla card indipendentemente dall'altezza del contenuto.

```html
<!-- Applicare a tutte e tre le card -->
<div class="card h-100">
  <div class="card-body d-flex flex-column">
    <h5 class="card-title mb-3">...</h5>
    <a href="..." class="btn btn-primary mt-auto">Crea Movimento</a>
  </div>
</div>
```

**File da modificare:** `pyspendless/templates/ps-home.html`

**Modifiche:**
- Aggiungere `h-100` alla classe `.card` di tutte e tre le card nella `row`.
- Aggiungere `d-flex flex-column` alla classe `.card-body` di tutte e tre le card.
- Aggiungere `mt-auto` al pulsante (o al `div.btn-group-vertical`) di ogni card.
- Aggiungere `row-cols-1 row-cols-md-3` alla `div.row` per gestire correttamente il layout su mobile (1 colonna) e desktop (3 colonne), e `g-3` per il gap tra le card.

---

## Issue #2 — Settings Gruppo: Tabella Membri → Lista Card

### Problema
In `ps-setting-group.html`, la sezione **Membri del Gruppo** e **Inviti Pendenti** usano `<table>` con `<thead>` e `<tbody>` popolati dinamicamente via JavaScript. Su schermi piccoli la tabella non si adatta e causa overflow orizzontale o compressione del testo.

### Analisi del Codice
```html
<table class="table" id="membersTable">
  <thead>
    <tr>
      <th>Email</th>
      <th>Nome</th>
      <th>Stato</th>
      <th>Azioni</th>
    </tr>
  </thead>
  <tbody id="membersTableBody">
    <!-- Popolato dinamicamente via JS -->
  </tbody>
</table>
```

La tabella ha 4 colonne (Email, Nome, Stato, Azioni) ed è dentro un `col-md-6`, spazio già ridotto. Il JavaScript popola `membersTableBody` con `innerHTML`. Lo stesso pattern esiste per `pendingInvitesTable`.

### Soluzione
Sostituire le due tabelle con **Bootstrap List Group** a struttura card-like. Il JavaScript che costruisce le righe (`innerHTML`) viene aggiornato per produrre elementi `<li>` di list-group invece di `<tr>`.

**Struttura HTML sostitutiva per i Membri:**
```html
<!-- Sostituisce <table id="membersTable"> -->
<ul class="list-group list-group-flush" id="membersTable">
  <!-- Popolato dinamicamente -->
</ul>
```

**Struttura di ogni item (generata via JS):**
```html
<li class="list-group-item">
  <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
    <div>
      <div class="fw-semibold"><i class="bi bi-person-circle me-1"></i>{email}</div>
      <small class="text-muted">{nome}</small>
    </div>
    <div class="d-flex align-items-center gap-2">
      <span class="badge bg-success">Attivo</span>
      <button class="btn btn-sm btn-outline-danger" ...>
        <i class="bi bi-person-dash"></i>
      </button>
    </div>
  </div>
</li>
```

**Struttura sostitutiva per gli Inviti Pendenti:**
```html
<ul class="list-group list-group-flush" id="pendingInvitesTable">
  <!-- Popolato dinamicamente -->
</ul>
```

**File da modificare:** `pyspendless/templates/ps-setting-group.html`

**Modifiche:**
1. Sostituire `<table id="membersTable">...</table>` con `<ul class="list-group list-group-flush" id="membersTable"></ul>`.
2. Sostituire `<table id="pendingInvitesTable">...</table>` con `<ul class="list-group list-group-flush" id="pendingInvitesTable"></ul>`.
3. Aggiornare il blocco `{% block scripts %}` — le funzioni JS `loadGroupMembers()` e `loadPendingInvites()` che fanno `innerHTML` con `<tr>` devono produrre `<li class="list-group-item">` con la struttura sopra.
4. Rimuovere il riferimento a `membersTableBody` e `pendingInvitesBody` (o mantenerli come ID sull'`<ul>` stesso).

---

## Issue #3 — Tabella Visualizza Movimenti: Responsive

### Problema
In `ps-show-mov.html`, la tabella `#movementsTable` usa **DataTables 1.13.7** con `responsive: true` nelle opzioni JS, ma mancano i file CSS/JS dell'**estensione Responsive** di DataTables. Di conseguenza l'opzione `responsive` viene ignorata e su mobile la tabella con 8 colonne (Data, Categoria, Wallet, Nota, Utente, Entrata, Uscita, Azioni) causa overflow orizzontale.

### Analisi del Codice
```html
<!-- Caricato nel template (attuale) -->
<link rel="stylesheet" href=".../dataTables.bootstrap5.min.css">
<script src=".../jquery.dataTables.min.js"></script>
<script src=".../dataTables.bootstrap5.min.js"></script>

<!-- Inizializzazione (attuale) -->
$('#movementsTable').DataTable({
  responsive: true,  ← opzione presente ma estensione non caricata
  order: [[0, 'desc']],
  pageLength: 25,
  language: { url: '.../it-IT.json' }
});
```

Il wrapper `<div class="card-body">` non ha `overflow-x: auto`, e l'estensione `dataTables.responsive` non è inclusa.

### Requisiti da mantenere
- ✅ Ricerca full-text (DataTables built-in)
- ✅ Paginazione (DataTables built-in)
- ✅ Ordinamento per colonna (DataTables built-in)

### Soluzione

**Approccio A — DataTables Responsive Extension (raccomandato)**

Aggiungere i CDN dell'estensione Responsive e configurare le colonne prioritarie:

```html
<!-- Aggiungere dopo i CSS esistenti di DataTables -->
<link rel="stylesheet" href="https://cdn.datatables.net/responsive/2.5.0/css/responsive.bootstrap5.min.css">

<!-- Aggiungere dopo gli script esistenti di DataTables -->
<script src="https://cdn.datatables.net/responsive/2.5.0/js/dataTables.responsive.min.js"></script>
<script src="https://cdn.datatables.net/responsive/2.5.0/js/responsive.bootstrap5.min.js"></script>
```

Aggiornare l'inizializzazione DataTables:
```javascript
$('#movementsTable').DataTable({
  language: { url: '...' },
  order: [[0, 'desc']],
  pageLength: 25,
  responsive: true,
  columnDefs: [
    { responsivePriority: 1, targets: 0 },  // Data — sempre visibile
    { responsivePriority: 2, targets: 7 },  // Azioni — alta priorità
    { responsivePriority: 3, targets: 5 },  // Entrata
    { responsivePriority: 3, targets: 6 },  // Uscita
    { responsivePriority: 4, targets: 1 },  // Categoria
    { responsivePriority: 5, targets: 2 },  // Wallet
    { responsivePriority: 6, targets: 3 },  // Nota — collassabile
    { responsivePriority: 6, targets: 4 },  // Utente — collassabile
  ]
});
```

Con questa configurazione, su schermi piccoli DataTables nasconde automaticamente le colonne a bassa priorità e mostra un controllo espandi/collassa per visualizzarle inline.

**Approccio B — `table-responsive` wrapper (fallback semplice)**

Se l'estensione Responsive introduce complessità indesiderata:
```html
<div class="table-responsive">
  <table id="movementsTable" class="table table-striped table-bordered table-hover">
    ...
  </table>
</div>
```

Questo abilita lo scroll orizzontale su mobile senza nascondere colonne, mantenendo intatta tutta la funzionalità DataTables. Soluzione meno elegante ma immediata.

**Approccio scelto: A + B come safety net**
Caricare l'estensione Responsive (Approccio A) e aggiungere il wrapper `table-responsive` (Approccio B) come ulteriore protezione.

**File da modificare:** `pyspendless/templates/ps-show-mov.html`

**Modifiche:**
1. Aggiungere CDN CSS `responsive.bootstrap5.min.css` dopo il CDN DataTables esistente.
2. Aggiungere CDN JS `dataTables.responsive.min.js` e `responsive.bootstrap5.min.js` dopo gli script DataTables esistenti.
3. Aggiungere `<div class="table-responsive">` attorno al `<table>`.
4. Aggiornare l'init DataTables con `columnDefs` per le priorità responsive.

---

## Riepilogo Modifiche

| File | Modifiche |
|------|-----------|
| `ps-home.html` | Card layout con `h-100`, `d-flex flex-column`, `mt-auto` sui pulsanti |
| `ps-setting-group.html` | Sostituire `<table>` con `<ul class="list-group">` + aggiornare JS |
| `ps-show-mov.html` | Aggiungere DataTables Responsive extension + `table-responsive` wrapper + `columnDefs` |

## Ordine di Implementazione

1. `ps-show-mov.html` — fix più impattante, interessa la pagina principale
2. `ps-home.html` — fix semplice, pura modifica CSS/HTML
3. `ps-setting-group.html` — richiede aggiornamento HTML + JS, più complessa
