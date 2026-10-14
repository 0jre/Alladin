import argparse
import json
import os
import sys
import signal
import threading
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

def _interrupt(signum,frame):
    raise KeyboardInterrupt()

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
    serve.add_argument('--paper-worker',action='store_true')
    serve.add_argument('--poll-seconds',type=int,default=30)
    paper_live = sub.add_parser('paper-live'); paper_live.add_argument('--poll-seconds',type=int,default=30)
    paper_live.add_argument('--cycles',type=int,default=None)
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
            if args.agents == 'llm' and (args.command in {'paper-live','paper-tick','replay'}
                    or args.command == 'serve' and args.paper_worker):
                if not os.environ.get('OPENAI_API_KEY') or not (args.model or os.environ.get('OPENAI_MODEL')):
                    raise ValueError('Modo llm exige OPENAI_API_KEY e OPENAI_MODEL ou --model')
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
                from .runtime import PaperRunner
                runner = PaperRunner(service,args.poll_seconds)
                previous = signal.signal(signal.SIGTERM,lambda *_:runner.stop_event.set())
                try:
                    runner.run(args.cycles)
                except KeyboardInterrupt:
                    runner.stop_event.set()
                finally:
                    signal.signal(signal.SIGTERM,previous)
                print(json.dumps({'result':'stopped','positions_left_open':len(service.status()['positions'])}),flush=True)
                return 0
            if args.command == 'serve':
                from .runtime import PaperRunner
                runner = PaperRunner(service,args.poll_seconds) if args.paper_worker else None
                server = build_server(service,args.port,runner=runner)
                worker_failed = threading.Event()
                def work():
                    try:
                        runner.run()
                    except Exception:
                        worker_failed.set()
                        print(json.dumps({'result':'worker_failed','detail':'worker stopped; supervisor restart required'}),flush=True)
                        server.shutdown()
                thread = threading.Thread(target=work,daemon=True,name='paper-worker') if runner else None
                previous = signal.signal(signal.SIGTERM,_interrupt)
                try:
                    print(json.dumps(dict(status='listening',host='127.0.0.1',port=server.server_port,
                        venue='coinbase_advanced',chain=cfg.chain,execution=cfg.execution,
                        paper_worker=bool(runner))),flush=True)
                    if thread:
                        thread.start()
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    if runner:
                        runner.stop_event.set()
                    server.server_close()
                    if thread and thread.ident is not None:
                        thread.join(timeout=30)
                    signal.signal(signal.SIGTERM,previous)
                return 1 if worker_failed.is_set() else 0
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
