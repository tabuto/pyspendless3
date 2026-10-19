# Fase 8 — Dashboard e report

**Agente**: `ps-component`
**Stima**: 2-3 gg
**Dipende da**: Fase 7 verde.

`ps-dashboard-monthly.html` (4 canvas), `ps-dashboard-yearly.html` (5 canvas),
`ps-reports.html`.

Il markup è semplice: card con dentro un `<canvas>`. Il lavoro vero è il
**tema dei grafici**, che è anche l'ultimo pezzo mancante del dark mode.

## Il problema

I colori sono scritti in chiaro: la palette `COLORS` a 10 valori, i
`rgba(25,135,84,.7)` dei dataset, e i tick e le griglie che Chart.js disegna
in grigio scuro di default. Su fondo `#0b1120` diventano illeggibili.

## Soluzione

```js
function psChartTheme() {
  const s = getComputedStyle(document.documentElement);
  Chart.defaults.color       = s.getPropertyValue('--ps-text-muted').trim();
  Chart.defaults.borderColor = s.getPropertyValue('--ps-border').trim();
}
psChartTheme();
document.addEventListener('ps:themechange', () => {
  psChartTheme();
  Object.values(Chart.instances || {}).forEach(c => c.update());
});
```

I colori **semantici** dei dataset (entrate verde, uscite rosso) leggono
`--ps-income` e `--ps-expense`.

La palette categoriale a 10 colori va sostituita con una che funzioni su
entrambi i fondi (saturazione media, luminanza 40-65%), ma con **stesso ordine
e stesso numero di colori**: le categorie devono conservare la stessa
associazione cromatica da un grafico all'altro, altrimenti confrontare la torta
mensile con quella annuale diventa fuorviante.

Il plugin `chartjs-plugin-datalabels` è registrato ma disabilitato di default
(`Chart.defaults.plugins.datalabels.display = false`) e riabilitato su singoli
grafici: comportamento da preservare.

## `ps-reports.html`

Nessun grafico: select anno, bottone di download, spinner e tre stati di
messaggio (`loadingMsg`, `successMsg`, `errorMsg`), più una list-group che
descrive le 8 sezioni del report.

⚠️ Il PDF è generato **server-side** da `report_pdf.py` e `report_charts.py`
(matplotlib). È **fuori scope** e non va toccato: continuerà ad avere il
vecchio aspetto, ed è corretto così. Il gate sul diff lo protegge.

## Criteri di accettazione

### Verificabili dall'agente (senza browser)

| # | Criterio | Come si verifica |
|---|---|---|
| A8.1 | `.venv/bin/python -m pyspendless.test.test_task19_0` esce 0 | exit code |
| A8.2 | I 3 template estendono `ps-nav-tw.html`, nessuna classe Bootstrap residua | grep |
| A8.3 | Gli id dei canvas e dei filtri preservati | incluso nel test |
| A8.4 | Nessun colore hardcoded nei dataset semantici: si legge da `--ps-income` / `--ps-expense` | grep su `rgba(25,135,84`, `rgba(220,53,69` |
| A8.5 | La palette categoriale ha ancora **10 colori, nello stesso ordine** | confronto con `git show HEAD:` |
| A8.6 | `report_pdf.py` e `report_charts.py` **non toccati** | `git diff --name-only` |
| A8.7 | Il listener su `ps:themechange` è registrato in tutti i file con canvas | grep |

### Verificabili solo dall'agente principale (Chrome)

| # | Criterio |
|---|---|
| A8.8 | Mensile: i 4 grafici rendono gli **stessi dati** di prima (confronto con baseline) |
| A8.9 | Annuale: i 5 grafici idem |
| A8.10 | Cambiando tema **senza ricaricare**, assi, griglie e legende si aggiornano e restano leggibili |
| A8.11 | Una stessa categoria ha lo stesso colore nel grafico mensile e in quello annuale |
| A8.12 | I filtri anno/mese aggiornano i grafici |
| A8.13 | Il trend per categoria (annuale) funziona |
| A8.14 | Reports: la select anno si popola, il download parte, il PDF si apre |
| A8.15 | I tre stati di messaggio compaiono quando devono (loading, successo, errore) |
| A8.16 | Nessun overflow a 375 px; i canvas si ridimensionano |

## Definition of done

Tutti e 9 i canvas leggibili in light e in dark, con gli stessi dati di prima,
e il tema che cambia senza ricaricare la pagina.
