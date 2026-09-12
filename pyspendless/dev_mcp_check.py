"""
Script di verifica locale del server MCP di PySpendless (task20-0, Fase 5).

Non è una suite di test automatica: è uno script di controllo manuale riproducibile,
in linea con il resto del progetto (che non ha pytest).

Uso:
    1. avviare l'app in locale:      python -m pyspendless.app
    2. in un altro terminale:        python -m pyspendless.dev_mcp_check

Opzioni:
    --base-url URL     default http://localhost:5000
    --user-id ID       utente da usare (default: il primo utente del DB)
    --keep             non cancella i movimenti di prova creati

Lo script crea un token MCP temporaneo, esegue i controlli, poi revoca il token e
cancella i movimenti creati (salvo --keep). Lavora sul DB configurato in .env:
NON eseguirlo puntando al database di produzione.
"""

import argparse
import json
import sys
from datetime import date, timedelta

import requests

# Support both relative and absolute imports
try:
    from .conf import get_db_session
    from .models import User
    from .repository import TokenRepository, MovementRepository
except ImportError:
    from conf import get_db_session
    from models import User
    from repository import TokenRepository, MovementRepository


# ===== INFRASTRUTTURA DI CONTROLLO =====

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


class McpClient:
    """Client JSON-RPC minimale per l'endpoint /mcp."""

    def __init__(self, url, secret=None, header_mode='bearer'):
        self.url = url
        self.secret = secret
        self.header_mode = header_mode
        self._id = 0

    def _headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        if self.secret:
            if self.header_mode == 'bearer':
                headers['Authorization'] = 'Bearer {}'.format(self.secret)
            else:
                headers[self.header_mode] = self.secret
        return headers

    def call(self, method, params=None, notification=False, raw_body=None):
        if raw_body is not None:
            return requests.post(self.url, data=raw_body, headers=self._headers(), timeout=30)

        payload = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            payload['params'] = params
        if not notification:
            self._id += 1
            payload['id'] = self._id

        return requests.post(self.url, data=json.dumps(payload), headers=self._headers(), timeout=30)


def rpc_result(response):
    """Estrae il 'result' da una risposta, o None."""
    try:
        return response.json().get('result')
    except ValueError:
        return None


def tool_payload(response):
    """Estrae (isError, testo, structuredContent) da una risposta tools/call."""
    result = rpc_result(response) or {}
    text = ''
    for block in result.get('content', []):
        if block.get('type') == 'text':
            text += block.get('text', '')
    return result.get('isError'), text, result.get('structuredContent') or {}


# ===== PREPARAZIONE =====

def pick_user(user_id=None):
    """Ritorna (user_id, account_id) da usare per i controlli."""
    db = get_db_session()
    try:
        if user_id:
            user = db.query(User).filter_by(id=user_id).first()
        else:
            user = db.query(User).order_by(User.id).first()

        if not user:
            print('ERRORE: nessun utente nel database. Esegui prima il setup/onboarding.')
            sys.exit(2)

        return user.id, user.account_id
    finally:
        db.close()


def create_token(user_id, account_id):
    db = get_db_session()
    try:
        created = TokenRepository(db).create_mcp_token(user_id, account_id, 'dev_mcp_check')
        return created['secret'], created['token_hash']
    finally:
        db.close()


def revoke_token(token_hash):
    db = get_db_session()
    try:
        TokenRepository(db).mark_as_used(token_hash)
    finally:
        db.close()


def delete_movements(movement_ids):
    if not movement_ids:
        return
    db = get_db_session()
    try:
        repo = MovementRepository(db)
        for movement_id in movement_ids:
            repo.delete_movement(movement_id)
    finally:
        db.close()


# ===== CONTROLLI =====

def run(base_url, user_id, keep):
    url = base_url.rstrip('/') + '/mcp'
    checker = Checker()
    created_movements = []

    user_id, account_id = pick_user(user_id)
    print('Utente {} / account {} — endpoint {}'.format(user_id, account_id, url))

    secret, token_hash = create_token(user_id, account_id)
    client = McpClient(url, secret)

    try:
        # --- protocollo ---
        checker.section('Protocollo')

        response = client.call('initialize', {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'dev_mcp_check', 'version': '1'}
        })
        result = rpc_result(response) or {}
        checker.check('initialize risponde 200', response.status_code == 200, response.status_code)
        checker.check('initialize dichiara serverInfo',
                      bool(result.get('serverInfo', {}).get('version')), result)
        checker.check('initialize espone capability tools', 'tools' in result.get('capabilities', {}))

        response = client.call('initialize', {'protocolVersion': '1999-01-01'})
        checker.check('initialize con versione sconosciuta non fallisce',
                      response.status_code == 200 and rpc_result(response) is not None)

        response = client.call('notifications/initialized', {}, notification=True)
        checker.check('notifications/initialized risponde 202 senza corpo',
                      response.status_code == 202 and not response.text.strip(),
                      '{} {!r}'.format(response.status_code, response.text[:80]))

        response = client.call('ping')
        checker.check('ping risponde 200', response.status_code == 200)

        response = client.call('tools/list')
        tools = (rpc_result(response) or {}).get('tools', [])
        names = sorted(tool.get('name') for tool in tools)
        checker.check('tools/list espone i due tool previsti',
                      names == ['add_movement', 'list_categories'], names)
        checker.check('ogni tool ha un inputSchema di tipo object',
                      all(tool.get('inputSchema', {}).get('type') == 'object' for tool in tools))

        response = client.call('metodo/inesistente')
        error = (response.json() or {}).get('error', {})
        checker.check('metodo sconosciuto -> -32601', error.get('code') == -32601, error)

        response = client.call(None, raw_body='non-json')
        error = (response.json() or {}).get('error', {})
        checker.check('corpo non JSON -> -32700', error.get('code') == -32700, error)

        response = requests.get(url, timeout=30)
        checker.check('GET /mcp -> 405 in JSON',
                      response.status_code == 405 and 'json' in response.headers.get('Content-Type', ''),
                      response.status_code)

        response = requests.delete(url, timeout=30)
        checker.check('DELETE /mcp -> 405', response.status_code == 405, response.status_code)

        # --- autenticazione ---
        checker.section('Autenticazione')

        # Nota: un 401 (o un header WWW-Authenticate) farebbe partire il flusso OAuth
        # lato client. Gli errori di autenticazione devono viaggiare come esito di tool.
        anonymous = McpClient(url)
        response = anonymous.call('tools/call', {'name': 'list_categories', 'arguments': {}})
        is_error, text, structured = tool_payload(response)
        checker.check('tools/call senza token -> 200 con isError',
                      response.status_code == 200 and is_error is True,
                      '{} {}'.format(response.status_code, text[:80]))
        checker.check('errore di auth marcato in structuredContent',
                      structured.get('auth_error') is True, structured)
        checker.check('nessun header WWW-Authenticate (non deve innescare OAuth)',
                      'WWW-Authenticate' not in response.headers, dict(response.headers))

        response = anonymous.call('tools/list')
        checker.check('tools/list resta accessibile senza token (sonda del connettore)',
                      response.status_code == 200, response.status_code)

        wrong = McpClient(url, 'segreto-inventato')
        response = wrong.call('tools/call', {'name': 'list_categories', 'arguments': {}})
        is_error, _, structured = tool_payload(response)
        checker.check('token errato -> 200 con isError',
                      response.status_code == 200 and is_error is True, response.status_code)
        checker.check('token errato non emette WWW-Authenticate',
                      'WWW-Authenticate' not in response.headers)

        # --- discovery OAuth: deve essere 404 JSON, mai HTML o redirect ---
        for path in ('/.well-known/oauth-protected-resource',
                     '/.well-known/oauth-protected-resource/mcp',
                     '/.well-known/oauth-authorization-server',
                     '/.well-known/oauth-authorization-server/mcp',
                     '/.well-known/openid-configuration'):
            probe = requests.get(base_url.rstrip('/') + path, timeout=30, allow_redirects=False)
            checker.check('{} -> 404 JSON'.format(path),
                          probe.status_code == 404
                          and 'json' in probe.headers.get('Content-Type', ''),
                          '{} {}'.format(probe.status_code, probe.headers.get('Content-Type')))

        for header in ('x-api-token', 'x-api-key', 'x-auth-token'):
            alt = McpClient(url, secret, header_mode=header)
            response = alt.call('tools/call', {'name': 'list_categories', 'arguments': {}})
            checker.check('fallback header {} accettato'.format(header),
                          response.status_code == 200, response.status_code)

        # --- list_categories ---
        checker.section('Tool list_categories')

        response = client.call('tools/call', {'name': 'list_categories', 'arguments': {}})
        is_error, text, structured = tool_payload(response)
        categories = structured.get('categories', [])
        wallets = structured.get('wallets', [])
        checker.check('list_categories non è in errore', is_error is False, text)
        checker.check('restituisce almeno una categoria', len(categories) > 0)
        checker.check('nessuna categoria di tipo transfer',
                      all(c.get('type') != 'transfer' for c in categories))
        checker.check('restituisce i wallet con un predefinito',
                      len(wallets) > 0 and wallets[0].get('is_default') is True)

        response = client.call('tools/call',
                               {'name': 'list_categories', 'arguments': {'kind': 'income'}})
        _, _, structured = tool_payload(response)
        checker.check('filtro kind=income restituisce solo entrate',
                      all(c.get('type') == 'income' for c in structured.get('categories', [])))

        expense_categories = [c['name'] for c in categories if c.get('type') == 'expense']
        if not expense_categories:
            print('  (nessuna categoria di spesa: i controlli su add_movement vengono saltati)')
            return checker.summary()

        category_name = expense_categories[0]

        # --- add_movement ---
        checker.section('Tool add_movement')

        unique_note = 'dev_mcp_check {}'.format(date.today().isoformat())

        response = client.call('tools/call', {
            'name': 'add_movement',
            'arguments': {
                'amount': 12.34,
                'category': category_name,
                'date': date.today().isoformat(),
                'note': unique_note
            }
        })
        is_error, text, structured = tool_payload(response)
        checker.check('movimento valido creato', is_error is False, text)
        checker.check('restituisce il movement_id', bool(structured.get('movement_id')), structured)
        if structured.get('movement_id'):
            created_movements.append(structured['movement_id'])

        response = client.call('tools/call', {
            'name': 'add_movement',
            'arguments': {'amount': 12.34, 'category': category_name, 'note': unique_note}
        })
        is_error, text, structured = tool_payload(response)
        checker.check('chiamata identica rifiutata come duplicato',
                      is_error is True and structured.get('duplicate') is True, text)

        response = client.call('tools/call', {
            'name': 'add_movement',
            'arguments': {'amount': 12.34, 'category': category_name,
                          'note': unique_note, 'force': True}
        })
        is_error, text, structured = tool_payload(response)
        checker.check('con force=true il duplicato viene registrato', is_error is False, text)
        if structured.get('movement_id'):
            created_movements.append(structured['movement_id'])

        response = client.call('tools/call', {
            'name': 'add_movement',
            'arguments': {'amount': 12.34, 'category': category_name,
                          'note': unique_note + ' variante'}
        })
        is_error, text, structured = tool_payload(response)
        checker.check('nota diversa -> non è un duplicato', is_error is False, text)
        if structured.get('movement_id'):
            created_movements.append(structured['movement_id'])

        response = client.call('tools/call', {
            'name': 'add_movement',
            'arguments': {'amount': 12.34, 'category': category_name,
                          'note': unique_note + ' variante',
                          'date': (date.today() - timedelta(days=1)).isoformat()}
        })
        is_error, text, structured = tool_payload(response)
        checker.check('stessa impronta con data diversa -> bloccato (la data non è nel fingerprint)',
                      is_error is True and structured.get('duplicate') is True, text)

        response = client.call('tools/call', {
            'name': 'add_movement',
            'arguments': {'amount': 7.77, 'category': category_name, 'note': unique_note + ' senza data'}
        })
        is_error, text, structured = tool_payload(response)
        checker.check('senza date usa la data odierna locale',
                      is_error is False and structured.get('move_date') == date.today().isoformat(),
                      structured.get('move_date'))
        if structured.get('movement_id'):
            created_movements.append(structured['movement_id'])

        # --- errori applicativi ---
        checker.section('Errori applicativi del tool')

        cases = [
            ('categoria inesistente',
             {'amount': 5, 'category': 'categoria-che-non-esiste-xyz'}),
            ('importo negativo', {'amount': -5, 'category': category_name}),
            ('importo zero', {'amount': 0, 'category': category_name}),
            ('importo non numerico', {'amount': 'tanti', 'category': category_name}),
            ('data malformata',
             {'amount': 5, 'category': category_name, 'date': '12/09/2026'}),
            ('wallet inesistente',
             {'amount': 5, 'category': category_name, 'wallet': 'wallet-che-non-esiste-xyz'}),
            ('kind non valido',
             {'amount': 5, 'category': category_name, 'kind': 'transfer'}),
        ]

        for description, arguments in cases:
            response = client.call('tools/call',
                                   {'name': 'add_movement', 'arguments': arguments})
            is_error, text, _ = tool_payload(response)
            checker.check('{} -> isError con messaggio'.format(description),
                          response.status_code == 200 and is_error is True and bool(text),
                          '{} {}'.format(response.status_code, text[:80]))

        response = client.call('tools/call', {'name': 'tool_inesistente', 'arguments': {}})
        error = (response.json() or {}).get('error', {})
        checker.check('tool sconosciuto -> -32602', error.get('code') == -32602, error)

        # --- token revocato ---
        checker.section('Revoca del token')

        revoke_token(token_hash)
        response = client.call('tools/call', {'name': 'list_categories', 'arguments': {}})
        is_error, _, structured = tool_payload(response)
        checker.check('token revocato -> 200 con isError',
                      response.status_code == 200 and is_error is True, response.status_code)
        checker.check('token revocato marcato come auth_error',
                      structured.get('auth_error') is True, structured)

        return checker.summary()

    finally:
        revoke_token(token_hash)
        if keep:
            if created_movements:
                print('\nMovimenti di prova lasciati nel DB: {}'.format(', '.join(created_movements)))
        else:
            delete_movements(created_movements)
            if created_movements:
                print('\n{} movimenti di prova cancellati.'.format(len(created_movements)))


def main():
    parser = argparse.ArgumentParser(description='Verifica locale del server MCP di PySpendless')
    parser.add_argument('--base-url', default='http://localhost:5000')
    parser.add_argument('--user-id', default=None)
    parser.add_argument('--keep', action='store_true',
                        help='non cancella i movimenti di prova creati')
    args = parser.parse_args()

    try:
        requests.get(args.base_url.rstrip('/') + '/version', timeout=10)
    except requests.RequestException:
        print("ERRORE: l'app non risponde su {}. Avviala con: python -m pyspendless.app".format(
            args.base_url))
        sys.exit(2)

    sys.exit(run(args.base_url, args.user_id, args.keep))


if __name__ == '__main__':
    main()
