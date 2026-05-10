# Report – Mensilità senza movimenti
**Database:** `data/pyspendless3-20260510.db`  
**Analisi:** 2026-05-10  
**Periodo coperto:** gennaio 2018 → maggio 2026 (101 mesi)  
**Totale movimenti:** 7.736

---

## 1. Riepilogo per Account

| Account | Movimenti | Mesi con movimenti | Mesi senza movimenti |
|---|---|---|---|
| 1 – FamigliaGOD | 7.736 | 98 / 101 | **3** |
| 2 – FamigliaGod2 | 0 | 0 / 101 | **101** ⚠️ |

### Account 2 (FamigliaGod2)
L'account non ha **nessun movimento** registrato in tutto il periodo storico.  
Si tratta probabilmente di un account di test o mai utilizzato.

---

## 2. Mensilità mancanti – Account 1 (FamigliaGOD)

Tre mesi consecutivi risultano privi di qualsiasi movimento a livello di account:

| Mese | Note |
|---|---|
| **2025-01** | Nessun movimento in tutti i wallet |
| **2025-02** | Nessun movimento in tutti i wallet |
| **2025-03** | Nessun movimento in tutti i wallet |

> L'unico movimento registrato in prossimità di questo gap è **2025-04-01** (1 movimento su FinecoBea: "gas e luce nen aprile 2025", spesa €146). L'attività riprende regolarmente da **maggio 2025**.

---

## 3. Analisi per Wallet (Account FamigliaGOD)

### Wallet 7 – FinecoBea ⭐ (principale)
- **98 mesi con movimenti**, 3 mesi mancanti
- **Mesi mancanti:** 2025-01, 2025-02, 2025-03
- Wallet attivo e continuativo per tutto il periodo.

### Wallet 8 – FinecoFra ⭐ (principale)
- **97 mesi con movimenti**, 4 mesi mancanti
- **Mesi mancanti:** 2025-01, 2025-02, 2025-03, **2025-04**
- In 2025-04 l'unico movimento di account è su FinecoBea (non su FinecoFra).

### Wallet 3 – FinecoFraBea (nuovo)
- Attivo da **gennaio 2026**, 5 mesi con movimenti, nessun gap.
- Wallet più recente, creato il 2026-02-25.

### Wallet 4 – BancoPosta (praticamente inattivo)
- Solo **2 movimenti** in tutta la storia: agosto 2018 e febbraio 2019.
- **92 mesi senza movimenti** dal suo primo utilizzo.

### Wallet 5 – CashBea (abbandonato)
- Attivo solo nel **2018** (12 mesi: gen-dic 2018).
- **89 mesi senza movimenti** da gennaio 2019 in poi.

### Wallet 6 – CashFra (abbandonato)
- Attivo nel **2018-2020** (13 mesi sparsi).
- **88 mesi senza movimenti** da gennaio 2019 in poi (con qualche mese nel 2020).

---

## 4. Tabella movimenti mensili – Account FamigliaGOD

| Anno | Gen | Feb | Mar | Apr | Mag | Giu | Lug | Ago | Set | Ott | Nov | Dic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 72 | 70 | 69 | 107 | 88 | 114 | 103 | 105 | 96 | 80 | 81 | 88 |
| 2019 | 63 | 73 | 110 | 113 | 87 | 94 | 73 | 80 | 57 | 90 | 72 | 91 |
| 2020 | 66 | 61 | 37 | 24 | 49 | 61 | 69 | 92 | 79 | 49 | 46 | 56 |
| 2021 | 55 | 42 | 46 | 76 | 104 | 97 | 112 | 94 | 80 | 99 | 95 | 74 |
| 2022 | 64 | 58 | 74 | 50 | 90 | 94 | 72 | 58 | 86 | 83 | 81 | 89 |
| 2023 | 78 | 70 | 86 | 77 | 87 | 79 | 62 | 98 | 90 | 97 | 109 | 98 |
| 2024 | 78 | 143 | 179 | 106 | 89 | 84 | 75 | 84 | 100 | 61 | 80 | 66 |
| 2025 | ❌ | ❌ | ❌ | 1 | 58 | 73 | 71 | 140 | 81 | 66 | 71 | 59 |
| 2026 | 59 | 67 | 82 | 61 | 33 | – | – | – | – | – | – | – |

> ❌ = nessun movimento registrato

---

## 5. Conclusioni e raccomandazioni

1. **Gap 2025-01/02/03**: Tre mesi completamente vuoti nell'account principale. Potrebbe trattarsi di dati non ancora importati o di un periodo in cui l'applicazione non era in uso. **Verificare se esistono dati da importare per questo periodo.**

2. **Account FamigliaGod2**: Mai utilizzato. Valutare se mantenerlo o eliminarlo.

3. **Wallet BancoPosta, CashBea, CashFra**: Di fatto abbandonati dopo i primi mesi. Valutare la marcatura come "archiviati" o la loro rimozione.

4. **Wallet FinecoFraBea**: Nuovo wallet (feb 2026), monitorare la continuità dei dati.
