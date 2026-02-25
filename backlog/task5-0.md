# Task 5.0: Implementazione Pannello Amministratore

Questo task riguarda l'implementazione di una sezione "Admin" nelle impostazioni, accessibile esclusivamente all'utente specificato tramite variabile d'ambiente.

## Obiettivo
Creare una pagina di amministrazione (Backend UI) per la gestione degli utenti e della whitelist email. La pagina deve essere visibile e accessibile **solo** dall'utente il cui ID corrisponde a `ADMIN_USER_ID`.

## Requisiti

### 1. Configurazione e Sicurezza
- [ ] Aggiungere la variabile `ADMIN_USER_ID` in `.env` e caricarla in `conf.py`.
- [ ] Implementare un controllo (es. decoratore o check nella rotta/template) che permetta l'accesso alla pagina admin solo se `current_user.id == ADMIN_USER_ID`.
- [ ] **IMPORTANTE**: Tutte le rotte API di amministrazione (sotto `/admin/...`) devono verificare rigorosamente che l'utente in sessione corrisponda a `ADMIN_USER_ID`.
- [ ] Se un utente non autorizzato tenta di accedere alla rotta admin o alle API admin, restituire errore 403.
- [ ] Il link alla pagina "Admin" nel menu (es. in `ps-nav.html` o sidebar) deve essere visibile solo per l'admin.

### 2. Pagina di Amministrazione (`/settings/admin`)
- [ ] Creare una nuova rotta in `app.py`: `/settings/admin`.
- [ ] Creare il template `templates/ps-setting-admin.html` che estende `base.html` (o `ps-base.html`).
- [ ] La pagina deve mostrare due sezioni principali:
    1.  **Gestione Whitelist**:
        - Tabella con le email attualmente in whitelist (`EmailWhitelist`).
        - Form per aggiungere una nuova email alla whitelist.
        - Pulsante per rimuovere un'email dalla whitelist.
    2.  **Gestione Utenti**:
        - Tabella con tutti gli utenti registrati (`User`).
        - Colonne visualizzate: ID, Nome, Email, Ruolo, Data creazione.
        - Azione: **Elimina Utente** (con conferma).

### 3. API Endpoints (`/admin/...`)
- [ ] Le operazioni di modifica devono essere esposte tramite API REST sotto il path `/admin`:
    - `POST /admin/whitelist`: Aggiungi email alla whitelist (Body: `{ email: "...", note: "..." }`).
    - `DELETE /admin/whitelist/<email>`: Rimuovi email dalla whitelist.
    - `GET /admin/users`: (Opzionale, se serve caricamento asincrono) Lista utenti.
    - `DELETE /admin/users/<user_id>`: Elimina un utente e i suoi dati correlati.
- [ ] Queste API devono restituire JSON e gestire gli errori (es. 403 Forbidden se non admin).

### 4. Aggiornamenti Backend (`repository.py`)
- [ ] Estendere `UserRepository` (o creare `AdminRepository`) con i metodi necessari:
    - `get_all_users()`: restituisce la lista di tutti gli utenti.
    - `delete_user(user_id)`: elimina un utente dato l'ID.
    - `get_all_whitelist()`: restituisce tutte le email in whitelist.
    - `add_to_whitelist(email, note)`: aggiunge email.
    - `remove_from_whitelist(email)`: rimuove email.

## Istruzioni Tecniche
1.  **Mockup Interfaccia**: Ispirarsi alle altre pagine di settings (`ps-setting-category.html`, ecc.) usando lo stile AdminLTE già presente.
2.  **Route Flask**:
    ```python
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if str(session.get('user_id')) != str(os.environ.get('ADMIN_USER_ID')):
                if request.is_json:
                     return jsonify({'error': 'Accesso negato'}), 403
                abort(403)
            return f(*args, **kwargs)
        return decorated_function

    @app.route("/admin/whitelist", methods=["POST"])
    @admin_required
    def admin_add_whitelist():
        # ... logic ...
    ```
3.  **Database**:
    - Assicurarsi che la cancellazione utente sia coerente. Se l'utente è `owner` di un Account, decidere se cancellare anche l'Account (cascade delete) o impedire la cancellazione. *Approccio suggerito*: Al momento permettere cancellazione e lasciare che SQLAlchemy gestisca i cascade se configurati, o gestire manualmente la pulizia dei dati correlati.

## Criteri di Accettazione
- L'utente Admin vede la voce "Admin" nel menu.
- Gli utenti normali NON vedono la voce e NON possono accedere alla rotta.
- L'admin può aggiungere e rimuovere email dalla whitelist.
- L'admin può visualizzare la lista utenti ed eliminarne uno.
- Le modifiche persistono nel DB sqlite.
