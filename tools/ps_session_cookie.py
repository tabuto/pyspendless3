#!/usr/bin/env python3
"""
Produce un cookie di sessione Flask firmato per l'utente di sviluppo.

Serve agli script di verifica headless (Playwright) per raggiungere le pagine
autenticate senza passare da Google OAuth e senza toccare credenziali: e' lo
stesso meccanismo che `test_task19_0.py` usa con `session_transaction()`, solo
espresso come cookie da iniettare in un browser vero.

Uso:
    .venv/bin/python tools/ps_session_cookie.py          # stampa nome=valore
    from tools.ps_session_cookie import build_cookie     # (nome, valore, utente)
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, os.path.join(_ROOT, "pyspendless")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from flask.sessions import SecureCookieSessionInterface  # noqa: E402

from pyspendless.app import app  # noqa: E402
from pyspendless.conf import get_db_session  # noqa: E402
from pyspendless.models import User  # noqa: E402


def build_cookie():
    """Ritorna (nome_cookie, valore_firmato, dict_utente) per il primo utente."""
    db = get_db_session()
    try:
        row = db.query(User).first()
        if row is None:
            raise SystemExit(
                "Nessun utente nel DB locale: popola il DB di sviluppo "
                "(vedi backlog/task19-0/fasi/fase-0.md §0.1)."
            )
        user = {
            "id": row.id,
            "account_id": row.account_id,
            "email": row.email,
            "name": row.name,
        }
    finally:
        db.close()

    serializer = SecureCookieSessionInterface().get_signing_serializer(app)
    if serializer is None:
        raise SystemExit("SECRET_KEY assente: impossibile firmare la sessione.")

    value = serializer.dumps({
        "user_id": user["id"],
        "account_id": user["account_id"],
        "user_email": user["email"],
        "user_name": user["name"],
    })
    name = app.config.get("SESSION_COOKIE_NAME") or "session"
    return name, value, user


if __name__ == "__main__":
    n, v, u = build_cookie()
    print(f"{n}={v}", file=sys.stdout)
    print(f"[utente] id={u['id']} email={u['email']} account_id={u['account_id']}",
          file=sys.stderr)
