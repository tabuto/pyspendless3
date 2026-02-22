# Per avviare correttamente:
# python -m pyspendless.app

from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from conf import load_env, SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI, get_db_session
from repository import UserRepository, CategoryRepository, WalletRepository, MovementRepository, UnauthorizedError

import os
import logging
import traceback
from authlib.integrations.flask_client import OAuth

# Configura logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

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
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    """
    Callback OAuth Google - Gestisce login e creazione utente/account
    """
    try:
        # Ottieni il token da Google
        logger.info("Inizio callback OAuth")
        token = google.authorize_access_token()
        logger.debug(f"Token ricevuto: {token}")
        
        resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
        user_info = resp.json()
        logger.info(f"User info ricevuto: {user_info.get('email')}")
        
        # Crea una sessione database
        db = get_db_session()
        user_repo = UserRepository(db)
        
        try:
            # Crea o recupera l'utente (include controllo whitelist)
            user = user_repo.create_user_from_oauth(user_info)
            logger.info(f"Utente creato/recuperato: {user.email}")
            
            # Salva informazioni in sessione
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['account_id'] = user.account_id
            
            flash(f'Benvenuto, {user.name}!', 'success')
            return redirect(url_for('home'))
            
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
    Form per creare un nuovo movimento
    """
    # Verifica autenticazione
    if not session.get('user_id'):
        flash('Devi effettuare il login', 'warning')
        return redirect(url_for('login'))
    
    account_id = session.get('account_id')
    
    # Recupera dati dal database
    db = get_db_session()
    try:
        category_repo = CategoryRepository(db)
        wallet_repo = WalletRepository(db)
        
        categories = category_repo.get_categories_for_account(account_id)
        wallets = wallet_repo.get_wallets_for_account(account_id)
        
        return render_template(
            "ps-add-mov.html", 
            categories=categories, 
            wallets=wallets, 
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
        
        # Recupera dati per i filtri
        categories = category_repo.get_categories_for_account(account_id)
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
    flash('Logout effettuato con successo', 'info')
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
        categories = category_repo.get_categories_for_account(account_id)
        
        result = [
            {
                'id': cat.id,
                'name': cat.name,
                'type': cat.type
            }
            for cat in categories
        ]
        
        return jsonify(result), 200
    finally:
        db.close()


@app.route("/api/movements", methods=['POST'])
def api_create_movement():
    """
    API per creare un nuovo movimento
    Riceve JSON e salva il movimento nel database
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
                'id': str(uuid.uuid4()),
                'move_date': date_obj,
                'move_year': move_year,
                'move_month': move_month,
                'category': category.name,  # Legacy field
                'wallet': wallet.code,      # Legacy field
                'income': float(income) if income else None,
                'expense': float(expense) if expense else None,
                'note': note,
                'user': user.email,         # Legacy field
                'account_id': account_id,
                'user_id': user_id,
                'category_id': category_id,
                'wallet_id': wallet_id
            }
            
            # Crea il movimento
            movement = movement_repo.create_movement(movement_data)
            
            return jsonify({
                'success': True,
                'message': 'Movimento salvato con successo',
                'movement_id': movement.id
            }), 201
            
        finally:
            db.close()
            
    except ValueError as e:
        logger.error(f"Errore di validazione: {str(e)}")
        return jsonify({'error': f'Errore di validazione: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Errore durante la creazione del movimento: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(debug=True)
