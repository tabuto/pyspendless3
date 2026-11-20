# Fase 0 — Il metro di misura

**Chi**: **agente principale**. **Non si delega.**
**Dipende da**: niente.
**Fatto quando**: `pyspendless/test/test_task28_0.py` esiste,
`.venv/bin/python test/test_task28_0.py` gira e stampa `0 controlli superati,
N falliti` — con **una riga** per ogni controllo, non uno stack trace.
**Vincolo cardine**: **nessun file applicativo viene modificato.** Se in questa
fase cambia una riga di `app.py`, `repository.py`, `ps-labels.js` o di un
template, la fase è sbagliata.

## Perché non si delega

Qui si scrive il criterio con cui si valuteranno le tre fasi successive.
Delegare a un subagent la scrittura del proprio metro è il modo più diretto di
ottenere un metro che dice sempre "fatto".

## Cosa produce

| File | Ruolo |
|---|---|
| `pyspendless/test/test_task28_0.py` | lo script di controllo, 3 sezioni selezionabili, exit code 0/1 |

Nient'altro: non c'è schema da cambiare (nessuna colonna, nessuna migrazione —
spec §1), e `ps-py`/`ps-ui` sono profili durevoli che esistono già.

```bash
cd pyspendless
.venv/bin/python test/test_task28_0.py repo        # Fase 1
.venv/bin/python test/test_task28_0.py api         # Fase 2
.venv/bin/python test/test_task28_0.py contract    # Fase 3
.venv/bin/python test/test_task28_0.py             # tutte
```

Indipendenti: la Fase 3 può lavorare con `contract` rossa e le altre verdi.
Finché una fase non è implementata, la sua sezione fallisce con **un** messaggio
che dice cosa manca.

## I controlli

I 16 casi di `repo`, i 10 di `api` e i 9 di `contract` sono elencati in
`task28-spec.md` §9 — questa fase li traduce in codice, uno a uno, senza
aggiungerne e senza sceglierne un sottoinsieme.

Tre punti dove il test è più delicato di quello che sembra:

1. **Il caso 7 di `repo` (una sola chiamata a `sync_from_note`)** si fa con una
   spia, non con un timer: si avvolge `LabelRepository.sync_from_note` in una
   funzione che incrementa un contatore e delega all'originale, si lancia
   `bulk_update_movements` su 5 movimenti e si verifica `calls == 1`. È il solo
   modo di rendere D4 un exit code invece di un'opinione sulle prestazioni.
2. **Il caso 10 (sforo della nota)** si costruisce con una nota calcolata, non
   con 497 caratteri scritti a mano: `'x' * (MAX_NOTE_LENGTH - 3)` e la label
   `'casa'` (`' #casa'` sono 6 caratteri). Se un domani `MAX_NOTE_LENGTH`
   cambia, il caso resta valido.
3. **Il caso 12 (10 label fra cui quella richiesta)** distingue "saltato" da
   "no-op" e vale la pena scriverlo prima dell'implementazione: è esattamente
   la riga che un'implementazione affrettata sbaglia, perché conta le label
   della nota e si ferma al limite senza guardare *quali* sono.

Per la sezione `api` si usa il Flask test client su app in-memory, come
`test_task23_0.py`; il caso 10 di `api` (`data-ps-labels-max` nella pagina) è
l'unico che rende `/movements`, e serve a non far passare una Fase 2 che
dimentica il contesto del `render_template`.

Per `contract` si legge il file e si usano regex, come `test_task19_0.py`: i
controlli sono statici per scelta, e quello che le regex non possono vedere
(Tom Select che si misura bene dentro la modale, il dark mode del campo) è il
mandato della Fase 4, dichiarato lì come verifica manuale.

## Due cose da accertare prima di chiudere la fase

1. **La regressione è verde?** Le quattro suite elencate in `CLAUDE.md` ("Come
   si verifica") passano, e `test_task1_3.py` è già rosso da prima. Se qualcosa
   è cambiato, si accerta **adesso**: una suite già rossa prima della Fase 1
   renderebbe impossibile distinguere un danno nuovo da uno preesistente.
2. **`test_task19_0.py` va aggiornato?** Il `CONTRACT` di quel file elenca gli
   `id` di `/movements` (`test_task19_0.py:193`) e non conosce `bulk-labels`.
   Aggiungere un `id` **non** lo fa fallire (controlla la presenza, non
   l'assenza di altri): si verifica che sia così e si lascia il file in pace.
   Se invece fallisse, si aggiunge `"bulk-labels"` alla voce
   `/movements` — ed è **l'unica** modifica ammessa a una suite esistente in
   tutto il task.

Gli altri vincoli (Python 3.9, nessuna dipendenza nuova, 404 e non 403, stile,
test in-memory) **non si ripetono qui**: stanno in `CLAUDE.md`, in copia unica,
ed è quella che i subagent leggono.

## Il metro va validato, non solo scritto

Come in task26-0 e task27-0: i casi si eseguono contro un'implementazione di
riferimento usa-e-getta, **scritta fuori dal repo e buttata**, finché le tre
sezioni non sono verdi. Serve a dimostrare che i casi sono coerenti fra loro e
che l'harness **sa** diventare verde. Un metro che non può passare è peggio di
nessun metro.

Quell'implementazione non entra nel repo: scriverla è la Fase 1.
