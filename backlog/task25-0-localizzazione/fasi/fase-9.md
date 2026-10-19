# Fase 9 — La traduzione `en_GB`, il QA e la documentazione

**Chi**: 1-2 × agente di traduzione su **haiku** per la prima passata, con
**revisione dell'agente principale**; il QA e la documentazione al principale.
**Durata**: 1-2 giorni.
**Dipende da**: Fase 8 verde e committata.

Fino a qui l'app è stata interamente in italiano, per scelta: avvolgere e
tradurre nello stesso passaggio avrebbe reso impossibile distinguere un errore
di wrapping da un errore di traduzione. Qui si traduce, e il contratto DOM
resta la rete di sicurezza — perché in `it` niente deve cambiare.

---

## 9.1 Il glossario, prima della traduzione

Il punto **P7** va chiuso **adesso**: la bozza è in `piano-localizzazione.md`
§8, e va confermata dall'utente. Dopo, viene copiata in
`pyspendless/translations/GLOSSARIO.md` e citata nel brief dell'agente di
traduzione.

Il motivo dell'ordine: cambiare "transaction" in "movement" su un catalogo già
tradotto è un trova-e-sostituisci, ma su 900 stringhe qualche occorrenza
sfugge, e un'app che dice "transaction" in una pagina e "movement" in un'altra
sembra tradotta male anche quando ogni singola frase è giusta.

## 9.2 La traduzione

L'agente principale rigenera il catalogo (`./tools/build-i18n.sh`) e lo passa
all'agente di traduzione a **blocchi**, non tutto insieme: `.po` da ~900 msgid
è troppo per una invocazione, e un file così grande riscritto in un colpo è
impossibile da rivedere.

Divisione suggerita, per area funzionale (il `.po` conserva il riferimento al
file di origine di ogni msgid, quindi i blocchi si ritagliano per
`#: pyspendless/templates/...`):

| Blocco | Origine | msgid attese |
|---|---|---|
| 9.A | shell, navigazione, accesso (Fase 3) | ~60 |
| 9.B | movimenti (Fase 5) | ~110 |
| 9.C | dashboard e report (Fase 6) | ~75 |
| 9.D | impostazioni (Fase 7) | ~310 |
| 9.E | messaggi Python (Fase 4) | ~240 |

Regole per chi traduce:

1. **Il glossario vince** sulla scelta migliore nel singolo caso. Coerenza
   prima di eleganza.
2. **I placeholder si copiano identici**, nome compreso. Un `%(num)d` che
   diventa `%(number)d` è un `KeyError` in produzione — e `check-i18n.py` lo
   becca, ma meglio non arrivarci.
3. **Le forme plurali**: il `.po` dichiara `nplurals=2` per l'inglese; entrambe
   vanno riempite, anche quando sono identiche.
4. **Sentence case** nei bottoni e nei titoli (`Add transaction`), coerente con
   l'italiano attuale.
5. **Niente `fuzzy`**: una traduzione marcata fuzzy non viene usata e
   `build-i18n.sh` fallisce (Fase 1 §1.7). Se un msgid non si sa tradurre, si
   lascia **vuoto** e si segnala: vuoto significa "resta in italiano", che è un
   fallimento onesto.
6. **Non si traducono**: nomi propri (`PySpendless`), `EUR`, i nomi delle
   colonne CSV (restano in italiano, sono un formato di scambio), e le stringhe
   già inglesi (`Login with Google`).

## 9.3 QA incrociato

Lo fa l'agente principale, in Chrome, su **entrambe** le lingue:

- il set `it` confrontato con `docs/ui-after/` del task19-0 → **deve essere
  identico** (criterio A1);
- il set `en_GB` archiviato in `docs/ui-i18n-en/`, cercando: troncamenti,
  bottoni che vanno a capo, tabelle che sfondano a 375 px. L'inglese è più
  corto dell'italiano quasi sempre — ma non nelle etichette dei bottoni, dove
  "Save" è più corto di "Salva" e "Settings" è più lungo di "Impostazioni";
- le due lingue in light **e** in dark;
- il percorso completo login → onboarding → movimento → dashboard → export in
  `en_GB`.

## 9.4 Documentazione

| File | Cosa |
|---|---|
| `CLAUDE.md` | passo 0-bis della procedura di rilascio (`./tools/build-i18n.sh`); nel passo 5, il `pip install` sul server **prima** del Reload; una sezione gemella di "CSS: il passo che si dimentica" sui cataloghi |
| `pyspendless/README.md` | setup locale (`pybabel`), come si aggiunge una lingua, come si corregge una traduzione |
| `backlog/features.md` | riga del task da `SPEC` a `DONE` |
| `.gitignore` | commento che spiega **perché** i `.mo` sono versionati, così nessuno li "ripulisca" credendoli artefatti di build |
| `pyspendless/migrations/` o il README | la nota sull'`ALTER TABLE` da eseguire sul DB di produzione |
| `backlog/task25-0-localizzazione/note-verifica.md` | quello che il piano non aveva previsto: serve a chi pianificherà il prossimo task |

---

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A9.1 | `./tools/build-i18n.sh` esce 0 e riporta **100% tradotto**, 0 fuzzy | statistiche |
| A9.2 | `tools/check-i18n.py` (modo completo) esce **0**, whitelist vuota | exit code |
| A9.3 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce **0** | exit code — in `it` niente è cambiato |
| A9.4 | `.venv/bin/python -m pyspendless.test.test_task25_0` esce **0** | exit code |
| A9.5 | Placeholder coerenti fra tutti i msgid e i msgstr | `check-i18n.py` |
| A9.6 | Il set di screenshot `it` è identico a `docs/ui-after/` | confronto |
| A9.7 | Nessun troncamento né overflow a 375 px in `en_GB` su nessuna pagina | screenshot |
| A9.8 | Percorso completo in `en_GB` percorribile end-to-end | Chrome |
| A9.9 | Export CSV in `en_GB`: header **italiano**, date ISO | Chrome + file |
| A9.10 | Il PDF annuale in `en_GB` è tradotto e leggibile | file |
| A9.11 | Il glossario è rispettato: nessuna occorrenza di "movement" dove il glossario dice "transaction" | grep sul `.po` |
| A9.12 | `CLAUDE.md` contiene il passo 0-bis **e** il `pip install` del passo 5 | lettura |
| A9.13 | `git status` pulito dopo un `build-i18n.sh` | il commit è completo |

## Definition of done

L'app parla due lingue, in italiano è identica a come era prima del task, e la
procedura di rilascio dice come non dimenticarsi i cataloghi.

Da qui, se l'utente lo chiede: `_APP_VERSION` a **0.4.0**, commit, tag, push, e
il passo manuale sul server — `pip install -r requirements.txt`, `ALTER TABLE`,
Reload — nell'ordine.
