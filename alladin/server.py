"""Headless JSON command server. Bind loopback; use authenticated TLS proxy externally."""
import hmac
import json
import os
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs
from .dispatch import execute
from .transport import DataError

CONTRACT = {
    'version':'0.6','venue':'solana_dex','chain':'solana','execution':'paper',
    'endpoints':{'GET /health':'process health; no portfolio data',
                 'GET /v1/status':'persistent portfolio state',
                 'GET /v1/audit?limit=100':'decision and execution events',
                 'GET /v1/contract':'command contract',
                 'GET /v1/audit/verify':'verify event hash chain',
                 'POST /v1/commands':'{command,args}; Bearer token + Idempotency-Key'},
    'commands':{
        'paper_tick':{'args':[],'result':'read-only Solana pool/RPC data -> forward-only warmup or spot paper cycle; never signs or sends'},
        'ingest':{'args':['candle','snapshot'],'result':'closed bar -> agents -> risk -> pending paper action'},
        'analyze':{'args':[],'result':'analysis of stored data; does not schedule a trade'},
        'evaluate':{'args':['proposal'],'result':'risk approval only; does not execute'},
        'halt':{'args':[],'result':'latching stop; flatten on next valid bar'},
        'finalize':{'args':[],'result':'research settlement at last observed mark; closes session'},
        'universe':{'args':[],'result':'registered mints and funnel status'},
        'admit':{'args':['snapshot'],'result':'classify a mint; does not trade'},
        'watch':{'args':['mint','arm (optional)'],'result':'move an eligible mint into the watched or negotiable book'},
        'unwatch':{'args':['mint'],'result':'drop a mint back to eligible and cancel its pending action'}},
    'agent_flow':['paper_tick','analyze/evaluate','status/audit'],
    'mcp':{'command':'python -m alladin mcp','transport':'stdio'},
    'notes':['Backend Python; Solana mainnet only; spot paper only.',
             'paper_tick reads Coinbase Advanced Trade public SOL spot market data and read-only Solana RPC.',
             'No wallet connection, signer, transaction builder or transaction submission.',
             'Paper fills use the current Coinbase midpoint plus configured cost assumptions; they are not routed quotes.',
             'ingest automatically invokes the council; synthetic replay is not a live-market performance test.']}

def build_server(service,port=8080,token=None):
    token = token or os.environ.get('LAB_API_TOKEN')
    if not token or len(token) < 32:
        raise ValueError('LAB_API_TOKEN obrigatório com pelo menos 32 caracteres')
    mutation_lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        server_version = 'Alladin/0.6'
        def log_message(self,*args):
            pass  # avoid tokens, addresses, request paths and payloads in access logs
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
                return self.send_json(200,{'status':'ok','venue':'solana_dex','chain':service.cfg.chain,'execution':service.cfg.execution})
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
