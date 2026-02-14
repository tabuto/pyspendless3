import os
from dotenv import load_dotenv

def load_env(env_path=None):
    """Carica le variabili d'ambiente da un file .env."""
    if env_path is None:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)

# Esempio di utilizzo:
# load_env()
# GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
# GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
# ...
