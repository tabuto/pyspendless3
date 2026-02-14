Installazione nell'ambiente virtuale
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt

## Avvio dell'applicazione Flask

Assicurati di aver attivato l'ambiente virtuale e installato le dipendenze.

Per avviare l'applicazione:

```
.venv/bin/python -m pyspendless.app
```

Oppure, se preferisci usare Flask CLI:

```
export FLASK_APP=pyspendless.app
export FLASK_ENV=development
.venv/bin/flask run
```

L'app sarà disponibile su http://localhost:5000/login

in locale:
export OAUTHLIB_INSECURE_TRANSPORT=1