"""
Authorization Server minimale per /mcp-oauth2 (task23-0, Alexa+).

Scritto a mano (niente authlib.oauth2.rfc6749/AuthorizationServer): Authlib nel
progetto è usato solo come client OAuth per il login Google (vedi app.py), il
sottomodulo server non è mai stato usato e i requisiti qui sono volutamente
chiusi — due grant type (authorization_code + PKCE S256, client_credentials),
nessuna Dynamic Client Registration, nessun OpenID Connect, un solo client
pre-registrato via variabili d'ambiente (oggi Alexa+, pensato per più client
in futuro tramite OAUTH_CLIENTS).

Non toglie né altera nulla di `/mcp`: usa la stessa tabella Token (via
TokenRepository, nuovi type OAUTH_CODE/OAUTH_ACCESS/OAUTH_REFRESH) e la stessa
sessione Flask già usata dal login Google esistente.
"""

import hmac
import secrets
from urllib.parse import urlencode

from flask import Blueprint, request, redirect, render_template, session, url_for, jsonify, abort

# Support both relative and absolute imports (stesso pattern di app.py/mcp_server.py)
try:
    from .conf import (
        get_db_session, BASE_URL,
        OAUTH_ALEXA_CLIENT_ID, OAUTH_ALEXA_CLIENT_SECRET, OAUTH_ALEXA_REDIRECT_URIS
    )
    from .repository import TokenRepository
    from .mcp_server import OAUTH_RESOURCE_PATH
except ImportError:
    from conf import (
        get_db_session, BASE_URL,
        OAUTH_ALEXA_CLIENT_ID, OAUTH_ALEXA_CLIENT_SECRET, OAUTH_ALEXA_REDIRECT_URIS
    )
    from repository import TokenRepository
    from mcp_server import OAUTH_RESOURCE_PATH


oauth_bp = Blueprint('oauth', __name__)

# Risorsa protetta (il server MCP su /mcp-oauth2) che un access token deve avere
# nel parametro `resource` per essere accettato — stessa regola su authorize/token.
RESOURCE_URI = '{}{}'.format(BASE_URL, OAUTH_RESOURCE_PATH)

# Registro client pre-registrati (niente Dynamic Client Registration). Un dict
# keyed by client_id, pensato da subito per più client futuri: oggi ne contiene
# solo uno (Alexa+), aggiungerne un altro è solo una nuova voce + nuove env var.
OAUTH_CLIENTS = {}
if OAUTH_ALEXA_CLIENT_ID:
    OAUTH_CLIENTS[OAUTH_ALEXA_CLIENT_ID] = {
        'secret': OAUTH_ALEXA_CLIENT_SECRET,
        'redirect_uris': set(OAUTH_ALEXA_REDIRECT_URIS),
        'name': 'Alexa+'
    }


# ===== VALIDAZIONE DELLA RICHIESTA DI AUTORIZZAZIONE =====

class _AuthorizeRejected(Exception):
    """Alza un errore di validazione già trasformato in risposta Flask."""

    def __init__(self, response):
        super().__init__()
        self.response = response


def _reject_unsafe(message):
    """
    client_id/redirect_uri non fidati: risposta diretta (JSON, non un redirect),
    per non diventare un open-redirect verso una URL non registrata.
    """
    raise _AuthorizeRejected((jsonify({'error': 'invalid_request', 'error_description': message}), 400))


def _reject_via_redirect(redirect_uri, state, error, description=None):
    """
    redirect_uri è fidato (whitelisted per quel client_id): si può rimandare
    lì con l'errore, come previsto da RFC 6749 §4.1.2.1.
    """
    params = {'error': error}
    if description:
        params['error_description'] = description
    if state is not None:
        params['state'] = state
    raise _AuthorizeRejected(redirect('{}?{}'.format(redirect_uri, urlencode(params))))


def _validate_authorize_params(args):
    """Valida i parametri di GET /oauth/authorize. Ritorna il dict 'pending' da salvare in sessione."""
    client_id = args.get('client_id')
    redirect_uri = args.get('redirect_uri')

    client = OAUTH_CLIENTS.get(client_id)
    if not client:
        _reject_unsafe("client_id non riconosciuto.")
    if not redirect_uri or redirect_uri not in client['redirect_uris']:
        _reject_unsafe("redirect_uri non registrato per questo client.")

    state = args.get('state')

    if args.get('response_type') != 'code':
        _reject_via_redirect(redirect_uri, state, 'unsupported_response_type')

    code_challenge = args.get('code_challenge')
    if not code_challenge or args.get('code_challenge_method') != 'S256':
        _reject_via_redirect(redirect_uri, state, 'invalid_request', 'PKCE S256 obbligatorio.')

    resource = args.get('resource')
    if resource != RESOURCE_URI:
        _reject_via_redirect(redirect_uri, state, 'invalid_target', 'Parametro resource non valido.')

    return {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'code_challenge': code_challenge,
        'resource': resource,
        'state': state,
        'scope': args.get('scope')
    }


def _drop_none(mapping):
    return {key: value for key, value in mapping.items() if value is not None}


# ===== AUTORIZZAZIONE (browser, sessione Flask esistente) =====

@oauth_bp.route('/oauth/authorize', methods=['GET'])
def authorize():
    """
    Avvia il flusso authorization_code + PKCE.

    Se l'utente non è loggato, salva la richiesta validata in sessione e
    rimanda a `/login` (Google, già esistente): i 3 punti di uscita del login
    in app.py, se trovano `session['oauth_authorize_redirect']`, rimandano qui
    SENZA query string — in quel caso si rilegge la richiesta pendente dalla
    sessione invece di ripartire dai parametri dell'URL (che sarebbero vuoti).
    """
    try:
        if not request.args and session.get('oauth_pending_authorize'):
            pending = session['oauth_pending_authorize']
        else:
            pending = _validate_authorize_params(request.args)
    except _AuthorizeRejected as rejected:
        return rejected.response

    if not session.get('user_id'):
        session['oauth_pending_authorize'] = pending
        session['oauth_authorize_redirect'] = url_for('oauth.authorize')
        return redirect(url_for('login'))

    csrf_token = secrets.token_urlsafe(32)
    session['oauth_csrf'] = csrf_token
    session['oauth_pending_authorize'] = pending

    client = OAUTH_CLIENTS.get(pending['client_id'], {})
    return render_template(
        'ps-oauth-consent.html',
        client_name=client.get('name', pending['client_id']),
        csrf_token=csrf_token
    )


@oauth_bp.route('/oauth/authorize/confirm', methods=['POST'])
def authorize_confirm():
    """Elabora la decisione (consenti/annulla) della schermata di consenso."""
    pending = session.get('oauth_pending_authorize')
    user_id = session.get('user_id')

    if not pending or not user_id:
        return redirect(url_for('login'))

    submitted_csrf = request.form.get('csrf_token')
    if not submitted_csrf or not hmac.compare_digest(submitted_csrf, session.get('oauth_csrf') or ''):
        abort(400)

    session.pop('oauth_pending_authorize', None)
    session.pop('oauth_csrf', None)

    redirect_uri = pending['redirect_uri']
    state = pending.get('state')

    if request.form.get('decision') != 'allow':
        return redirect('{}?{}'.format(redirect_uri, urlencode(_drop_none({'error': 'access_denied', 'state': state}))))

    db = get_db_session()
    try:
        code = TokenRepository(db).create_oauth_code(
            user_id=user_id,
            account_id=session.get('account_id'),
            client_id=pending['client_id'],
            redirect_uri=redirect_uri,
            code_challenge=pending['code_challenge'],
            resource=pending['resource'],
            scope=pending.get('scope')
        )
    finally:
        db.close()

    return redirect('{}?{}'.format(redirect_uri, urlencode(_drop_none({'code': code, 'state': state}))))


# ===== TOKEN ENDPOINT (server-to-server) =====

def _authenticate_client(flask_request):
    """
    Autentica il client OAuth via HTTP Basic (obbligatorio per Alexa+), con
    fallback client_secret_post nel body. Confronto del secret SEMPRE a tempo
    costante.
    """
    auth = flask_request.authorization
    if auth and auth.type == 'basic':
        client_id, client_secret = auth.username, auth.password
    else:
        client_id = flask_request.form.get('client_id')
        client_secret = flask_request.form.get('client_secret')

    client = OAUTH_CLIENTS.get(client_id)
    if not client or not client_secret or not client.get('secret'):
        return None
    if not hmac.compare_digest(client_secret, client['secret']):
        return None

    return client_id


def _token_authorization_code(client_id, form):
    code = form.get('code')
    redirect_uri = form.get('redirect_uri')
    code_verifier = form.get('code_verifier')

    if not code or not redirect_uri or not code_verifier:
        return jsonify({'error': 'invalid_request'}), 400

    db = get_db_session()
    try:
        token_repo = TokenRepository(db)
        payload = token_repo.redeem_oauth_code(
            code=code, client_id=client_id, redirect_uri=redirect_uri,
            code_verifier=code_verifier, resource=RESOURCE_URI
        )
        if payload is None:
            return jsonify({'error': 'invalid_grant'}), 400

        access = token_repo.create_oauth_access_token(
            user_id=payload.get('user_id'), account_id=payload.get('account_id'),
            client_id=client_id, scope=payload.get('scope'), resource=RESOURCE_URI
        )
        refresh = token_repo.create_oauth_refresh_token(
            user_id=payload.get('user_id'), account_id=payload.get('account_id'),
            client_id=client_id, scope=payload.get('scope'), resource=RESOURCE_URI
        )
    finally:
        db.close()

    return jsonify(_drop_none({
        'access_token': access['access_token'],
        'token_type': 'Bearer',
        'expires_in': access['expires_in'],
        'refresh_token': refresh['refresh_token'],
        'scope': payload.get('scope')
    })), 200


def _token_client_credentials(client_id, form):
    # Vincolo esplicito Alexa+: nessun refresh token per client_credentials, e
    # nessun user_id/account_id (service-level, niente dati utente).
    db = get_db_session()
    try:
        access = TokenRepository(db).create_oauth_access_token(
            user_id=None, account_id=None, client_id=client_id,
            scope=form.get('scope'), resource=RESOURCE_URI
        )
    finally:
        db.close()

    return jsonify({
        'access_token': access['access_token'],
        'token_type': 'Bearer',
        'expires_in': access['expires_in']
    }), 200


def _token_refresh(client_id, form):
    refresh_token_value = form.get('refresh_token')
    if not refresh_token_value:
        return jsonify({'error': 'invalid_request'}), 400

    db = get_db_session()
    try:
        token_repo = TokenRepository(db)
        payload = token_repo.redeem_oauth_refresh_token(refresh_token_value, client_id)
        if payload is None:
            return jsonify({'error': 'invalid_grant'}), 400

        access = token_repo.create_oauth_access_token(
            user_id=payload.get('user_id'), account_id=payload.get('account_id'),
            client_id=client_id, scope=payload.get('scope'), resource=RESOURCE_URI
        )
        refresh = token_repo.create_oauth_refresh_token(
            user_id=payload.get('user_id'), account_id=payload.get('account_id'),
            client_id=client_id, scope=payload.get('scope'), resource=RESOURCE_URI
        )
    finally:
        db.close()

    return jsonify(_drop_none({
        'access_token': access['access_token'],
        'token_type': 'Bearer',
        'expires_in': access['expires_in'],
        'refresh_token': refresh['refresh_token'],
        'scope': payload.get('scope')
    })), 200


_GRANT_HANDLERS = {
    'authorization_code': _token_authorization_code,
    'client_credentials': _token_client_credentials,
    'refresh_token': _token_refresh
}


@oauth_bp.route('/oauth/token', methods=['POST'])
def token():
    """Token endpoint: authorization_code (+PKCE), client_credentials, refresh_token."""
    client_id = _authenticate_client(request)
    if client_id is None:
        return jsonify({'error': 'invalid_client'}), 401

    grant_type = request.form.get('grant_type')
    handler = _GRANT_HANDLERS.get(grant_type)
    if handler is None:
        return jsonify({'error': 'unsupported_grant_type'}), 400

    return handler(client_id, request.form)


# ===== METADATA DI DISCOVERY (solo sui path dedicati, non sulla radice) =====

@oauth_bp.route('/.well-known/oauth-authorization-server/oauth', methods=['GET'])
def authorization_server_metadata():
    issuer = '{}/oauth'.format(BASE_URL)
    return jsonify({
        'issuer': issuer,
        'authorization_endpoint': '{}/oauth/authorize'.format(BASE_URL),
        'token_endpoint': '{}/oauth/token'.format(BASE_URL),
        'grant_types_supported': ['authorization_code', 'client_credentials', 'refresh_token'],
        'code_challenge_methods_supported': ['S256'],
        'token_endpoint_auth_methods_supported': ['client_secret_basic', 'client_secret_post'],
        'response_types_supported': ['code']
    }), 200


@oauth_bp.route('/.well-known/oauth-protected-resource' + OAUTH_RESOURCE_PATH, methods=['GET'])
def protected_resource_metadata():
    return jsonify({
        'resource': RESOURCE_URI,
        'authorization_servers': ['{}/oauth'.format(BASE_URL)]
    }), 200
