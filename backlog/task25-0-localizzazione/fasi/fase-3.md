# Fase 3 — Shell e pagine di accesso

**Chi**: **4 × `ps-i18n-template`** su **haiku**, in worktree, **in parallelo**.
**Durata**: mezza giornata.
**Dipende da**: Fase 2 verde e **committata** (il worktree vede solo file
tracciati: senza il commit, `check-i18n.py` e `i18n.py` non esistono lì).

Otto file, sette con del testo (`ps-auth.html` non ne ha: si verifica e si
lascia stare). Queste pagine per prime perché coprono **entrambe** le shell (`ps-auth.html` e
`ps-nav.html`), sono le meno dense, e `ps-login` è la porta d'ingresso: un
errore qui si vede subito invece di restare nascosto in una pagina interna.

**Questa è anche la fase di collaudo del metodo.** Se quattro haiku su otto
template semplici tornano con lavoro pulito, le tredici invocazioni delle fasi
5-7 sono prevedibili. Se tornano sporche, si corregge
`.claude/agents/ps-i18n-template.md` **prima** di moltiplicarla per tredici.

---

## Le quattro invocazioni

| # | File | Stringhe attese |
|---|---|---|
| 3.A | `ps-nav.html` | 21 testi + 10 attributi |
| 3.B | `ps-home.html` + `ps-onboarding.html` | 20 testi + 3 attributi |
| 3.C | `ps-base.html` + `ps-oauth-consent.html` | 6 testi |
| 3.D | `ps-maintenance.html` + `ps-login.html` + `ps-auth.html` | 7 testi |

I file sono **disgiunti**: il parallelismo è sicuro. Nessuno dei quattro apre
il browser (Flask gira dal checkout principale, non dai worktree).

### Primo comando, dentro il worktree

```bash
./tools/worktree-bootstrap.sh --test
```

Collega `pyspendless/.env` (non tracciato, quindi assente dal worktree), sceglie
il virtualenv giusto fra i due del repo, ed esegue il contratto DOM. Nel
checkout principale è un no-op.

---

## Note per file

### `ps-nav.html` (3.A)

È la shell di ogni pagina autenticata: un errore qui si moltiplica per 15
pagine. Da avvolgere: le voci di navigazione, le etichette dell'header, i 10
`aria-label` (compreso `"Selettore tema"` a riga 186 e quelli del selettore di
lingua aggiunto in Fase 2).

**Non** avvolgere: `{{ user_name }}`, `{{ user_email }}`, `{{ app_version }}`.

### `ps-home.html` + `ps-onboarding.html` (3.B)

`ps-onboarding.html` ha i `form-text` sotto i campi e i flash message: i primi
si avvolgono, i secondi **no** — il testo dei flash arriva da Python e lo
avvolge la Fase 4. Qui si avvolge solo ciò che è scritto nel template.

Preservare `required`, `maxlength="100"` e i `name` dei campi (`account_name`,
`wallet_name`): sono nel contratto DOM.

### `ps-base.html` + `ps-oauth-consent.html` (3.C)

In `ps-base.html`:

- il footer: `&copy; 2026 PySpendless` → **non si avvolge**. Non c'è niente da
  tradurre in un anno e in un nome proprio;
- `<meta name="title">` e `<meta name="description">`: **sì**, le vede chi
  condivide un link;
- `<meta name="keywords">`: **no**. Non è testo visibile, e tradurre una lista
  di parole chiave aggiunge msgid che nessuno leggerà;
- `lang="{{ current_locale }}"` è già a posto dalla Fase 1: **non toccarlo**;
- lo **script anti-FOUC** inline (righe 63-73): **non si tocca**. Non contiene
  testo, e una modifica lì riporta il flash di tema che la Fase 1 del task19-0
  ha eliminato.

`ps-oauth-consent.html` è la pagina di consenso del flusso Alexa (task23-0). La
vede un utente vero, arriva da un redirect esterno e **può non avere sessione**:
la sua lingua viene da `?lang=` o da `Accept-Language`. Nessuna dipendenza da
`current_user` va introdotta qui.

### `ps-maintenance.html` + `ps-login.html` + `ps-auth.html` (3.D)

`ps-maintenance.html` è reso dal `before_request` con status **503** e **senza
toccare il database** (specifica §5.5). Avvolgere il testo non cambia questo —
a condizione di non introdurre nessuna espressione che richieda una query.

`ps-login.html`: preservare `id="login-google-btn"`, `href="/auth/login"`,
l'icona `bi bi-google`. Il testo `"Login with Google"` è **già inglese**: si
avvolge comunque (in `en_GB` resta uguale, in italiano futuro potrà cambiare).

`ps-auth.html` non ha testo: si verifica e si lascia stare.

---

## Criteri di accettazione

Validi per **ogni** invocazione. Un subagent rilascia solo quando tutti i suoi
sono soddisfatti.

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A3.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code — il contratto DOM è la prova che il testo reso in `it` non è cambiato |
| A3.2 | `tools/check-i18n.py --file <ogni file assegnato>` esce **0** | exit code |
| A3.3 | Il testo reso in italiano è **identico** a prima | `git stash` + diff del testo con i tag rimossi, oppure A3.1 che lo copre per le pagine nel contratto |
| A3.4 | Tutti gli `id=`, i `name=` e gli `{{ url_for }}` preservati | diff degli attributi estratti da `git show HEAD:<file>` |
| A3.5 | Stesso numero di `{% if %}`, `{% for %}`, `{{ }}` di prima (più quelli dei `_()` aggiunti) | conteggio |
| A3.6 | Nessun `_()` attorno a un'espressione Jinja | coperto da A3.2 |
| A3.7 | Nessuna stringa tradotta in inglese nei template | grep — in questa fase si **avvolge**, non si traduce |
| A3.8 | `git status --short` mostra **solo** i file assegnati | ispezione — in particolare **niente `translations/`**: ha un solo scrittore (§4.4 del piano) |

### Verificabili solo dall'agente principale (dopo il merge)

| # | Criterio |
|---|---|
| A3.9 | `./tools/build-i18n.sh` esce 0 e il `.pot` contiene i ~54 msgid nuovi |
| A3.10 | Percorso login → onboarding → home percorribile end-to-end, in italiano, identico a prima |
| A3.11 | Con `?lang=en_GB` le pagine restano in italiano (il catalogo è vuoto) e **non** vanno in errore |
| A3.12 | `MAINTENANCE_MODE=1` → ancora **503**, ancora zero query |
| A3.13 | La pagina di consenso OAuth si rende ancora correttamente senza sessione |
| A3.14 | Gli otto file sono stati tolti dalla whitelist di `check-i18n.py`, **in un colpo solo** |
| A3.15 | `git diff --stat` tocca solo `pyspendless/templates/**` |

## Definition of done

Le otto pagine sono avvolte, il contratto è verde, l'app in italiano è
identica a prima, e il metodo è collaudato: si sa se haiku può fare le dodici
invocazioni successive.
