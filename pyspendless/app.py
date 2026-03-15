# Per avviare correttamente:
# python -m pyspendless.app
# oppure
# python pyspendless/app.py

from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify, abort

# Support both relative and absolute imports
try:
    from .conf import load_env, SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI, BASE_URL, ADMIN_USER_ID, get_db_session
    from .repository import UserRepository, CategoryRepository, WalletRepository, MovementRepository, GroupRepository, AccountRepository, TokenRepository, StatsRepository, AdminRepository, UnauthorizedError
except ImportError:
    from conf import load_env, SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI, BASE_URL, ADMIN_USER_ID, get_db_session
    from repository import UserRepository, CategoryRepository, WalletRepository, MovementRepository, GroupRepository, AccountRepository, TokenRepository, StatsRepository, AdminRepository, UnauthorizedError

import os
import logging
import traceback
from authlib.integrations.flask_client import OAuth
from functools import wraps

# Configura logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configurazioni sessione per compatibilità OAuth
# Impostiamo SameSite a None (richiede Secure=False su HTTP localhost se il browser lo permette, altrimenti Lax)
# Ma dato che i cookie non arrivano proprio, proviamo a rimuovere SameSite o usare Lax in modo esplicito
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_NAME'] = 'pyspendless_session'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 604800  # 7 giorni (7 * 24 * 60 * 60)
# Importante: Assicurarsi che il path sia corretto
app.config['SESSION_COOKIE_PATH'] = '/'

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ===== ADMIN DECORATOR =====
def admin_required(f):
    """Decoratore per proteggere le rotte amministrative"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if str(session.get('user_id')) != str(ADMIN_USER_ID):
            if request.is_json:
                return jsonify({'error': 'Accesso negato'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    """Helper per verificare se l'utente corrente è admin"""
    return str(session.get('user_id')) == str(ADMIN_USER_ID)

# ===== CONTEXT PROCESSOR =====
@app.context_processor
def inject_admin_status():
    """Rende disponibile is_admin in tutti i template"""
    return {'is_admin': is_admin()}

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

@app.route("/")
def index():
    """
    Pagina iniziale - reindirizza a home se autenticato, altrimenti a login
    """
    if session.get('user_id'):
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route("/login")
def login():
    return render_template("ps-login.html")

@app.route("/auth/login")
def auth_login():
    redirect_uri = os.getenv('OAUTH_REDIRECT_URI', url_for('auth_callback', _external=True))
    
    # IMPORTANTE: Authlib gestisce lo state internamente.
    # Non dobbiamo interferire manualmente se non necessario.
    
    # Genera la redirect OAuth
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    """
    Callback OAuth Google - Gestisce login e creazione utente/account
    """
    try:
        # Ottieni il token da Google
        logger.info("Inizio callback OAuth")
        
        # Recupera l'invite_token dal cookie se presente
        invite_token_from_cookie = request.cookies.get('pending_invite_token')
        if invite_token_from_cookie:
            logger.info(f"Invite token trovato nel cookie: {invite_token_from_cookie}")
        
        # Gestione errore CSRF/MismatchingStateError
        # Se la sessione è persa, authlib lancerà MismatchingStateError
        try:
            token = google.authorize_access_token()
        except Exception as e:
            logger.warning(f"Errore token access (possibile sessione persa): {e}")
            # Se siamo qui, probabilmente la sessione è persa.
            # Ma Google ci ha risposto correttamente. Possiamo provare a recuperare le info utente manualmente?
            # No, perché serve il 'code' validato con lo 'state'.
            
            # L'unica opzione è riprovare il login o fallire gentilmente
            flash('Sessione scaduta durante il login. Per favore riprova.', 'warning')
            return redirect(url_for('login'))
            
        logger.debug(f"Token ricevuto: {token}")
        
        resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
        user_info = resp.json()
        logger.info(f"User info ricevuto: {user_info.get('email')}")
        
        # Crea una sessione database
        db = get_db_session()
        user_repo = UserRepository(db)
        token_repo = TokenRepository(db)
        
        try:
            # Verifica se l'utente esiste già
            existing_user = user_repo.get_user_by_email(user_info.get('email'))
            
            if existing_user:
                # Utente esistente - procedi con login normale
                logger.info(f"Utente esistente: {existing_user.email}")
                
                # Salva informazioni in sessione
                session.permanent = True
                session['user_id'] = existing_user.id
                session['user_email'] = existing_user.email
                session['user_name'] = existing_user.name
                session['account_id'] = existing_user.account_id
                
                flash(f'Benvenuto, {existing_user.name}!', 'success')
                return redirect(url_for('home'))
            
            # Utente nuovo - verifica whitelist prima
            if not user_repo.is_email_whitelisted(user_info.get('email')):
                raise UnauthorizedError(f"Email {user_info.get('email')} non in whitelist")
            
            # Prima controlla se c'è un invito pendente
            logger.info(f"Nuovo utente: {user_info.get('email')}")
            logger.info(f"Sessione corrente: {dict(session)}")
            pending_token = session.pop('pending_invite_token', None)
            
            # Se non c'è nella sessione, usa quello dal cookie
            if not pending_token and invite_token_from_cookie:
                pending_token = invite_token_from_cookie
                logger.info(f"Usando token dal cookie: {pending_token}")
            
            # Valida il token e recupera account_id se presente
            target_account_id = None
            invite_email = None
            token_obj = None
            
            if pending_token:
                logger.info(f"Validando token di invito: {pending_token}")
                token_obj = token_repo.validate_token(pending_token)
                
                if token_obj:
                    payload = token_repo.get_payload(pending_token)
                    invite_email = payload.get('email')
                    target_account_id = payload.get('account_id')
                    logger.info(f"Token valido - email: {invite_email}, account_id: {target_account_id}")
                    
                    # Verifica che l'email dell'utente corrisponda all'invito
                    if user_info.get('email', '').lower() != invite_email.lower():
                        logger.warning(f"Email mismatch: invito per {invite_email}, login come {user_info.get('email')}")
                        target_account_id = None  # Non usare account_id se email non corrisponde
                else:
                    logger.warning(f"Token di invito non valido: {pending_token}")
            
            # Se c'è un invito valido, crea l'utente e aggiungilo all'account
            if token_obj and target_account_id:
                user = user_repo.create_user_from_oauth(user_info, account_id=target_account_id)
                logger.info(f"Utente creato da invito: {user.email}, account_id: {user.account_id}")
                
                # Salva informazioni in sessione
                session.permanent = True
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['user_name'] = user.name
                session['account_id'] = user.account_id
                
                # Marca il token come usato
                token_repo.mark_as_used(pending_token)
                flash(f'Benvenuto, {user.name}! Hai accettato l\'invito con successo.', 'success')
                
                # Crea la response
                response = redirect(url_for('home'))
                
                # Rimuovi il cookie del pending_invite_token se esiste
                if invite_token_from_cookie:
                    response.set_cookie('pending_invite_token', '', expires=0)
                
                return response
            
            # Nessun invito - avvia onboarding
            # Salva le informazioni dell'utente nella sessione (parziali - non ancora nel DB)
            session['oauth_user_info'] = user_info
            
            # Rimuovi il cookie del pending_invite_token se esiste
            response = redirect(url_for('onboarding'))
            if invite_token_from_cookie:
                response.set_cookie('pending_invite_token', '', expires=0)
            
            return response
            
        except UnauthorizedError as e:
            # Email non in whitelist
            logger.warning(f"Accesso non autorizzato: {str(e)}")
            logger.debug(traceback.format_exc())
            flash('Accesso non autorizzato. La tua email non è nella whitelist.', 'danger')
            return redirect(url_for('login'))
            
        except Exception as e:
            # Errore generico
            logger.error(f"Errore durante il login: {str(e)}")
            logger.debug(traceback.format_exc())
            flash(f'Errore durante il login: {str(e)}', 'danger')
            return redirect(url_for('login'))
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore durante l'autenticazione: {str(e)}")
        logger.debug(traceback.format_exc())
        flash(f'Errore durante l\'autenticazione: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route("/onboarding", methods=['GET'])
def onboarding():
    """
    Pagina di onboarding per nuovi utenti
    """
    # Se l'utente proviene da un link di invito, non mostrare l'onboarding
    pending_token = session.get('pending_invite_token') or request.cookies.get('pending_invite_token')
    if pending_token:
        # Redirect al login per gestire l'invito
        return redirect(url_for('auth_login'))
    
    # Verifica che l'utente abbia informazioni OAuth nella sessione
    oauth_user_info = session.get('oauth_user_info')
    if not oauth_user_info:
        return redirect(url_for('login'))
    
    user_name = oauth_user_info.get('name', 'Utente')
    return render_template("ps-onboarding.html", user_name=user_name)

@app.route("/onboarding", methods=['POST'])
def onboarding_submit():
    """
    Gestisce il submit del form di onboarding
    """
    # Se l'utente proviene da un link di invito, non permettere l'onboarding
    pending_token = session.get('pending_invite_token') or request.cookies.get('pending_invite_token')
    if pending_token:
        # Redirect al login per gestire l'invito
        return redirect(url_for('auth_login'))
    
    # Verifica che l'utente abbia informazioni OAuth nella sessione
    oauth_user_info = session.get('oauth_user_info')
    if not oauth_user_info:
        return redirect(url_for('login'))
    
    # Recupera i dati dal form
    account_name = request.form.get('account_name', '').strip()
    wallet_name = request.form.get('wallet_name', '').strip()
    
    # Validazione
    if not account_name:
        flash('Il nome dell\'account è obbligatorio', 'danger')
        return redirect(url_for('onboarding'))
    
    if not wallet_name:
        flash('Il nome del wallet è obbligatorio', 'danger')
        return redirect(url_for('onboarding'))
    
    # Crea una sessione database
    db = get_db_session()
    user_repo = UserRepository(db)
    
    try:
        # Completa l'onboarding
        user = user_repo.complete_onboarding(oauth_user_info, account_name, wallet_name)
        logger.info(f"Onboarding completato per utente: {user.email}, account_id: {user.account_id}")
        
        # Salva informazioni in sessione
        session.permanent = True
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        session['account_id'] = user.account_id
        
        # Rimuovi oauth_user_info dalla sessione
        session.pop('oauth_user_info', None)
        
        flash(f'Benvenuto, {user.name}! Il tuo account è stato configurato con successo.', 'success')
        return redirect(url_for('home'))
        
    except Exception as e:
        logger.error(f"Errore durante l'onboarding: {str(e)}")
        logger.debug(traceback.format_exc())
        flash(f'Errore durante la configurazione: {str(e)}', 'danger')
        return redirect(url_for('onboarding'))
        
    finally:
        db.close()

@app.route("/home")
def home():
    """
    Home page - richiede autenticazione
    """
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    
    if not user_email:
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    return render_template("ps-home.html", user_email=user_email, user_name=user_name)

@app.route("/create")
def create():
    """
    Form per creare o modificare un movimento
    Se movement_id è presente nella query string, carica il movimento per la modifica
    """
    # Verifica autenticazione
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    account_id = session.get('account_id')
    movement_id = request.args.get('movement_id')
    
    # Recupera dati dal database
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        wallet_repo = WalletRepository(db)
        movement_repo = MovementRepository(db)
        
        # Recupera categorie ordinate per order_index
        categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
        wallets = wallet_repo.get_wallets_for_account(account_id)
        
        # Se movement_id è presente, recupera il movimento per la modifica
        movement = None
        if movement_id:
            movement = movement_repo.get_movement_by_id(movement_id, account_id)
            if not movement:
                flash('Movimento non trovato', 'error')
                return redirect(url_for('movements'))
        
        return render_template(
            "ps-add-mov.html", 
            categories=categories, 
            wallets=wallets,
            movement=movement,
            users=[]  # TODO: implementare quando ci saranno i gruppi
        )
    finally:
        db.close()

@app.route("/movements")
def movements():
    """
    Pagina visualizzazione movimenti con filtri e statistiche
    """
    # Verifica autenticazione
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    account_id = session.get('account_id')
    
    # Recupera filtri dalla query string
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    year = request.args.get('year', type=int, default=current_year)
    month = request.args.get('month', type=int, default=current_month)
    wallet_id = request.args.get('wallet_id', type=int, default=None)
    category_type = request.args.get('category_type', default=None)
    category_id = request.args.get('category_id', type=int, default=None)
    
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        wallet_repo = WalletRepository(db)
        movement_repo = MovementRepository(db)
        
        # Recupera dati per i filtri (ordinati per order_index per UX migliore)
        categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
        wallets = wallet_repo.get_wallets_for_account(account_id)
        
        # Recupera movimenti filtrati
        movements = movement_repo.get_movements_for_account(
            account_id=account_id,
            wallet_id=wallet_id,
            year=year,
            month=month,
            category_id=category_id,
            category_type=category_type
        )
        
        # Recupera statistiche
        stats = movement_repo.get_movements_stats(
            account_id=account_id,
            wallet_id=wallet_id,
            year=year,
            month=month,
            category_id=category_id,
            category_type=category_type
        )
        
        # Prepara anni disponibili (dal 2020 ad oggi + 1 anno futuro)
        years = list(range(2020, current_year + 2))
        months = [
            {'value': 1, 'name': 'Gennaio'},
            {'value': 2, 'name': 'Febbraio'},
            {'value': 3, 'name': 'Marzo'},
            {'value': 4, 'name': 'Aprile'},
            {'value': 5, 'name': 'Maggio'},
            {'value': 6, 'name': 'Giugno'},
            {'value': 7, 'name': 'Luglio'},
            {'value': 8, 'name': 'Agosto'},
            {'value': 9, 'name': 'Settembre'},
            {'value': 10, 'name': 'Ottobre'},
            {'value': 11, 'name': 'Novembre'},
            {'value': 12, 'name': 'Dicembre'}
        ]
        
        category_types = [
            {'value': 'expense', 'name': 'Uscite'},
            {'value': 'income', 'name': 'Entrate'}
        ]
        
        return render_template(
            "ps-show-mov.html",
            movements=movements,
            stats=stats,
            categories=categories,
            wallets=wallets,
            years=years,
            months=months,
            category_types=category_types,
            filters={
                'year': year,
                'month': month,
                'wallet_id': wallet_id,
                'category_type': category_type,
                'category_id': category_id
            }
        )
    finally:
        db.close()

@app.route("/auth/logout")
def logout():
    """
    Logout - pulisce la sessione
    """
    session.clear()
    return redirect(url_for('login'))

@app.route("/api/categories", methods=['GET'])
def api_get_categories():
    """
    API per recuperare le categorie dell'account corrente
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
        
        result = [
            {
                'id': cat.id,
                'name': cat.name,
                'type': cat.type,
                'order_index': cat.order_index
            }
            for cat in categories
        ]
        
        return jsonify(result), 200
    finally:
        db.close()


@app.route("/api/movements", methods=['POST'])
def api_create_movement():
    """
    API per creare o aggiornare un movimento
    Riceve JSON e salva/aggiorna il movimento nel database
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    user_id = session.get('user_id')
    
    try:
        data = request.get_json()
        
        # Validazione dati
        if not data:
            return jsonify({'error': 'Dati non forniti'}), 400
        
        movement_id = data.get('movement_id')  # Se presente, è un UPDATE
        move_date = data.get('move_date')
        category_id = data.get('category_id')
        wallet_id = data.get('wallet_id')
        income = data.get('income')
        expense = data.get('expense')
        note = data.get('note', '')
        
        # Validazione campi obbligatori
        if not move_date or not category_id or not wallet_id:
            return jsonify({'error': 'Campi obbligatori mancanti'}), 400
        
        # Almeno uno tra income e expense deve essere valorizzato
        if not income and not expense:
            return jsonify({'error': 'Specificare almeno entrata o spesa'}), 400
        
        db = get_db_session()
        try:
            # Recupera category e wallet per ottenere i nomi (retrocompatibilità)
            category_repo = CategoryRepository(db)
            wallet_repo = WalletRepository(db)
            user_repo = UserRepository(db)
            movement_repo = MovementRepository(db)
            
            category = category_repo.get_category(category_id)
            wallet = wallet_repo.get_wallet(wallet_id)
            user = user_repo.get_user_by_id(user_id)
            
            if not category or not wallet or not user:
                return jsonify({'error': 'Categoria, wallet o utente non trovati'}), 404
            
            # Verifica che category e wallet appartengano allo stesso account
            if category.account_id != account_id or wallet.account_id != account_id:
                return jsonify({'error': 'Accesso non autorizzato'}), 403
            
            # Converti la data e calcola year/month
            from datetime import datetime
            import uuid
            
            date_obj = datetime.strptime(move_date, '%Y-%m-%d').date()
            move_year = date_obj.year
            move_month = date_obj.month
            
            # Prepara i dati del movimento
            movement_data = {
                'move_date': date_obj,
                'move_year': move_year,
                'move_month': move_month,
                'category': category.name,  # Legacy field
                'wallet': wallet.code,      # Legacy field
                'income': float(income) if income else None,
                'expense': float(expense) if expense else None,
                'note': note,  # Colonna nel DB è 'note'
                'user': user.email,         # Legacy field
                'category_id': category_id,
                'wallet_id': wallet_id
            }
            
            # UPDATE o CREATE
            if movement_id:
                # Verifica che il movimento appartenga all'account
                existing = movement_repo.get_movement_by_id(movement_id, account_id)
                if not existing:
                    return jsonify({'error': 'Movimento non trovato'}), 404
                
                # Aggiorna il movimento
                movement = movement_repo.update_movement(movement_id, movement_data)
                message = 'Movimento aggiornato con successo'
                status_code = 200
            else:
                # Crea nuovo movimento
                movement_data['id'] = str(uuid.uuid4())
                movement_data['account_id'] = account_id
                movement_data['user_id'] = user_id
                movement = movement_repo.create_movement(movement_data)
                message = 'Movimento salvato con successo'
                status_code = 201
            
            return jsonify({
                'success': True,
                'message': message,
                'movement_id': movement.id
            }), status_code
            
        finally:
            db.close()
            
    except ValueError as e:
        logger.error(f"Errore di validazione: {str(e)}")
        return jsonify({'error': f'Errore di validazione: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Errore durante la creazione del movimento: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@app.route("/api/movements/<movement_id>", methods=['DELETE'])
def api_delete_movement(movement_id):
    """
    API per eliminare un movimento
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    
    try:
        db = get_db_session()
        try:
            movement_repo = MovementRepository(db)
            
            # Verifica che il movimento appartenga all'account
            movement = movement_repo.get_movement_by_id(movement_id, account_id)
            if not movement:
                return jsonify({'error': 'Movimento non trovato'}), 404
            
            # Elimina il movimento
            success = movement_repo.delete_movement(movement_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Movimento eliminato con successo'
                }), 200
            else:
                return jsonify({'error': 'Errore durante l\'eliminazione'}), 500
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore durante l'eliminazione del movimento: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@app.route("/ps-search-mov")
def search_movements():
    """
    Pagina ricerca movimenti con paginazione server-side
    """
    # Verifica autenticazione
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    account_id = session.get('account_id')
    
    # Recupera parametri dalla query string
    search_text = request.args.get('search', '').strip()
    page = request.args.get('page', type=int, default=1)
    per_page = 20
    
    db = get_db_session()
    try:
        movement_repo = MovementRepository(db)
        
        # Ricerca movimenti
        result = movement_repo.search_movements(
            account_id=account_id,
            search_text=search_text if search_text else None,
            page=page,
            per_page=per_page
        )
        
        return render_template(
            "ps-search-mov.html",
            movements=result['movements'],
            total=result['total'],
            pages=result['pages'],
            current_page=result['current_page'],
            per_page=result['per_page'],
            search_text=search_text
        )
    finally:
        db.close()


# ========== SETTINGS ROUTES ==========

@app.route("/settings/categories")
def settings_categories():
    """Pagina gestione categorie"""
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    return render_template("ps-setting-categories.html")


@app.route("/settings/wallets")
def settings_wallets():
    """Pagina gestione wallet"""
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    return render_template("ps-setting-wallet.html")


@app.route("/settings/group")
def settings_group():
    """Pagina gestione gruppo"""
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    account_id = session.get('account_id')
    
    db = get_db_session()
    try:
        account_repo = AccountRepository(db)
        account = account_repo.get_account(account_id)
        
        return render_template("ps-setting-group.html", account=account)
    finally:
        db.close()


@app.route("/settings/import-export")
def settings_import_export():
    """Pagina import/export"""
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    return render_template("ps-setting-import-export.html")


@app.route("/settings/admin")
@admin_required
def settings_admin():
    """Pagina amministratore - solo per admin"""
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    db = get_db_session()
    try:
        admin_repo = AdminRepository(db)
        users = admin_repo.get_all_users()
        whitelist = admin_repo.get_all_whitelist()
        return render_template("ps-setting-admin.html", users=users, whitelist=whitelist)
    finally:
        db.close()


# ========== API ADMIN CRUD ==========

@app.route("/admin/whitelist", methods=["POST"])
@admin_required
def admin_add_whitelist():
    """API per aggiungere un'email alla whitelist"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email obbligatoria'}), 400
    
    email = data['email']
    note = data.get('note', '')
    
    db = get_db_session()
    try:
        admin_repo = AdminRepository(db)
        success = admin_repo.add_to_whitelist(email, note)
        if success:
            return jsonify({'message': 'Email aggiunta alla whitelist', 'email': email}), 201
        else:
            return jsonify({'error': 'Email già presente in whitelist'}), 400
    finally:
        db.close()


@app.route("/admin/whitelist/<email>", methods=["DELETE"])
@admin_required
def admin_remove_whitelist(email):
    """API per rimuovere un'email dalla whitelist"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    db = get_db_session()
    try:
        admin_repo = AdminRepository(db)
        success = admin_repo.remove_from_whitelist(email)
        if success:
            return jsonify({'message': 'Email rimossa dalla whitelist'}), 200
        else:
            return jsonify({'error': 'Email non trovata in whitelist'}), 404
    finally:
        db.close()


@app.route("/admin/users", methods=["GET"])
@admin_required
def admin_get_users():
    """API per recuperare la lista utenti"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    db = get_db_session()
    try:
        admin_repo = AdminRepository(db)
        users = admin_repo.get_all_users()
        return jsonify({'users': users}), 200
    finally:
        db.close()


@app.route("/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def admin_delete_user(user_id):
    """API per eliminare un utente"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    # Previeni l'eliminazione dell'admin stesso
    if str(user_id) == str(ADMIN_USER_ID):
        return jsonify({'error': 'Non puoi eliminare l\'utente admin'}), 400
    
    db = get_db_session()
    try:
        admin_repo = AdminRepository(db)
        success = admin_repo.delete_user(user_id)
        if success:
            return jsonify({'message': 'Utente eliminato con successo'}), 200
        else:
            return jsonify({'error': 'Utente non trovato'}), 404
    finally:
        db.close()


# ========== API CATEGORIES CRUD ==========

@app.route("/api/accounts/<int:account_id>/categories", methods=['POST'])
def api_create_category(account_id):
    """API per creare una nuova categoria"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    if session.get('account_id') != account_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    data = request.get_json()
    if not data or not data.get('name') or not data.get('type'):
        return jsonify({'error': 'Nome e tipo sono obbligatori'}), 400
    
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        category = category_repo.create_category(
            name=data['name'],
            account_id=account_id,
            type=data['type'],
            order_index=data.get('order_index', 0)
        )
        return jsonify({
            'id': category.id,
            'name': category.name,
            'type': category.type,
            'order_index': category.order_index
        }), 201
    finally:
        db.close()


@app.route("/api/categories/<int:category_id>", methods=['PUT'])
def api_update_category(category_id):
    """API per aggiornare una categoria"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    data = request.get_json()
    
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        category = category_repo.get_category(category_id)
        
        if not category:
            return jsonify({'error': 'Categoria non trovata'}), 404
        
        if category.account_id != account_id:
            return jsonify({'error': 'Accesso non autorizzato'}), 403
        
        category = category_repo.update_category(category_id, data)
        return jsonify({
            'id': category.id,
            'name': category.name,
            'type': category.type,
            'order_index': category.order_index
        }), 200
    except Exception as e:
        logger.error(f"Errore aggiornamento categoria: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore durante aggiornamento: {str(e)}'}), 500
    finally:
        db.close()


@app.route("/api/categories/<int:category_id>", methods=['DELETE'])
def api_delete_category(category_id):
    """
    API per eliminare una categoria.
    Se la categoria ha movimenti, richiede target_category_id come parametro per spostare i movimenti.
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    
    # Leggi parametri dalla query string o dal body JSON
    data = request.get_json() if request.is_json else {}
    target_category_id = data.get('target_category_id') or request.args.get('target_category_id', type=int)
    
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        movement_repo = MovementRepository(db)
        
        category = category_repo.get_category(category_id)
        
        if not category:
            return jsonify({'error': 'Categoria non trovata'}), 404
        
        if category.account_id != account_id:
            return jsonify({'error': 'Accesso non autorizzato'}), 403
        
        # Verifica se la categoria è usata in movimenti
        movements = movement_repo.get_movements_for_account(account_id, category_id=category_id)
        movements_count = len(movements) if movements else 0
        
        if movements_count > 0 and not target_category_id:
            # Restituisce info per permettere al client di chiedere la categoria target
            return jsonify({
                'error': 'Categoria utilizzata in movimenti',
                'requires_target': True,
                'movements_count': movements_count,
                'category_name': category.name,
                'category_type': category.type
            }), 400
        
        # Elimina la categoria (con migrazione se target_category_id è fornito)
        success = category_repo.delete_category(category_id, target_category_id)
        
        if success:
            message = 'Categoria eliminata con successo'
            if target_category_id and movements_count > 0:
                message = f'Categoria eliminata e {movements_count} movimenti spostati'
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': 'Errore durante eliminazione'}), 500
            
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Errore eliminazione categoria: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore durante eliminazione: {str(e)}'}), 500
    finally:
        db.close()


# ========== API WALLETS CRUD ==========

@app.route("/api/accounts/<int:account_id>/wallets", methods=['GET'])
def api_get_wallets(account_id):
    """API per ottenere i wallet di un account con saldo"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    if session.get('account_id') != account_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    db = get_db_session()
    try:
        wallet_repo = WalletRepository(db)
        movement_repo = MovementRepository(db)
        
        wallets = wallet_repo.get_wallets_for_account(account_id)
        
        result = []
        for wallet in wallets:
            # Calcola saldo
            movements = movement_repo.get_movements_for_account(account_id, wallet_id=wallet.id)
            income = sum(float(m.income) if m.income else 0 for m in movements)
            expense = sum(float(m.expense) if m.expense else 0 for m in movements)
            balance = income - expense
            
            result.append({
                'id': wallet.id,
                'code': wallet.code,
                'name': wallet.name,
                'currency': wallet.currency,
                'balance': balance,
                'order_index': wallet.order_index if hasattr(wallet, 'order_index') else 0
            })
        
        return jsonify(result), 200
    finally:
        db.close()


@app.route("/api/accounts/<int:account_id>/wallets", methods=['POST'])
def api_create_wallet(account_id):
    """API per creare un nuovo wallet"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    if session.get('account_id') != account_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Nome è obbligatorio'}), 400
    
    import uuid
    db = get_db_session()
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.create_wallet(
            code=str(uuid.uuid4())[:8],
            name=data['name'],
            account_id=account_id,
            currency=data.get('currency', 'EUR')
        )
        return jsonify({
            'id': wallet.id,
            'code': wallet.code,
            'name': wallet.name,
            'currency': wallet.currency,
            'order_index': wallet.order_index if hasattr(wallet, 'order_index') else 0
        }), 201
    finally:
        db.close()


@app.route("/api/wallets/<int:wallet_id>", methods=['PUT'])
def api_update_wallet(wallet_id):
    """API per aggiornare un wallet"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    data = request.get_json()
    
    db = get_db_session()
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet(wallet_id)
        
        if not wallet:
            return jsonify({'error': 'Wallet non trovato'}), 404
        
        if wallet.account_id != account_id:
            return jsonify({'error': 'Accesso non autorizzato'}), 403
        
        wallet = wallet_repo.update_wallet(wallet_id, data)
        return jsonify({
            'id': wallet.id,
            'code': wallet.code,
            'name': wallet.name,
            'currency': wallet.currency,
            'order_index': wallet.order_index if hasattr(wallet, 'order_index') else 0
        }), 200
    finally:
        db.close()


@app.route("/api/wallets/<int:wallet_id>", methods=['DELETE'])
def api_delete_wallet(wallet_id):
    """API per eliminare un wallet"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    
    db = get_db_session()
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet(wallet_id)
        
        if not wallet:
            return jsonify({'error': 'Wallet non trovato'}), 404
        
        if wallet.account_id != account_id:
            return jsonify({'error': 'Accesso non autorizzato'}), 403
        
        # Verifica se il wallet è usato in movimenti
        movement_repo = MovementRepository(db)
        movements = movement_repo.get_movements_for_account(account_id, wallet_id=wallet_id)
        if movements:
            return jsonify({'error': 'Impossibile eliminare: wallet utilizzato in movimenti'}), 400
        
        wallet_repo.delete_wallet(wallet_id)
        return jsonify({'message': 'Wallet eliminato'}), 200
    finally:
        db.close()


# ========== API GROUPS ==========

@app.route("/api/groups/<int:group_id>/members", methods=['GET'])
def api_get_group_members(group_id):
    """API per ottenere i membri di un gruppo"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    db = get_db_session()
    try:
        group_repo = GroupRepository(db)
        group = group_repo.get_group(group_id)
        
        if not group or group.account_id != session.get('account_id'):
            return jsonify({'error': 'Gruppo non trovato'}), 404
        
        members = group_repo.get_group_members(group_id)
        
        result = []
        for member in members:
            result.append({
                'id': member.id,
                'email': member.invite_email,
                'status': member.status,
                'user_name': member.user.name if member.user else None
            })
        
        return jsonify(result), 200
    finally:
        db.close()


@app.route("/api/groups/<int:group_id>/invite", methods=['POST'])
def api_invite_to_group(group_id):
    """API per invitare un utente a un gruppo"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email è obbligatoria'}), 400
    
    user_id = session.get('user_id')
    
    db = get_db_session()
    try:
        group_repo = GroupRepository(db)
        group = group_repo.get_group(group_id)
        
        if not group or group.account_id != session.get('account_id'):
            return jsonify({'error': 'Gruppo non trovato'}), 404
        
        # Solo l'owner può invitare
        if str(group.owner_user_id) != str(user_id):
            return jsonify({'error': 'Solo il proprietario può invitare'}), 403
        
        membership = group_repo.create_invite(
            group_id=group_id,
            invite_email=data['email'],
            invited_by_user_id=user_id
        )
        
        return jsonify({
            'id': membership.id,
            'email': membership.invite_email,
            'status': membership.status,
            'token': membership.token
        }), 201
    finally:
        db.close()


# ========== API ACCOUNTS ==========

@app.route("/api/accounts/<int:account_id>", methods=['GET'])
def api_get_account(account_id):
    """API per ottenere i dettagli di un account"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    if session.get('account_id') != account_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    db = get_db_session()
    try:
        account_repo = AccountRepository(db)
        account = account_repo.get_account(account_id)
        
        if not account:
            return jsonify({'error': 'Account non trovato'}), 404
        
        return jsonify({
            'id': account.id,
            'name': account.name,
            'created_at': account.created_at.isoformat() if account.created_at else None
        }), 200
    finally:
        db.close()


@app.route("/api/accounts/<int:account_id>", methods=['PUT'])
def api_update_account(account_id):
    """API per aggiornare il nome dell'account"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    if session.get('account_id') != account_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Nome è obbligatorio'}), 400
    
    db = get_db_session()
    try:
        account_repo = AccountRepository(db)
        account = account_repo.update_account(account_id, {'name': data['name']})
        
        if not account:
            return jsonify({'error': 'Account non trovato'}), 404
        
        return jsonify({
            'id': account.id,
            'name': account.name
        }), 200
    finally:
        db.close()


# ========== API IMPORT/EXPORT ==========

@app.route("/api/export/movements", methods=['POST'])
def api_export_movements():
    """API per esportare movimenti in CSV"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    
    db = get_db_session()
    try:
        movement_repo = MovementRepository(db)
        movements = movement_repo.get_movements_for_account(account_id)
        
        # Crea CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Data', 'Categoria', 'Wallet', 'Entrata', 'Spesa', 'Note'])
        
        # Dati
        for m in movements:
            writer.writerow([
                m.move_date.strftime('%Y-%m-%d'),
                m.category,
                m.wallet,
                float(m.income) if m.income else '',
                float(m.expense) if m.expense else '',
                m.note or ''
            ])
        
        output.seek(0)
        
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=movimenti.csv'
        return response
    finally:
        db.close()


@app.route("/api/import/movements", methods=['POST'])
def api_import_movements():
    """API per importare movimenti da CSV"""
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    account_id = session.get('account_id')
    user_id = session.get('user_id')
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nessun file caricato'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    import csv
    import hashlib
    from datetime import datetime
    
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        wallet_repo = WalletRepository(db)
        user_repo = UserRepository(db)
        movement_repo = MovementRepository(db)
        
        user = user_repo.get_user_by_id(user_id)
        
        # Leggi CSV
        stream = file.stream.read().decode('utf-8')
        csv_reader = csv.DictReader(stream.splitlines())
        
        imported = 0
        errors = []
        
        for row in csv_reader:
            try:
                # Parse data
                move_date_str = row.get('Data', '')
                category_name = row.get('Categoria', '')
                wallet_code = row.get('Wallet', '')
                income_str = row.get('Entrata', '')
                expense_str = row.get('Spesa', '')
                note = row.get('Note', '')
                
                # Converti data
                date_obj = datetime.strptime(move_date_str, '%Y-%m-%d').date()
                
                # Trova categoria (ordine non critico per import ma per consistenza usiamo order_by_index)
                categories = category_repo.get_categories_for_account(account_id, order_by_index=True)
                category = next((c for c in categories if c.name == category_name), None)
                if not category:
                    errors.append(f"Categoria '{category_name}' non trovata")
                    continue
                
                # Trova wallet
                wallets = wallet_repo.get_wallets_for_account(account_id)
                wallet = next((w for w in wallets if w.code == wallet_code), None)
                if not wallet:
                    errors.append(f"Wallet '{wallet_code}' non trovato")
                    continue
                
                # Converti importi
                income = float(income_str) if income_str else None
                expense = float(expense_str) if expense_str else None
                
                # Genera ID come hash per evitare duplicati
                hash_string = f"{date_obj}|{income or 0}|{expense or 0}|{category_name}|{wallet_code}|{note}"
                movement_id = hashlib.md5(hash_string.encode()).hexdigest()
                
                # Verifica se esiste già
                existing = movement_repo.get_movement(movement_id)
                if existing:
                    continue  # Skip duplicati
                
                # Crea movimento
                movement_data = {
                    'id': movement_id,
                    'move_date': date_obj,
                    'move_year': date_obj.year,
                    'move_month': date_obj.month,
                    'category': category.name,
                    'wallet': wallet.code,
                    'income': income,
                    'expense': expense,
                    'note': note,
                    'user': user.email,
                    'account_id': account_id,
                    'user_id': user_id,
                    'category_id': category.id,
                    'wallet_id': wallet.id
                }
                
                movement_repo.create_movement(movement_data)
                imported += 1
                
            except Exception as e:
                errors.append(f"Errore riga: {str(e)}")
        
        return jsonify({
            'imported': imported,
            'errors': errors
        }), 200
    except Exception as e:
        logger.error(f"Errore import: {str(e)}")
        return jsonify({'error': f'Errore durante import: {str(e)}'}), 500
    finally:
        db.close()


# ===== INVITE & TOKEN ENDPOINTS =====

@app.route("/api/generate-link", methods=['POST'])
def generate_link():
    """
    Genera un link di invito per condividere l'account
    
    Input JSON:
        {
            "email": "invitato@gmail.com"
        }
    
    Output JSON:
        {
            "link": "http://localhost:5000/generate-link/callback?token=UUID"
        }
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    try:
        data = request.get_json()
        invite_email = data.get('email')
        
        if not invite_email:
            return jsonify({'error': 'Email mancante'}), 400
        
        # Validazione email Gmail
        if not invite_email.lower().endswith('@gmail.com'):
            return jsonify({'error': 'Solo email Gmail sono accettate'}), 400
        
        account_id = session.get('account_id')
        
        db = get_db_session()
        try:
            token_repo = TokenRepository(db)
            
            # Crea payload
            payload = {
                'email': invite_email,
                'account_id': account_id
            }
            
            # Genera token (valido 7 giorni)
            token = token_repo.create_token('SHARE', payload, expire_days=7)
            
            # Genera link di callback
            link = f"{BASE_URL}/generate-link/callback?token={token.uuid}"
            
            logger.info(f"Link generato per {invite_email}: {link}")
            
            return jsonify({'link': link}), 200
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore generazione link: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route("/api/pending-invites", methods=['GET'])
def get_pending_invites():
    """
    API per recuperare gli inviti pendenti dell'account corrente
    
    Output JSON:
        {
            "invites": [
                {
                    "token_uuid": "...",
                    "email": "...",
                    "created_at": "...",
                    "expires_at": "..."
                }
            ]
        }
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    try:
        account_id = session.get('account_id')
        
        db = get_db_session()
        try:
            token_repo = TokenRepository(db)
            invites = token_repo.get_pending_invites_for_account(account_id)
            return jsonify({'invites': invites}), 200
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore recupero inviti pendenti: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route("/api/pending-invites/<token_uuid>", methods=['DELETE'])
def delete_pending_invite(token_uuid):
    """
    API per eliminare un invito pendente
    
    Input: token_uuid (UUID del token da eliminare)
    
    Output JSON:
        {
            "success": true
        }
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    try:
        account_id = session.get('account_id')
        
        db = get_db_session()
        try:
            token_repo = TokenRepository(db)
            
            # Verifica che il token appartenga all'account corrente
            token = token_repo.get_token(token_uuid)
            if not token:
                return jsonify({'error': 'Invito non trovato'}), 404
            
            # Verifica che il token sia dell'account corrente
            payload = token_repo.get_payload(token_uuid)
            if not payload or payload.get('account_id') != account_id:
                return jsonify({'error': 'Non autorizzato'}), 403
            
            # Elimina il token
            success = token_repo.delete_token(token_uuid)
            if success:
                return jsonify({'success': True}), 200
            else:
                return jsonify({'error': 'Errore durante l\'eliminazione'}), 500
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore eliminazione invito: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route("/generate-link/callback")
def generate_link_callback():
    """
    Callback per gestire l'invito tramite token
    
    Scenario A: Utente loggato
        - Verifica token
        - Aggiunge utente all'account
        - Invalida token
        - Redirect a home
    
    Scenario B: Utente NON loggato
        - Verifica token (base)
        - Salva token in sessione
        - Redirect a login OAuth
    """
    token_uuid = request.args.get('token')
    
    if not token_uuid:
        flash('Token di invito mancante', 'danger')
        return redirect(url_for('login'))
    
    db = get_db_session()
    try:
        token_repo = TokenRepository(db)
        user_repo = UserRepository(db)
        
        # Valida il token
        token = token_repo.validate_token(token_uuid)
        
        if not token:
            flash('Link di invito non valido o scaduto', 'danger')
            return redirect(url_for('login'))
        
        # Recupera payload
        payload = token_repo.get_payload(token_uuid)
        invite_email = payload.get('email')
        target_account_id = payload.get('account_id')
        
        # Scenario A: Utente già loggato
        if session.get('user_id'):
            user_id = session.get('user_id')
            user_email = session.get('user_email')
            
            # Verifica corrispondenza email (opzionale ma consigliato)
            if user_email.lower() != invite_email.lower():
                flash(f'Questo invito è per {invite_email}, ma sei loggato come {user_email}', 'warning')
                # Opzione: forzare logout o permettere comunque l'aggiunta
                # Per ora permettiamo l'aggiunta
            
            # Aggiunge l'utente all'account target
            user = user_repo.get_user_by_id(user_id)
            
            if user.account_id == target_account_id:
                flash('Sei già membro di questo account', 'info')
                token_repo.mark_as_used(token_uuid)
                return redirect(url_for('home'))
            
            # Cambia account dell'utente
            user.account_id = target_account_id
            user.role = 'member'  # Non è owner
            db.commit()
            
            # Aggiorna sessione
            session['account_id'] = target_account_id
            
            # Invalida token
            token_repo.mark_as_used(token_uuid)
            
            flash('Hai accettato l\'invito con successo!', 'success')
            return redirect(url_for('home'))
        
        # Scenario B: Utente NON loggato
        else:
            # TENTATIVO 1: Salva il token in un cookie (best effort)
            response = redirect(url_for('auth_login'))
            
            # Imposta cookie con il token (max_age = 1 ora)
            # Nota: Su localhost HTTP questo cookie potrebbe essere perso al ritorno da Google
            # Se succede, l'utente farà login normale e dovrà cliccare di nuovo sul link di invito
            response.set_cookie(
                'pending_invite_token', 
                token_uuid, 
                max_age=3600,
                path='/',
                httponly=True,
                samesite='Lax'
            )
            
            logger.info(f"Token salvato in cookie: {token_uuid}")
            
            # Messaggio più chiaro per l'utente
            flash('Per accettare l\'invito, effettua prima il login.', 'info')
            return response
            
    except Exception as e:
        logger.error(f"Errore callback invito: {str(e)}")
        logger.debug(traceback.format_exc())
        flash(f'Errore durante l\'elaborazione dell\'invito: {str(e)}', 'danger')
        return redirect(url_for('login'))
    finally:
        db.close()


@app.route("/api/accounts/<int:account_id>/users", methods=['GET'])
def get_account_users(account_id):
    """
    Recupera tutti gli utenti associati a un account
    
    Output JSON:
        {
            "users": [
                {
                    "id": 1,
                    "email": "user@gmail.com",
                    "name": "User Name",
                    "role": "owner"
                }
            ]
        }
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    # Verifica che l'utente appartenga all'account richiesto
    if session.get('account_id') != account_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    try:
        db = get_db_session()
        try:
            user_repo = UserRepository(db)
            users = user_repo.get_users_by_account(account_id)
            
            users_data = [
                {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'role': user.role
                }
                for user in users
            ]
            
            return jsonify({'users': users_data}), 200
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore recupero utenti: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route("/api/user/delete-account", methods=['DELETE'])
def delete_user_account():
    """
    Elimina l'account dell'utente corrente
    
    Comportamento:
    - Se l'utente è l'unico nell'account: elimina tutto (user, account, categories, wallets, movements)
    - Se ci sono altri utenti: elimina solo l'utente e i suoi movimenti
    
    Output JSON:
        {
            "success": true,
            "message": "Account eliminato con successo"
        }
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Non autenticato'}), 401
    
    user_id = session.get('user_id')
    
    try:
        db = get_db_session()
        try:
            user_repo = UserRepository(db)
            
            # Elimina l'utente e i dati associati
            success = user_repo.delete_user(user_id)
            
            if success:
                # Pulisci la sessione
                session.clear()
                
                return jsonify({
                    'success': True,
                    'message': 'Account eliminato con successo'
                }), 200
            else:
                return jsonify({'error': 'Utente non trovato'}), 404
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore eliminazione account: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore durante l\'eliminazione: {str(e)}'}), 500


# =============================================
# Dashboard Routes
# =============================================

@app.route("/dashboard/monthly")
def dashboard_monthly():
    """
    Pagina Dashboard Mensile - richiede autenticazione
    """
    user_id = session.get('user_id')
    account_id = session.get('account_id')
    
    if not user_id or not account_id:
        flash('Devi effettuare il login per accedere a questa pagina', 'warning')
        return redirect(url_for('login'))
    
    return render_template("ps-dashboard-monthly.html")


@app.route("/dashboard/yearly")
def dashboard_yearly():
    """
    Pagina Dashboard Annuale - richiede autenticazione
    """
    user_id = session.get('user_id')
    account_id = session.get('account_id')
    
    if not user_id or not account_id:
        flash('Devi effettuare il login per accedere a questa pagina', 'warning')
        return redirect(url_for('login'))
    
    return render_template("ps-dashboard-yearly.html")


# =============================================
# Stats API Routes
# =============================================

@app.route("/api/stats/monthly", methods=['GET'])
def api_stats_monthly():
    """
    API per statistiche mensili
    Query params: year (int), month (int)
    """
    try:
        user_id = session.get('user_id')
        account_id = session.get('account_id')
        
        if not user_id or not account_id:
            return jsonify({'error': 'Non autorizzato'}), 401
        
        # Recupera parametri
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        if not year or not month:
            return jsonify({'error': 'Parametri year e month richiesti'}), 400
        
        if month < 1 or month > 12:
            return jsonify({'error': 'Mese non valido (1-12)'}), 400
        
        db = get_db_session()
        try:
            stats_repo = StatsRepository(db)
            stats = stats_repo.get_monthly_stats(account_id, year, month)
            return jsonify(stats), 200
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore recupero stats mensili: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore: {str(e)}'}), 500


@app.route("/api/stats/yearly", methods=['GET'])
def api_stats_yearly():
    """
    API per statistiche annuali
    Query params: year (int)
    """
    try:
        user_id = session.get('user_id')
        account_id = session.get('account_id')
        
        if not user_id or not account_id:
            return jsonify({'error': 'Non autorizzato'}), 401
        
        # Recupera parametri
        year = request.args.get('year', type=int)
        
        if not year:
            return jsonify({'error': 'Parametro year richiesto'}), 400
        
        db = get_db_session()
        try:
            stats_repo = StatsRepository(db)
            stats = stats_repo.get_yearly_stats(account_id, year)
            return jsonify(stats), 200
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore recupero stats annuali: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore: {str(e)}'}), 500


@app.route("/api/stats/category-trend", methods=['GET'])
def api_stats_category_trend():
    """
    API per andamento mensile di una categoria
    Query params: year (int), category_name (string)
    """
    try:
        user_id = session.get('user_id')
        account_id = session.get('account_id')
        
        if not user_id or not account_id:
            return jsonify({'error': 'Non autorizzato'}), 401
        
        # Recupera parametri
        year = request.args.get('year', type=int)
        category_name = request.args.get('category_name', type=str)
        
        if not year:
            return jsonify({'error': 'Parametro year richiesto'}), 400
        
        if not category_name:
            return jsonify({'error': 'Parametro category_name richiesto'}), 400
        
        db = get_db_session()
        try:
            stats_repo = StatsRepository(db)
            trend = stats_repo.get_category_monthly_trend(account_id, year, category_name)
            return jsonify(trend), 200
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore recupero trend categoria: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore: {str(e)}'}), 500


@app.route("/api/filters/years", methods=['GET'])
def api_filters_years():
    """
    API per recuperare la lista degli anni disponibili
    """
    try:
        user_id = session.get('user_id')
        account_id = session.get('account_id')
        
        if not user_id or not account_id:
            return jsonify({'error': 'Non autorizzato'}), 401
        
        db = get_db_session()
        try:
            stats_repo = StatsRepository(db)
            years = stats_repo.get_available_years(account_id)
            return jsonify(years), 200
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore recupero anni disponibili: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore: {str(e)}'}), 500


if __name__ == "__main__":
    app.run(debug=True)
