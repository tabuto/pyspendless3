# Task 8.0: Maintenance Mode - Pagina di Cortesia

Questo task implementa una funzionalità di "Maintenance Mode" che permette di bloccare l'accesso a tutte le route dell'applicazione Flask mostrando una pagina di cortesia, controllata tramite variabile d'ambiente.

## Obiettivi
1. Bloccare l'accesso a tutte le route quando la modalità manutenzione è attiva.
2. Mostrare una pagina di cortesia informativa agli utenti.
3. Permettere l'attivazione/disattivazione tramite variabile d'ambiente senza modifiche al codice.
4. Mantenere la coerenza con il design AdminLTE 3 esistente.

## Soluzione Tecnica: `@app.before_request`

### Descrizione
Flask fornisce il decorator `@app.before_request` che permette di eseguire una funzione **prima** di ogni richiesta HTTP. Questa funzione viene invocata automaticamente dal framework prima che la richiesta raggiunga la route di destinazione.

Se la funzione decorata con `@app.before_request` restituisce una risposta (es. `render_template()` o `redirect()`), Flask interrompe il normale flusso e restituisce quella risposta al client, **senza invocare la route effettiva**.

### Vantaggi
- **Centralizzato**: Un unico punto di controllo per tutte le route.
- **Non invasivo**: Non richiede modifiche alle singole route esistenti.
- **Flessibile**: Permette di escludere facilmente route statiche o specifiche pagine.
- **Zero downtime**: Attivazione/disattivazione tramite variabile d'ambiente senza restart (se si rilegge la variabile ad ogni richiesta).

## Modifiche ai File

### 1. Variabile d'Ambiente (`.env`)

Aggiungere la seguente variabile al file `.env`:

```env
# Maintenance Mode (1 = attivo, 0 = disattivo)
MAINTENANCE_MODE=0
```

### 2. Configurazione (`conf.py`)

Aggiungere la lettura della variabile d'ambiente in `conf.py`:

```python
# Maintenance Mode
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', '0') == '1'
```

**Nota**: Per permettere l'attivazione senza restart dell'applicazione, la variabile può essere riletta dinamicamente ad ogni richiesta (vedi implementazione in `app.py`).

### 3. Template Pagina di Cortesia (`templates/ps-maintenance.html`)

Creare un nuovo template che estende `base_auth.html` (layout senza sidebar) seguendo le specifiche AdminLTE 3:

```html
{% extends "ps-auth.html" %}

{% block title %}Manutenzione in corso{% endblock %}

{% block content %}
<div class="login-box">
    <div class="card card-outline card-warning">
        <div class="card-header text-center">
            <span class="h1"><b>Py</b>Spendless</span>
        </div>
        <div class="card-body">
            <div class="text-center mb-4">
                <i class="fas fa-tools fa-4x text-warning"></i>
            </div>
            <h4 class="text-center mb-3">Manutenzione in corso</h4>
            <p class="login-box-msg">
                Il servizio è temporaneamente non disponibile per manutenzione programmata.
            </p>
            <p class="text-center text-muted">
                <small>Ci scusiamo per il disagio. Riprova tra qualche minuto.</small>
            </p>
            <div class="text-center mt-4">
                <button onclick="window.location.reload()" class="btn btn-outline-secondary">
                    <i class="fas fa-sync-alt"></i> Riprova
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 4. Implementazione in `app.py`

Aggiungere il seguente codice **subito dopo** la configurazione dell'app Flask e **prima** della definizione delle route:

```python
import os

# ===== MAINTENANCE MODE =====
@app.before_request
def check_maintenance_mode():
    """
    Intercetta tutte le richieste e mostra la pagina di manutenzione
    se la variabile d'ambiente MAINTENANCE_MODE è impostata a '1'.
    
    Esclude:
    - File statici (CSS, JS, immagini)
    - Eventuali endpoint di health check
    """
    # Rilegge la variabile ad ogni richiesta per hot-reload
    maintenance_mode = os.getenv('MAINTENANCE_MODE', '0') == '1'
    
    if not maintenance_mode:
        return None  # Continua normalmente
    
    # Escludi i file statici per permettere il rendering corretto della pagina
    if request.path.startswith('/static/'):
        return None
    
    # Escludi eventuali endpoint di health check (opzionale)
    if request.path == '/health':
        return None
    
    # Mostra la pagina di manutenzione
    return render_template('ps-maintenance.html'), 503
```

## Specifiche Funzionali

### Comportamento
1. **MAINTENANCE_MODE=0** (default): L'applicazione funziona normalmente.
2. **MAINTENANCE_MODE=1**: Tutte le richieste vengono intercettate e restituite con la pagina di manutenzione e HTTP status code `503 Service Unavailable`.

### Esclusioni
Le seguenti route sono escluse dal blocco per garantire il corretto funzionamento:

| Path | Motivo |
|------|--------|
| `/static/*` | Permette il caricamento di CSS e JS per la pagina di manutenzione |
| `/health` | Endpoint opzionale per health check di sistemi di monitoraggio |

### HTTP Status Code
La pagina di manutenzione restituisce lo status code **503 Service Unavailable**, che:
- Informa i client e i crawler che il servizio è temporaneamente non disponibile
- Indica ai motori di ricerca di non indicizzare la pagina di errore
- È lo status code standard per situazioni di manutenzione

## Flusso di Attivazione

```
1. Modifica .env: MAINTENANCE_MODE=1
2. (Opzionale) Restart applicazione se non supporta hot-reload
3. Tutte le richieste mostrano la pagina di manutenzione
4. Esegui operazioni di manutenzione
5. Modifica .env: MAINTENANCE_MODE=0
6. L'applicazione torna operativa
```

## Note Tecniche

### Hot-Reload della Configurazione
L'implementazione proposta rilegge `os.getenv('MAINTENANCE_MODE')` ad ogni richiesta, permettendo di attivare/disattivare la modalità manutenzione modificando la variabile d'ambiente senza riavviare l'applicazione (se l'ambiente lo supporta).

### Ordine del Decorator
Il decorator `@app.before_request` viene eseguito **prima** di qualsiasi altro middleware o decorator delle route. Questo garantisce che il blocco sia effettivo su tutte le pagine.

### Compatibilità con OAuth
Durante la manutenzione, anche le route di autenticazione OAuth (`/auth/login`, `/auth/callback`) saranno bloccate. Questo è il comportamento desiderato per una manutenzione completa.

### Test
Per testare la funzionalità:
1. Impostare `MAINTENANCE_MODE=1` nel file `.env`
2. Riavviare l'applicazione (se necessario)
3. Accedere a qualsiasi URL dell'applicazione
4. Verificare che venga mostrata la pagina di manutenzione con status code 503
5. Verificare che i file statici vengano caricati correttamente (stile della pagina corretto)

## Estensioni Future (Opzionali)

### Accesso Admin durante Manutenzione
È possibile estendere la funzionalità per permettere agli admin di accedere durante la manutenzione:

```python
@app.before_request
def check_maintenance_mode():
    maintenance_mode = os.getenv('MAINTENANCE_MODE', '0') == '1'
    
    if not maintenance_mode:
        return None
    
    # Permetti accesso agli admin
    if session.get('user_id') and str(session.get('user_id')) == str(ADMIN_USER_ID):
        return None
    
    # Permetti la pagina di login per gli admin
    if request.path in ['/login', '/auth/login', '/auth/callback']:
        return None
    
    if request.path.startswith('/static/'):
        return None
    
    return render_template('ps-maintenance.html'), 503
```

### Messaggio Personalizzato
È possibile aggiungere un messaggio personalizzato tramite variabile d'ambiente:

```env
MAINTENANCE_MESSAGE=Aggiornamento del database in corso. Torneremo alle 15:00.
```

E utilizzarlo nel template:

```python
message = os.getenv('MAINTENANCE_MESSAGE', 'Manutenzione in corso')
return render_template('ps-maintenance.html', message=message), 503
```
