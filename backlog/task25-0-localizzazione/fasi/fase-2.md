# Fase 2 — La preferenza dell'utente

**Chi**: 1 subagent su **sonnet**, in worktree. Non haiku: tocca `models.py`,
`repository.py`, `app.py` e i tre punti di login, e deve rispettare un finding
di sicurezza del task24-0.
**Durata**: mezza giornata.
**Dipende da**: Fase 1 verde **e committata**.

Alla fine di questa fase la preferenza si salva, si rilegge e sopravvive al
logout — con una sola lingua disponibile. È voluto: si collauda il meccanismo
prima di avere qualcosa da mostrare.

---

## 2.1 Modello dati

`pyspendless/models.py`, in `User`, subito dopo `preferred_wallet_id` (riga 46):

```python
# Lingua preferita dell'utente (task25-0). None è uno stato legittimo
# ("decidi dal browser", cioè Accept-Language): nessun backfill alla
# migrazione, perché gli utenti attuali sono tutti italiani e NULL dà
# esattamente il comportamento di oggi.
locale = Column(Text, nullable=True)
```

## 2.2 DDL

`sql/sqllite/NEXT_RELEASE/alter_user_add_locale.sql` (nuovo), con l'intestazione
a commenti nello stile di `alter_user_add_preferred_wallet.sql`:

```sql
ALTER TABLE User ADD COLUMN locale TEXT;
```

Nessun `UPDATE` di backfill. È la differenza rispetto al task22-0, che aveva
una preferenza preesistente da preservare: qui non c'è niente da preservare.

Aggiornare anche `sql/sqllite/create_user.sql` per i database creati da zero.

## 2.3 `repository.py`

In `UserRepository`, accanto ai metodi del wallet preferito:

```python
def get_locale(self, user_id) -> str | None
def set_locale(self, user_id, locale) -> str | None   # None = "dal browser"
```

`set_locale` valida contro `SUPPORTED_LOCALES` e **non** accetta altro. La
validazione sta qui *e* nella rotta: la rotta protegge l'API, il repository
protegge chi chiamerà il repository domani.

## 2.4 API

```
PUT /api/user/locale     body {"locale": "en_GB"}  o  {"locale": null}
  200 {"locale": "en_GB"}
  400 se non in SUPPORTED_LOCALES
  401 se non autenticato
```

Modellata su `api_set_preferred_wallet` (`app.py:1662`). Tre vincoli, tutti dal
task24-0:

1. **Si scrive solo sull'utente in sessione.** Nessun `user_id` dal client:
   `session.get('user_id')` e basta. È il finding "mass assignment" del
   task24-0, e questa rotta non deve aggiungerne un terzo caso.
2. **Whitelist, non regex.** Il valore finisce in `<html lang>` e nel path dei
   cataloghi.
3. **Solo la chiave `locale`** viene letta dal body. Tutto il resto si ignora.

La rotta aggiorna anche `session['locale']`, così l'effetto è immediato senza
rileggere il DB.

## 2.5 Sessione

Nei **tre** punti in cui il login popola la sessione (`app.py:223-226`,
`274-277`, `385-388`), aggiungere `session['locale'] = user.locale` accanto a
`user_name` e `account_id`. Se è `None` non si scrive la chiave: l'assenza
significa "risolvi da `Accept-Language`", che è diverso da "italiano".

## 2.6 UI

**Profilo** (`ps-setting-profile.html`): card "Lingua" dopo "Dati utente"
(riga 14), con un `<select id="localeSelect">` reso da un ciclo su
`supported_locales` — **mai** con le `<option>` scritte a mano (specifica §5.7
punto 3) — più l'opzione "Come il browser" per `NULL`. Al cambio: `PUT`
all'API, poi `window.location.reload()`.

**Testata** (`ps-nav.html`): selettore compatto accanto al toggle del tema
(riga 186), stessa forma a gruppo di bottoni, `aria-label` incluso. Nelle
pagine non autenticate agisce via `?lang=`, dove l'API non è disponibile.

> **Punto aperto P4**, da decidere qui guardando la testata a **375 px**: il
> selettore di lingua in testata su tutte le pagine, o solo su quelle senza
> login (dove il profilo non è raggiungibile)? Due gruppi di bottoni accanto
> affollano la barra su mobile. Decide l'agente principale con uno screenshot,
> o l'utente.

I testi nuovi di questa fase **restano in italiano, non avvolti**: li avvolgono
le fasi 3 e 7, insieme al resto delle rispettive pagine. Avvolgerli qui
significherebbe toccare `translations/` fuori turno.

---

## Criteri di accettazione

### Verificabili dal subagent (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A2.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code (contratto DOM) |
| A2.2 | `.venv/bin/python -m pyspendless.test.test_task25_0` esce **0**, compresi i test nuovi del resolver e dell'API | exit code |
| A2.3 | `PUT /api/user/locale` con `{"locale": "fr"}` → **400**, e il DB non cambia | test |
| A2.4 | La stessa rotta senza sessione → **401** | test |
| A2.5 | Un body con `{"locale": "en_GB", "user_id": <altro utente>}` **non** scrive sull'altro utente | test — è il finding del task24-0 |
| A2.6 | Scrittura → nuovo client (sessione nuova) → login → la lingua si ritrova | test |
| A2.7 | `locale = NULL` → la lingua viene da `Accept-Language` | test con header finto |
| A2.8 | Il `<select>` è reso da un ciclo su `supported_locales` | grep: nessuna `<option value="en_GB"` letterale |
| A2.9 | `git diff --stat` resta nell'elenco della Fase 2 (§6.4 del piano) | ispezione |

### Verificabili solo dall'agente principale (Chrome)

| # | Criterio |
|---|---|
| A2.10 | Il DDL applicato al DB di sviluppo non rompe nessuna pagina |
| A2.11 | Il cambio lingua dal profilo persiste dopo logout/login |
| A2.12 | La testata a 375 px è ancora leggibile con i due selettori — **oppure** P4 è stato deciso in senso opposto, con la motivazione scritta qui |
| A2.13 | Il selettore in testata funziona su `/login`, dove non c'è sessione |

## Definition of done

Esiste un posto dove l'utente dice in che lingua vuole l'app, la risposta viene
salvata su di lui, e l'infrastruttura della Fase 1 la riceve. Niente è ancora
tradotto.
