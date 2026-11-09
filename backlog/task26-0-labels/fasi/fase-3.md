# Fase 3 — `/api/labels`, filtro `?label=`, rotta della pagina

**Chi**: subagent **`ps-labels-py`** (haiku).
**Dipende da**: Fase 2 verde.
**Fatto quando**: `.venv/bin/python test/test_task26_0.py api` esce con
**exit code 0** (19 controlli), e `parser` + `repo` restano verdi.
**File che puoi toccare**: `pyspendless/app.py`,
`pyspendless/templates/ps-setting-labels.html` (solo lo scheletro, vedi 3.4).

## 3.1 Le quattro API

| Metodo | Rotta | Note |
|---|---|---|
| `GET` | `/api/labels?q=&limit=10` | `LabelRepository.search` (ricerca per **sottostringa**, prefisso prima). Risposta `[{id, name}]`. `limit` massimo 50. |
| `GET` | `/api/labels?with_counts=1` | `get_labels_with_counts`. Risposta `[{id, name, name_norm, movements_count}]`. |
| `PUT` | `/api/labels/<int:id>` | Body `{name}`. 400 se `labels.is_valid` dice no. |
| `DELETE` | `/api/labels/<int:id>` | — |

Per tutte, nell'ordine:

1. `session.get('user_id')` assente → **401**;
2. label non trovata **oppure** `label.account_id != session['account_id']` →
   **404** (non 403: non si conferma nemmeno l'esistenza di una risorsa
   altrui). È la lezione di `backlog/task24-0-auth-assessment.md`;
3. input non valido → **400**, e il valore ricevuto **non** torna in pagina;
4. `try/finally` con `db.close()`, come tutte le rotte esistenti.

## 3.2 `_parse_movement_filters()`

Aggiungi `labels`:

```python
labels_raw = request.args.getlist('label')          # ?label=coop&label=buoni
labels = [l for l in (s.strip().lstrip('#') for s in labels_raw) if is_valid(l)]
```

Le grafie non valide si **ignorano in silenzio**: è input non fidato, non si
fa `abort(400)` e non si rimanda in pagina. `active_count` cresce di 1 se
`labels` non è vuota. Il dict ritornato guadagna `labels` e `labels_raw`.

Poi: `labels=f['labels']` va passata a tutte le chiamate che già ricevono gli
altri filtri — `/movements` (riga ~572 e la `get_movements_stats` subito dopo),
`/api/movements`, `/api/movements/export`, e il dict `filters` di
`/api/movements/bulk-update` (riga ~843). Sono i punti che il test verifica.

## 3.3 Il nome del parametro

`?label=` al singolare, ripetuto (`getlist`), come già fa `category_id`.
Non `labels=coop,buoni`: una label può contenere `-` e `_` ma non la virgola,
però l'uniformità col resto della query string vale più della brevità.

## 3.4 La rotta della pagina (lo scheletro, non la pagina)

Il test `api` verifica che `GET /settings/labels` risponda **200**. In questa
fase crei:

- la rotta `settings_labels()` in `app.py`, con lo stesso preambolo delle altre
  (`/settings/categories`, riga ~1259): sessione, `account_id`, `render_template`;
- `templates/ps-setting-labels.html` **minimo**: `{% extends 'ps-nav.html' %}`,
  un `ps-card` con il titolo e un contenitore vuoto.

La pagina vera (tabella, conteggi, modali di rinomina ed eliminazione) è la
**Fase 7**. Qui serve solo che la rotta esista e risponda.

## Trappola

`/movements` passa i filtri **due volte**: una a `get_movements_for_account` e
una a `get_movements_stats`. Se aggiungi `labels` solo alla prima, la pagina
mostra 3 movimenti filtrati e i totali di 40. Il test lo verifica lato
repository (Fase 2) ma non può verificare l'occhio dell'utente: controlla
entrambe le chiamate a mano.
