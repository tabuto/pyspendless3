# Fase 4 — La card in home e il form pre-compilato

**Chi**: subagent **`ps-ui`** (haiku).
**Dipende da**: Fase 2 (`pending_recurrents`, `prefill_recurrent_id` e
`prefill_date` arrivano già ai template) e Fase 3 (stessa famiglia di stringhe e
di classi).
**Fatto quando**: `cd pyspendless && .venv/bin/python test/test_task27_0.py contract`
esce con **exit code 0** su tutti i controlli, e `repo` e `api` restano verdi.
**File che puoi toccare**: `pyspendless/templates/ps-home.html`,
`pyspendless/templates/ps-add-mov.html`. **Nient'altro.**

## 1. La card in `/home`

[ps-home.html](../../../pyspendless/templates/ps-home.html) è quasi vuota: la
card va **sopra** la griglia delle tre card di navigazione, subito dopo il
paragrafo di benvenuto, perché è l'unica cosa in pagina che richiede un'azione.

```html
{% if pending_recurrents %}
<div class="ps-card mt-4">
  <div class="ps-card-header">
    <h3 class="ps-card-title">
      <i class="bi bi-exclamation-triangle mr-2 text-[var(--ps-warning)]"></i>
      {{ pending_recurrents|length }} movimenti ricorrenti attesi
    </h3>
  </div>
  <div class="ps-card-body">
    <ul class="divide-y divide-[var(--ps-border)]">
      {% for rm in pending_recurrents %}
      <li class="flex flex-wrap items-center gap-2 py-2" id="pending-{{ rm.id }}">
        <span class="font-medium">{{ rm.name }}</span>
        <span class="ps-muted">€ {{ "%.2f"|format(rm.income or rm.expense) }}</span>
        <span class="ps-muted">atteso il {{ rm.due_date.day }}</span>
        <span class="ml-auto flex gap-2">
          <a href="{{ url_for('create', recurrent_id=rm.id) }}"
             class="ps-btn ps-btn-sm ps-btn-primary">Registra</a>
          <button type="button" class="ps-btn ps-btn-sm ps-btn-outline-secondary"
                  onclick="skipPending({{ rm.id }})">Ignora questo mese</button>
        </span>
      </li>
      {% endfor %}
    </ul>
  </div>
</div>
{% endif %}
```

Il `{% if %}` esterno è un controllo del metro: **nessuna card quando non c'è
niente**. Una card "0 movimenti attesi" su una home che per il 90% del mese non
ha proposte è rumore, e dopo due settimane l'utente smette di guardarla.

`url_for('create', recurrent_id=rm.id)` e non una stringa `/create?...`: la
rotta ha un nome, si usa quello.

Il plurale non si risolve qui: la stringa resta `"N movimenti ricorrenti
attesi"` anche per N = 1. Il `ngettext` è del task25-0 (spec §11 R2), e
anticiparlo con un `{% if %}` sul numero creerebbe una stringa in più da
tradurre.

### `skipPending`

```html
<script>
async function skipPending(id) {
  try {
    const response = await fetch(`/api/recurrent-movements/${id}/skip`, { method: 'POST' });
    if (response.ok) {
      document.getElementById(`pending-${id}`)?.remove();
      if (!document.querySelector('[id^="pending-"]')) location.reload();
    }
  } catch (err) { /* la proposta ricompare al prossimo caricamento */ }
}
</script>
```

Il `location.reload()` quando l'ultima riga sparisce serve a far sparire la card
intera: il `{% if %}` è server-side, e una card vuota con solo l'intestazione è
peggio di un reload. Lo `?.remove()` tollera un doppio click.

In caso di errore non si mostra un alert: `ps-home.html` non ha un
`#alertContainer` e non è questa la fase che gliene aggiunge uno. La proposta
ricompare al prossimo caricamento, che è il comportamento corretto per
un'operazione che non è andata a buon fine.

## 2. Il form pre-compilato

Due modifiche a
[ps-add-mov.html](../../../pyspendless/templates/ps-add-mov.html), e sono
entrambe piccole perché la logica di riempimento **esiste già**.

### 2a. La data

L'input `move_date` ([riga 61](../../../pyspendless/templates/ps-add-mov.html))
ha già due rami; se ne aggiunge un terzo, **prima** di quello di `repeat_source`
non è necessario — l'ordine fra i due è indifferente perché i casi sono
mutuamente esclusivi:

```html
value="{% if movement %}{{ movement.move_date.strftime('%Y-%m-%d') }}{% elif repeat_source %}{{ today.strftime('%Y-%m-%d') }}{% elif prefill_date %}{{ prefill_date.strftime('%Y-%m-%d') }}{% endif %}"
```

È il passo 3 della specifica §7.3: la data è quella di **scadenza del mese
corrente** (decisione dell'utente, 2026-11-16), non oggi. Ed è il server a
metterla.

### 2b. La preselezione

Nell'`<option>` della select `recurrent_template`
([riga 47](../../../pyspendless/templates/ps-add-mov.html)) il `selected` ha già
una condizione; se ne aggiunge una seconda:

```html
{% if (repeat_source and repeat_source.recurrent_movement_id == rt.id) or prefill_recurrent_id == rt.id %}selected{% endif %}
```

E in coda al blocco `<script>`, **dopo** la registrazione del listener di
`recurrent_template` ([riga 210](../../../pyspendless/templates/ps-add-mov.html)):

```js
// Prefill da una proposta (/create?recurrent_id=N): l'<option> è già
// selected lato server, ma il listener che riempie i campi si innesca solo
// su 'change'. La data NON si tocca: la mette il server (vedi move_date).
{% if prefill_recurrent_id %}
document.getElementById('recurrent_template')?.dispatchEvent(new Event('change'));
{% endif %}
```

Questo è il passo 4: la logica che riempie tipo, categoria, wallet, importo e
nota **non si riscrive, si innesca**. Quel listener contiene già il commento «La
data NON viene toccata», che è esattamente ciò che serve qui.

## Le quattro trappole

0. **Le icone disponibili sono 59, non 2.078.** `MB-008` ha ridotto Bootstrap
   Icons a un subset, e `MB-009` registra la conseguenza: **un'icona `bi-*` non
   presente nel subset si vede vuota, senza errori in console né 404**. Chi la
   aggiunge non ha alcun segnale. L'elenco vero è in
   `pyspendless/static/css/ps-icons.css`:

   ```bash
   grep -o "bi-[a-z0-9-]*" pyspendless/static/css/ps-icons.css | sort -u
   ```

   `bi-exclamation-triangle` c'è (e `bi-exclamation-circle` **no**: era la prima
   scelta di questa specifica, scartata per questo). Se ti serve un'icona che
   non c'è, **usane una del subset o non metterne nessuna** — non rigenerare il
   font, che è lavoro di `MB-009`.


1. **L'ordine conta.** Il `dispatchEvent` deve stare **dopo** la riga che
   registra il listener, e dopo `filterCategories()`: l'handler chiama
   `filterCategories()` da sé e poi imposta `category.value`, quindi se gira
   prima che le option siano in pagina l'assegnazione non attacca e la categoria
   resta vuota — senza nessun errore in console. È il bug più probabile di
   questa fase.
2. **`prefill_recurrent_id` è `None` o un `int`; `rt.id` è un `int`.** Il
   confronto `prefill_recurrent_id == rt.id` funziona perché la Fase 2 passa
   `prefill_recurrent.id` (un intero), non `request.args.get('recurrent_id')`
   (una stringa). Non "sistemare" il confronto con un `|string`: se non
   combacia, il difetto è a monte e va segnalato.
3. **Il blocco `{% if not movement %}` intorno alla select.** La select
   `recurrent_template` esiste **solo in creazione**
   ([riga 40](../../../pyspendless/templates/ps-add-mov.html)): in modifica non
   c'è, e `getElementById` restituisce `null`. L'`?.` dello snippet non è
   decorativo. Il `{% if prefill_recurrent_id %}` lo copre comunque, perché la
   Fase 2 non valorizza il prefill quando c'è un `movement`.

## Cosa NON fare

- Non toccare il submit del form movimento né `recurrent_movement_id`: il
  legame che chiude la proposta si crea già da sé, perché la select è
  preselezionata e l'handler scrive il campo nascosto. **È tutto il meccanismo
  di A2**: se ti viene voglia di aggiungere codice per "chiudere la proposta
  dopo il salvataggio", fermati — significa che il prefill non sta funzionando.
- Non aggiungere un `#alertContainer` a `ps-home.html`.
- Non toccare le tre card di navigazione esistenti.
- Non modificare `test/test_task27_0.py`. Se un controllo ti sembra sbagliato,
  **fermati e dillo**.
