# Fase 8 — CSS, verifica visiva, rilascio

**Chi**: **agente principale**. **Non si delega** (serve il browser e serve
decidere se la cosa è presentabile).
**Dipende da**: fasi 5, 6, 7 verdi.
**Fatto quando**: tutte e quattro le sezioni di `test_task26_0.py` verdi,
`test_task19_0.py`/`test_task22_0.py`/`test_task23_0.py` verdi, `git status`
pulito **dopo** la build del CSS, e gli screenshot allegati al task.

## 8.1 Il passo che si dimentica

```bash
./tools/build-css.sh
```

`.ps-label-chip` e lo skin di Tom Select sono classi nuove: senza la build, in
produzione finisce il CSS vecchio e le chip non hanno stile — fallimento
degradato, non rotto, e quindi difficile da notare. Il modo di accorgersene è
che **`git status` resti pulito dopo la build**: se la build cambia il file, il
commit era incompleto.

La sezione `contract` del test controlla `.ps-label-chip` **nel `.src.css` e
nel `.css` compilato**: è lì proprio per questo.

## 8.2 Verifica visiva (browser pane)

Sette cose, in light **e** dark:

1. `/create`: aggiunta di una label dal dropdown → la nota cambia in coda;
2. rimozione di una chip da metà testo → nessuno spazio doppio (il caso A3);
3. digitazione di `#coop` a mano nella textarea → la chip compare;
4. `/movements`: chip nelle note, in tabella e nelle card mobile (375 px);
5. cambio pagina di DataTables → le chip ci sono ancora (il caso `draw.dt`);
6. filtro per due label → risultati in AND, badge dei filtri attivi coerente;
7. `Impostazioni → Labels`: rinomina con merge ed eliminazione, coi conteggi.

Più la prova del degrado: con il CDN di Tom Select bloccato, il campo sparisce
e la textarea resta usabile (console pulita).

## 8.3 Rilascio

Oltre alla procedura di `CLAUDE.md` (build CSS → bump `_APP_VERSION` → commit →
tag → push → `git pull` + Reload), **due passi di schema sul server**, dopo il
`git pull` e **prima** del Reload:

```
sqlite3 /home/tabuto/data/pyspendless3.db < sql/sqllite/NEXT_RELEASE/create_label.sql
python migrations/backfill_labels.py
```

Nessuna dipendenza Python nuova: niente `pip install`, nessun rischio di quota
disco.

- `CREATE TABLE` dimenticato → ogni salvataggio di movimento va in errore:
  fallimento **rotto**.
- backfill dimenticato → le label storiche non compaiono
  nell'autocompletamento finché i movimenti non vengono risalvati: fallimento
  **degradato**.

La procedura si **propone** all'utente e si attende conferma: non si esegue di
iniziativa (regola non negoziabile di `CLAUDE.md`).
