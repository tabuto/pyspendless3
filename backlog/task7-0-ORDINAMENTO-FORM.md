# Ordinamento Categorie nei Form - Implementato

## Obiettivo
Assicurare che in tutte le pagine con combo/dropdown per la selezione delle categorie, le categorie vengano presentate ordinate secondo il campo `order_index` (ordinamento personalizzato dall'utente).

## Modifiche Implementate

### File: `pyspendless/app.py`

#### 1. Route `/create` - Form Aggiunta/Modifica Movimento
**Riga 362**
```python
# Prima:
categories = category_repo.get_categories_for_account(account_id)

# Dopo:
categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
```

**Beneficio**: Nel form di aggiunta/modifica movimento, il dropdown categorie mostra le categorie nell'ordine personalizzato dall'utente.

#### 2. Route `/movements` - Pagina Visualizzazione Movimenti con Filtri
**Riga 413**
```python
# Prima:
categories = category_repo.get_categories_for_account(account_id)

# Dopo:
categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
```

**Beneficio**: Nei filtri di ricerca/visualizzazione movimenti, il dropdown categorie è ordinato per `order_index`.

#### 3. Route API `/api/stats/...` - Dashboard
**Riga 499**
```python
# Già corretto:
categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
```

**Beneficio**: Nelle dashboard, i dati delle categorie seguono l'ordinamento personalizzato.

#### 4. Route `/api/import-export/import` - Import Movimenti CSV
**Riga 1355**
```python
# Prima:
categories = category_repo.get_categories_for_account(account_id)

# Dopo:
categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
```

**Beneficio**: Durante l'import, le categorie vengono caricate con ordinamento consistente (anche se in questo contesto l'ordine non è critico per la funzionalità).

### Riepilogo Modifiche

**Totale route aggiornate**: 3
**Route già corrette**: 1

Tutte le chiamate a `get_categories_for_account()` nell'app.py ora usano esplicitamente `order_by_index=True`.

## Comportamento Attuale

### 1. Form Aggiunta Movimento (`/create`)
- ✅ Dropdown "Categoria" mostra categorie ordinate per `order_index`
- ✅ Il filtro JavaScript preserva l'ordine quando filtra per tipo (expense/income)
- ✅ L'ordine è quello personalizzato dall'utente in Settings

### 2. Pagina Movimenti (`/movements`)
- ✅ Dropdown filtro "Categoria" ordinato per `order_index`
- ✅ Coerenza con l'ordine visto in Settings

### 3. Dashboard (`/dashboard/...`)
- ✅ Già implementato correttamente
- ✅ Grafici mostrano categorie nell'ordine personalizzato

### 4. Settings Categorie (`/settings/categories`)
- ✅ Già implementato nella Task 7.0
- ✅ Permette di modificare l'ordine con drag & drop numerico

## Template Coinvolti

### `ps-add-mov.html`
- **Non richiede modifiche** al JavaScript
- Il template riceve le categorie già ordinate da Jinja2
- Il JavaScript preserva l'ordine quando filtra per tipo
- Struttura:
  ```javascript
  const allCategoryOptions = Array.from(categorySelect.querySelectorAll('option'));
  // forEach preserva l'ordine del DOM
  allCategoryOptions.forEach(option => { ... });
  ```

### Altri template
- Non richiedono modifiche perché ricevono le categorie via Jinja2 o via API
- L'API `/api/categories` già restituisce categorie ordinate (implementato precedentemente)

## Consistenza Ordine Categorie

Ora in tutta l'applicazione le categorie appaiono nello stesso ordine personalizzato:

| Pagina/Componente | Ordinamento |
|-------------------|-------------|
| Settings > Categorie | ✅ order_index |
| Form Nuovo Movimento | ✅ order_index |
| Filtri Visualizzazione Movimenti | ✅ order_index |
| Dashboard Mensile/Annuale | ✅ order_index |
| API `/api/categories` | ✅ order_index |
| Import CSV | ✅ order_index |

## Test Consigliati

### Test Manuale
1. ✅ Vai in Settings > Categorie
2. ✅ Imposta ordini personalizzati (es: Alimentari=1, Trasporti=2, Svago=3)
3. ✅ Vai in "Nuovo Movimento"
4. ✅ Verifica che il dropdown categorie mostri le categorie nello stesso ordine
5. ✅ Cambia tipo movimento (Entrata/Uscita)
6. ✅ Verifica che l'ordine sia preservato dopo il filtro
7. ✅ Vai in Visualizza Movimenti
8. ✅ Verifica che il filtro categorie mostri lo stesso ordine

### Test di Regressione
- [ ] Verificare che categorie senza `order_index` (default 0) funzionino
- [ ] Verificare ordinamento con più categorie con stesso `order_index`
- [ ] Verificare che il secondo criterio di ordinamento (alfabetico) funzioni

## Note Tecniche

### Default Behavior del Repository
Il metodo `get_categories_for_account()` ha il parametro:
```python
def get_categories_for_account(self, account_id: int, order_by_index: bool = True)
```

- `order_by_index=True` (default): Ordina per `order_index ASC, name ASC`
- `order_by_index=False`: Ordina solo per `name ASC` (alfabetico)

### Retrocompatibilità
- Categorie esistenti senza `order_index` hanno default 0
- Il secondo criterio di ordinamento (alfabetico) assicura ordinamento deterministico
- Nessuna modifica breaking per categorie legacy

## File Modificati

- `pyspendless/app.py` (3 chiamate aggiornate)

## Status

✅ **COMPLETATO**

Tutte le pagine con dropdown/combo di selezione categorie ora utilizzano l'ordinamento personalizzato dall'utente via campo `order_index`.
