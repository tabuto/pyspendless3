# Fase 4 — Verifica, CSS, regressione

**Chi**: **agente principale**. Non si delega: qui si giudica, e il giudizio
visivo è il mandato che resta all'agente principale (`CLAUDE.md`, "Delega a
subagent").
**Dipende da**: Fasi 1, 2, 3 verdi.
**Fatto quando**: tutti i punti della checklist qui sotto sono verificati, e
quello che non torna è scritto da qualche parte (voce `MB-NNN` o riga nel
riepilogo) invece di restare nella testa di chi ha guardato.

## 1. Le suite

```bash
cd pyspendless
.venv/bin/python test/test_task28_0.py          # tutte le sezioni
.venv/bin/python test/test_task19_0.py
.venv/bin/python test/test_task22_0.py
.venv/bin/python test/test_task23_0.py
.venv/bin/python test/test_task26_0.py
```

Le quattro di regressione **non devono passare da verde a rosso**.
`test_task26_0.py` è la più interessante delle quattro: il suo controllo
"`bulk_update_movements` registra le label" (`test_task26_0.py:286`) chiama il
metodo con la firma vecchia ed è la prova che il contratto non si è rotto —
se diventa rosso, la Fase 1 ha cambiato qualcosa che non doveva.

`test/test_task1_3.py` è **già rosso** da prima (`ModuleNotFoundError: No
module named 'conf'`) e non fa parte della regressione.

E la grammatica JS, che la Fase 3 ha toccato il file che la contiene:

```bash
node tools/check-labels-js.mjs
```

## 2. Il CSS

```bash
./tools/build-css.sh
git status --short pyspendless/static/css/ps-tailwind.css
```

Se la build **cambia** il file, la Fase 3 ha introdotto classi nuove e il CSS
compilato va messo in staging: sul server non c'è Node e l'output è versionato.
Se non lo cambia, non c'è niente da fare — ed è il caso previsto, perché la
Fase 3 ha il mandato di usare solo classi già in pagina.

Il modo di accorgersene è proprio questo: `git status` che resta pulito dopo
una build. Se resta sporco e si committa senza, in produzione finisce il CSS
vecchio e il campo nuovo non ha stile — fallimento degradato, non rotto, e per
questo difficile da notare.

## 3. La prova manuale

Quello che le regex della sezione `contract` non possono vedere. Su
`/movements`, con qualche movimento filtrato:

| # | Prova | Atteso |
|---|---|---|
| 1 | apri la modale, guarda il campo "Aggiungi label" | larghezza piena del contenitore, dropdown allineato al campo: se è largo 0 o il dropdown esce dalla modale, l'init non ha aspettato `shown.bs.modal` |
| 2 | digita 2 caratteri | il dropdown propone le label esistenti dell'account |
| 3 | digita `ciao!` e premi Invio | rifiuto con il messaggio sotto il campo, nessun `alert()` |
| 4 | scegli una label e premi Applica | conferma che **nomina** la label, poi la pagina si ricarica e le chip compaiono nelle note dei movimenti filtrati, **accanto** al testo che c'era |
| 5 | rilancia la stessa operazione | niente raddoppia |
| 6 | tema **dark** | campo, chip e dropdown leggibili: è la lezione di `MB-012` |
| 7 | mobile (viewport 375) | la modale resta usabile e il campo non sfora |
| 8 | chiudi e riapri la modale | il campo è ancora lì e funziona (l'istanza non si ricostruisce, la guardia regge) |
| 9 | solo "Nuova descrizione", senza label | comportamento di prima del task, identico |
| 10 | pagina `Impostazioni → Labels` | l'avviso riscritto distingue aggiunta e sostituzione |

La prova 4 è quella che chiude il task: è il criterio A1 guardato con gli occhi
invece che con un `assert`.

## 4. Le cose da scrivere, non da ricordare

1. **R2 della specifica**: `bulk-update` non valida `len(note)` contro
   `MAX_NOTE_LENGTH`, mentre il percorso nuovo rispetta il limite per
   movimento. È preesistente: si apre una voce `MB-NNN` in
   `backlog/00-task-minor-bugfix.md` (stato `APERTA`, con "Dove" e "Perché") e
   **non** si corregge qui.
2. **`backlog/features.md`**: la riga del task28-0 passa da `PIANIFICATO` a
   `DONE`.
3. **`task28-spec.md`**: lo **Stato** in testa passa da `PIANIFICATO` a
   `IMPLEMENTATO`, con la data.
4. Se un subagent ha segnalato una scelta non coperta dalla specifica, la
   decisione va scritta nella specifica (§8), non lasciata nel commento del
   codice.

## 5. Rilascio

**Non si esegue di iniziativa.** Se le modifiche sembrano da rilasciare, si
**propone** la procedura di `CLAUDE.md` ("Rilascio / Deploy") e si attende
conferma: bump di `_APP_VERSION` (da `0.4.1` a `0.4.2` — è una feature su una
funzione esistente, non un cambio di modello dati), commit, tag, push, e il
passo manuale su PythonAnywhere (`git pull` + Reload), con la verifica finale
su `GET /version`.
