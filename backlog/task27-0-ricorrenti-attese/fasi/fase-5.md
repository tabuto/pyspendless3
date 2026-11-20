# Fase 5 — CSS, verifica visiva, rilascio

**Chi**: **agente principale**. Non si delega: qui si giudica, e il giudizio è
quello che i subagent non hanno.
**Dipende da**: Fasi 1-4 tutte verdi.
**Fatto quando**: `./tools/build-css.sh` eseguito e `git status` **pulito** su
`ps-tailwind.css`; le quattro schermate di §2 verificate in light e dark;
proposta di rilascio all'utente **e sua conferma**.

## 1. Il CSS — il passo che si dimentica

Le Fasi 3 e 4 introducono classi in `class="..."`. Dal task19-0 la
presentazione è Tailwind compilato, e **l'output compilato è versionato**: sul
server non c'è Node e non c'è una fase di build.

```bash
./tools/build-css.sh
git status    # deve restare PULITO su ps-tailwind.css
```

Se la build **cambia** il file, il commit era incompleto: è il modo di
accorgersene prima che in produzione finisca il CSS vecchio, con le classi nuove
senza stile. Fallimento degradato, non rotto — e quindi facile da non vedere.

Due classi possono mancare in `ps-tailwind.src.css`, e le Fasi 3-4 hanno
l'istruzione di **segnalarlo invece di inventarle**:

- `ps-badge-warning` — il badge dello stato `pending`;
- `ps-badge-secondary` — il badge dello stato `skipped`.

Se mancano, si aggiungono qui, nello stesso `@layer` degli altri `ps-badge-*`,
riusando i token esistenti (`--ps-warning`, `--ps-muted`). **Non** fuori dal
layer: è la causa di `MB-012` (Tom Select scuro su scuro), e il motivo per cui
una regola fuori layer vince su quelle dentro.

## 2. La verifica visiva

Dev server dalla Browser pane, non da Bash. Quattro schermate, **ciascuna in
light e in dark**:

| # | Dove | Cosa si guarda |
|---|---|---|
| 1 | `/home` con 2 proposte | la card c'è, i bottoni stanno in riga su desktop e vanno a capo su mobile (375px) |
| 2 | `/home` senza proposte | la card **non** c'è, e le tre card di navigazione sono dove erano |
| 3 | `/recurrent-movements` | la colonna Stato mostra tutti e cinque gli stati leggibili; il badge `skipped` e il bottone Ripristina non si sovrappongono |
| 4 | `/create?recurrent_id=N` | tipo, categoria, wallet, importo e nota pieni; **la data è quella di scadenza**, non oggi |

La 4 è quella che vale: se la categoria è vuota, è la trappola 1 della Fase 4
(ordine del `dispatchEvent`) e il metro **non** la prende — i controlli di
`contract` sono statici, leggono il file, non eseguono il JS.

Per i dati di prova: un template con `due_day` passato e nessun movimento del
mese (→ `pending`), uno con un movimento del mese (→ `registered`), uno con
`skip_period` del mese corrente, uno con `due_day` futuro, uno senza `due_day`.

## 3. La UAT dell'utente

Prima del rilascio, l'utente prova il giro completo sul suo ambiente. In
particolare il caso che il metro non può verificare: **l'affitto registrato
dalla proposta scompare dalla home**, senza altre azioni (A2).

## 4. La migrazione sul server

`sql/sqllite/NEXT_RELEASE/alter_recurrentmovement_add_due_day.sql` va eseguito
**una volta**, sul database di produzione, **prima** del Reload della web app.
Due colonne nullable: `ADD COLUMN` su SQLite non ricostruisce la tabella e non
blocca niente.

L'ordine conta in un verso solo: codice nuovo su schema vecchio → errore a ogni
query sulle ricorrenti. Schema nuovo su codice vecchio → nessun problema, le due
colonne restano ignorate. Quindi **prima il DDL, poi il Reload**.

## 5. La proposta di rilascio

`0.4.1` → **`0.5.0`**: colonne nuove e funzione nuova, non un fix.

La procedura è quella di `CLAUDE.md`, e **si esegue solo su richiesta esplicita
dell'utente**:

0. `./tools/build-css.sh`, `ps-tailwind.css` aggiornato e **staged**
1. bump di `_APP_VERSION` in `pyspendless/app.py`
2. `git commit`
3. `git tag v0.5.0`
4. `git push && git push --tags`
5. **sul server**: console Bash → `cd /home/tabuto/pyspendless3` → `git pull` →
   **il DDL di §4** → Reload dalla tab *Web*
6. `GET https://tabuto.pythonanywhere.com/version` → `0.5.0`

Il passo 5 ha un pezzo in più rispetto al solito (il DDL). È il punto in cui si
sbaglia l'ordine.

## 6. Chiusura del backlog

- `backlog/features.md`: riga del task → `DONE`
- `backlog/task27-0-ricorrenti-attese/task27-spec.md`: intestazione → stato
  finale, con la data e i file effettivamente toccati
- `MB-013` (deduzione del template sul percorso MCP/Alexa) resta **APERTA**: è
  la conseguenza dichiarata dell'opzione A, non un residuo da chiudere qui
