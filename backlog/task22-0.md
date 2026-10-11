# Task 22.0: Wallet preferito per singolo utente (bugfix MB-004/MB-005)

## Obiettivo
Il "wallet preferito" (MB-004/MB-005) è stato implementato come proprietà
dell'**account**: un unico wallet condiviso da tutti gli utenti dello stesso
account. È un bug — la preferenza deve essere del **singolo utente**: utenti
diversi dello stesso account (es. membri della stessa famiglia) devono poter
avere wallet preferiti diversi, senza che l'uno sovrascriva quello dell'altro.

## Analisi — causa del bug

La preferenza non ha una colonna dedicata: è espressa per convenzione da
`Wallet.order_index == 0`, scoperta per `account_id`
(`WalletRepository.PREFERRED_ORDER_INDEX`, [repository.py](../pyspendless/repository.py)).
Ogni punto che la consuma ragiona per account, non per utente:

- `app.py` — `create()` (form movimento, riga ~428), `api_get_wallets`
  (riga ~1535), `api_set_preferred_wallet`/`api_unset_preferred_wallet`
  (righe ~1640-1715): tutti prendono `account_id` da sessione e non
  distinguono tra gli utenti dello stesso account.
- `mcp_server.py` — `_tool_list_categories`, `_tool_add_movement`,
  `resolve_wallet()`: usano `WalletRepository.get_preferred_wallet(account_id)`
  pur avendo già **sia** `ctx['user_id']` **sia** `ctx['account_id']` nel
  contesto della chiamata (il token MCP è per utente, non per account).

Il modello dati rende il bug inevitabile con l'implementazione attuale: `User`
(models.py:31) ha `account_id`, un account ha più utenti
(`Account.users`, relazione 1:N) — ma il preferito vive sul `Wallet`, che
appartiene all'account, non all'utente che lo sceglie.

## Soluzione

Preferenza per singolo utente, con una colonna dedicata invece di riusare
`order_index` (quella convenzione smette di esistere: due utenti dello stesso
account possono avere preferiti diversi, quindi non si può più "riservare" un
singolo valore di `order_index` per wallet).

### Schema dati
- `User.preferred_wallet_id` (nullable, FK a `Wallet.id`) — [models.py](../pyspendless/models.py).
  `None` è uno stato legittimo ("nessun preferito"), come prima.
- `Wallet.order_index` torna a essere **puro ordinamento di visualizzazione**
  (il suo scopo originale, task7-1): nessun valore riservato, validazione
  semplificata a "intero >= 0".
- Migrazione: [sql/sqllite/NEXT_RELEASE/alter_user_add_preferred_wallet.sql](../sql/sqllite/NEXT_RELEASE/alter_user_add_preferred_wallet.sql).
  `ALTER TABLE User ADD COLUMN preferred_wallet_id` + backfill: per ogni
  account che aveva un wallet a `order_index = 0`, quel wallet diventa il
  preferito iniziale di **tutti** gli utenti dell'account (continuità con il
  comportamento pre-fix, poi ognuno può cambiarlo indipendentemente).

### Codice
- `UserRepository` ([repository.py](../pyspendless/repository.py)): nuovi
  `get_preferred_wallet(user_id)`, `set_preferred_wallet(user_id, wallet_id, account_id)`
  (verifica che utente e wallet appartengano allo stesso account),
  `unset_preferred_wallet(user_id, wallet_id)` (richiede che `wallet_id`
  corrisponda al preferito corrente, stesso vincolo della versione precedente).
  Sono l'unico punto che conosce `User.preferred_wallet_id`.
- `WalletRepository`: rimossi `PREFERRED_ORDER_INDEX`, `MIN_USER_ORDER_INDEX`,
  `get_preferred_wallet`, `set_preferred_wallet`, `unset_preferred_wallet`.
  `validate_order_index` non riserva più lo 0. `delete_wallet` adesso libera
  esplicitamente `User.preferred_wallet_id` dei wallet cancellati (SQLite non
  applica qui il vincolo FK, nessun `PRAGMA foreign_keys`).
- `app.py`: `create()`, `api_get_wallets`, `api_set_preferred_wallet`,
  `api_unset_preferred_wallet` usano `UserRepository` con
  `session.get('user_id')` invece di `WalletRepository` con `account_id`.
- `mcp_server.py`: `_tool_list_categories` e `_tool_add_movement` recuperano
  il preferito con `UserRepository.get_preferred_wallet(ctx['user_id'])`.
  `resolve_wallet()` e la `description` del parametro `wallet` nello schema
  del tool aggiornate per riflettere che il preferito è dell'utente che
  chiama.
- `templates/ps-setting-wallet.html`: nessun cambio di contratto API (stesso
  `is_preferred` in risposta, ora relativo a chi guarda la pagina). Rimossa
  la disabilitazione del campo "Ordine" quando il wallet è preferito (non ha
  più senso: l'ordine non è più legato alla preferenza). Aggiunta una nota
  che il preferito è personale.
- `templates/ps-add-mov.html`: nessun cambio, riceve `preferred_wallet_id`
  già calcolato per l'utente corrente da `app.py`.

## Casi limite
- **Account con due utenti e preferiti diversi**: coperto dal test
  `check_user_repository` in
  [pyspendless/test/test_task22_0.py](../pyspendless/test/test_task22_0.py)
  — impostare il preferito di un utente non deve toccare quello dell'altro.
- **Wallet di un altro account**: `set_preferred_wallet` lo rifiuta (stesso
  controllo multi-tenant già usato altrove).
- **DELETE su un wallet che non è (più) il preferito corrente**: nessun
  effetto, 404 come la versione precedente.
- **Cancellazione del wallet preferito**: il `preferred_wallet_id` pendente
  viene azzerato da `delete_wallet`, non lasciato a puntare a un wallet
  inesistente.
- **Utente senza preferito** (mai impostato, o azzerato): stato legittimo,
  identico a prima — form e MCP ripiegano sul comportamento esistente
  (ultimo wallet usato / primo della lista).
- **Migrazione — account senza wallet a `order_index = 0`**: i suoi utenti
  non vengono toccati dal backfill, restano senza preferito (non è un errore,
  significa solo che quell'account non ne aveva mai impostato uno).
- **Migrazione — account con più wallet storici a `order_index = 0`**: stesso
  criterio deterministico già usato da `get_preferred_wallet` (primo in
  ordine alfabetico), per coerenza con cosa l'utente vedeva come preferito
  prima della migrazione.

## File toccati
- `pyspendless/models.py` — `User.preferred_wallet_id`.
- `pyspendless/repository.py` — `UserRepository` (nuovi metodi),
  `WalletRepository` (rimossa la riserva su `order_index`, `delete_wallet`
  libera i preferiti pendenti).
- `pyspendless/app.py` — `create()`, `api_get_wallets`,
  `api_set_preferred_wallet`, `api_unset_preferred_wallet`,
  `api_update_wallet` (messaggio d'errore).
- `pyspendless/mcp_server.py` — `_tool_list_categories`, `_tool_add_movement`,
  `resolve_wallet()`, schema del tool `add_movement`.
- `pyspendless/templates/ps-setting-wallet.html` — UI preferenza/ordine.
- `pyspendless/dev_mcp_check.py` — commento aggiornato (il controllo stesso
  non cambia: resta "al massimo un preferito **per la chiamata**", vero anche
  per utente).
- `sql/sqllite/NEXT_RELEASE/alter_user_add_preferred_wallet.sql` — nuovo,
  schema + backfill.
- `pyspendless/test/test_task22_0.py` — nuovo, verifica isolata (DB
  SQLite in-memory/temporaneo, non tocca `.env`/il DB configurato).

## Test
Eseguiti in `pyspendless/test/test_task22_0.py` (21 controlli, tutti
superati):
1. Preferito per utente: impostarlo per un utente non influisce sull'altro
   utente dello stesso account (il bug originale).
2. Rifiuto di un wallet di un altro account come preferito.
3. `unset` con `wallet_id` diverso dal preferito corrente → nessun effetto.
4. `order_index` parte da 0 e non è più riservato; `validate_order_index`
   accetta 0 e rifiuta i negativi.
5. Cancellare il wallet preferito azzera `preferred_wallet_id` sull'utente.
6. Backfill: eseguito lo script SQL reale su uno schema "vecchio" costruito a
   mano (pre-task22-0) con due account — uno con un wallet storico a
   `order_index = 0` condiviso da due utenti, uno senza. Verificato che
   entrambi gli utenti del primo account ereditino lo stesso wallet e che
   l'utente del secondo account resti senza preferito.

Non eseguito (richiede l'app avviata in locale e un DB reale, fuori
dall'ambito di una verifica automatica): `dev_mcp_check.py` end-to-end
sull'endpoint `/mcp`. Il comportamento che copre (al massimo un preferito per
chiamata) non cambia nella sostanza, solo nel "di chi" — da verificare
manualmente prima del rilascio in produzione, assieme alla migrazione SQL sul
DB di produzione.
