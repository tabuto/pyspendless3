# Fase 2 — Nuova app-shell

**Agente**: `ps-component`
**Stima**: 2-3 gg
**Dipende da**: Fase 1 verde.

Crea la gerarchia Tailwind accanto a quella esistente. I file vecchi
(`ps-base.html`, `ps-nav.html`, `ps-auth.html`) **non si toccano**: restano in
servizio per le pagine non ancora migrate fino alla Fase 9.

## Attività

### 2.1 — `ps-base-tw.html`

I blocchi Jinja devono avere **gli stessi nomi** di `ps-base.html`
(`title`, `head`, `content`, `scripts`): è ciò che rende la migrazione di una
pagina un cambio di una riga.

Contiene:

- lo script anti-FOUC **inline, bloccante**, prima del `<link>` al CSS
- `<link>` e `<script>` con cache busting: `?v={{ app_version }}`
  (`app_version` è già iniettata dal context processor a `app.py:75-78` —
  nessuna modifica a `app.py`)
- il footer **identico**: `© 2026 PySpendless · v{{ app_version }}`
- i meta: viewport, `color-scheme`, `theme-color` per light e dark, description,
  keywords. Occasione per correggere il `<title>` duplicato (P4), se D10 è
  approvata.

### 2.2 — `ps-nav-tw.html`

Blocco `{% block nav_content %}`, **stesso nome** di oggi.

Layout mobile first: drawer off-canvas sotto `lg`, sidebar fissa da `lg` in su.

La sidebar espone **le stesse 13 destinazioni, nello stesso ordine**:

```
Home · Crea Movimento · Visualizza Movimenti · Cerca Movimenti ·
Spese Ricorrenti · [Dashboard > Analisi Mensile, Analisi Annuale] ·
Reports · [Impostazioni > Categorie, Wallet, Account, Import/Export,
           Admin (se is_admin)] · Logout
```

Stessi `url_for`, stesse icone `bi bi-*`, stesso testo italiano.

Comportamenti da replicare esattamente:

- i due treeview (Dashboard, Impostazioni) **chiusi di default**, chevron che
  ruota, classe `menu-open` sul `<li>` — oggi è JS inline a
  `ps-nav.html:167-213`
- voce Account in alto a destra, con la stessa logica
  `session.user_email.split('@')[0] || session.user_name || 'User'`
- voce Admin condizionata a `{% if is_admin %}`
- `role="navigation"`, `aria-label` e **`id="navigation"`** sul `<ul>` della
  sidebar. Quell'id non è decorativo: `test_nav_destinazioni` lo usa per
  delimitare l'estrazione dei link, perché fuori di lì ci sono la voce Account
  dell'header e i link delle card di `/home`, che falserebbero l'ordine.

**Nuovo**: il toggle tema, accanto alla voce Account. È l'unico elemento di UI
che questo task aggiunge.

### 2.3 — `ps-auth-tw.html`

Shell delle pagine non autenticate, layout centrato.

Occasione per correggere **P3**: in `ps-auth.html` il markup `.login-box` sta
fuori da qualsiasi `{% block %}` in un template figlio, quindi Jinja lo scarta
— di fatto oggi quella struttura non viene resa affatto. Nel nuovo file la
struttura va **dentro** il block. Soggetto a D10.

### 2.4 — Pagina di prova

Una pagina temporanea che estende `ps-nav-tw.html`, usata solo per i criteri
qui sotto. Si cancella in Fase 3, quando arrivano le pagine vere.

## Criteri di accettazione

| # | Criterio | Come si verifica |
|---|---|---|
| A2.1 | I blocchi di `ps-base-tw.html` hanno gli stessi nomi di `ps-base.html` | `grep '{% block'` sui due file, insiemi identici |
| A2.2 | `ps-nav-tw.html` espone `{% block nav_content %}` | grep |
| A2.3 | **Stesse 13 destinazioni, stesso ordine** della nav attuale | `test_nav_destinazioni` sulla pagina di prova |
| A2.4 | Tutti gli `url_for` della nav risolvono | la pagina di prova rende 200, nessun `BuildError` |
| A2.5 | Treeview chiusi al caricamento, si aprono al click, chevron ruota | prova manuale, Chrome |
| A2.6 | Voce Admin presente solo se `is_admin` | prova con utente admin e non admin |
| A2.7 | Drawer mobile: si apre, si chiude, blocca lo scroll del body sotto | prova a 375 px |
| A2.8 | Toggle tema presente e funzionante dalla shell | prova manuale nei 3 stati |
| A2.9 | Footer con `v{{ app_version }}` | `test_footer_versione` |
| A2.10 | `ps-base.html`, `ps-nav.html`, `ps-auth.html` **non modificati** | `git diff --name-only` non li elenca |
| A2.11 | Nessun riferimento a Bootstrap o AdminLTE nei tre file `-tw` | grep su `bootstrap`, `adminlte` |
| A2.12 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |

## Definition of done

Una pagina che estende `ps-nav-tw.html` mostra la shell completa, naviga
ovunque come oggi, e il confronto fra le destinazioni estratte dalla nav vecchia
e dalla nuova dà differenza vuota.
