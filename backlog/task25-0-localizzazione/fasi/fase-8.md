# Fase 8 — Date, numeri, valuta e il PDF

**Chi**: 1 subagent su **sonnet**, in worktree. Non haiku: il criterio "non ho
toccato i formati macchina" è un test, ma scegliere **quale** helper applicare
**dove** richiede di distinguere una data di vista da una data di contratto —
ed è esattamente la distinzione che un modello piccolo sbaglia.
**Durata**: 1 giorno.
**Dipende da**: fasi 5, 6, 7 verdi e committate.

---

## 8.1 Gli helper (in `i18n.py`)

Tre filtri Jinja e tre funzioni Python, registrati in un punto solo:

| Helper | Usa | Risultato `it` | Risultato `en_GB` |
|---|---|---|---|
| `ps_date` | `babel.dates.format_date(fmt='short')` | `19/10/2026` | `19/10/2026` |
| `ps_datetime` | `format_datetime(fmt='short')` | `19/10/2026, 14:30` | `19/10/2026, 14:30` |
| `ps_amount` | `babel.numbers.format_decimal` | `1.234,56` | `1,234.56` |
| `ps_currency` | `format_currency(..., 'EUR')` | `1.234,56 €` | `€1,234.56` |

`en_GB` dà le date nell'ordine giorno-mese: è la ragione per cui si è scelto
`en_GB` e non `en` (P2). Vale la pena verificarlo in un test, non per fiducia
nel CLDR ma perché un `en` scappato da qualche parte si manifesterebbe proprio
qui, e in forma subdola — `10/19/2026` è una data valida, solo sbagliata.

**Il separatore dei decimali cambia.** Oggi l'app stampa sempre `1234.56`:
cioè è già "inglese" nei numeri. Con `it` attivo diventerà `1.234,56`, e questo
è un **cambiamento visibile per gli utenti attuali**. È voluto ed è una
correzione, non una regressione — ma va detto all'utente prima del rilascio,
perché è l'unica cosa in tutto il task che un utente italiano noterà.

## 8.2 Dove si applicano

I punti sono già censiti (specifica §2.3). Vista → helper:

| File | Righe |
|---|---|
| `app.py` | 722, 1093 (`move_date` nelle risposte JSON rese all'utente) |
| `repository.py` | 1166, 1253, 1358, 1619 (date dei token e delle connessioni) |
| `templates/ps-search-mov.html` | 77 |
| `templates/ps-show-mov.html` | 215 (**solo la vista**, non il `data-order`) |
| `templates/ps-recurrent-mov.html` | 99 |
| `templates/ps-add-mov.html` | 19 (**non** il `value` di riga 57) |
| `templates/ps-setting-group.html` | 28 |

Contratto → **non si toccano**:

| File | Righe | Cosa |
|---|---|---|
| `app.py` | 775, 779, 1920, 1925 | header e date ISO dell'export CSV |
| `app.py` | 1983 | parsing ISO dell'import |
| `templates/ps-show-mov.html` | 215 | `data-order="{{ ...isoformat() }}"` |
| `templates/ps-add-mov.html` | 57 | `value` dell'`<input type="date">` |
| `mcp_server.py` | 685, 727 | fuori scope (specifica §9) |

## 8.3 I nomi dei mesi: si eliminano le due copie

L'helper `month_names()` esiste dalla Fase 6. Qui si cancellano le due liste
rimaste:

- `repository.py:2212` → `month_names(...)`
- `report_pdf.py:13` `MONTHS_IT` → `month_names(...)`, e l'uso a riga 236

Da dodici stringhe duplicate in tre punti a una funzione. È la ripulitura che
giustifica da sola metà di questa fase.

## 8.4 Il report PDF

`report_pdf.py` (~22 etichette) e `report_charts.py` (~6). Due vincoli:

1. Il PDF si genera **fuori dal ciclo di richiesta**? No: si genera dentro una
   rotta, quindi `gettext` funziona. Ma le costanti a livello di modulo vanno
   comunque a `lazy_gettext` (specifica §5.3).
2. `ReportPDF._safe()` sostituisce i caratteri non-latin1 (riga ~40): `fpdf2`
   con i font standard **non** gestisce l'UTF-8 completo. Le traduzioni inglesi
   non introducono caratteri problematici, ma **il meccanismo non si tocca** —
   e se una futura lingua lo richiedesse, servirebbe un font TrueType
   incorporato, che è un altro task.

---

## Criteri di accettazione

### Verificabili dal subagent

| # | Criterio | Come si verifica |
|---|---|---|
| A8.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code |
| A8.2 | `.venv/bin/python -m pyspendless.test.test_task25_0` esce **0** | exit code |
| A8.3 | **Criterio A6**: con `en_GB` attivo l'export CSV ha header italiano e date `%Y-%m-%d` | test |
| A8.4 | `data-order` e il `value` degli input date **invariati** | grep + diff |
| A8.5 | Con `it`: `19/10/2026` e `1.234,56`. Con `en_GB`: `19/10/2026` e `1,234.56` | test parametrico sui due locale |
| A8.6 | `MONTHS_IT` non esiste più in `report_pdf.py`, e `month_names` non è duplicato | grep |
| A8.7 | Il PDF si genera senza eccezioni nei due locale | test o esecuzione diretta |
| A8.8 | Nessun `strftime` resta su una data di **vista** | grep incrociato con l'elenco di §8.2 |

### Verificabili solo dall'agente principale

| # | Criterio |
|---|---|
| A8.9 | `/movements`, `/settings/profile`, le due dashboard: date e importi corretti nei due locale |
| A8.10 | Ordinamento per data in DataTables ancora corretto (se si è rotto il `data-order`, le date si ordinano alfabeticamente) |
| A8.11 | Round-trip export→import ancora riuscito |
| A8.12 | Il PDF annuale scaricato è leggibile nei due locale, mesi inclusi |
| A8.13 | L'utente è stato avvisato del cambio di separatore decimale in italiano (§8.1) |
| A8.14 | `git diff --stat` resta nell'elenco della Fase 8 (§6.4 del piano) |

## Definition of done

Date, importi e valute seguono la lingua in **vista**, i formati macchina non si
sono mossi di un carattere, e i nomi dei mesi vivono in un posto solo.
