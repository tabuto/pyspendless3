# Fase 7 — `Impostazioni → Labels`

**Chi**: subagent **`ps-markup`** per il template, **`ps-labels-py`** se serve
toccare `app.py`. Le due parti non si sovrappongono.
**Dipende da**: Fase 3 verde (API `PUT`/`DELETE` e rotta `/settings/labels`
già esistenti) e Fase 4 verde.
**Fatto quando**: `contract` verde su questa parte, `test_task19_0.py` verde,
`test_task26_0.py api` ancora verde.
**File**: `pyspendless/templates/ps-setting-labels.html` (da scheletro a
pagina), `pyspendless/templates/ps-nav.html`,
`pyspendless/test/test_task19_0.py` (**solo** `NAV_LINKS_ORDER`).

## 7.1 La pagina

Modello di riferimento: `ps-setting-categories.html` (stessa struttura di card,
tabella, modali). Contenuto:

- tabella: label, numero di movimenti, azioni;
- **rinomina** in un `PsModal`: mostra quanti movimenti verranno riscritti. Se
  la nuova grafia coincide (case-insensitive) con una label esistente, il modal
  lo dice **esplicitamente** — "#coop esiste già: i 12 movimenti di #coopp
  verranno uniti" — e la conferma esegue il merge;
- **elimina** con conferma che riporta il conteggio e la frase "la label verrà
  rimossa dal testo delle note di N movimenti". È irreversibile sul testo
  scritto dagli utenti: la conferma non è una formalità;
- **nessuna creazione** da questa pagina: una label nasce usandola.

I conteggi arrivano da `GET /api/labels?with_counts=1`.

## 7.2 La nav

Voce dopo "Categorie", icona `bi-hash`:

```html
<li>
  <a href="{{ url_for('settings_labels') }}" class="ps-nav-link pl-10">
    <i class="bi bi-hash" aria-hidden="true"></i>
    <span>Labels</span>
  </a>
</li>
```

E **due aggiornamenti obbligatori** che non sono cosmetici:

1. `/settings/labels` va aggiunta a `NAV_LINKS_ORDER`
   (`test_task19_0.py:276`), fra `/settings/categories` e `/settings/wallets`.
   Il test della nav **ignora** i link che non conosce: senza questo passo la
   voce nuova non è coperta da niente e un riordino futuro non se ne accorge.
2. Il commento in testa a `ps-nav.html` parla di "13 destinazioni": diventano
   14. È il commento che spiega perché l'ordine è contratto — lasciarlo
   sbagliato è peggio che non averlo.

## 7.3 Una nota sul rischio R1

In questa pagina (o nella pagina `/movements`, decidi tu dove si vede meglio)
va detto che **la correzione massiva sostituisce la nota e quindi cancella le
label** dei movimenti filtrati. È il rischio R1 della specifica §15: resta
fuori perimetro, ma l'utente deve poterlo sapere **prima**, non scoprirlo
dopo.
