# Baseline visiva — prima del restyling Tailwind (task19-0)

Fotografia dell'interfaccia **AdminLTE 4 + Bootstrap 5.3**, catturata in Fase 0
prima che una riga di markup cambiasse. Serve come termine di paragone per
l'`after`: l'isofunzionalità si dimostra confrontando queste immagini con quelle
prodotte dallo stesso script a fine lavoro.

Generata il **2026-10-17**, app alla versione **0.2.2**, su `localhost:5000`
con il DB di sviluppo locale.

## Come si rigenera

```bash
.venv/bin/python tools/ui-shots.py                      # baseline (qui)
.venv/bin/python tools/ui-shots.py --out docs/ui-after  # dopo il restyling
```

Serve che l'app giri su `http://localhost:5000`. **Non serve fare login**: lo
script firma un cookie di sessione Flask per il primo utente del DB
(`tools/ps_session_cookie.py`), lo stesso meccanismo che `test_task19_0.py` usa
con `session_transaction()`. Nessuna credenziale, nessun passaggio da Google.

Le inquadrature sono nel codice, non nelle mani di chi cattura: è l'unico modo
perché il confronto fra immagini prese a settimane di distanza significhi
qualcosa.

## Convenzioni di nome

```
<rotta>__<viewport>__<tema>.png          pagina intera (full page)
stato--<descrizione>__<viewport>__<tema>.png   stato non di default
```

- **viewport**: `375` (mobile), `768` (tablet, la soglia del breakpoint),
  `1440` (desktop).
- **tema**: oggi solo `light` — il tema scuro nasce in Fase 2, e da lì in poi
  la matrice raddoppia.

## Cosa c'è dentro

Le pagine raggiungibili dell'applicazione, ciascuna ai tre viewport, più gli
stati che un semplice caricamento non mostra: i modal aperti, il tab "Entrate"
delle categorie, il pannello filtri aperto, la card-list dopo lo scroll
infinito, l'alert di successo, la progress bar dell'import, la zona pericolosa
con il bottone abilitato.

### Due avvertenze sugli stati

1. Gli stati che nell'uso reale seguono una **scrittura** (l'alert di successo,
   la progress bar dell'import) sono stati prodotti invocando il codice di
   presentazione della pagina, **senza salvare né importare niente**. Sono
   fedeli come pixel; non lo sono come percorso utente.
2. La "zona pericolosa" è fotografata con il bottone **abilitato** ma mai
   premuto.

### Pagine non catturabili

| Pagina | Perché |
|---|---|
| `/onboarding` | Risponde 302 a un utente che ha già un account. Servirebbe una fixture con un utente appena creato. |
| consenso OAuth2 (`ps-oauth-consent.html`) | Reso da `oauth_server.py`, raggiungibile solo dentro un flusso OAuth2 completo. Non è nel piano di nessuna fase: va deciso se rientra nel restyling. |

La manutenzione (`ps-maintenance.html`) **è** catturata, ma per vie traverse: il
gate legge `MAINTENANCE_MODE` a ogni richiesta e il server in esecuzione non ce
l'ha. Lo script rende la pagina con il test client e la variabile attiva, poi la
passa al browser con `set_content` e un `<base>` che fa risolvere `/static` sul
server vero. Il risultato è il markup reale, reso dal browser reale.
