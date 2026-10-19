# Fase 6 — `ps-show-mov.html`, la pagina critica

**Agente**: `ps-component` (non `ps-markup`)
**Stima**: 3-4 gg
**Dipende da**: Fase 5 verde.

Una fase per una sola pagina, perché questa pagina concentra da sola: pannello
filtri collassabile, 3 KPI card, Chart.js, DataTables + jQuery, Tom Select,
card-list mobile con IntersectionObserver, export CSV e delete.

Va fatta **in sottopassi sequenziali**, verificando dopo ognuno. Non in un
colpo solo: se si rompe qualcosa, lo spazio di ricerca deve restare piccolo.

## Sottopassi

### 6.1 — Layout, KPI card, card del grafico
Senza toccare il JS. Le 3 KPI mantengono la semantica: Entrate verde, Uscite
rossa, Bilancio `info` se ≥ 0 e `warning` se < 0 — il colore dipende dal segno,
è logica, va preservata.

### 6.2 — Pannello filtri collassabile
Da preservare: `aria-expanded` derivato da `filters.active_count`, il badge con
il conteggio dei filtri attivi, la rotazione del chevron, e il fatto che il
pannello è **chiuso di default** ma si apre da solo se ci sono filtri diversi
dai default.

### 6.3 — Tom Select
Sostituzione del tema `bootstrap5` + skin Tailwind.

⚠️ L'inizializzazione è **rimandata** a `shown.bs.collapse`
(righe 398-404), e il commento a 377-379 spiega perché: inizializzare Tom
Select mentre il contenitore è `display:none` produce larghezze e dropdown
sbagliati. `ps-ui.js` deve emettere l'evento equivalente a **transizione
conclusa**, e va replicata la logica:

```js
if (pannello già aperto) init();
else on('shown', init, { once: true });
```

Emettere l'evento troppo presto ricrea esattamente il bug che quel codice evita.

### 6.4 — DataTables
Tema neutro (`dataTables.dataTables.css`) al posto di `bootstrap5`, più skin
Tailwind per il chrome generato dal plugin: casella di ricerca, select della
lunghezza, riga info, paginazione, e il child row del Responsive.

jQuery **resta** (decisione D5). La sostituzione è rimandata a un task
autonomo, dopo il restyling.

### 6.5 — Card-list mobile
Qui si applica la regola sulle classi dinamiche nel modo più pesante
(righe 446-485): le classi sono costruite per concatenazione e **spariscono
dal CSS compilato**. Ogni ramo deve produrre la classe intera, meglio se una
`.ps-*`.

`IntersectionObserver` e la logica di paginazione: invariati.

### 6.6 — Chart.js theme-aware
Colori dal design system via CSS custom properties, listener su
`ps:themechange` che rilegge e chiama `.update()`.

## Criteri di accettazione

### Verificabili dall'agente (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A6.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |
| A6.2 | I 6 `name=` del form filtri preservati | incluso nel test (`form_fields`) |
| A6.3 | I 12 `id` della pagina preservati | incluso nel test |
| A6.4 | Nessuna classe costruita per concatenazione | `IgieneTemplate`, file tolto dalla whitelist |
| A6.5 | Il breakpoint resta **768px**: `md:hidden` / `hidden md:block`, nessun valore arbitrario | grep |
| A6.6 | `matchMedia('(min-width: 768px)')` invariato nel JS | grep |

### Verificabili solo dall'agente principale (Chrome)

| # | Criterio |
|---|---|
| A6.7 | **A 767 px si vede solo la card-list; a 768 px solo la tabella.** Mai entrambe, mai nessuna |
| A6.8 | I filtri (date, wallet, tipo, multi-categoria, keyword) producono la **stessa querystring** di prima |
| A6.9 | Il pannello filtri è chiuso di default, e aperto se ci sono filtri attivi; il badge mostra il conteggio giusto |
| A6.10 | Tom Select: si apre con la larghezza giusta **alla prima apertura del pannello** (è il bug che 6.3 evita) |
| A6.11 | "Seleziona tutto" / "Deseleziona" funzionano |
| A6.12 | DataTables: ordina su tutte e 8 le colonne, pagina a 25, cerca, cambia lunghezza, stringhe in italiano |
| A6.13 | Collasso responsive a ~800 px: le colonne a bassa priorità passano nel child row espandibile |
| A6.14 | Infinite scroll a 375 px: carica pagina 2, 3, poi mostra "Nessun altro movimento" |
| A6.15 | Export CSV rispetta i filtri correnti |
| A6.16 | Delete: `confirm()`, poi reload, poi il movimento non c'è più |
| A6.17 | Il grafico mostra gli stessi dati, leggibile in light **e** dark; cambia tema senza ricaricare |
| A6.18 | Le 3 KPI: Bilancio `info` se ≥ 0, `warning` se < 0 |
| A6.19 | Nessun overflow a 375 px |

A6.7 e A6.10 sono i due che vanno provati per primi: sono quelli in cui un
errore produce un bug silenzioso invece di un errore visibile.

## Definition of done

La pagina più complessa dell'app fa esattamente quello che faceva, su tutte e
tre le larghezze e nei due temi. Se c'è un dubbio su un comportamento, si
confronta con lo screenshot di baseline — non si decide a memoria.
