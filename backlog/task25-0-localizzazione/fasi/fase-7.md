# Fase 7 — Impostazioni

**Chi**: **7 × `ps-i18n-template`** su **haiku**, in worktree, in parallelo.
**Durata**: 1-2 giorni.
**Dipende da**: Fase 3 verde e committata; `ps-setting-profile.html` dipende
anche dalla **Fase 2** (la card "Lingua" nasce lì).

Sono le pagine più dense del progetto: ~190 testi e ~120 stringhe nel JS, più
della metà di tutto il lavoro delle fasi 3-7. Sette invocazioni, sette file
disgiunti.

---

## Le sette invocazioni

| # | File | Testi | Attributi | JS |
|---|---|---:|---:|---:|
| 7.A | `ps-setting-profile.html` | 55 | 2 | 17 |
| 7.B | `ps-setting-group.html` | 47 | 5 | 40 |
| 7.C | `ps-setting-categories.html` | 36 | 3 | 20 |
| 7.D | `ps-setting-wallet.html` | 21 | 2 | 26 |
| 7.E | `ps-setting-import-export.html` | 27 | 0 | 6 |
| 7.F | `ps-setting-admin.html` | 22 | 1 | 9 |

E uno che **non** si fa: `ps-recurrent-mov.html` (29 testi + 10 nel JS) non è
una pagina di impostazioni, ma è rimasta senza fase. **Va aggiunta qui come
7.G**: è l'unico template dell'applicazione che altrimenti resterebbe fuori.

Il conto torna solo includendolo: 22 template meno `_styleguide.html` (pagina
di sviluppo) = **21 da lavorare**, di cui 8 in Fase 3, 3 in Fase 5, 3 in
Fase 6, **7 qui**.

---

## Note per file

### `ps-setting-profile.html` (7.A)

La pagina con più stringhe. Contiene i token personali (connettore Claude) e le
connessioni OAuth (task23-0), e dalla Fase 2 anche la card "Lingua".

- Il **valore** di un token generato (`id="newTokenValue"`) non si tocca: è un
  segreto reso in un campo readonly.
- `{{ mcp_url }}` non si avvolge.
- I 10 messaggi nel JS (conferme di revoca, esiti) si avvolgono: li legge
  l'utente.
- Gli `id` dei tre `<dialog>` (`addTokenModal`, `showTokenModal`) sono nel
  contratto DOM: si preservano.

### `ps-setting-group.html` (7.B)

**40 stringhe nel JS**, il massimo del progetto: inviti, membri, conferme di
rimozione. Tutte le `confirm(...)` si avvolgono. Attenzione alle frasi che
contengono l'email dell'invitato: sono interpolate → `{% trans %}` o
`_('...%(email)s...') % {...}` nel JS reso da Jinja.

### `ps-setting-categories.html` (7.C) e `ps-setting-wallet.html` (7.D)

I nomi di categorie e wallet **sono dati dell'utente**: non si avvolgono mai.
Si avvolgono le etichette dei tipi (`expense`/`income`/`transfer` → "Spesa",
"Entrata", "Trasferimento") **se** sono scritte nel template; se arrivano da
Python sono Fase 4.

In `ps-setting-wallet.html` c'è la UI del wallet preferito (task22-0): la
dicitura "preferito" va al glossario come **default wallet** (§8 del piano).

### `ps-setting-import-export.html` (7.E)

⚠️ **Il punto più importante di questa fase.** La pagina descrive il formato
CSV, e l'header del CSV — `Data, Categoria, Wallet, Entrata, Spesa, Note` — è un
**formato di scambio** che l'import rilegge per nome (`app.py:1983`).

- Le **istruzioni** si avvolgono.
- I **nomi delle colonne**, ovunque siano citati come nomi di colonna, **no**:
  tradurli nella pagina farebbe credere all'utente che il CSV accetti header
  inglesi, e il file che preparerebbe non si importerebbe.

Se la citazione è ambigua, la si lascia in italiano e si segnala: è un caso in
cui sbagliare per prudenza costa nulla.

### `ps-setting-admin.html` (7.F)

Pagina riservata all'admin (`is_admin`). Si avvolge come le altre: è comunque
interfaccia.

### `ps-recurrent-mov.html` (7.G)

29 testi + 10 nel JS. `{{ rm.last_move_date.strftime('%d/%m/%Y') }}` (riga 99):
il formato è Fase 8, qui si avvolge solo l'etichetta che lo accompagna.

---

## Criteri di accettazione

### Verificabili dal subagent

| # | Criterio | Come si verifica |
|---|---|---|
| A7.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code |
| A7.2 | `tools/check-i18n.py --file <file assegnato>` esce **0** | exit code |
| A7.3 | Nessun nome di colonna CSV tradotto (7.E) | grep su `Categoria`, `Entrata`, `Spesa` nel contesto dell'header |
| A7.4 | Nessun `_()` su nomi di categoria, wallet, gruppo, email, token | grep |
| A7.5 | Gli `id` dei `<dialog>` e dei form preservati | diff |
| A7.6 | Stesso numero di `confirm(` e `alert(` di prima | conteggio: un messaggio non deve sparire |
| A7.7 | `git status --short` mostra solo il file assegnato, niente `translations/` | ispezione |

### Verificabili solo dall'agente principale

| # | Criterio |
|---|---|
| A7.8 | Le sette pagine si rendono in light e in dark, a 375 px e a desktop |
| A7.9 | Generazione e revoca di un token personale funzionanti |
| A7.10 | Invito a un gruppo: il messaggio con l'email è corretto e l'email **non** è tradotta |
| A7.11 | Rinomina di una categoria e cambio del wallet preferito funzionanti |
| A7.12 | **Export → import dello stesso file**: round-trip riuscito. È la prova che l'header CSV non si è mosso |
| A7.13 | Il `.pot` dopo `build-i18n.sh` contiene ~650 msgid: tutte le pagine sono dentro |
| A7.14 | La whitelist di `check-i18n.py` è **vuota** e `tools/check-i18n.py` senza `--file` esce 0 |
| A7.15 | `git diff --stat` tocca solo `templates/**` |

## Definition of done

Tutti i 21 template dell'applicazione sono avvolti, la whitelist è vuota, e il
round-trip export→import del CSV funziona ancora. L'app è ancora interamente
in italiano, e deve esserlo: l'inglese arriva in Fase 9.
