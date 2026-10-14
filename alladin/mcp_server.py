"""MCP stdio server for headless SOL research and paper execution.

stdout carries JSON-RPC frames only. Process logs and errors use stderr.
"""
import json
import sys
import uuid
from . import __version__
from .dispatch import execute
from .server import CONTRACT
from .transport import DataError
from .prompts import PromptLibrary

PROTOCOL = '2024-11-05'
ACCEPTED = {'2024-11-05', '2025-03-26', '2025-06-18'}
_KEY = {'idempotency_key': {'type': 'string', 'description': 'Reuse the same key when retrying the identical operation.'}}


def _tool(name, description, properties, required=()):
    schema = {'type': 'object', 'properties': {**properties, **_KEY}, 'additionalProperties': False}
    if required:
        schema['required'] = list(required)
    return {'name': name, 'description': description, 'inputSchema': schema}


def tools():
    optional = {}
    return [
        _tool('catalog', 'Discover all public Coinbase product types without a SOL allowlist. Visibility is not execution support or account eligibility.', {'refresh':{'type':'boolean'}}),
        _tool('instrument', 'Read product-specific metadata and implemented capabilities.', {'product_id':{'type':'string'}}, ('product_id',)),
        _tool('instrument_book', 'Read a public Coinbase product book for research; does not authorize execution.', {'product_id':{'type':'string'}}, ('product_id',)),
        _tool('alladin_status', 'Read paper account, positions, pending activity and safety blocks. Does not send orders.', {}),
        _tool('alladin_diagnostics', 'Check current Coinbase access and failure phase without account mutation.', {}),
        _tool('alladin_performance', 'Observed net trade statistics, uncertainty and the descriptive 900-trade target; no profit guarantee.', {}),
        _tool('alladin_audit', 'Recent decision and execution events.', {'limit': {'type': 'integer'}}),
        _tool('alladin_contract', 'Alladin command contract.', {}),
        _tool('paper_tick', 'Collect public Coinbase SOL-USDC candles, book and trades; warm up and process at most one forward spot paper bar. No wallet access or transaction submission.', {}),
        _tool('ingest', 'Ingest a closed replay bar and snapshot; eligible paper entry occurs on the next bar.', {'candle': {'type': 'object'}, 'snapshot': {'type': 'object'}}, ('candle', 'snapshot')),
        _tool('execution_check', 'Explicit controlled paper OPEN/CLOSE with Coinbase quotes and normal risk; not autonomous strategy evaluation.', {'action':{'type':'string','enum':['OPEN','CLOSE']},'check_id':{'type':'string'},'purpose':{'type':'string','enum':['execution_validation']},'proposal':{'type':'object'}}, ('action','check_id','purpose')),
        _tool('prepare_decision', 'Prepare or reuse frozen evidence and prompts for the external session; no inference.', {}),
        _tool('submit_decision', 'Validate external reports and plan; execution is paper only.', {k:{'type':'object' if k in {'reports','decision'} else 'string'} for k in ['task_id','evidence_sha256','reports','decision','session_id']}, ('task_id','evidence_sha256','reports','decision','session_id')),
        _tool('analyze', 'Analyze stored context without scheduling a trade.', optional),
        _tool('evaluate', 'Evaluate proposal risk without execution.', {'proposal': {'type': 'object'}}, ('proposal',)),
        _tool('halt', 'Latch an entry halt; flattening requires subsequent valid processing.', optional),
        _tool('finalize', 'Settle research at the last stored observed mark.', optional),
        _tool('universe', 'Research mint funnel and status.', optional),
        _tool('admit', 'Classify a research snapshot without trading.', {'snapshot': {'type': 'object'}}, ('snapshot',)),
        _tool('watch', 'Move an eligible research mint to watched or negotiable.', {'mint': {'type': 'string'}, 'arm': {'type': 'boolean'}}, ('mint',)),
        _tool('unwatch', 'Remove a watched mint and cancel its pending action.', {'mint': {'type': 'string'}}, ('mint',)),
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
        raise ValueError('Invalid MCP frame')
    return json.loads(stream.read(length))


def write_message(stream, payload):
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    stream.write(f'Content-Length: {len(raw)}\r\n\r\n'.encode('ascii') + raw)
    stream.flush()


def handle(service, message):
    if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or 'method' not in message:
        raise ValueError('Invalid JSON-RPC')
    method = message['method']
    params = message.get('params') or {}
    if method == 'initialize':
        version = params.get('protocolVersion')
        return {
            'protocolVersion': version if version in ACCEPTED else PROTOCOL,
            'capabilities': {'tools': {'listChanged': False}, 'prompts': {'listChanged': False}},
            'serverInfo': {'name': 'alladin', 'version': __version__},
            'instructions': 'Alladin discovers the full public Coinbase product catalog through catalog, instrument and instrument_book. Check alladin_capabilities before proposing execution. The legacy paper executor remains SOL-USDC spot; other execution adapters are not implemented. All fills are simulated. External sessions supply reasoning; never connect a wallet or sign transactions.',
        }
    if method == 'ping':
        return {}
    if method == 'tools/list':
        return {'tools': tools()}
    if method == 'tools/call':
        return _call(service, params)
    if method == 'prompts/list':
        return {'prompts':[{'name':'alladin_'+role,'description':'Reviewed Solana spot paper finance role: '+role,
                 'arguments':[{'name':'regime','description':'Optional trend, range or shock context','required':False}]}
                 for role in sorted(PromptLibrary.ROLES)]}
    if method == 'prompts/get':
        name=params.get('name','')
        role=name.removeprefix('alladin_') if isinstance(name,str) else ''
        if name!='alladin_'+role or role not in PromptLibrary.ROLES:
            raise ValueError('Prompt not found')
        arguments=params.get('arguments') or {}
        regime=arguments.get('regime')
        if regime not in (None,'trend','range','shock'):
            raise ValueError('Unknown regime')
        return {'description':'Alladin Finance Prompt '+role,
                'messages':[{'role':'user','content':{'type':'text','text':PromptLibrary().render(role,regime)}}]}
    raise ValueError('Unknown MCP method')


def _call(service, params):
    name = params.get('name')
    arguments = params.get('arguments') or {}
    known = {tool['name'] for tool in tools()}
    if name not in known or not isinstance(arguments, dict):
        return _error('Unknown tool')
    try:
        if name == 'alladin_status':
            result = service.status()
        elif name == 'alladin_diagnostics':
            result=service.diagnostics()
        elif name == 'alladin_performance':
            result = service.performance()
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
    except DataError as exc:
        return _error(json.dumps({'error':'provider_unavailable','message':str(exc)[:300],**exc.details()}))
    except (ValueError, KeyError, TypeError) as exc:
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
            print('MCP frame rejected', file=sys.stderr)
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
            write_message(outgoing, {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32603, 'message': 'internal error'}})
