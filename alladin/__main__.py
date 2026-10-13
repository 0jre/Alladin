import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from .models import Config
from .engine import Service
from .research import write_demo,jsonl_feed,export
from .server import build_server,CONTRACT
from .mcp_server import serve as serve_mcp
from .client import BackendClient
from .transport import DataError
from .validation import validate

def main():
    parser = argparse.ArgumentParser(description='Solana-only research backend; paper execution and read-only market data.')
    parser.add_argument('--config',default='config.json')
    parser.add_argument('--db',default='data/session.sqlite')
    parser.add_argument('--agents',choices=['rules','llm'],default='rules')
    parser.add_argument('--model',default=None)
    parser.add_argument('--max-llm-calls',type=int,default=200)
    sub = parser.add_subparsers(dest='command',required=True)
    demo = sub.add_parser('generate-demo'); demo.add_argument('--output',default='data/demo.jsonl'); demo.add_argument('--bars',type=int,default=600)
    run = sub.add_parser('replay'); run.add_argument('--feed',required=True); run.add_argument('--output',default='results'); run.add_argument('--finalize',action='store_true')
    serve = sub.add_parser('serve'); serve.add_argument('--port',type=int,default=8080)
    paper_live = sub.add_parser('paper-live'); paper_live.add_argument('--poll-seconds',type=int,default=30)
    sub.add_parser('paper-tick')
    sub.add_parser('mcp')
    sub.add_parser('status'); sub.add_parser('contract')
    exp = sub.add_parser('export'); exp.add_argument('--output',default='results')
    sub.add_parser('halt')
    val=sub.add_parser('validate'); val.add_argument('--feed',required=True); val.add_argument('--output',default='results/validation');val.add_argument('--folds',type=int,default=3)
    request = sub.add_parser('call'); request.add_argument('--url',default='http://127.0.0.1:8080'); request.add_argument('--request',required=True); request.add_argument('--key',required=True)
    args = parser.parse_args()
    try:
        if args.command == 'generate-demo':
            if not 80 <= args.bars <= 10000:
                raise ValueError('Demo: 80–10000 barras')
            write_demo(args.output,args.bars)
            result = {'file':args.output,'data':'SYNTHETIC','bars':args.bars}
        elif args.command == 'contract':
            result = CONTRACT
        elif args.command == 'call':
            d = json.loads(Path(args.request).read_text())
            result = BackendClient(args.url).command(d['command'],d['args'],args.key)
        else:
            if not 1 <= args.max_llm_calls <= 10000:
                raise ValueError('Limite de chamadas: 1–10000')
            cfg = Config.load(args.config)
            if args.command == 'validate':
                if args.agents != 'rules':
                    raise ValueError('Validação por folds nesta versão aceita rules; avaliação LLM ainda pendente')
                result=validate(cfg,args.feed,args.output,args.folds)
                print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
                return 0
            service = Service(cfg,args.db,args.agents,args.model,args.max_llm_calls)
            if args.command == 'mcp':
                return serve_mcp(service)
            if args.command == 'paper-tick':
                result = service.command('paper_tick',{},'paper-tick-'+str(time.time_ns()))
                print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
                return 0
            elif args.command == 'paper-live':
                if not 10 <= args.poll_seconds <= 300:
                    raise ValueError('poll-seconds precisa estar entre 10 e 300')
                if cfg.chain != 'solana' or cfg.execution != 'paper' or set(cfg.allowed_markets) != {'spot'}:
                    raise ValueError('paper-live exige Solana, execução paper e spot apenas')
                try:
                    next_poll = time.monotonic()
                    failures = 0
                    while True:
                        try:
                            result = service.command('paper_tick',{},'paper-live-'+str(time.time_ns()))
                            failures = 0
                            delay = args.poll_seconds
                        except DataError as exc:
                            failures += 1
                            delay = max(min(300,max(args.poll_seconds,10)*(2**min(failures-1,4))),
                                        getattr(exc,'retry_after',0) or 0)
                            result = {'result':'provider_unavailable','error':str(exc),'retry_seconds':delay,
                                      'portfolio_unchanged':True}
                        print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
                        next_poll += delay
                        time.sleep(max(0,next_poll-time.monotonic()))
                except KeyboardInterrupt:
                    print(json.dumps({'result':'stopped','positions_left_open':len(service.status()['positions'])}),flush=True)
                return 0
            if args.command == 'serve':
                server = build_server(service,args.port)
                print(json.dumps(dict(status='listening',host='127.0.0.1',port=server.server_port,venue='coinbase_advanced',chain=cfg.chain,execution=cfg.execution)),flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    server.server_close()
                return 0
            if args.command == 'status':
                result = service.status()
            elif args.command == 'halt':
                result = service.command('halt',{},'cli-halt-'+str(time.time_ns()))
            elif args.command == 'export':
                result = export(service,args.output)
            else:
                count = 0
                armed = {cfg.mint}
                for b,s in jsonl_feed(args.feed):
                    if b.mint not in armed:
                        # Non-anchor mints enter through the same funnel: admit
                        # classifies the snapshot, watch fails fast if ineligible.
                        service.command('admit',dict(snapshot=asdict(s)),f'replay:admit:{b.mint}')
                        service.command('watch',dict(mint=b.mint,arm=True),f'replay:watch:{b.mint}')
                        armed.add(b.mint)
                    service.command('ingest',dict(candle=asdict(b),snapshot=asdict(s)),f'replay:{b.mint}:{b.timestamp}')
                    count += 1
                if args.finalize:
                    service.command('finalize',{},'replay:finalize')
                result = export(service,args.output)
                result['feed_records'] = count
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
        return 0
    except (ValueError,KeyError,TypeError,DataError,OSError) as e:
        print(json.dumps({'error':str(e)[:300]},ensure_ascii=False),file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
