"""Headless JSON command server. Bind loopback; use authenticated TLS proxy externally."""
import hmac
import json
import os
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs
from .connect import complete
from .dispatch import execute
from .transport import HTTP, DataError

CONTRACT = {
    'version':'0.5','venue':'coinbase','execution':'paper',
    'endpoints':{'GET /health':'process health; no portfolio data',
                 'GET /v1/status':'persistent portfolio state',
                 'GET /v1/audit?limit=100':'decision and execution events',
                 'GET /v1/contract':'command contract',
                 'GET /v1/audit/verify':'verify event hash chain',
                 'POST /v1/commands':'{command,args}; Bearer token + Idempotency-Key'},
    'commands':{
        'ingest':{'args':['candle','snapshot'],'result':'closed bar -> agents -> risk -> pending paper action'},
        'analyze':{'args':[],'result':'analysis of stored data; does not schedule a trade'},
        'evaluate':{'args':['proposal'],'result':'risk approval only; does not execute'},
        'halt':{'args':[],'result':'latching stop; flatten on next valid bar'},
        'finalize':{'args':[],'result':'research settlement at last observed mark; closes session'},
        'coinbase_products':{'args':['product_type (optional)','limit (optional)'],'result':'public Advanced Trade products; SPOT by default'},
        'coinbase_candles':{'args':['product_id','start','end','granularity (optional)'],'result':'public Advanced Trade candles'},
        'coinbase_quote':{'args':['network','from_token','to_token','from_amount','taker'],'result':'CDP Trade API swap quote for ethereum, base or arbitrum; does not execute'},
        'coinbase_preview':{'args':['product_id','side','quote_size','client_order_id'],'result':'Advanced Trade order preview; does not send'},
        'coinbase_order':{'args':['product_id','side','quote_size','client_order_id'],'result':'Advanced Trade spot order; requires live_arm and COINBASE_JWT or OAuth'},
        'coinbase_connect':{'args':['scopes (optional)','trade (optional)'],'result':'action_request with the Coinbase Connect account URL; does not return a token'},
        'coinbase_connection':{'args':[],'result':'whether the local process stored an OAuth session; no token'},
        'market_radar':{'args':['sources (optional)','symbols (optional)','query (optional)','limit (optional)','chain (optional)'],'result':'read-only ranking, classification, signals, tracker, alpha and copy candidates'},
        'market_prices':{'args':['symbol','sources (optional)','limit (optional)'],'result':'read-only prices for one symbol across sources'},
        'desks':{'args':['desk (optional)'],'result':'Alladin research desks bound to these tools'},
        'platforms':{'args':['name (optional)'],'result':'tool manifests for Cursor, ChatGPT, Claude and computer sandboxes'},
        'universe':{'args':[],'result':'registered mints and funnel status'},
        'admit':{'args':['snapshot'],'result':'classify a mint; does not trade'},
        'watch':{'args':['mint','arm (optional)'],'result':'move an eligible mint into the watched or negotiable book'},
        'unwatch':{'args':['mint'],'result':'drop a mint back to eligible and cancel its pending action'}},
    'agent_flow':['market_radar/market_prices','coinbase_connect when an order needs an account','coinbase_products/coinbase_candles/coinbase_quote','ingest closed candles','analyze/evaluate','status/audit'],
    'mcp':{'command':'python -m alladin mcp','transport':'stdio'},
    'notes':['Chats connect through MCP. The loopback HTTP API remains for sandbox and idempotent clients',
             'Orders execute only at Coinbase',
             'Binance, OKX, CoinGecko, CoinMarketCap, DexScreener and GMGN are read-only vision',
             'action_request.url is the Connect account link; the token stays in the local process',
             'ingest automatically invokes council; accepted entries execute on next bar open',
             'no arbitrary shell command; order send requires live_arm']}

def build_server(service,port=8080,token=None):
    token = token or os.environ.get('LAB_API_TOKEN')
    if not token or len(token) < 32:
        raise ValueError('LAB_API_TOKEN obrigatório com pelo menos 32 caracteres')
    mutation_lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        server_version = 'Alladin/0.5'
        def log_message(self,*args):
            pass  # avoid tokens, addresses, request paths and payloads in access logs
        def _oauth_callback(self, query):
            params = parse_qs(query)
            code = (params.get('code') or [''])[0]
            state = (params.get('state') or [''])[0]
            try:
                complete(code, state, HTTP())
                body = '<!doctype html><title>Coinbase</title><p>Conta Coinbase conectada. Pode fechar esta aba.</p>'
                status = 200
            except (ValueError, DataError):
                body = '<!doctype html><title>Coinbase</title><p>Não foi possível concluir a conexão.</p>'
                status = 400
            raw = body.encode()
            self.send_response(status)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            self.wfile.write(raw)
        def send_json(self,status,value):
            raw = json.dumps(value,allow_nan=False,separators=(',',':')).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            self.wfile.write(raw)
        def authenticated(self):
            supplied = self.headers.get('Authorization','')
            if not hmac.compare_digest(supplied.encode('utf-8'),('Bearer '+token).encode('utf-8')):
                self.send_json(401,{'error':'unauthorized'})
                return False
            return True
        def do_GET(self):
            self.connection.settimeout(15)
            parsed = urlsplit(self.path)
            if parsed.path == '/health':
                return self.send_json(200,{'status':'ok','venue':'coinbase','chain':service.cfg.chain,'execution':service.cfg.execution})
            if parsed.path == '/oauth/coinbase/callback':
                return self._oauth_callback(parsed.query)
            if not self.authenticated():
                return
            try:
                if parsed.path == '/v1/status':
                    result = service.status()
                elif parsed.path == '/v1/contract':
                    result = CONTRACT
                elif parsed.path == '/v1/audit/verify':
                    result = service.store.verify_audit()
                elif parsed.path == '/v1/audit':
                    limit = int(parse_qs(parsed.query).get('limit',['100'])[0])
                    result = {'events':service.store.audit(limit)}
                else:
                    return self.send_json(404,{'error':'not_found'})
                self.send_json(200,result)
            except (ValueError,TypeError):
                self.send_json(400,{'error':'invalid_request_or_session'})
            except Exception:
                self.send_json(500,{'error':'internal_error'})
        def do_POST(self):
            self.connection.settimeout(15)
            if not self.authenticated():
                return
            if self.path != '/v1/commands':
                return self.send_json(404,{'error':'not_found'})
            if not mutation_lock.acquire(blocking=False):
                return self.send_json(503,{'error':'command_busy','retry':'same_idempotency_key'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 1 <= length <= 200000 or self.headers.get('Transfer-Encoding'):
                    return self.send_json(413,{'error':'invalid_body_size'})
                if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    return self.send_json(415,{'error':'json_required'})
                d = json.loads(self.rfile.read(length),parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                if not isinstance(d,dict) or set(d) != {'command','args'} or not isinstance(d['args'],dict):
                    raise ValueError('Body deve conter somente command e args')
                name,args = d['command'],d['args']
                if not isinstance(name,str):
                    raise ValueError('command inválido')
                key = self.headers.get('Idempotency-Key','')
                result = execute(service, name, args, key)
                self.send_json(200,{'result':result})
            except (ValueError,TypeError,KeyError) as e:
                self.send_json(400,{'error':'invalid_request','detail':str(e)[:200]})
            except DataError as e:
                self.send_json(503,{'error':'provider_unavailable','detail':str(e)[:200]})
            except Exception:
                self.send_json(500,{'error':'internal_error'})
            finally:
                mutation_lock.release()
    # Reads/health remain available during LLM calls; one serialized command at a time.
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
