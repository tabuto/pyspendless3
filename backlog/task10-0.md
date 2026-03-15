# Task 10.0: Memorizza e preseleziona l'ultimo wallet usato

## Obiettivo

Migliorare la UX nella pagina **Crea Movimento** (`ps-add-mov.html`) memorizzando lato client l'ultimo wallet selezionato dall'utente. Alla riapertura del form (nuova creazione), il wallet viene preselezionato automaticamente se l'informazione è presente in `localStorage`.

---

## Analisi

### Stato attuale

In `ps-add-mov.html`, il `<select id="wallet">` preseleziona un wallet solo in modalità **modifica** (quando esiste un oggetto `movement` con `wallet_id`):

```html
<select class="form-select" id="wallet" name="wallet" required>
  {% for wal in wallets %}
    <option value="{{ wal.id }}"
      {% if movement and movement.wallet_id == wal.id %}selected{% endif %}>
      {{ wal.name }}
    </option>
  {% endfor %}
</select>
```

In modalità **creazione** non avviene alcuna preselezione: il primo wallet della lista viene selezionato di default dal browser.

### Flusso di submit

Il form invia i dati via `fetch` (AJAX/JSON). Il wallet viene letto così:

```javascript
wallet_id: parseInt(document.getElementById('wallet').value),
```

---

## Soluzione

### 1. Salvataggio in `localStorage` al submit

Dopo un submit avvenuto con successo, salvare l'ID del wallet scelto:

```javascript
localStorage.setItem('ps_last_wallet_id', walletId.toString());
```

La chiave `ps_last_wallet_id` viene scritta **solo se il salvataggio del movimento va a buon fine** (risposta HTTP 200/201 dall'API).

### 2. Preselezione al caricamento del form (solo modalità creazione)

All'avvio della pagina, se **non** si è in modalità modifica (nessun `movement.id` presente), leggere il valore dal localStorage e impostarlo sul select:

```javascript
document.addEventListener('DOMContentLoaded', function () {
  const isEditMode = /* verificare se movement_id è presente nella pagina */;
  if (!isEditMode) {
    const lastWalletId = localStorage.getItem('ps_last_wallet_id');
    if (lastWalletId) {
      const walletSelect = document.getElementById('wallet');
      const option = walletSelect.querySelector(`option[value="${lastWalletId}"]`);
      if (option) {
        walletSelect.value = lastWalletId;
      }
    }
  }
});
```

> **Nota**: se il wallet salvato non è più disponibile (es. eliminato), la preselezione non avviene silenziosamente e rimane il default del browser.

---

## File da modificare

| File | Modifica |
|------|----------|
| `pyspendless/templates/ps-add-mov.html` | Aggiungere logica JS per lettura/scrittura `localStorage` |

---

## Dettaglio implementativo

### Blocco `{% block scripts %}` in `ps-add-mov.html`

**Al submit (successo):**

Nella callback del `fetch` POST/PUT, subito prima del redirect o del reset del form, aggiungere:

```javascript
// salva l'ultimo wallet usato
const walletId = parseInt(document.getElementById('wallet').value);
if (!isNaN(walletId)) {
  localStorage.setItem('ps_last_wallet_id', walletId.toString());
}
```

**Al DOMContentLoaded (solo nuova creazione):**

```javascript
// preselezione wallet (solo nuova creazione)
const editMovementId = document.getElementById('movement_id')?.value;
if (!editMovementId) {
  const lastWalletId = localStorage.getItem('ps_last_wallet_id');
  if (lastWalletId) {
    const walletSelect = document.getElementById('wallet');
    if (walletSelect && walletSelect.querySelector(`option[value="${lastWalletId}"]`)) {
      walletSelect.value = lastWalletId;
    }
  }
}
```

> **Come rilevare la modalità modifica**: verificare la presenza di un campo nascosto `<input type="hidden" id="movement_id">` (già presente o da aggiungere) valorizzato dal backend solo in edit mode.

---

## Criteri di accettazione

- [ ] Dopo aver creato un movimento con wallet X, riaprendo il form di creazione, il wallet X risulta preselezionato.
- [ ] In modalità modifica di un movimento esistente, la preselezione da `localStorage` **non** sovrascrive il wallet del movimento.
- [ ] Se il wallet memorizzato non è presente nel select (es. è stato eliminato), il form mostra il comportamento di default senza errori.
- [ ] La chiave `ps_last_wallet_id` viene aggiornata solo in caso di salvataggio riuscito.
- [ ] Nessuna chiamata aggiuntiva al backend: tutto gestito lato client con `localStorage`.
