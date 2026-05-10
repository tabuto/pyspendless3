# Task 13.0: Funzionalità "Reports" – Report Annuale PDF

## Obiettivo

Aggiungere una nuova sezione **Reports** all'applicazione che consenta all'utente di selezionare un anno tra quelli disponibili e scaricare un report annuale in PDF. Il report analizza le spese, le confronta con gli anni precedenti, evidenzia le singole spese più grandi e le categorie con maggiore incidenza sul budget.

---

## 1. Dati da includere nel report

### 1.1 Intestazione e sommario anno
- Nome account e anno selezionato
- Totale entrate anno
- Totale uscite anno
- Saldo (entrate − uscite)
- Numero totale di movimenti

### 1.2 Confronto storico – Anni precedenti
Tabella e grafico a barre con serie storica (tutti gli anni disponibili):
- Totale entrate per anno
- Totale uscite per anno
- Saldo per anno
- Variazione % uscite rispetto all'anno precedente

### 1.3 Trend mensile anno selezionato
Grafico a linee (12 mesi) con:
- Uscite mensili
- Entrate mensili
- Saldo mensile cumulativo

### 1.4 Top 10 spese singole dell'anno
Tabella ordinata per importo decrescente:
- Data, Categoria, Wallet, Nota, Importo

### 1.5 Spese per categoria – Incidenza sul budget
Tabella + grafico a torta:
- Categoria
- Totale speso
- % sul totale uscite anno
- N° movimenti
- Confronto con anno precedente (importo + variazione %)

### 1.6 Top 5 categorie per peso sul budget
Box evidenziati con le categorie che incidono di più (≥5% del totale uscite).

### 1.7 Distribuzione spese per wallet
Tabella + grafico a barre orizzontali:
- Nome wallet, totale uscite, % sul totale

### 1.8 Mesi anomali
Tabella dei mesi in cui le uscite superano del 20% la media mensile dell'anno.

---

## 2. Descrizione UX

### Navigazione
Aggiungere voce **"Reports"** nella sidebar (`ps-nav.html`), sotto Dashboard, con icona `bi-file-earmark-bar-graph`.

### Pagina `/reports`
- **Selettore anno**: dropdown con gli anni disponibili (popolato da API `/api/filters/years` già esistente). L'anno corrente è selezionato di default.
- **Pulsante "Genera PDF"**: avvia la generazione e scarica automaticamente il file.
- **Anteprima**: sezione opzionale (fase 2) che mostra un'anteprima HTML del report prima del download.
- **Stato**: indicatore di caricamento durante la generazione (spinner Bootstrap).

### Comportamento
1. L'utente arriva su `/reports`.
2. Seleziona l'anno dal dropdown.
3. Clicca **"Scarica Report PDF"**.
4. Il browser riceve un file `report-{anno}.pdf` e lo scarica.
5. In caso di errore compare un alert Bootstrap.

### Template da creare
- `ps-reports.html` — pagina principale Reports (estende `ps-nav.html`)

---

## 3. Soluzione tecnica

### Libreria PDF
**WeasyPrint** — converte HTML+CSS in PDF server-side. È la scelta più naturale perché:
- Riutilizza il sistema di template Jinja2 già esistente.
- Supporta CSS moderno (Bootstrap-like) per tabelle e layout.
- Non richiede un browser headless.

Alternativa: `xhtml2pdf` (più leggero ma meno fedele al CSS).

I **grafici** vengono generati server-side come immagini SVG/PNG con **matplotlib** (già disponibile nell'ecosistema Python) e incorporati nel template HTML prima della conversione PDF.

### Struttura file da modificare/creare

| File | Tipo | Modifica |
|---|---|---|
| `pyspendless/app.py` | Modifica | Route `GET /reports` (pagina) + `POST /api/reports/annual` (genera PDF) |
| `pyspendless/repository.py` | Modifica | Nuovo metodo `ReportRepository.get_annual_report_data()` |
| `pyspendless/templates/ps-reports.html` | Nuovo | Pagina UI Reports |
| `pyspendless/templates/ps-report-pdf.html` | Nuovo | Template HTML per conversione PDF (standalone, no navbar) |
| `pyspendless/requirements.txt` | Modifica | Aggiungere `weasyprint`, `matplotlib` |

---

## 4. Query da eseguire

### Q1 – Sommario anno
```sql
SELECT
    SUM(income)   AS tot_income,
    SUM(expense)  AS tot_expense,
    COUNT(*)      AS n_movimenti
FROM Movement
WHERE account_id = :account_id
  AND move_year  = :year;
```

### Q2 – Serie storica anni (confronto)
```sql
SELECT
    move_year,
    ROUND(SUM(income),  2) AS tot_income,
    ROUND(SUM(expense), 2) AS tot_expense,
    COUNT(*)               AS n_movimenti
FROM Movement
WHERE account_id = :account_id
GROUP BY move_year
ORDER BY move_year;
```

### Q3 – Trend mensile anno selezionato
```sql
SELECT
    move_month,
    ROUND(SUM(income),  2) AS tot_income,
    ROUND(SUM(expense), 2) AS tot_expense
FROM Movement
WHERE account_id = :account_id
  AND move_year  = :year
GROUP BY move_month
ORDER BY move_month;
```

### Q4 – Top 10 spese singole
```sql
SELECT
    move_date,
    category,
    COALESCE(w.name, m.wallet) AS wallet_name,
    note,
    expense
FROM Movement m
LEFT JOIN Wallet w ON m.wallet_id = w.id
WHERE m.account_id = :account_id
  AND m.move_year  = :year
  AND m.expense    IS NOT NULL
ORDER BY m.expense DESC
LIMIT 10;
```

### Q5 – Spese per categoria con confronto anno precedente
```sql
-- Anno corrente
SELECT
    category,
    ROUND(SUM(expense), 2)       AS tot_expense,
    COUNT(*)                      AS n_movimenti,
    ROUND(SUM(expense) * 100.0 /
        (SELECT SUM(expense) FROM Movement
         WHERE account_id = :account_id AND move_year = :year
           AND expense IS NOT NULL), 2) AS pct_budget
FROM Movement
WHERE account_id = :account_id
  AND move_year  = :year
  AND expense    IS NOT NULL
GROUP BY category
ORDER BY tot_expense DESC;

-- Anno precedente (stesso schema, year = :year - 1)
```

### Q6 – Spese per wallet
```sql
SELECT
    COALESCE(w.name, m.wallet) AS wallet_name,
    ROUND(SUM(m.expense), 2)   AS tot_expense,
    COUNT(*)                    AS n_movimenti
FROM Movement m
LEFT JOIN Wallet w ON m.wallet_id = w.id
WHERE m.account_id = :account_id
  AND m.move_year  = :year
  AND m.expense    IS NOT NULL
GROUP BY COALESCE(w.name, m.wallet)
ORDER BY tot_expense DESC;
```

### Q7 – Mesi anomali (uscite > media + 20%)
```sql
WITH monthly AS (
    SELECT move_month, ROUND(SUM(expense), 2) AS tot
    FROM Movement
    WHERE account_id = :account_id AND move_year = :year AND expense IS NOT NULL
    GROUP BY move_month
),
avg_month AS (
    SELECT AVG(tot) AS media FROM monthly
)
SELECT m.move_month, m.tot, ROUND(m.tot - a.media, 2) AS delta
FROM monthly m, avg_month a
WHERE m.tot > a.media * 1.2
ORDER BY m.tot DESC;
```

---

## 5. API da esporre

### `GET /reports`
**Auth:** sessione richiesta  
Renderizza la pagina `ps-reports.html` con la lista degli anni disponibili.

---

### `GET /api/reports/annual`
**Auth:** sessione richiesta  
**Query params:**
- `year` (int, obbligatorio) — anno del report

**Response:** file PDF (`Content-Type: application/pdf`)  
**Filename:** `report-spese-{year}.pdf`

**Logica server-side:**
1. Valida `year` (intero, presente nei dati dell'account).
2. Esegue le query Q1–Q7 tramite `ReportRepository`.
3. Genera i grafici con `matplotlib` (PNG in-memory, base64 per l'embedding HTML).
4. Renderizza il template `ps-report-pdf.html` con Jinja2.
5. Converte l'HTML in PDF con WeasyPrint.
6. Ritorna il PDF come stream con `send_file`.

**Errori:**
```json
{ "error": "Anno non valido o nessun dato disponibile" }   // 400
{ "error": "Non autorizzato" }                              // 401
{ "error": "Errore generazione PDF: <dettaglio>" }          // 500
```

---

## 6. Piano di implementazione

### Fase 1 – Backend dati e query
1. Aggiungere `weasyprint` e `matplotlib` a `requirements.txt`.
2. Creare classe `ReportRepository` in `repository.py` con metodo `get_annual_report_data(account_id, year)` che esegue tutte le query (Q1–Q7) e ritorna un dizionario strutturato.
3. Scrivere unit test in `pyspendless/test/` per `get_annual_report_data`.

### Fase 2 – Template HTML del PDF
4. Creare `ps-report-pdf.html`: template HTML standalone (no navbar) con:
   - Intestazione con anno e nome account
   - Tabelle per ogni sezione dati
   - Tag `<img>` per i grafici (base64 PNG)
   - CSS inline ottimizzato per stampa (page-break, font system)

### Fase 3 – Generazione grafici
5. Creare funzione helper `generate_report_charts(data) -> dict[str, str]` in un nuovo modulo `pyspendless/report_charts.py`:
   - Grafico a barre storico anni (`matplotlib`)
   - Grafico a linee trend mensile
   - Grafico a torta incidenza categorie
   - Ogni grafico ritorna una stringa base64 PNG

### Fase 4 – Route e API Flask
6. Aggiungere route `GET /reports` in `app.py`.
7. Aggiungere route `GET /api/reports/annual` in `app.py` con generazione PDF.

### Fase 5 – Pagina UI
8. Creare `ps-reports.html` con:
   - Dropdown anno (chiama `/api/filters/years`)
   - Pulsante download PDF (chiama `/api/reports/annual?year=...`)
   - Spinner durante la generazione
9. Aggiungere voce **Reports** alla sidebar in `ps-nav.html`.

### Fase 6 – Test e raffinamento
10. Test manuali con anni diversi.
11. Verifica layout PDF su browser diversi.
12. Ottimizzazione tempi di generazione (cache grafici se necessario).

---

## Criteri di accettazione

- [x] Voce "Reports" presente nella sidebar e accessibile agli utenti autenticati.
- [x] Dropdown anni popolato correttamente con gli anni disponibili.
- [x] Clic su "Scarica Report PDF" avvia il download del file `report-spese-{anno}.pdf`.
- [x] Il PDF contiene tutte le 8 sezioni dati descritte nella sezione 1.
- [x] I grafici sono leggibili e correttamente etichettati.
- [x] La tabella "Top 10 spese singole" è ordinata per importo decrescente.
- [x] La sezione confronto storico mostra almeno gli ultimi 5 anni disponibili.
- [x] I mesi senza movimenti nel trend mensile mostrano 0 (non vengono omessi).
- [x] L'API risponde con 401 se l'utente non è autenticato.
- [x] L'API risponde con 400 se l'anno non è valido.
- [x] Il tempo di generazione del PDF è inferiore a 10 secondi. *(1.4s in test)*

---

## Note tecniche

- WeasyPrint richiede alcune dipendenze di sistema (libcairo, libpango). Su Linux: `apt install python3-weasyprint`. Documentare nel README.
- I grafici matplotlib devono usare un backend non-interattivo (`matplotlib.use('Agg')`) per evitare errori in ambiente server.
- Il template PDF non usa Bootstrap CDN (richiede internet), ma CSS inline per garantire la corretta resa offline.
- `matplotlib` e `weasyprint` aggiungono peso alle dipendenze (~50MB). Valutare se usare `pdfkit`+`wkhtmltopdf` come alternativa leggera se WeasyPrint causa problemi di deploy.
