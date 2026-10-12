#!/usr/bin/env python3
"""
Verifica locale del task23-0 (OAuth2 su /mcp-oauth2, Alexa+).

Non e' pytest (il progetto non lo usa, vedi dev_mcp_check.py/test_task22_0.py):
e' uno script di controllo riproducibile con assert espliciti, che lavora SOLO
su un database SQLite in-memory creato al volo. Non tocca in nessun caso il
database configurato in .env.

Copre:
  1. TokenRepository: creazione/validazione/redenzione dei token OAuth
     (OAUTH_CODE con PKCE, OAUTH_ACCESS, OAUTH_REFRESH), connessioni e revoca.
  2. mcp_server.handle_http_request nei due auth_mode ('static' invariato,
     'oauth' nuovo): nessuna regressione su /mcp, 401/403 solo su /mcp-oauth2.
  3. Il flusso end-to-end /oauth/authorize -> /oauth/authorize/confirm ->
     /oauth/token -> /mcp-oauth2, via Flask test client sull'app reale.

Uso:
    pyspendless/.venv/bin/python -m pyspendless.test.test_task23_0
"""

import os
import sys
import uuid
import base64
import hashlib
from urllib.parse import urlparse, parse_qs

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Account, User, Category, Token
from repository import TokenRepository, WalletRepository
import mcp_server
import oauth_server
import app as app_module


TEST_CLIENT_ID = 'test-alexa-client'
TEST_CLIENT_SECRET = 'test-secret-xyz'
TEST_REDIRECT_URI = 'https://example-alexa.test/callback'


class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []

    def check(self, description, condition, detail=''):
        if condition:
            self.passed += 1
            print('  OK   {}'.format(description))
        else:
            self.failed += 1
            self.failures.append(description)
            print('  FAIL {}{}'.format(description, ' -> {}'.format(detail) if detail else ''))

    def section(self, title):
        print('\n== {} =='.format(title))

    def summary(self):
        print('\n{}\n{} controlli superati, {} falliti'.format('-' * 60, self.passed, self.failed))
        if self.failures:
            print('\nFalliti:')
            for failure in self.failures:
                print('  - {}'.format(failure))
        return 0 if self.failed == 0 else 1


def in_memory_session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def b64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def make_pkce_pair():
    verifier = b64url_no_pad(os.urandom(32))
    challenge = b64url_no_pad(hashlib.sha256(verifier.encode('ascii')).digest())
    return verifier, challenge


class FakeFlaskRequest:
    """Stand-in minimale per flask.Request: solo .headers e .get_data(as_text=True)."""

    def __init__(self, body, headers=None):
        self._body = body
        self._headers = headers or {}

    @property
    def headers(self):
        return self._headers

    def get_data(self, as_text=False):
        return self._body


def rpc_call(method, params=None, msg_id=1):
    payload = {'jsonrpc': '2.0', 'method': method}
    if params is not None:
        payload['params'] = params
    if msg_id is not None:
        payload['id'] = msg_id
    import json
    return json.dumps(payload)


# ===== SEZIONE 1: TokenRepository — ciclo di vita dei token OAuth =====

def check_token_repository_oauth(checker):
    checker.section('TokenRepository — token OAuth (codice/PKCE, access, refresh, connessioni)')

    db = in_memory_session()
    account = Account(name='Famiglia Test')
    db.add(account)
    db.flush()
    user = User(public_uid=str(uuid.uuid4()), google_id='g-{}'.format(uuid.uuid4()),
                email='u-{}@example.com'.format(uuid.uuid4()), name='Utente',
                account_id=account.id, role='member')
    db.add(user)
    db.flush()

    token_repo = TokenRepository(db)
    resource = 'http://localhost:5000/mcp-oauth2'
    verifier, challenge = make_pkce_pair()

    code = token_repo.create_oauth_code(
        user_id=user.id, account_id=account.id, client_id=TEST_CLIENT_ID,
        redirect_uri=TEST_REDIRECT_URI, code_challenge=challenge, resource=resource
    )
    checker.check('create_oauth_code ritorna un codice non vuoto', bool(code))

    wrong_verifier, _ = make_pkce_pair()
    checker.check(
        'redeem con code_verifier errato viene rifiutato',
        token_repo.redeem_oauth_code(code, TEST_CLIENT_ID, TEST_REDIRECT_URI, wrong_verifier, resource) is None
    )

    payload = token_repo.redeem_oauth_code(code, TEST_CLIENT_ID, TEST_REDIRECT_URI, verifier, resource)
    checker.check('redeem con PKCE corretto riesce e porta lo user_id giusto',
                  payload is not None and payload.get('user_id') == str(user.id), payload)

    checker.check('lo stesso codice non è riutilizzabile (monouso)',
                  token_repo.redeem_oauth_code(code, TEST_CLIENT_ID, TEST_REDIRECT_URI, verifier, resource) is None)

    code2 = token_repo.create_oauth_code(user.id, account.id, TEST_CLIENT_ID, TEST_REDIRECT_URI, challenge, resource)
    checker.check('redirect_uri diverso da quello dell\'authorize viene rifiutato',
                  token_repo.redeem_oauth_code(code2, TEST_CLIENT_ID, 'https://altro/cb', verifier, resource) is None)
    checker.check('resource diversa da quella dell\'authorize viene rifiutata',
                  token_repo.redeem_oauth_code(code2, TEST_CLIENT_ID, TEST_REDIRECT_URI, verifier, 'http://altro/mcp') is None)

    access = token_repo.create_oauth_access_token(user.id, account.id, TEST_CLIENT_ID, 'movements', resource)
    checker.check('create_oauth_access_token espone expires_in=3600', access['expires_in'] == 3600)
    validated = token_repo.validate_oauth_access_token(access['access_token'])
    checker.check('validate_oauth_access_token accetta il token appena creato', validated is not None)
    checker.check('validate_oauth_access_token rifiuta un token inventato',
                  token_repo.validate_oauth_access_token('inventato') is None)

    refresh = token_repo.create_oauth_refresh_token(user.id, account.id, TEST_CLIENT_ID, 'movements', resource)
    rotated = token_repo.redeem_oauth_refresh_token(refresh['refresh_token'], TEST_CLIENT_ID)
    checker.check('redeem_oauth_refresh_token riesce e porta lo user_id giusto',
                  rotated is not None and rotated.get('user_id') == str(user.id), rotated)
    checker.check('lo stesso refresh token non è riutilizzabile (rotazione)',
                  token_repo.redeem_oauth_refresh_token(refresh['refresh_token'], TEST_CLIENT_ID) is None)
    checker.check('redeem_oauth_refresh_token rifiuta un client_id diverso',
                  token_repo.redeem_oauth_refresh_token(
                      token_repo.create_oauth_refresh_token(user.id, account.id, TEST_CLIENT_ID, None, resource)['refresh_token'],
                      'altro-client'
                  ) is None)

    # client_credentials: nessun utente associato
    cc_access = token_repo.create_oauth_access_token(None, None, TEST_CLIENT_ID, 'service', resource)
    cc_token = token_repo.validate_oauth_access_token(cc_access['access_token'])
    cc_payload = __import__('json').loads(cc_token.payload)
    checker.check('token client_credentials ha user_id=None nel payload', cc_payload.get('user_id') is None, cc_payload)

    # connessioni + revoca: non deve toccare i token MCP personali
    mcp_created = token_repo.create_mcp_token(user.id, account.id, 'Claude')
    connections = token_repo.get_oauth_connections_for_user(user.id)
    checker.check('get_oauth_connections_for_user elenca il client OAuth',
                  any(c['client_id'] == TEST_CLIENT_ID for c in connections), connections)

    revoked = token_repo.revoke_oauth_connection(user.id, TEST_CLIENT_ID)
    checker.check('revoke_oauth_connection revoca almeno un token', revoked > 0, revoked)
    checker.check('validate_oauth_access_token rifiuta il token appena revocato',
                  token_repo.validate_oauth_access_token(access['access_token']) is None)
    checker.check('revoke_oauth_connection NON ha toccato il token MCP personale',
                  token_repo.validate_mcp_secret(mcp_created['secret']) is not None)

    db.close()


# ===== SEZIONE 2: mcp_server — auth_mode 'static' (invariato) vs 'oauth' =====

def check_mcp_server_auth_modes(checker):
    checker.section("mcp_server.handle_http_request — auth_mode 'static' invariato vs 'oauth'")

    db_session = in_memory_session()
    account = Account(name='Famiglia Test')
    db_session.add(account)
    db_session.flush()
    user = User(public_uid=str(uuid.uuid4()), google_id='g-{}'.format(uuid.uuid4()),
                email='u2-{}@example.com'.format(uuid.uuid4()), name='Utente',
                account_id=account.id, role='member')
    db_session.add(user)
    db_session.flush()
    db_session.add(Category(name='Spesa', account_id=account.id, type='expense'))
    db_session.commit()

    engine = db_session.get_bind()
    session_factory = sessionmaker(bind=engine)
    original_get_db_session = mcp_server.get_db_session
    mcp_server.get_db_session = lambda: session_factory()

    try:
        token_repo = TokenRepository(session_factory())
        mcp_token = token_repo.create_mcp_token(user.id, account.id, 'Claude')
        resource = '{}{}'.format(mcp_server.BASE_URL, mcp_server.OAUTH_RESOURCE_PATH)
        oauth_access = token_repo.create_oauth_access_token(user.id, account.id, TEST_CLIENT_ID, None, resource)
        cc_access = token_repo.create_oauth_access_token(None, None, TEST_CLIENT_ID, None, resource)

        list_categories_call = rpc_call('tools/call', {'name': 'list_categories', 'arguments': {}})

        # --- static (/mcp): INVARIATO — mai 401, mai WWW-Authenticate ---
        req = FakeFlaskRequest(list_categories_call)
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0')
        checker.check('static: tools/call senza token -> 200', status == 200, status)
        checker.check('static: isError=True senza token', body['result']['isError'] is True, body)
        checker.check('static: nessun header (dict vuoto)', headers == {}, headers)

        req = FakeFlaskRequest(list_categories_call, {'Authorization': 'Bearer {}'.format(mcp_token['secret'])})
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0')
        checker.check('static: token MCP valido -> 200 senza errore',
                      status == 200 and body['result']['isError'] is False, body)

        req = FakeFlaskRequest(list_categories_call, {'Authorization': 'Bearer {}'.format(oauth_access['access_token'])})
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0')
        checker.check('static: token OAuth rifiutato come 200+isError (non 401)',
                      status == 200 and body['result']['isError'] is True, (status, body))
        checker.check('static: nessun WWW-Authenticate anche con token OAuth', headers == {})

        req = FakeFlaskRequest(rpc_call('initialize', {'protocolVersion': '2025-11-25'}))
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0')
        checker.check("static: initialize NON accetta 2025-11-25 (echo solo la propria)",
                      body['result']['protocolVersion'] == mcp_server.PROTOCOL_VERSION, body)

        # --- oauth (/mcp-oauth2): NUOVO — 401/403 con WWW-Authenticate ---
        req = FakeFlaskRequest(list_categories_call)
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0', auth_mode='oauth')
        checker.check('oauth: tools/call senza token -> 401', status == 401 and body is None, status)
        checker.check('oauth: 401 porta WWW-Authenticate', 'WWW-Authenticate' in headers, headers)

        req = FakeFlaskRequest(list_categories_call, {'Authorization': 'Bearer {}'.format(mcp_token['secret'])})
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0', auth_mode='oauth')
        checker.check('oauth: token statico MCP rifiutato (tipo diverso) -> 401', status == 401, status)

        req = FakeFlaskRequest(list_categories_call, {'Authorization': 'Bearer {}'.format(oauth_access['access_token'])})
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0', auth_mode='oauth')
        checker.check('oauth: access token utente valido -> 200 senza errore',
                      status == 200 and body['result']['isError'] is False, (status, body))

        req = FakeFlaskRequest(list_categories_call, {'Authorization': 'Bearer {}'.format(cc_access['access_token'])})
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0', auth_mode='oauth')
        checker.check('oauth: client_credentials su tools/call -> 403', status == 403, status)
        checker.check('oauth: 403 porta WWW-Authenticate con insufficient_scope',
                      'insufficient_scope' in headers.get('WWW-Authenticate', ''), headers)

        req = FakeFlaskRequest(rpc_call('tools/list'))
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0', auth_mode='oauth')
        checker.check('oauth: tools/list resta pubblico senza token', status == 200, status)

        req = FakeFlaskRequest(rpc_call('initialize', {'protocolVersion': '2025-11-25'}))
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0', auth_mode='oauth')
        checker.check('oauth: initialize accetta 2025-11-25',
                      body['result']['protocolVersion'] == '2025-11-25', body)

        req = FakeFlaskRequest('non-json', {})
        body, status, headers = mcp_server.handle_http_request(req, '0.0.0')
        checker.check('static: corpo non JSON -> 400 (comportamento preesistente, invariato)',
                      status == 400, status)

    finally:
        mcp_server.get_db_session = original_get_db_session
        db_session.close()


# ===== SEZIONE 3: flusso end-to-end via Flask test client =====

def check_end_to_end_oauth_flow(checker):
    checker.section('/oauth/authorize -> /oauth/authorize/confirm -> /oauth/token -> /mcp-oauth2 (end-to-end)')

    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    setup_db = session_factory()
    account = Account(name='Famiglia Test')
    setup_db.add(account)
    setup_db.flush()
    user = User(public_uid=str(uuid.uuid4()), google_id='g-{}'.format(uuid.uuid4()),
                email='u3-{}@example.com'.format(uuid.uuid4()), name='Utente',
                account_id=account.id, role='member')
    setup_db.add(user)
    setup_db.flush()
    setup_db.add(Category(name='Spesa', account_id=account.id, type='expense'))
    WalletRepository(setup_db).create_wallet(code='W1', name='Contanti', account_id=account.id)
    setup_db.commit()
    user_id, account_id = user.id, account.id
    setup_db.close()

    original_mcp_get_db = mcp_server.get_db_session
    original_oauth_get_db = oauth_server.get_db_session
    original_app_get_db = app_module.get_db_session
    original_clients = oauth_server.OAUTH_CLIENTS

    mcp_server.get_db_session = lambda: session_factory()
    oauth_server.get_db_session = lambda: session_factory()
    app_module.get_db_session = lambda: session_factory()
    oauth_server.OAUTH_CLIENTS = {
        TEST_CLIENT_ID: {
            'secret': TEST_CLIENT_SECRET,
            'redirect_uris': {TEST_REDIRECT_URI},
            'name': 'Alexa+ (test)'
        }
    }

    resource = '{}{}'.format(mcp_server.BASE_URL, mcp_server.OAUTH_RESOURCE_PATH)
    verifier, challenge = make_pkce_pair()
    basic_auth = base64.b64encode('{}:{}'.format(TEST_CLIENT_ID, TEST_CLIENT_SECRET).encode()).decode()

    flask_app = app_module.app
    flask_app.config['TESTING'] = True

    def authorize_query(**overrides):
        q = {
            'response_type': 'code', 'client_id': TEST_CLIENT_ID,
            'redirect_uri': TEST_REDIRECT_URI, 'code_challenge': challenge,
            'code_challenge_method': 'S256', 'resource': resource, 'state': 'state123'
        }
        q.update(overrides)
        return q

    try:
        with flask_app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = user_id
                sess['account_id'] = account_id

            resp = client.get('/oauth/authorize', query_string=authorize_query(client_id='client-sconosciuto'))
            checker.check('client_id sconosciuto -> 400 diretto (non un redirect, anti open-redirect)',
                          resp.status_code == 400, resp.status_code)

            resp = client.get('/oauth/authorize', query_string=authorize_query(redirect_uri='https://evil.test/cb'))
            checker.check('redirect_uri non in whitelist -> 400 diretto',
                          resp.status_code == 400, resp.status_code)

            resp = client.get('/oauth/authorize', query_string=authorize_query(resource='http://altro/mcp'))
            location = resp.headers.get('Location', '')
            checker.check('resource errata -> redirect a redirect_uri con error=invalid_target',
                          resp.status_code in (302, 303) and location.startswith(TEST_REDIRECT_URI)
                          and 'error=invalid_target' in location, location)

            resp = client.get('/oauth/authorize', query_string=authorize_query())
            checker.check('richiesta valida + utente già loggato -> pagina di consenso',
                          resp.status_code == 200 and b'Consenti' in resp.data, resp.status_code)

            with client.session_transaction() as sess:
                csrf_token = sess.get('oauth_csrf')
            checker.check('CSRF token salvato in sessione', bool(csrf_token))

            resp = client.post('/oauth/authorize/confirm', data={'csrf_token': 'sbagliato', 'decision': 'allow'})
            checker.check('CSRF errato su confirm -> 400', resp.status_code == 400, resp.status_code)

            resp = client.get('/oauth/authorize', query_string=authorize_query())
            with client.session_transaction() as sess:
                csrf_token = sess.get('oauth_csrf')

            resp = client.post('/oauth/authorize/confirm', data={'csrf_token': csrf_token, 'decision': 'deny'})
            location = resp.headers.get('Location', '')
            checker.check('decision=deny -> redirect con error=access_denied',
                          location.startswith(TEST_REDIRECT_URI) and 'error=access_denied' in location, location)

            resp = client.get('/oauth/authorize', query_string=authorize_query())
            with client.session_transaction() as sess:
                csrf_token = sess.get('oauth_csrf')
            resp = client.post('/oauth/authorize/confirm', data={'csrf_token': csrf_token, 'decision': 'allow'})
            location = resp.headers.get('Location', '')
            checker.check('decision=allow -> redirect con code+state',
                          location.startswith(TEST_REDIRECT_URI) and 'code=' in location and 'state=state123' in location,
                          location)

            code = parse_qs(urlparse(location).query)['code'][0]

            resp = client.post('/oauth/token', data={
                'grant_type': 'authorization_code', 'code': code,
                'redirect_uri': TEST_REDIRECT_URI, 'code_verifier': verifier
            }, headers={'Authorization': 'Basic {}'.format(basic_auth)})
            token_data = resp.get_json() or {}
            checker.check('scambio code->token riuscito, con access_token e refresh_token',
                          resp.status_code == 200 and token_data.get('access_token') and token_data.get('refresh_token'),
                          token_data)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')

            resp = client.post('/oauth/token', data={
                'grant_type': 'authorization_code', 'code': code,
                'redirect_uri': TEST_REDIRECT_URI, 'code_verifier': verifier
            }, headers={'Authorization': 'Basic {}'.format(basic_auth)})
            checker.check('code riusato -> 400 invalid_grant',
                          resp.status_code == 400 and (resp.get_json() or {}).get('error') == 'invalid_grant')

            resp = client.post('/mcp-oauth2', json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'list_categories', 'arguments': {}}
            }, headers={'Authorization': 'Bearer {}'.format(access_token)})
            body = resp.get_json() or {}
            checker.check('tools/call su /mcp-oauth2 con access token valido -> 200 senza errore',
                          resp.status_code == 200 and body.get('result', {}).get('isError') is False, body)

            resp = client.post('/mcp-oauth2', json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'list_categories', 'arguments': {}}
            })
            checker.check('tools/call su /mcp-oauth2 senza token -> 401', resp.status_code == 401, resp.status_code)
            checker.check('401 porta l\'header WWW-Authenticate', 'WWW-Authenticate' in resp.headers)

            resp = client.post('/mcp', json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'list_categories', 'arguments': {}}
            }, headers={'Authorization': 'Bearer {}'.format(access_token)})
            body = resp.get_json() or {}
            checker.check('token OAuth rifiutato su /mcp come 200+isError, non 401',
                          resp.status_code == 200 and body.get('result', {}).get('isError') is True, (resp.status_code, body))
            checker.check('nessun WWW-Authenticate su /mcp', 'WWW-Authenticate' not in resp.headers)

            resp = client.post('/oauth/token', data={'grant_type': 'client_credentials', 'scope': 'service'},
                                headers={'Authorization': 'Basic {}'.format(basic_auth)})
            cc_data = resp.get_json() or {}
            checker.check('client_credentials -> access_token senza refresh_token',
                          resp.status_code == 200 and cc_data.get('access_token') and 'refresh_token' not in cc_data,
                          cc_data)

            resp = client.post('/mcp-oauth2', json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'list_categories', 'arguments': {}}
            }, headers={'Authorization': 'Bearer {}'.format(cc_data.get("access_token"))})
            checker.check('client_credentials su tools/call -> 403', resp.status_code == 403, resp.status_code)

            resp = client.get('/.well-known/oauth-protected-resource/mcp-oauth2')
            metadata = resp.get_json() or {}
            checker.check('metadata reali sul path dedicato (non il 404 generico)',
                          resp.status_code == 200 and metadata.get('resource') == resource, metadata)

            resp = client.get('/.well-known/oauth-protected-resource')
            checker.check('well-known radice resta 404 JSON (invariato)', resp.status_code == 404, resp.status_code)

            resp = client.get('/.well-known/oauth-protected-resource/mcp')
            checker.check("well-known radice con suffisso 'mcp' resta 404 (sonda Claude)",
                          resp.status_code == 404, resp.status_code)

            resp = client.get('/.well-known/oauth-authorization-server/oauth')
            metadata = resp.get_json() or {}
            checker.check("metadata authorization server su /.../oauth, issuer termina con '/oauth'",
                          resp.status_code == 200 and metadata.get('issuer', '').endswith('/oauth'), metadata)

            db = session_factory()
            revoked = TokenRepository(db).revoke_oauth_connection(user_id, TEST_CLIENT_ID)
            db.close()
            checker.check('revoca della connessione: almeno un token invalidato', revoked > 0, revoked)

            resp = client.post('/oauth/token', data={'grant_type': 'refresh_token', 'refresh_token': refresh_token},
                                headers={'Authorization': 'Basic {}'.format(basic_auth)})
            checker.check('refresh_token dopo la revoca -> invalid_grant',
                          resp.status_code == 400 and (resp.get_json() or {}).get('error') == 'invalid_grant')

    finally:
        mcp_server.get_db_session = original_mcp_get_db
        oauth_server.get_db_session = original_oauth_get_db
        app_module.get_db_session = original_app_get_db
        oauth_server.OAUTH_CLIENTS = original_clients


def main():
    checker = Checker()
    check_token_repository_oauth(checker)
    check_mcp_server_auth_modes(checker)
    check_end_to_end_oauth_flow(checker)
    sys.exit(checker.summary())


if __name__ == '__main__':
    main()
