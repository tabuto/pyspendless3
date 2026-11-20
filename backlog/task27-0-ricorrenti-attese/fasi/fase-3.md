# Fase 3 — Pagina Spese Ricorrenti: il giorno e lo stato

**Chi**: subagent **`ps-ui`** (haiku).
**Dipende da**: Fase 2 (`api` verde; le variabili `status`, `due_date`,
`current_month_date` arrivano già al template).
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task27_0.py contract`
esce con **exit code 0** per i controlli di `ps-recurrent-mov.html`, e `repo` e
`api` restano verdi.
**File che puoi toccare**: `pyspendless/templates/ps-recurrent-mov.html`.
**Nient'altro** — non `app.py` (chiusa in Fase 2), non il CSS (Fase 5).

## Il mandato

Due interventi su
[ps-recurrent-mov.html](../../../pyspendless/templates/ps-recurrent-mov.html):
un campo nel form e una colonna nella tabella.

### 1. Il campo "Giorno del mese"

Nel form, **dopo** `rm_amount` e **prima** di `rm_note`:

```html
<div class="mb-3">
  <label for="rm_due_day" class="ps-label">Giorno del mese</label>
  <input type="number" min="1" max="31" step="1" class="ps-input" id="rm_due_day">
  <p class="ps-help">Lascia vuoto per non ricevere proposte per questa ricorrenza.</p>
</div>
```

**Senza `required`**: il campo è opzionale (decisione dell'utente, 2026-11-16) e
il metro lo verifica. Usa `ps-help` come fa il campo labels, non una classe
nuova.

Nel payload del submit, accanto a `note`:

```js
due_day: document.getElementById('rm_due_day').value
  ? parseInt(document.getElementById('rm_due_day').value, 10)
  : null,
```

Il ternario serve: `parseInt('')` è `NaN`, e `JSON.stringify({x: NaN})` produce
`{"x":null}` — funzionerebbe per caso. Scrivi l'intenzione, non l'accidente.

In `resetForm()` non serve nulla: `form.reset()` azzera anche l'input nuovo.

### 2. `editRecurrent` deve riempirlo

Qui c'è il rischio R1 della specifica. L'`onclick` inline passa già **7**
argomenti posizionali:

```
editRecurrent({{ rm.id }}, '{{ rm.name|e }}', '{{ ... }}', {{ rm.category_id }},
              {{ rm.wallet_id }}, {{ rm.income or rm.expense }}, '{{ rm.note|e ... }}')
```

Due strade, **entrambe accettate** dal metro:

**(a) L'ottavo argomento, in coda.** Diff minimo:

```html
onclick="editRecurrent(..., '{{ rm.note|e if rm.note else '' }}', {{ rm.due_day if rm.due_day else 'null' }})"
```

e `function editRecurrent(id, name, movType, categoryId, walletId, amount, note, dueDay)`.
Attenzione al `{{ ... if ... else 'null' }}`: serve il letterale JS `null`, non
la stringa `'None'` di Python né un buco che renderebbe `editRecurrent(..., )`.

**(b) `data-*` sul bottone + `dataset`.** Più lavoro, ma chiude il rischio: la
riga HTML smette di essere una lista di posizioni. Se la scegli, sposta tutti e
otto i valori su `data-*`, non sei su `data-*` e due posizionali.

Non lasciare la firma a 7 argomenti riempiendo il campo da un'altra parte: il
form non sarebbe più coerente con la riga su cui hai cliccato.

### 3. La colonna "Stato"

La `<th>` **"Data ultima spesa"** diventa **"Stato"**, e la cella rende i cinque
stati della specifica §4. Il template **non** fa aritmetica sulle date: riceve
`rm.status` già calcolato.

```html
<td>
  {% if rm.status == 'pending' %}
    <span class="ps-badge ps-badge-warning">Attesa il {{ rm.due_date.day }}</span>
  {% elif rm.status == 'registered' %}
    <span class="ps-badge ps-badge-income">Registrata il {{ rm.current_month_date.strftime('%d/%m') }}</span>
  {% elif rm.status == 'skipped' %}
    <span class="ps-badge ps-badge-secondary">Ignorata questo mese</span>
    <button class="ps-btn ps-btn-sm ps-btn-outline-secondary" onclick="unskipRecurrent({{ rm.id }})">Ripristina</button>
  {% elif rm.status == 'upcoming' %}
    <span class="ps-muted">Attesa il {{ rm.due_date.day }}</span>
  {% else %}
    <span class="ps-muted">—</span>
  {% endif %}
</td>
```

`current_month_date` e **non** `last_move_date`: è la trappola 2 della Fase 1,
ed è l'errore più probabile di questa fase. `last_move_date` è il massimo su
**tutti** i mesi — un affitto pagato a ottobre e non a novembre mostrerebbe
*"Registrata il 05/10"* accanto a uno stato che dice il contrario.

Se `ps-badge-warning` o `ps-badge-secondary` non esistono in
`ps-tailwind.src.css`, **non inventarle qui**: usa le classi che ci sono
(`ps-badge-income`, `ps-badge-expense`) e **segnalalo**. Le classi nuove e la
ricompilazione sono della Fase 5.

### 4. `unskipRecurrent`

```js
async function unskipRecurrent(id) {
  const response = await fetch(`/api/recurrent-movements/${id}/skip`, { method: 'DELETE' });
  const result = await response.json();
  if (response.ok) { location.reload(); }
  else { showAlert(result.error || 'Errore', 'danger'); }
}
```

`location.reload()` e non una manipolazione del DOM: la pagina già ricarica dopo
ogni salvataggio (`setTimeout(() => location.reload(), 800)`), quindi è la
convenzione del file. Ricalcolare lo stato in JS vorrebbe dire duplicare in
JavaScript la regola di §4 — che è il contrario del disegno.

## Le due trappole

1. **`colspan="8"` della riga vuota.** Il `<tr id="empty-row">` ha
   `colspan="8"`, e le colonne restano 8 (sostituisci "Data ultima spesa", non
   ne aggiungi una). Se decidi di **tenere** anche la colonna storica, le
   colonne diventano 9 e il `colspan` va aggiornato **in due posti**: nel
   template e nella stringa JS dentro il gestore di `confirm-delete-btn`
   ([riga ~282](../../../pyspendless/templates/ps-recurrent-mov.html)). Il
   secondo è quello che si dimentica.
2. **Lo `strftime` su `None`.** `rm.current_month_date` è `None` in tutti gli
   stati tranne `registered`, e `rm.due_date` è `None` quando `status` è
   `'none'`. L'ordine dei rami `{% if %}` qui sopra li protegge entrambi: non
   riordinarli mettendo un `{% if rm.due_date %}` esterno "per sicurezza", che
   nasconderebbe lo stato `none` invece di renderlo.

## Cosa NON fare

- Non toccare il campo labels né `ps-labels.js`: la nota e le sue chip
  funzionano, e `rm_due_day` non c'entra.
- Non introdurre nuove chiamate a `bootstrap.*`. Il task19-0 ha rimosso
  Bootstrap; i due residui in questo file (`new bootstrap.Modal`,
  `bootstrap.Modal.getInstance`) sono preesistenti e li lasci come sono — ma non
  ne aggiungi altri.
- Non aggiungere classi CSS che non esistono (vedi §3).
- Non modificare `test/test_task27_0.py`. Se un controllo ti sembra sbagliato,
  **fermati e dillo**.
