"""
Configurazione per PySpendless
Costanti, configurazioni e funzioni per il database
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Carica le variabili d'ambiente
def load_env(env_path=None):
    """Carica le variabili d'ambiente da un file .env."""
    if env_path is None:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)

# Carica subito le variabili d'ambiente
load_env()

# ===== CONFIGURAZIONI DATABASE =====
def _resolve_db_path(db_url):
    """Converte i percorsi SQLite relativi in assoluti basati sulla posizione di questo file"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"DATABASE_URL originale: {db_url}")
    
    if db_url.startswith('sqlite:///'):
        # Percorso già assoluto (inizia con /)
        db_path = db_url.replace('sqlite:///', '', 1)
        logger.info(f"Percorso estratto: {db_path}")
        
        if not db_path.startswith('/'):
            # Percorso relativo - convertilo in assoluto
            base_dir = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.abspath(os.path.join(base_dir, db_path))
            
            logger.info(f"Base dir: {base_dir}")
            logger.info(f"Percorso assoluto: {abs_path}")
            
            # Crea la directory se non esiste
            db_dir = os.path.dirname(abs_path)
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Directory database: {db_dir}")
            
            # Verifica che il file sia accessibile
            if os.path.exists(abs_path):
                logger.info(f"File database esiste: {abs_path}")
            else:
                logger.warning(f"File database NON esiste: {abs_path}")
            
            resolved_url = f'sqlite:///{abs_path}'
            logger.info(f"DATABASE_URL risolto: {resolved_url}")
            return resolved_url
    
    logger.info(f"DATABASE_URL non modificato: {db_url}")
    return db_url

DATABASE_URL = _resolve_db_path(os.getenv('DATABASE_URL', 'sqlite:///../data/pyspendless.db'))
print(f"[CONF] DATABASE_URL finale: {DATABASE_URL}")

# ===== CONFIGURAZIONI OAUTH =====
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5000/auth/callback')

# ===== CONFIGURAZIONI APPLICAZIONE =====
SECRET_KEY = os.getenv('SECRET_KEY', 'changeme')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'EUR')
PAGINATION_LIMIT = int(os.getenv('PAGINATION_LIMIT', '50'))
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

# ===== WHITELIST EMAILS (opzionale, preferibile usare DB) =====
WHITELIST_EMAILS = os.getenv('WHITELIST_EMAILS', '').split(',')

# ===== ADMIN USER ID =====
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')

# ===== DATABASE ENGINE E SESSION =====
# Engine globale per l'applicazione
_engine = None
_SessionLocal = None

def get_db_engine():
    """Ritorna l'engine del database (singleton)"""
    global _engine
    if _engine is None:
        connect_args = {}
        if DATABASE_URL.startswith('sqlite'):
            connect_args = {
                'check_same_thread': False,
                'timeout': 30  # Timeout di 30 secondi per SQLite
            }
        _engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            echo=FLASK_ENV == 'development'  # Log SQL queries in development
        )
    return _engine

def get_session_factory():
    """Ritorna la factory per creare sessioni"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_db_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal

def get_db_session() -> Session:
    """Crea e ritorna una nuova sessione database"""
    SessionLocal = get_session_factory()
    return SessionLocal()

@contextmanager
def get_db():
    """
    Context manager per gestire la sessione del database.
    Uso:
        with get_db() as db:
            user = db.query(User).first()
    """
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Inizializza il database creando tutte le tabelle.
    Nota: Le tabelle sono già create tramite gli script SQL,
    questa funzione è utile per verificare che tutto sia a posto.
    """
    from models import Base
    engine = get_db_engine()
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

def drop_db():
    """
    ATTENZIONE: Elimina tutte le tabelle dal database.
    Da usare solo in development!
    """
    if FLASK_ENV != 'development':
        raise RuntimeError("Cannot drop database in production!")
    
    from models import Base
    engine = get_db_engine()
    Base.metadata.drop_all(bind=engine)
    print("Database dropped!")
