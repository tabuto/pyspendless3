"""
Server MCP (Model Context Protocol) per PySpendless — task20-0

Espone un endpoint HTTP JSON-RPC 2.0 **stateless** (nessuna sessione, nessun SSE,
nessuna dipendenza ASGI/Starlette) montato dall'app Flask esistente sulla rotta `/mcp`.

Metodi supportati: initialize, notifications/initialized, tools/list, tools/call, ping.

Tool esposti:
  - add_movement    (scrittura) registra una spesa/entrata
  - list_categories (lettura)   elenca categorie e wallet dell'account

Autenticazione: token personale generato dal profilo utente, validato contro la
tabella `Token` esistente (type='MCP', segreto hashato SHA-256). Vedi
`TokenRepository.validate_mcp_secret`.

Il modulo non conosce Flask se non per l'oggetto `request` che riceve in ingresso:
tutta la logica è in funzioni pure testabili.
"""

import json
import logging
import unicodedata
import traceback
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Support both relative and absolute imports (stesso pattern di app.py)
try:
    from .conf import get_db_session
    from .repository import (
        UserRepository, CategoryRepository, WalletRepository,
        MovementRepository, TokenRepository
    )
except ImportError:
    from conf import get_db_session
    from repository import (
        UserRepository, CategoryRepository, WalletRepository,
        MovementRepository, TokenRepository
    )

logger = logging.getLogger(__name__)

# ===== COSTANTI DI PROTOCOLLO =====

SERVER_NAME = 'pyspendless'

# Versione dichiarata dal server. Se il client ne chiede una che conosciamo,
# facciamo eco alla sua; se ne chiede una sconosciuta rispondiamo con la nostra
# senza fallire (la negoziazione la chiude il client).
PROTOCOL_VERSION = '2025-06-18'
SUPPORTED_PROTOCOL_VERSIONS = ('2024-11-05', '2025-03-26', '2025-06-18')

# Codici di errore JSON-RPC 2.0
ERR_PARSE = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_INTERNAL = -32603

# Metodi che richiedono un token valido. `initialize`, `tools/list` e `ping` non
# toccano dati dell'utente e restano accessibili senza credenziali: serve a far
# passare la sonda che Claude esegue sulla URL quando si aggiunge il connettore.
# Tutto ciò che legge o scrive dati passa da `tools/call`, che è autenticato.
AUTH_REQUIRED_METHODS = ('tools/call',)

# Header accettati per il token (decisione D1).
# `Authorization: Bearer <segreto>` è la forma primaria; gli altri sono fallback
# con valore nudo, per adattarsi a quello che la UI dei connettori rende
# selezionabile senza dover toccare il server.
FALLBACK_TOKEN_HEADERS = ('x-api-token', 'x-api-key', 'x-auth-token')

# Fuso orario di riferimento per il default della data (decisione D5)
LOCAL_TIMEZONE = 'Europe/Rome'

# Limiti difensivi sui testi che rientrano nel contesto del modello
MAX_NOTE_LENGTH = 500
MAX_LISTED_ITEMS = 200

# Tipi di categoria gestibili dal tool: 'transfer' è escluso (decisione D6)
ALLOWED_CATEGORY_TYPES = ('expense', 'income')


# ===== HELPER GENERICI =====

def _normalize(value):
    """Normalizza un testo per i confronti: lowercase, senza accenti, spazi collassati."""
    if value is None:
        return ''
    text = str(value).strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return ' '.join(text.split())


def _local_today():
    """
    Data odierna nel fuso orario locale (decisione D5).

    Usata solo quando il client non valorizza il campo `date`: il server gira in UTC
    su PythonAnywhere, quindi una spesa registrata dopo le 23:00 italiane finirebbe
    sul giorno dopo.
    """
    try:
        from zoneinfo import ZoneInfo  # stdlib da Python 3.9
        return datetime.now(ZoneInfo(LOCAL_TIMEZONE)).date()
    except Exception:
        # Sistema senza database tzdata: ripiego su UTC. Peggiora solo il default
        # della data, non fa fallire l'inserimento.
        logger.warning("[MCP] zoneinfo non disponibile per %s, uso UTC", LOCAL_TIMEZONE)
        return datetime.utcnow().date()


def _parse_amount(raw):
    """
    Converte l'importo in Decimal a 2 decimali.

    Accetta numeri e stringhe (anche con virgola decimale, come le detta la voce).
    Ritorna (Decimal, None) oppure (None, messaggio_errore).
    """
    if raw is None or raw == '':
        return None, "Manca l'importo."

    if isinstance(raw, bool):
        return None, "L'importo non è un numero valido."

    try:
        if isinstance(raw, str):
            cleaned = raw.strip().replace('€', '').replace(' ', '').replace(',', '.')
            amount = Decimal(cleaned)
        else:
            amount = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None, "L'importo non è un numero valido."

    amount = amount.quantize(Decimal('0.01'))

    if amount <= 0:
        return None, "L'importo deve essere maggiore di zero."

    return amount, None


def _parse_date(raw):
    """Converte la data da 'YYYY-MM-DD'. Ritorna (date, None) oppure (None, errore)."""
    if raw is None or raw == '':
        return _local_today(), None

    try:
        return datetime.strptime(str(raw).strip(), '%Y-%m-%d').date(), None
    except (ValueError, TypeError):
        return None, "La data non è nel formato corretto (atteso YYYY-MM-DD)."


def _format_amount(amount):
    """Formatta un importo all'italiana: 1234.5 -> '1.234,50'."""
    try:
        return '{:,.2f}'.format(Decimal(amount)).replace(',', '@').replace('.', ',').replace('@', '.')
    except (InvalidOperation, ValueError, TypeError):
        return str(amount)


# ===== AUTENTICAZIONE =====

def extract_token(headers):
    """
    Estrae il segreto dagli header (decisione D1).

    Ordine: `Authorization: Bearer <segreto>` (schema case-insensitive), poi i
    fallback con valore nudo. Nessun token viene mai letto dalla query string.
    """
    authorization = headers.get('Authorization')
    if authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == 'bearer' and parts[1].strip():
            return parts[1].strip()

    for header_name in FALLBACK_TOKEN_HEADERS:
        value = headers.get(header_name)
        if value and value.strip():
            return value.strip()

    return None


def authenticate(db, secret):
    """
    Valida il segreto e ritorna il contesto della chiamata.

    Returns:
        dict {'user_id', 'account_id', 'label', 'prefix'} se valido, altrimenti None
    """
    if not secret:
        return None

    token_repo = TokenRepository(db)
    token = token_repo.validate_mcp_secret(secret)

    if not token:
        return None

    try:
        payload = json.loads(token.payload)
    except (json.JSONDecodeError, TypeError):
        logger.error("[MCP] payload del token non deserializzabile (hash %s...)", str(token.uuid)[:8])
        return None

    user_id = payload.get('user_id')
    account_id = payload.get('account_id')

    if user_id is None or account_id is None:
        return None

    return {
        'user_id': user_id,
        'account_id': account_id,
        'label': payload.get('label'),
        'prefix': payload.get('prefix', '')
    }


# ===== DEFINIZIONE DEI TOOL =====

TOOL_DEFINITIONS = [
    {
        'name': 'add_movement',
        'title': 'Registra un movimento',
        'description': (
            "Registra una spesa o un'entrata nel bilancio familiare PySpendless. "
            "Gli importi sono in euro e vanno sempre passati positivi: è il campo 'kind' a "
            "distinguere spesa da entrata. La categoria va indicata per nome e deve essere una "
            "di quelle dell'account: se non sei sicuro, chiama prima list_categories. "
            "Valorizza sempre 'date' con la data locale dell'utente in formato YYYY-MM-DD "
            "(se la ometti il server assume oggi, ora italiana). "
            "Se il movimento risulta identico all'ultimo registrato viene rifiutato: in quel caso "
            "chiedi conferma all'utente e richiama il tool con force=true."
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'amount': {
                    'type': 'number',
                    'exclusiveMinimum': 0,
                    'description': "Importo in euro, sempre positivo (es. 23.50)."
                },
                'kind': {
                    'type': 'string',
                    'enum': list(ALLOWED_CATEGORY_TYPES),
                    'default': 'expense',
                    'description': "'expense' per una spesa, 'income' per un'entrata."
                },
                'category': {
                    'type': 'string',
                    'description': "Nome della categoria (es. 'Supermercato')."
                },
                'wallet': {
                    'type': 'string',
                    'description': "Nome o codice del wallet. Se omesso si usa il wallet predefinito."
                },
                'date': {
                    'type': 'string',
                    'pattern': r'^\d{4}-\d{2}-\d{2}$',
                    'description': "Data del movimento in formato YYYY-MM-DD."
                },
                'note': {
                    'type': 'string',
                    'description': "Nota descrittiva libera (es. la frase detta dall'utente)."
                },
                'force': {
                    'type': 'boolean',
                    'default': False,
                    'description': "Se true, registra il movimento anche se sembra un duplicato."
                }
            },
            'required': ['amount', 'category'],
            'additionalProperties': False
        },
        'annotations': {
            'title': 'Registra un movimento',
            'readOnlyHint': False,
            'destructiveHint': False,
            'idempotentHint': False,
            'openWorldHint': False
        }
    },
    {
        'name': 'list_categories',
        'title': 'Elenca categorie e wallet',
        'description': (
            "Elenca le categorie di spesa/entrata e i wallet disponibili nell'account "
            "PySpendless dell'utente. Usalo prima di add_movement quando non conosci i nomi "
            "esatti delle categorie."
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'kind': {
                    'type': 'string',
                    'enum': list(ALLOWED_CATEGORY_TYPES),
                    'description': "Filtra le categorie per tipo. Se omesso le restituisce tutte."
                }
            },
            'additionalProperties': False
        },
        'annotations': {
            'title': 'Elenca categorie e wallet',
            'readOnlyHint': True,
            'destructiveHint': False,
            'idempotentHint': True,
            'openWorldHint': False
        }
    }
]


# ===== RISOLUZIONE DI CATEGORIE, WALLET E DUPLICATI =====

def _usable_categories(db, account_id, kind=None):
    """Categorie dell'account utilizzabili dal tool: 'transfer' sempre esclusa (D6)."""
    categories = CategoryRepository(db).get_categories_for_account(account_id)
    usable = [c for c in categories if c.type in ALLOWED_CATEGORY_TYPES]

    if kind:
        usable = [c for c in usable if c.type == kind]

    return usable


def resolve_category(categories, requested):
    """
    Risolve il nome di una categoria fra quelle disponibili.

    Ordine: match esatto case-insensitive, poi normalizzato (accenti/spazi),
    poi sottostringa **solo se unica**.

    Returns:
        (Category, None) | (None, 'not_found') | (None, 'ambiguous')
    """
    if not requested:
        return None, 'not_found'

    wanted = _normalize(requested)

    for category in categories:
        if str(category.name).strip().lower() == str(requested).strip().lower():
            return category, None

    for category in categories:
        if _normalize(category.name) == wanted:
            return category, None

    partial = [c for c in categories if wanted and wanted in _normalize(c.name)]
    if len(partial) == 1:
        return partial[0], None
    if len(partial) > 1:
        return None, 'ambiguous'

    return None, 'not_found'


def resolve_wallet(wallets, requested):
    """
    Risolve il wallet per nome o codice. Se `requested` è vuoto ritorna il primo
    wallet dell'account (ordinato per order_index), cioè il predefinito.

    Returns:
        (Wallet, None) | (None, 'not_found') | (None, 'no_wallet')
    """
    if not wallets:
        return None, 'no_wallet'

    if not requested:
        return wallets[0], None

    wanted = _normalize(requested)

    for wallet in wallets:
        if _normalize(wallet.name) == wanted or _normalize(wallet.code) == wanted:
            return wallet, None

    partial = [w for w in wallets if wanted and wanted in _normalize(w.name)]
    if len(partial) == 1:
        return partial[0], None

    return None, 'not_found'


def movement_fingerprint(amount, kind, category_id, note):
    """
    Impronta di un movimento per la verifica anti-duplicazione (decisione D7).

    Composta da importo (con segno determinato dal tipo), categoria e descrizione
    normalizzata. La data **non** entra nell'impronta: due movimenti identici in
    giorni diversi sono considerati duplicati.
    """
    signed_amount = Decimal(amount).quantize(Decimal('0.01'))
    if kind == 'expense':
        signed_amount = -signed_amount

    raw = '{}|{}|{}'.format(signed_amount, category_id, _normalize(note))
    return TokenRepository.hash_secret(raw)


def _movement_row_fingerprint(movement):
    """Ricalcola l'impronta su un record Movement già a DB."""
    if movement is None:
        return None

    if movement.expense is not None:
        kind = 'expense'
        amount = movement.expense
    elif movement.income is not None:
        kind = 'income'
        amount = movement.income
    else:
        return None

    if movement.category_id is None:
        # Movimento legacy senza FK: non confrontabile in modo affidabile
        return None

    try:
        return movement_fingerprint(amount, kind, movement.category_id, movement.note)
    except (InvalidOperation, ValueError, TypeError):
        return None


# ===== IMPLEMENTAZIONE DEI TOOL =====

def _tool_list_categories(db, ctx, args):
    """Tool di sola lettura: categorie e wallet dell'account."""
    account_id = ctx['account_id']
    kind = args.get('kind')

    if kind and kind not in ALLOWED_CATEGORY_TYPES:
        return _tool_error(
            "Il tipo '{}' non è valido: usa 'expense' o 'income'.".format(kind)
        )

    categories = _usable_categories(db, account_id, kind)[:MAX_LISTED_ITEMS]
    wallets = WalletRepository(db).get_wallets_for_account(account_id)[:MAX_LISTED_ITEMS]

    expenses = [c.name for c in categories if c.type == 'expense']
    incomes = [c.name for c in categories if c.type == 'income']

    lines = []
    if expenses:
        lines.append('Categorie di spesa: ' + ', '.join(expenses))
    if incomes:
        lines.append('Categorie di entrata: ' + ', '.join(incomes))
    if not expenses and not incomes:
        lines.append('Nessuna categoria disponibile.')

    if wallets:
        lines.append('Wallet: ' + ', '.join(
            '{} ({}){}'.format(w.name, w.code, ' — predefinito' if i == 0 else '')
            for i, w in enumerate(wallets)
        ))

    structured = {
        'categories': [{'name': c.name, 'type': c.type} for c in categories],
        'wallets': [
            {
                'name': w.name,
                'code': w.code,
                'currency': w.currency,
                'is_default': (i == 0)
            }
            for i, w in enumerate(wallets)
        ]
    }

    return _tool_result('\n'.join(lines), structured)


def _tool_add_movement(db, ctx, args):
    """Tool di scrittura: registra una spesa o un'entrata."""
    account_id = ctx['account_id']
    user_id = ctx['user_id']

    # --- validazione argomenti ---
    kind = args.get('kind') or 'expense'
    if kind not in ALLOWED_CATEGORY_TYPES:
        return _tool_error("Il tipo '{}' non è valido: usa 'expense' o 'income'.".format(kind))

    amount, error = _parse_amount(args.get('amount'))
    if error:
        return _tool_error(error)

    move_date, error = _parse_date(args.get('date'))
    if error:
        return _tool_error(error)

    note = args.get('note') or ''
    if not isinstance(note, str):
        note = str(note)
    note = note.strip()[:MAX_NOTE_LENGTH]

    force = bool(args.get('force'))

    # --- risoluzione categoria ---
    categories = _usable_categories(db, account_id, kind)
    if not categories:
        return _tool_error(
            "Non ci sono categorie di tipo '{}' configurate in questo account.".format(kind)
        )

    category, category_error = resolve_category(categories, args.get('category'))
    if category_error:
        available = ', '.join(c.name for c in categories[:MAX_LISTED_ITEMS])
        if category_error == 'ambiguous':
            message = "La categoria '{}' corrisponde a più categorie. Quelle disponibili sono: {}.".format(
                args.get('category'), available
            )
        else:
            message = "Non ho trovato la categoria '{}'. Quelle disponibili sono: {}.".format(
                args.get('category'), available
            )
        return _tool_error(message, {'categories': [c.name for c in categories]})

    # --- risoluzione wallet ---
    wallets = WalletRepository(db).get_wallets_for_account(account_id)
    wallet, wallet_error = resolve_wallet(wallets, args.get('wallet'))
    if wallet_error == 'no_wallet':
        return _tool_error("Questo account non ha nessun wallet configurato.")
    if wallet_error:
        available = ', '.join(w.name for w in wallets[:MAX_LISTED_ITEMS])
        return _tool_error(
            "Non ho trovato il wallet '{}'. Quelli disponibili sono: {}.".format(
                args.get('wallet'), available
            ),
            {'wallets': [w.name for w in wallets]}
        )

    # --- coerenza multi-tenant (stesso controllo di POST /api/movements) ---
    if category.account_id != account_id or wallet.account_id != account_id:
        logger.error(
            "[MCP] tentativo di scrittura cross-account: account=%s category=%s wallet=%s",
            account_id, category.id, wallet.id
        )
        return _tool_error("Categoria o wallet non appartengono a questo account.")

    # --- utente (campo legacy 'user' = email) ---
    user_repo = UserRepository(db)
    lookup_id = int(user_id) if str(user_id).isdigit() else user_id
    user = user_repo.get_user_by_id(lookup_id)
    if not user:
        logger.error("[MCP] utente %s non trovato per il token in uso", user_id)
        return _tool_error("Utente non trovato: il token potrebbe non essere più valido.")

    movement_repo = MovementRepository(db)

    # --- anti-duplicazione (decisione D7) ---
    fingerprint = movement_fingerprint(amount, kind, category.id, note)

    if not force:
        last = movement_repo.get_last_inserted_for_user(user_id, account_id)
        if last is not None and _movement_row_fingerprint(last) == fingerprint:
            logger.info(
                "[MCP] duplicato rifiutato (account=%s categoria=%s importo=%s)",
                account_id, category.name, amount
            )
            return _tool_error(
                "Non ho registrato nulla: sembra identico all'ultimo movimento inserito "
                "({} € — {} — \"{}\", del {}). Se è davvero un nuovo movimento, "
                "richiamami con force=true.".format(
                    _format_amount(last.expense if last.expense is not None else last.income),
                    last.category,
                    last.note or '',
                    last.move_date.strftime('%d/%m/%Y') if last.move_date else ''
                ),
                {
                    'duplicate': True,
                    'existing_movement_id': last.id,
                    'existing': {
                        'move_date': last.move_date.isoformat() if last.move_date else None,
                        'category': last.category,
                        'wallet': last.wallet,
                        'note': last.note,
                        'expense': float(last.expense) if last.expense is not None else None,
                        'income': float(last.income) if last.income is not None else None
                    }
                }
            )

    # --- creazione (stessa forma di POST /api/movements, app.py) ---
    movement_data = {
        'id': str(uuid.uuid4()),
        'move_date': move_date,
        'move_year': move_date.year,
        'move_month': move_date.month,
        'category': category.name,   # campo legacy
        'wallet': wallet.code,       # campo legacy
        'income': float(amount) if kind == 'income' else None,
        'expense': float(amount) if kind == 'expense' else None,
        'note': note,
        'user': user.email,          # campo legacy
        'account_id': account_id,
        'user_id': user_id,
        'category_id': category.id,
        'wallet_id': wallet.id
    }

    movement = movement_repo.create_movement(movement_data)

    verbo = 'Registrata spesa' if kind == 'expense' else 'Registrata entrata'
    text = '{} di {} € — {} / {} — {}'.format(
        verbo,
        _format_amount(amount),
        category.name,
        wallet.name,
        move_date.strftime('%d/%m/%Y')
    )
    if note:
        text += ' — "{}"'.format(note)

    logger.info(
        "[MCP] movimento creato id=%s account=%s categoria=%s importo=%s",
        movement.id, account_id, category.name, amount
    )

    return _tool_result(text, {
        'movement_id': movement.id,
        'move_date': move_date.isoformat(),
        'kind': kind,
        'amount': float(amount),
        'category': category.name,
        'wallet': wallet.name,
        'wallet_code': wallet.code,
        'currency': wallet.currency,
        'note': note,
        'duplicate': False
    })


TOOL_HANDLERS = {
    'add_movement': _tool_add_movement,
    'list_categories': _tool_list_categories,
}


# ===== COSTRUZIONE DELLE RISPOSTE =====

def _tool_result(text, structured=None):
    """Risultato di tool riuscito."""
    result = {
        'content': [{'type': 'text', 'text': text}],
        'isError': False
    }
    if structured is not None:
        result['structuredContent'] = structured
    return result


def _tool_error(text, structured=None):
    """
    Errore *applicativo* del tool: è una risposta JSON-RPC di successo con
    isError=True, così il modello può spiegarlo all'utente e riprovare.
    Da non confondere con gli errori di protocollo (_error_response).
    """
    result = {
        'content': [{'type': 'text', 'text': text}],
        'isError': True
    }
    if structured is not None:
        result['structuredContent'] = structured
    return result


def _success_response(request_id, result):
    return {'jsonrpc': '2.0', 'id': request_id, 'result': result}


def _error_response(request_id, code, message, data=None):
    error = {'code': code, 'message': message}
    if data is not None:
        error['data'] = data
    return {'jsonrpc': '2.0', 'id': request_id, 'error': error}


# ===== DISPATCH JSON-RPC =====

def _handle_initialize(params, app_version):
    requested = params.get('protocolVersion')
    version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION

    return {
        'protocolVersion': version,
        'capabilities': {'tools': {'listChanged': False}},
        'serverInfo': {'name': SERVER_NAME, 'version': app_version},
        'instructions': (
            "Server di PySpendless per registrare le spese familiari. "
            "Usa list_categories per conoscere categorie e wallet, add_movement per registrare "
            "una spesa o un'entrata."
        )
    }


def _handle_tools_call(params, secret, app_version):
    """Esegue un tool. È l'unico metodo che richiede autenticazione e tocca il DB."""
    name = params.get('name')
    arguments = params.get('arguments') or {}

    if not isinstance(arguments, dict):
        return None, _invalid_params("Il campo 'arguments' deve essere un oggetto.")

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return None, _invalid_params("Tool sconosciuto: '{}'.".format(name))

    db = get_db_session()
    try:
        ctx = authenticate(db, secret)
        if ctx is None:
            return None, 'unauthorized'

        started = datetime.utcnow()
        result = handler(db, ctx, arguments)
        elapsed_ms = int((datetime.utcnow() - started).total_seconds() * 1000)

        logger.info(
            "[MCP] tool=%s account=%s token=%s esito=%s durata=%sms",
            name, ctx['account_id'], ctx.get('prefix', ''),
            'errore' if result.get('isError') else 'ok', elapsed_ms
        )
        return result, None
    finally:
        db.close()


def _invalid_params(message):
    return ('invalid_params', message)


def _dispatch(message, secret, app_version):
    """
    Esegue un singolo messaggio JSON-RPC.

    Returns:
        (risposta_dict | None, stato_speciale | None)
        `None` come risposta significa notifica (nessun corpo da restituire).
        Lo stato speciale 'unauthorized' fa rispondere 401 al livello HTTP.
    """
    if not isinstance(message, dict):
        return _error_response(None, ERR_INVALID_REQUEST, 'Messaggio JSON-RPC non valido.'), None

    method = message.get('method')
    request_id = message.get('id')
    params = message.get('params') or {}

    if not isinstance(params, dict):
        return _error_response(request_id, ERR_INVALID_PARAMS,
                               "Il campo 'params' deve essere un oggetto."), None

    if not method or not isinstance(method, str):
        return _error_response(request_id, ERR_INVALID_REQUEST,
                               'Campo "method" mancante o non valido.'), None

    # Notifiche: nessun 'id' -> nessuna risposta
    is_notification = 'id' not in message

    if method in AUTH_REQUIRED_METHODS and not secret:
        return None, 'unauthorized'

    try:
        if method == 'initialize':
            result = _handle_initialize(params, app_version)
            return (None, None) if is_notification else (_success_response(request_id, result), None)

        if method == 'ping':
            return (None, None) if is_notification else (_success_response(request_id, {}), None)

        if method.startswith('notifications/'):
            # initialized, cancelled, ecc.: si accettano e si ignorano
            return None, None

        if method == 'tools/list':
            result = {'tools': TOOL_DEFINITIONS}
            return (None, None) if is_notification else (_success_response(request_id, result), None)

        if method == 'tools/call':
            result, special = _handle_tools_call(params, secret, app_version)

            if special == 'unauthorized':
                return None, 'unauthorized'

            if isinstance(special, tuple) and special[0] == 'invalid_params':
                return _error_response(request_id, ERR_INVALID_PARAMS, special[1]), None

            return (None, None) if is_notification else (_success_response(request_id, result), None)

        return _error_response(request_id, ERR_METHOD_NOT_FOUND,
                               "Metodo non supportato: '{}'.".format(method)), None

    except Exception as exc:  # noqa: BLE001 - vogliamo che nulla sfugga verso il client
        logger.error("[MCP] errore non gestito nel metodo %s: %s", method, exc)
        logger.debug(traceback.format_exc())
        if is_notification:
            return None, None
        return _error_response(request_id, ERR_INTERNAL, 'Errore interno del server.'), None


# ===== ENTRY POINT HTTP =====

def handle_http_request(flask_request, app_version):
    """
    Punto d'ingresso chiamato dalla rotta Flask `/mcp`.

    Returns:
        (body, status_code) — `body` è None quando non c'è corpo da restituire (202).
    """
    secret = extract_token(flask_request.headers)

    raw = flask_request.get_data(as_text=True) or ''

    try:
        message = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning('[MCP] corpo della richiesta non deserializzabile')
        return _error_response(None, ERR_PARSE, 'Corpo della richiesta non è JSON valido.'), 400

    # Batch JSON-RPC (rimosso dalle revisioni recenti della spec, gestito per tolleranza)
    if isinstance(message, list):
        if not message:
            return _error_response(None, ERR_INVALID_REQUEST, 'Batch vuoto.'), 400

        responses = []
        for item in message:
            response, special = _dispatch(item, secret, app_version)
            if special == 'unauthorized':
                return _unauthorized_body(), 401
            if response is not None:
                responses.append(response)

        if not responses:
            return None, 202
        return responses, 200

    response, special = _dispatch(message, secret, app_version)

    if special == 'unauthorized':
        logger.warning('[MCP] richiesta non autorizzata (token assente o non valido)')
        return _unauthorized_body(), 401

    if response is None:
        return None, 202

    return response, 200


def _unauthorized_body():
    return _error_response(
        None, ERR_INVALID_REQUEST,
        'Token mancante o non valido. Configura il token personale generato dal profilo '
        'PySpendless nell\'header Authorization: Bearer <token>.'
    )


def method_not_allowed_body():
    """Corpo JSON per GET/DELETE su /mcp (il server è stateless: niente stream, niente sessioni)."""
    return _error_response(
        None, ERR_INVALID_REQUEST,
        'Questo endpoint MCP accetta solo richieste POST (trasporto HTTP stateless).'
    )


def maintenance_body():
    """Corpo JSON restituito quando l'app è in modalità manutenzione."""
    return _error_response(
        None, ERR_INTERNAL,
        'PySpendless è temporaneamente in manutenzione: riprova più tardi.'
    )
