# Task 21.0: Correzione massiva dei movimenti (categoria / descrizione)

## Obiettivo
Nella pagina `/movements` l'utente filtra i movimenti con i filtri esistenti
(data, wallet, tipo categoria, categorie, keyword). Serve una funzione di
**correzione massiva**: dato l'insieme di movimenti risultante dai filtri
correnti, permettere di impostare una nuova **categoria** e/o una nuova
**descrizione (note)**, e applicare il cambiamento a **tutti** i movimenti
selezionati dai filtri (non solo quelli visibili/paginati a schermo).

È lo stesso principio già usato da "Esporta" (task16-0): i filtri della
pagina diventano la sorgente del set di record su cui agire, non la tabella
renderizzata.

## Analisi — stato attuale

### Filtri e recupero movimenti (riuso, non reinventare)
- `_parse_movement_filters()` ([app.py](../pyspendless/app.py)) estrae da
  query string: `date_from`, `date_to`, `wallet_id`, `category_type`,
  `category_ids` (multiplo), `keywords`.
- `MovementRepository.get_movements_for_account(...)` ([repository.py:696](../pyspendless/repository.py:696))
  applica questi filtri e ritorna la lista di `Movement`.
- Pattern di riferimento già esistente: `/api/movements/export` (GET,
  [app.py:719-773](../pyspendless/app.py:719)) fa esattamente
  `_parse_movement_filters()` → `get_movements_for_account(...)` → agisce su
  tutto il risultato, ignorando paginazione client-side (desktop DataTables)
  e infinite scroll (mobile). La correzione massiva deve seguire lo stesso
  schema per restare coerente con "Esporta".

### Modello dati — attenzione ai campi legacy
`Movement` ([models.py:114](../pyspendless/models.py:114)) ha sia il campo
FK `category_id` sia il campo legacy testuale `category` (nome categoria
come stringa, usato da viste/CSV/import). Quando si aggiorna la categoria di
un movimento **entrambi i campi vanno scritti insieme**, esattamente come fa
già `api_create_movement`/update singolo
([app.py:843](../pyspendless/app.py:843)-849): `category = category.name` e
`category_id = category.id`. Un bulk update che tocchi solo `category_id` o
solo `category` lascerebbe l'anagrafica incoerente (CSV export/import
leggono il campo legacy `category`, non la FK).

`update_movement(movement_id, data)` ([repository.py:759](../pyspendless/repository.py:759))
esiste solo per update singolo (un commit per chiamata); per un bulk update
va evitato un commit per riga — vedi sotto.

### Vincolo tipo categoria
`Category.type` è `expense|income|transfer` ([models.py:90](../pyspendless/models.py:90)).
Se tra i movimenti selezionati dai filtri coesistono entrate e uscite (es.
filtro senza `category_type`), e si tenta di assegnare una categoria di tipo
`expense` a un movimento che è un'entrata (o viceversa), il dato diventa
incoerente con la UI (dashboard/grafici raggruppano per `category_type`).
Va deciso un comportamento esplicito, non silenzioso (vedi "Casi limite").

## Specifiche funzionali

### 1. Nuovo endpoint backend
`POST /api/movements/bulk-update`

- Riceve via **query string** gli stessi parametri di filtro di
  `_parse_movement_filters()` (stesso schema di `/api/movements/export`),
  così il payload JSON del body contiene solo i valori da applicare:
  ```json
  { "category_id": 12, "note": "Spesa ricorrente" }
  ```
  Almeno uno tra `category_id` e `note` deve essere presente; se entrambi
  assenti → `400`.
- Verifica autenticazione (`session.get('user_id')`) e che `category_id`,
  se fornito, appartenga a `account_id` corrente (stesso controllo già fatto
  in `api_create_movement`, [app.py:823-828](../pyspendless/app.py:823)).
- Recupera il set di movimenti con `get_movements_for_account(...)` usando i
  filtri ricevuti.
- Applica le modifiche **in un solo giro di sessione/commit** (non N commit):
  per ciascun `Movement` del set, se `category_id` è presente setta sia
  `movement.category_id` sia `movement.category = category.name`; se `note`
  è presente setta `movement.note`. Un solo `db.commit()` a fine ciclo.
- Risponde con `{ "updated": <n> }` e status `200`. Se il set è vuoto,
  rispondere comunque `200` con `updated: 0` (nessun errore, nessuna no-op
  silenziosa percepita come bug).

Nuovo metodo in `MovementRepository` (non riusare `update_movement` riga per
riga, per evitare N query + N commit su dataset potenzialmente grandi):
```python
def bulk_update_movements(self, account_id, filters: dict,
                           category=None, category_id=None,
                           note=None) -> int:
    movements = self.get_movements_for_account(account_id=account_id, **filters)
    for m in movements:
        if category_id is not None:
            m.category_id = category_id
            m.category = category
        if note is not None:
            m.note = note
    self.db.commit()
    return len(movements)
```

### 2. UI — pagina `/movements`
Nuovo pulsante **"Correzione massiva"** accanto a "Esporta"
([ps-show-mov.html:148](../pyspendless/templates/ps-show-mov.html:148)),
stesso stile (`btn-outline-*`), stesso criterio di abilitazione (disabled se
`movements` è vuoto con i filtri correnti).

Click → apre un modal Bootstrap con:
- Riepilogo in cima: "Verranno modificati **N** movimenti corrispondenti ai
  filtri attivi" (N = conteggio dei movimenti correnti lato server o, su
  mobile, il `total` già noto da `/api/movements`).
- Campo **Categoria** (select, opzionale, stesso elenco categorie della
  pagina) — "Lascia vuoto per non modificare la categoria".
- Campo **Note / Descrizione** (textarea, opzionale) — "Lascia vuoto per non
  modificare la descrizione". Il valore sostituisce integralmente la nota
  esistente su ogni movimento selezionato (non è un find&replace).
- Pulsante "Applica" disabilitato finché nessuno dei due campi è compilato.
- Conferma esplicita prima dell'invio (es. `confirm()` nativo o un secondo
  step nel modal) che riporti il numero N — è un'operazione **non
  reversibile** (nessun undo), va trattata come le altre azioni distruttive
  del progetto.

Alla conferma: `POST /api/movements/bulk-update?<stessa query string dei
filtri correnti>` con body `{category_id?, note?}` → messaggio di esito
("N movimenti aggiornati") → refresh della tabella/card list con i filtri
correnti invariati (stesso refresh già fatto dopo altre operazioni sulla
pagina).

### 3. Casi limite
- **Nessun movimento nel set filtrato**: pulsante disabled (stesso criterio
  di "Esporta").
- **Filtri troppo ampi (es. nessun filtro attivo)**: il modal deve comunque
  mostrare il conteggio reale N prima di applicare, così l'utente vede se
  starebbe per modificare "tutti i movimenti dell'account" ed eventualmente
  annulla.
- **Categoria di tipo diverso da quella dei movimenti selezionati** (es.
  filtro misto entrate/uscite, o nessun filtro `category_type`, e si
  assegna una categoria `expense` anche a movimenti che sono entrate): da
  **bloccare lato backend con errore esplicito** (`400`, messaggio "La
  categoria selezionata non è compatibile con alcuni movimenti selezionati
  (entrata/uscita)"), non silenziosamente ignorato né applicato in modo
  incoerente. In alternativa più semplice da implementare: richiedere che
  il filtro `category_type` sia impostato (non "tutti") quando si sceglie di
  cambiare categoria, e validarlo lato backend confrontando `category.type`
  con `category_type` del filtro.
- **Nota vuota esplicita**: distinguere "non toccare la nota" (campo non
  inviato / `null`) da "azzera la nota" (campo inviato come stringa vuota
  `""`) — il frontend deve inviare il campo solo se l'utente lo ha
  effettivamente compilato o scelto di azzerare, altrimenti ometterlo dal
  body.

## File toccati (previsti)
- `pyspendless/app.py` — nuova route `api_bulk_update_movements()`.
- `pyspendless/repository.py` — nuovo metodo `MovementRepository.bulk_update_movements(...)`.
- `pyspendless/templates/ps-show-mov.html` — pulsante "Correzione massiva",
  modal, JS di chiamata all'endpoint e refresh post-applicazione.
- `backlog/features.md` — nuova riga in tabella Task/Descrizione/Stato.

## Test
- Filtro per categoria X + applicazione nuova categoria Y → tutti i
  movimenti del set risultano con `category_id` e `category` coerenti con Y
  (non solo la pagina visibile).
- Filtro con keyword su note + applicazione nuova descrizione → tutte le
  note dei movimenti filtrati sostituite.
- Set vuoto → pulsante disabled, nessuna chiamata.
- Categoria incompatibile con `category_type` dei movimenti selezionati →
  errore 400, nessuna modifica applicata (verificare che il commit non sia
  parziale).
- Mobile (infinite scroll) e desktop (DataTables paginato) devono operare
  entrambi sull'intero set filtrato, non solo sulla pagina caricata.
