# Task 14.0: Filtro per intervallo di date nella visualizzazione movimenti

## Obiettivo

Sostituire i filtri **Anno** e **Mese** nella sezione `/movements` con due campi data — **Data inizio** e **Data fine** — che permettano all'utente di visualizzare i movimenti in un intervallo arbitrario. I valori di default sono:

- **Data inizio**: giorno 1 del mese corrente (es. `2026-06-01`)
- **Data fine**: data odierna (es. `2026-06-06`)

---

## 1. Descrizione UX

### Barra dei filtri (`ps-show-mov.html`)

- Rimuovere i due `<select>` per **Anno** e **Mese**.
- Aggiungere due `<input type="date">`:
  - `date_from` — etichetta "Dal" — default: `YYYY-MM-01` (primo giorno mese corrente)
  - `date_to` — etichetta "Al" — default: `YYYY-MM-DD` (oggi)
- I valori di default vengono calcolati server-side in Flask e passati al template tramite il dizionario `filters`.
- La stessa API `/api/movements` (usata dalla vista card mobile con infinite scroll) deve accettare gli stessi parametri e restituire risultati coerenti.

### Comportamento atteso
1. L'utente arriva su `/movements` → vede automaticamente i movimenti dal 1° del mese corrente a oggi.
2. Può modificare le date e cliccare **Filtra** per aggiornare la vista.
3. Se `date_from > date_to`, il server restituisce un insieme vuoto (o un errore 400 nell'API JSON).
4. I filtri per **Wallet**, **Tipo** e **Categoria** rimangono invariati e si combinano con l'intervallo di date.

---

## 2. Modifiche da effettuare

### 2.1 `pyspendless/repository.py` — `MovementRepository`

**Metodo `get_movements_for_account`** (riga ~565):
- Aggiungere i parametri `date_from: Optional[date] = None` e `date_to: Optional[date] = None`.
- Rimuovere i parametri `year` e `month` (o mantenerli per retrocompatibilità con le altre route che li usano ancora, aggiungendo i nuovi in coda).
- Aggiungere i filtri SQLAlchemy:
  ```python
  if date_from:
      query = query.filter(Movement.move_date >= date_from)
  if date_to:
      query = query.filter(Movement.move_date <= date_to)
  ```

**Metodo `get_movements_stats`** (riga ~696):
- Aggiungere gli stessi parametri `date_from` e `date_to` e passarli alla chiamata interna a `get_movements_for_account`.
- Aggiornare anche i filtri nella seconda query (raggruppamento per categoria) per applicare il range di date.

### 2.2 `pyspendless/app.py` — route `GET /movements` (riga ~418)

- Sostituire la lettura di `year` e `month` dalla query string con `date_from` e `date_to`:
  ```python
  from datetime import date, datetime
  today = date.today()
  default_date_from = today.replace(day=1).isoformat()   # es. "2026-06-01"
  default_date_to   = today.isoformat()                  # es. "2026-06-06"

  date_from_str = request.args.get('date_from', default=default_date_from)
  date_to_str   = request.args.get('date_to',   default=default_date_to)

  # Parsing con fallback al default in caso di formato non valido
  try:
      date_from = date.fromisoformat(date_from_str)
  except ValueError:
      date_from = today.replace(day=1)
  try:
      date_to = date.fromisoformat(date_to_str)
  except ValueError:
      date_to = today
  ```
- Rimuovere la costruzione delle liste `years` e `months` (non più necessarie nel template).
- Passare al template i valori `date_from` e `date_to` (come stringhe `YYYY-MM-DD`) dentro il dizionario `filters`.
- Aggiornare le chiamate a `get_movements_for_account` e `get_movements_stats` sostituendo `year=year, month=month` con `date_from=date_from, date_to=date_to`.

### 2.3 `pyspendless/app.py` — route `GET /api/movements` (riga ~551)

- Sostituire la lettura di `year` e `month` con `date_from` e `date_to` (stesso schema di parsing della route HTML sopra).
- Aggiornare la chiamata a `get_movements_for_account`.
- Aggiungere validazione: se `date_from > date_to`, restituire `400` con messaggio `"date_from non può essere successiva a date_to"`.

### 2.4 `pyspendless/templates/ps-show-mov.html`

- Nella barra dei filtri, sostituire i due `<select>` per Anno e Mese con:
  ```html
  <div class="col-md-2">
    <label for="date_from" class="form-label">Dal</label>
    <input type="date" class="form-control" id="date_from" name="date_from"
           value="{{ filters.date_from }}">
  </div>
  <div class="col-md-2">
    <label for="date_to" class="form-label">Al</label>
    <input type="date" class="form-control" id="date_to" name="date_to"
           value="{{ filters.date_to }}">
  </div>
  ```
- Aggiornare eventuali riferimenti a `filters.year` e `filters.month` nel resto del template (es. titoli della pagina, didascalie dei grafici).

### 2.5 JavaScript nella vista card mobile (`ps-show-mov.html`, sezione infinite scroll)

- La chiamata fetch a `/api/movements` attualmente passa `year` e `month` come parametri. Aggiornare la costruzione della URL per leggere i valori dai nuovi campi `date_from` e `date_to`:
  ```js
  const dateFrom = document.getElementById('date_from').value;
  const dateTo   = document.getElementById('date_to').value;
  // Usare dateFrom e dateTo al posto di year e month nella URL dell'API
  ```

---

## 3. Note tecniche

- Il tipo SQLAlchemy `Date` su `Movement.move_date` supporta nativamente il confronto con oggetti `datetime.date` Python, quindi non è necessario convertire a stringa per i filtri.
- I campi `move_year` e `move_month` nel modello `Movement` rimangono invariati (sono usati da altre funzionalità come i report annuali). I filtri per range di date si basano esclusivamente su `move_date`.
- Verificare che la route `/api/movements` usata dall'infinite scroll nella vista card (task 12) funzioni correttamente con i nuovi parametri e che il JavaScript di quella vista venga aggiornato di conseguenza.
- Non è necessario modificare le route dei **Report** (task 13) né la route `/ps-search-mov`, che hanno logiche di filtro indipendenti.

---

## 4. Piano di implementazione

1. Modificare `get_movements_for_account` e `get_movements_stats` in `repository.py` per accettare `date_from` / `date_to`.
2. Aggiornare la route `GET /movements` in `app.py`.
3. Aggiornare la route `GET /api/movements` in `app.py`.
4. Aggiornare il template `ps-show-mov.html` (form filtri + JavaScript infinite scroll).
5. Test manuali: verifica default al caricamento, cambio intervallo, combinazione con gli altri filtri, vista desktop e mobile.

---

## Criteri di accettazione

- [ ] Al caricamento di `/movements` senza parametri, la vista mostra i movimenti dal 1° del mese corrente a oggi.
- [ ] I campi "Dal" e "Al" sono pre-popolati con le date di default.
- [ ] Modificando le date e premendo **Filtra**, la lista si aggiorna correttamente.
- [ ] I filtri Wallet, Tipo e Categoria continuano a funzionare in combinazione con il range di date.
- [ ] La vista card mobile (infinite scroll) rispetta lo stesso intervallo di date.
- [ ] L'API `/api/movements` risponde `400` se `date_from > date_to`.
- [ ] I report annuali (task 13) e la ricerca testuale (`/ps-search-mov`) non sono impattati.
