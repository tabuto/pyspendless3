# Fase 6 — Dashboard e report

**Chi**: **3 × `ps-i18n-template`** su **haiku**, in parallelo, **dopo** che
l'agente principale ha aggiunto l'helper dei mesi (§6.1).
**Durata**: mezza giornata.
**Dipende da**: Fase 3 verde e committata.

---

## 6.1 Prima: i nomi dei mesi in un posto solo (agente principale)

Oggi i nomi dei mesi in italiano sono scritti **tre volte**:

| Dove | Forma |
|---|---|
| `repository.py:2212` | `month_names = ["", "Gennaio", ...]` |
| `report_pdf.py:13` | `MONTHS_IT = ["", "Gennaio", ...]` |
| `templates/ps-dashboard-monthly.html:25` e seguenti | 12 `<option>` scritte a mano |

Tradurli in tre posti diversi è il modo sicuro di farli divergere. L'agente
principale aggiunge a `i18n.py`:

```python
def month_names(locale=None):
    """Nomi dei mesi dal CLDR, indicizzati 1-12 (l'indice 0 è vuoto, come
    nelle tre liste che questa funzione sostituisce)."""
```

usando `babel.dates.get_month_names('wide', locale=...)` — zero stringhe da
tradurre, dodici msgid in meno nel catalogo, e `Gennaio`/`January` corretti per
costruzione. (Con il **piano B** della Fase 0 la stessa funzione tiene due liste
scritte a mano: l'interfaccia non cambia.)

Poi espone `month_names` ai template nel context processor, così la dashboard
mensile può fare un ciclo.

**Questo pezzo non si delega**: è codice condiviso da tre moduli, e tre
subagent che lo scrivessero in parallelo lo scriverebbero in tre modi.

---

## Le tre invocazioni

| # | File | Stringhe attese |
|---|---|---|
| 6.A | `ps-dashboard-monthly.html` | 22 testi + 6 nel JS, **più** i 12 `<option>` da sostituire con un ciclo |
| 6.B | `ps-dashboard-yearly.html` | 11 testi + 7 nel JS |
| 6.C | `ps-reports.html` | 27 testi + 1 nel JS |

## Note per file

### `ps-dashboard-monthly.html` (6.A)

Le 12 `<option value="N">Mese</option>` diventano:

```jinja
{% for n in range(1, 13) %}
  <option value="{{ n }}"{% if n == selected_month %} selected{% endif %}>{{ month_names[n] }}</option>
{% endfor %}
```

**Il `value` resta il numero**: è quello che il server legge. Cambia solo
l'etichetta. E l'attributo `selected` va preservato esattamente com'è oggi —
se si perde, la dashboard si apre sempre su gennaio.

Le etichette dei grafici (`['Entrate', 'Uscite']`, riga 251) si avvolgono come
normali stringhe JS. I **colori** e le opzioni di Chart.js non si toccano.

### `ps-dashboard-yearly.html` (6.B) e `ps-reports.html` (6.C)

Avvolgimento ordinario. In `ps-reports.html` attenzione ai testi che descrivono
il PDF: il PDF stesso lo localizza la Fase 8, qui si avvolge solo la pagina che
lo genera.

---

## Criteri di accettazione

### Verificabili dal subagent

| # | Criterio | Come si verifica |
|---|---|---|
| A6.1 | `./tools/worktree-bootstrap.sh --test` esce **0** | exit code |
| A6.2 | `tools/check-i18n.py --file <file assegnato>` esce **0** | exit code |
| A6.3 | Nessun nome di mese letterale resta nel template | grep `Gennaio\|Febbraio\|...` |
| A6.4 | I `value` delle `<option>` sono ancora i numeri 1-12 | grep |
| A6.5 | L'attributo `selected` è preservato | diff |
| A6.6 | I `canvas` id e le opzioni di Chart.js invariati | diff |
| A6.7 | `git status --short` mostra solo il file assegnato | ispezione |

### Verificabili solo dall'agente principale

| # | Criterio |
|---|---|
| A6.8 | La dashboard mensile si apre sul mese corrente, non su gennaio |
| A6.9 | Il cambio di mese e di anno ricarica i dati giusti |
| A6.10 | I grafici si rendono in light e in dark, con le etichette al posto giusto |
| A6.11 | `repository.py:2212` e `report_pdf.py:13` **non** sono stati toccati (sono Fase 8): le tre liste convivono per ora, ma l'helper esiste già |
| A6.12 | Il PDF annuale si genera ancora, in italiano |
| A6.13 | `git diff --stat` tocca solo `templates/**` e `i18n.py` |

## Definition of done

Le tre pagine sono avvolte e i nomi dei mesi hanno **una** fonte, pronta per la
Fase 8 che eliminerà le altre due.
