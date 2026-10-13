"""Servidor MCP por stdio. Interface headless de pesquisa e paper na Solana.

stdout carrega só frames JSON-RPC. Log e erro de processo vão para stderr.
"""
import json
import sys
import uuid
from . import __version__
from .dispatch import execute
from .server import CONTRACT
from .transport import DataError

PROTOCOL = '2024-11-05'
ACCEPTED = {'2024-11-05', '2025-03-26', '2025-06-18'}
_KEY = {'idempotency_key': {'type': 'string', 'description': 'Reutilize a mesma chave ao repetir a mesma operação.'}}


def _tool(name, description, properties, required=()):
    schema = {'type': 'object', 'properties': {**properties, **_KEY}, 'additionalProperties': False}
    if required:
        schema['required'] = list(required)
    return {'name': name, 'description': description, 'inputSchema': schema}


def tools():
    optional = {}
    return [
        _tool('alladin_status', 'Carteira paper, posições, pendência e bloqueios. Não envia ordem.', {}),
        _tool('alladin_audit', 'Eventos recentes de decisão e execução.', {'limit': {'type': 'integer'}}),
        _tool('alladin_contract', 'Contrato de comandos do Alladin.', {}),
        _tool('paper_tick', 'Coleta candles, livro e trades públicos da Coinbase mais snapshot RPC somente leitura da Solana; aquece com OHLCV real e processa no máximo uma barra paper spot. Não acessa carteira nem envia transação.', {}),
        _tool('ingest', 'Barra fechada e snapshot. O conselho decide; a entrada paper sai na barra seguinte.', {'candle': {'type': 'object'}, 'snapshot': {'type': 'object'}}, ('candle', 'snapshot')),
        _tool('analyze', 'Analisa o que está gravado. Não agenda operação.', optional),
        _tool('evaluate', 'Valida risco de uma proposta. Não executa.', {'proposal': {'type': 'object'}}, ('proposal',)),
        _tool('halt', 'Bloqueia entradas e fecha na próxima barra válida.', optional),
        _tool('finalize', 'Encerra a pesquisa no último preço observado.', optional),
        _tool('universe', 'Mints e status do funil.', optional),
        _tool('admit', 'Classifica um snapshot. Não opera.', {'snapshot': {'type': 'object'}}, ('snapshot',)),
        _tool('watch', 'Move um mint elegível para vigiado ou negociável.', {'mint': {'type': 'string'}, 'arm': {'type': 'boolean'}}, ('mint',)),
        _tool('unwatch', 'Tira o mint do livro e cancela a ação pendente.', {'mint': {'type': 'string'}}, ('mint',)),
    ]


def read_message(stream):
    headers = {}
    while True:
        line = stream.readline()
        if line == b'':
            return None
        if line in (b'\r\n', b'\n'):
            break
        if b':' in line:
            name, value = line.decode('ascii', 'replace').split(':', 1)
            headers[name.strip().lower()] = value.strip()
    length = int(headers.get('content-length', '0'))
    if not 1 <= length <= 1_000_000:
        raise ValueError('Frame MCP inválido')
    return json.loads(stream.read(length))


def write_message(stream, payload):
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    stream.write(f'Content-Length: {len(raw)}\r\n\r\n'.encode('ascii') + raw)
    stream.flush()


def handle(service, message):
    if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or 'method' not in message:
        raise ValueError('JSON-RPC inválido')
    method = message['method']
    params = message.get('params') or {}
    if method == 'initialize':
        version = params.get('protocolVersion')
        return {
            'protocolVersion': version if version in ACCEPTED else PROTOCOL,
            'capabilities': {'tools': {'listChanged': False}, 'prompts': {'listChanged': False}},
            'serverInfo': {'name': 'alladin', 'version': __version__},
            'instructions': 'Alladin roda apenas Solana spot em paper. paper_tick coleta mercado atual, toma decisões com o motor configurado e registra apenas fills simulados. Nunca conecte carteira nem assine transação.',
        }
    if method == 'ping':
        return {}
    if method == 'tools/list':
        return {'tools': tools()}
    if method == 'tools/call':
        return _call(service, params)
    if method == 'prompts/list':
        return {'prompts': []}
    if method == 'prompts/get':
        raise ValueError('Prompt não encontrado')
    raise ValueError('Método MCP desconhecido')


def _call(service, params):
    name = params.get('name')
    arguments = params.get('arguments') or {}
    known = {tool['name'] for tool in tools()}
    if name not in known or not isinstance(arguments, dict):
        return _error('Ferramenta desconhecida')
    try:
        if name == 'alladin_status':
            result = service.status()
        elif name == 'alladin_audit':
            limit = arguments.get('limit', 20)
            if type(limit) is not int or not 1 <= limit <= 500:
                raise ValueError('limit: 1–500')
            result = {'events': service.store.audit(limit)}
        elif name == 'alladin_contract':
            result = CONTRACT
        else:
            args = dict(arguments)
            key = args.pop('idempotency_key', None) or 'mcp-' + uuid.uuid4().hex
            result = execute(service, name, args, key)
        return {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False, allow_nan=False)}], 'isError': False}
    except (ValueError, KeyError, TypeError, DataError) as exc:
        return _error(str(exc)[:300])


def _error(text):
    return {'content': [{'type': 'text', 'text': text}], 'isError': True}


def serve(service, stdin=None, stdout=None):
    incoming = stdin or sys.stdin.buffer
    outgoing = stdout or sys.stdout.buffer
    while True:
        try:
            message = read_message(incoming)
        except (ValueError, json.JSONDecodeError, UnicodeError):
            print('frame MCP recusado', file=sys.stderr)
            return 1
        if message is None:
            return 0
        if 'id' not in message:
            continue
        try:
            result = handle(service, message)
            write_message(outgoing, {'jsonrpc': '2.0', 'id': message['id'], 'result': result})
        except (ValueError, KeyError, TypeError) as exc:
            write_message(outgoing, {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32601, 'message': str(exc)[:200]}})
        except Exception:
            write_message(outgoing, {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32603, 'message': 'erro interno'}})
