# Task 1.7: Dashboard Mensile e Annuale

Questa specifica descrive l'implementazione di due nuove pagine di analisi dati (Dashboard Mensile e Dashboard Annuale) utilizzando il template AdminLTE 3 e la libreria Chart.js. I dati vengono recuperati dinamicamente tramite chiamate API REST/AJAX.

## 1. Dashboard Mensile (`ps-dashboard-monthly.html`)

### 1.1 UI e Layout
- **Template base**: Estende `base.html` (layout con sidebar).
- **Header**: Titolo "Analisi Mensile".
- **Filtri (Toolbar in alto)**:
  - Dropdown **Anno** (popolato dinamicamente con gli anni presenti nei movimenti).
  - Dropdown **Mese** (Gennaio-Dicembre).
  - Pulsante "Aggiorna" (o trigger `onchange`).

- **Layout Griglia (AdminLTE Cards)**:
  - **Riga 1**:
    - Colonna SX: Grafico a Torta "Entrate vs Uscite".
    - Colonna DX: Grafico a Torta "Spese per Categoria" (Top 5 o tutte).
  - **Riga 2**:
    - Colonna SX: Grafico a Torta "Spese per Wallet".
    - Colonna DX: Grafico a Torta "Entrate per Wallet".

### 1.2 Logica Frontend (JS + Chart.js)
- Al caricamento della pagina, chiamare le API per popolare i filtri e caricare i dati del mese corrente.
- Al variare dei filtri (Anno o Mese):
  - Inviare richiesta AJAX GET con query param `year` e `month`.
  - Aggiornare le istanze di Chart.js (`chart.data` e `chart.update()`).

---

## 2. Dashboard Annuale (`ps-dashboard-yearly.html`)

### 2.1 UI e Layout
- **Template base**: Estende `base.html`.
- **Header**: Titolo "Analisi Annuale".
- **Filtri Globali**:
  - Dropdown **Anno**.
- **Layout Griglia**:
  - **Riga 1 (Riepilogo)**:
    - Colonna SX: Grafico a Torta "Totale Entrate vs Uscite".
    - Colonna DX: Grafico a Torta "Totale Spese per Categoria".
  - **Riga 2 (Breakdown Wallet)**:
    - Colonna SX: Grafico a Torta "Totale Spese per Wallet".
    - Colonna DX: Grafico a Torta "Totale Entrate per Wallet".
  - **Riga 3 (Trend Categoria)**:
    - Card a tutta larghezza.
    - Header Card: Dropdown filtro **Categoria**.
    - Body Card: Grafico a Linea "Andamento Mensile Spese per Categoria Selezionata".

### 2.2 Logica Frontend (JS + Chart.js)
- Al variare del filtro **Anno**, aggiornare tutti i grafici (Torte + Linea).
- Al variare del filtro **Categoria** (nella Riga 3), aggiornare solo il Grafico a Linea, mantenendo l'anno selezionato.

---

## 3. Modifiche Backend (`app.py` & `repository.py`)

### 3.1 Nuovi Endpoint API (`app.py`)

Devono ritornare JSON. Tutti gli endpoint filtrano per l'Account dell'utente loggato.

1.  **GET `/api/stats/monthly`**
    - **Params**: `year` (int), `month` (int).
    - **Response JSON**:
      ```json
      {
        "income_vs_expense": { "income": 1200.0, "expense": 850.50 },
        "expense_by_wallet": { "Wallet A": 500.0, "Wallet B": 350.50 },
        "income_by_wallet": { "Wallet A": 1200.0 },
        "expense_by_category": { "Food": 200.0, "Rent": 600.0, "Transport": 50.50 }
      }
      ```

2.  **GET `/api/stats/yearly`**
    - **Params**: `year` (int).
    - **Response JSON**: (Struttura simile a `/stats/monthly` ma aggregata sull'anno intero).

3.  **GET `/api/stats/category-trend`**
    - **Params**: `year` (int), `category_id` (int/string).
    - **Response JSON**:
      ```json
      {
        "category_name": "Food",
        "year": 2024,
        "labels": ["Gen", "Feb", ...],
        "data": [150.0, 120.5, ...] // Valori mensili
      }
      ```
    - *Nota*: Se `category_id` non è specificato, usare una categoria di default o ritornare vuoto.

4.  **GET `/api/filters/years`**
    - **Response JSON**: Lista degli anni disponibili nei movimenti (`[2023, 2024, 2025]`).

### 3.2 Metodi Repository (`repository.py`)

Aggiungere funzioni che utilizzano SQLAlchemy `func.sum` e `group_by`.

- `get_monthly_stats(account_id, year, month)`
- `get_yearly_stats(account_id, year)`
- `get_category_monthly_trend(account_id, year, category_name)`: Ritorna array di 12 valori per i 12 mesi.
- `get_available_years(account_id)`: Query `distinct(Movement.move_year)`.

### 3.3 Rotte Frontend (`app.py`)

Rotte che renderizzano semplicemente il template HTML.

- `GET /dashboard/monthly` -> render `ps-dashboard-monthly.html`
- `GET /dashboard/yearly` -> render `ps-dashboard-yearly.html`

## 4. Dettagli Implementativi

- **Sicurezza**: Verificare sempre `current_user` e filtrare query per `account_id`.
- **Valuta**: I valori monetari nell'interfaccia devono essere formattati.
- **Colori Grafici**: Definire una palette di colori standard in JS per mantenere coerenza tra le categorie nei grafici a torta.
- **Empty States**: Se non ci sono dati per il periodo selezionato, i grafici devono mostrare uno stato vuoto o zero.
