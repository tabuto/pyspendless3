# Fase 0 — Baseline

**Agente**: `ps-contract` (estrazione) + principale (browser, DB)
**Stima**: 1-1.5 gg
**Nessuna modifica al markup.** Se in questa fase cambia una riga di template,
la fase è sbagliata.

## Perché viene prima

La baseline e il contratto vanno scritti *prima* che una riga di markup cambi.
È la differenza fra "abbiamo rifatto la grafica" e "abbiamo rifatto la grafica
e possiamo dimostrare che non abbiamo rotto niente".

## Attività

### 0.1 — DB di sviluppo popolato

Serve un DB locale che copra tutti gli stati che le pagine sanno mostrare,
altrimenti metà delle verifiche non è osservabile:

- movimenti su **almeno 2 anni** (servono alle dashboard e al confronto storico)
- **almeno un mese con movimenti dopo il giorno 12** (serve a 0.4)
- ≥ 2 wallet, categorie sia `expense` sia `income`
- ≥ 1 spesa ricorrente
- ≥ 1 invito pendente
- l'utente admin (`ADMIN_USER_ID` da `.env`), per la pagina `/settings/admin`
- abbastanza movimenti da superare le 25 righe (paginazione DataTables) e le
  20 della prima pagina API (infinite scroll)

### 0.2 — Contratto DOM completo

Lancia `ps-contract` sui 16 template renderizzati. Produce due elenchi:
identificatori critici **mancanti** dal `CONTRACT` in
`pyspendless/test/test_task19_0.py`, e voci **obsolete**.

Integra il CONTRACT con i mancanti. Questo è l'unico momento in cui il CONTRACT
si allarga liberamente: da Fase 1 in poi, toglierne una voce richiede una riga
di motivazione nel task.

### 0.3 — Test verde sul codice attuale

```bash
cd /Users/fradidio/Sviluppo/pyspendless3
.venv/bin/python -m pyspendless.test.test_task19_0
```

Se fallisce **ora**, il problema è nel test o nelle fixture, non nell'app:
l'app funziona. Casi attesi al primo giro:

- `SkipTest` "Nessun utente nel DB locale" → manca 0.1
- 302 invece di 200 su una rotta → la sessione finta non ha tutte le chiavi che
  quella rotta controlla; guarda cosa legge in `app.py`
- id dichiarato mancante ma presente nel template → probabile errore di
  trascrizione nel CONTRACT, correggi il CONTRACT

### 0.4 — Verifica empirica: ordinamento per data

Apri `/movements` in Chrome con un filtro su un mese che abbia movimenti dopo
il giorno 12. Confronta l'ordine visualizzato nella tabella con l'ordine
restituito dal server (`move_date DESC`).

Sospetto: DataTables riordina client-side la colonna 0 renderizzata
`gg/mm/aaaa`, il plugin `date-eu` non è caricato, `Date.parse` fallisce e
l'ordinamento diventa lessicografico — cioè per giorno del mese.

- **Confermato** → apri una voce `MB-NNN` in `backlog/00-task-minor-bugfix.md`
  e correggila **subito e separatamente** con `data-order="{{ mov.move_date.isoformat() }}"`
  sul `<td>` (`ps-show-mov.html:187`). Una riga, indipendente dal restyling.
  Non ha senso portarsi dietro un bug di ordinamento per settimane.
- **Smentito** → annotalo nel task, così nessuno ci torna sopra.

### 0.5 — Misura degli asset

Su `/movements`, con `read_network_requests`: peso trasferito e numero di
richieste, divisi per origine (CDN DataTables, jQuery, Chart.js, Tom Select,
Bootstrap, AdminLTE locale). Sostituisce le stime del piano con numeri veri, e
dà il metro per misurare il guadagno a fine lavoro.

### 0.6 — Screenshot before

`docs/ui-baseline/`, naming `<rotta>__<viewport>__<tema>.png`.

16 pagine × 3 viewport (375 / 768 / 1440). Più gli stati non di default, che
sono quelli che si dimentica sempre di catturare e che servono davvero:

- i 10 modal aperti
- tab "Entrate" su `/settings/categories`
- pannello filtri aperto con badge conteggio su `/movements`
- card-list mobile dopo uno scroll (seconda pagina caricata)
- un alert di successo dopo un salvataggio
- progress bar durante un import
- "Zona pericolosa" con il bottone abilitato (dopo aver digitato ELIMINA)

> **Sul come**: per la matrice completa conviene uno script Playwright, non
> l'agente. Un centinaio di screenshot guidati a mano sono lenti e, soprattutto,
> non riproducibili — e fra il "before" e l'"after" di tre settimane dopo serve
> la stessa inquadratura. L'agente copre gli stati interattivi, che in
> Playwright costerebbero più a scriptare che a fare a mano.

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A0.1 | DB di test popolato secondo 0.1 | query di conteggio su movimenti, wallet, categorie, ricorrenti, inviti |
| A0.2 | `CONTRACT` integrato con tutti i critici trovati da `ps-contract` | l'elenco "mancanti" dell'agente è vuoto alla seconda passata |
| A0.3 | **`.venv/bin/python -m pyspendless.test.test_task19_0` esce 0** | exit code |
| A0.4 | Ordinamento date: confermato o smentito, per iscritto | nota nel task; se confermato, `MB-NNN` aperta e risolta |
| A0.5 | Misura asset `/movements` registrata | tabella nel task con KB e numero richieste |
| A0.6 | `docs/ui-baseline/` contiene le 16 pagine × 3 viewport + gli stati elencati | conteggio file |

## Definition of done

Il test di contratto è verde sul codice **non modificato**, la baseline visiva
è archiviata, e le due verifiche empiriche hanno una risposta scritta.

Da qui in poi, ogni fallimento del test di contratto è una regressione
introdotta dal restyling — non un dubbio sul test.
