"""Pedido de conexão da conta Coinbase para o chat. O token não volta ao modelo.

O link oficial é login.coinbase.com/oauth2/auth. O cliente OAuth e o redirect
ficam no ambiente do processo. O segredo do cliente só entra na troca do code,
no servidor local, e a resposta ao navegador não inclui o token.
"""
import base64
import hashlib
import os
import secrets
import threading
import time
from urllib.parse import urlencode, urlsplit
from .transport import DataError

AUTHORIZE = 'https://login.coinbase.com/oauth2/auth'
TOKEN = 'https://login.coinbase.com/oauth2/token'
READ_SCOPES = (
    'wallet:user:read',
    'wallet:accounts:read',
    'wallet:trades:read',
    'wallet:transactions:read',
)
TRADE_SCOPE = 'wallet:trades:create'
_LOCK = threading.Lock()
_PENDING = {}
_SESSION = {'connected': False, 'scopes': []}
_PENDING_TTL_SECONDS = 3600


def _prune_pending(now=None):
    cutoff = (now or time.time()) - _PENDING_TTL_SECONDS
    for state in [s for s, p in _PENDING.items() if p.get('created', 0) < cutoff]:
        _PENDING.pop(state, None)


def _redirect_ok(value):
    parsed = urlsplit(value)
    host = (parsed.hostname or '').lower()
    local = parsed.scheme == 'http' and host in {'127.0.0.1', 'localhost'}
    public = parsed.scheme == 'https' and host not in {'', 'localhost'}
    return (local or public) and not parsed.username and not parsed.password and parsed.path


def connect_request(scopes=None, trade=False):
    if trade is not False and trade is not True:
        raise ValueError('trade deve ser booleano')
    client_id = os.environ.get('COINBASE_OAUTH_CLIENT_ID', '')
    redirect = os.environ.get('COINBASE_OAUTH_REDIRECT_URI', '')
    if not client_id or not redirect:
        raise DataError('Defina COINBASE_OAUTH_CLIENT_ID e COINBASE_OAUTH_REDIRECT_URI no processo, fora do chat')
    if not 8 <= len(client_id) <= 128 or not client_id.isalnum():
        raise ValueError('Client id OAuth inválido')
    if not _redirect_ok(redirect):
        raise ValueError('Redirect OAuth deve ser https ou http local, com caminho')
    selected = list(READ_SCOPES if scopes is None else scopes)
    if not isinstance(selected, list) or not selected:
        raise ValueError('Escopos OAuth inválidos')
    allowed = set(READ_SCOPES)
    if trade:
        if os.environ.get('COINBASE_OAUTH_ALLOW_TRADE') != '1':
            raise ValueError('Escopo de ordem exige COINBASE_OAUTH_ALLOW_TRADE=1 no processo')
        allowed.add(TRADE_SCOPE)
        selected.append(TRADE_SCOPE)
    if any(scope not in allowed for scope in selected):
        raise ValueError('Escopo OAuth fora da lista')
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    query = urlencode({
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect,
        'state': state,
        'scope': ','.join(dict.fromkeys(selected)),
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    })
    with _LOCK:
        _prune_pending()
        _PENDING[state] = {'verifier': verifier, 'redirect': redirect, 'scopes': list(dict.fromkeys(selected)),
                           'created': time.time()}
    return {
        'type': 'action_request',
        'action': 'open_url',
        'title': 'Conectar conta Coinbase',
        'label': 'Connect account',
        'url': f'{AUTHORIZE}?{query}',
        'state': state,
        'executed': False,
        'scopes': list(dict.fromkeys(selected)),
        'platforms': {
            'cursor': 'Exiba o link Connect account como pedido de ação. Abra só depois que a pessoa aceitar.',
            'chatgpt': 'Mostre o URL como link. O sandbox não chama essa URL.',
            'chatgpt_work': 'Mesma ferramenta. O link é a autorização da pessoa.',
            'claude': 'Mostre o URL. O computer use não abre /oauth2/token.',
            'claude_work': 'Registre alladin_command e exiba este action_request.',
            'sandbox': 'Imprima o URL para a pessoa. A troca do code fica no servidor local.',
        },
    }


def reset_session():
    with _LOCK:
        _PENDING.clear()
        _SESSION.clear()
        _SESSION.update(connected=False, scopes=[])


def connection_status():
    with _LOCK:
        return {'connected': _SESSION['connected'], 'scopes': list(_SESSION['scopes']), 'executed': False}


def bearer():
    with _LOCK:
        return _SESSION.get('token')


def complete(code, state, http):
    if not isinstance(code, str) or not isinstance(state, str) or not code or not state:
        raise ValueError('Callback OAuth incompleto')
    if any(word in code.lower() for word in ('secret', 'private_key')):
        raise ValueError('Callback OAuth recusado')
    secret = os.environ.get('COINBASE_OAUTH_CLIENT_SECRET', '')
    client_id = os.environ.get('COINBASE_OAUTH_CLIENT_ID', '')
    if not secret or not client_id:
        raise DataError('Troca OAuth sem client secret no processo')
    with _LOCK:
        _prune_pending()
        pending = _PENDING.pop(state, None)
    if pending is None:
        raise ValueError('State OAuth desconhecido')
    payload = http.form(TOKEN, {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': secret,
        'redirect_uri': pending['redirect'],
        'code_verifier': pending['verifier'],
    }, retry=False)
    token = payload.get('access_token') if isinstance(payload, dict) else None
    if not isinstance(token, str) or len(token) < 8:
        raise DataError('Coinbase não devolveu access token utilizável')
    with _LOCK:
        _SESSION.clear()
        _SESSION.update(connected=True, scopes=pending['scopes'], token=token)
    return {'connected': True, 'scopes': pending['scopes']}
