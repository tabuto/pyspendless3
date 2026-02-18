# Per avviare correttamente:
# python -m pyspendless.app

from flask import Flask, render_template, redirect, url_for, session, request, flash
from conf import load_env, SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI, get_db_session
from repository import UserRepository, CategoryRepository, WalletRepository, UnauthorizedError

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

@app.route("/auth/logout")
def logout():
    """
    Logout - pulisce la sessione
    """
    session.clear()
    flash('Logout effettuato con successo', 'info')
    return redirect(url_for('login'))

@app.route("/add_movement", methods=['POST'])
def add_movement():
    # In a real app, you'd get form data and save it to the DB
    # e.g., date = request.form.get('move_date')
    flash('Movimento salvato con successo!', 'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
