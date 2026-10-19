"""
Rende un template non instradato come lo renderebbe l'app (vedi tools/ui-preview.py).

Punto delicato: `app.jinja_env.get_template(...).render()` NON esegue i context
processor di Flask. Con quel metodo `app_version` e `is_admin` restano
indefiniti, il footer esce senza versione e la voce Admin non compare mai — e
sembrerebbe un difetto del template invece che del banco di prova.
Qui si passa da `flask.render_template` dentro un request context, che e'
esattamente la strada che percorre una pagina vera.
"""
import contextlib
import io
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def rendi_html(nome_template, contesto=None, user_id="admin"):
    """
    Rende il template con i context processor attivi.

    user_id: "admin"  -> sessione dell'utente ADMIN_USER_ID (is_admin True)
             "utente" -> primo utente non admin del DB (is_admin False)
             None     -> nessuna sessione (utente anonimo)
             <int>    -> quell'id
    """
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        from flask import render_template, session
        from pyspendless.app import app
        from pyspendless.conf import get_db_session, ADMIN_USER_ID
        from pyspendless.models import User

        uid = user_id
        if user_id in ("admin", "utente"):
            db = get_db_session()
            try:
                if user_id == "admin":
                    riga = db.query(User).filter(
                        User.id == int(ADMIN_USER_ID)).first()
                else:
                    riga = db.query(User).filter(
                        User.id != int(ADMIN_USER_ID)).first()
                if riga is None:
                    raise SystemExit(
                        f"Nessun utente '{user_id}' nel DB locale.")
                dati = {"id": riga.id, "account_id": riga.account_id,
                        "email": riga.email, "name": riga.name}
            finally:
                db.close()
            uid = dati["id"]
        else:
            dati = None

        app.config["TESTING"] = True
        with app.test_request_context("/"):
            if dati is not None:
                session["user_id"] = dati["id"]
                session["account_id"] = dati["account_id"]
                session["user_email"] = dati["email"]
                session["user_name"] = dati["name"]
            elif uid is not None:
                session["user_id"] = uid
            return render_template(nome_template, **(contesto or {}))
