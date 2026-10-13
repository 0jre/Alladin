"""Simulações A–Z. Dados sintéticos. Nenhuma ordem sai da Coinbase."""
import json
import os
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from alladin.agents import Council
from alladin.coinbase import Coinbase
from alladin.connect import connect_request, reset_session
from alladin.engine import Service
from alladin.market import build_views, tier_of
from alladin.mcp_server import handle
from alladin.models import SOL, USDC, TOKEN_2022, Candle, Config, Proposal, Snapshot
from alladin.research import demo_feed
from alladin.storage import Store
from alladin.universe import classify_snapshot, decode_mint_account

BASE = 1_700_000_000


def bar(i, mint=SOL, price=100.0):
    ts = BASE + i * 900
    span = max(price * 0.005, 1e-6)
    return Candle(ts, price, price + span, price - span, price, 100000, mint=mint)


def snap(i, mint=SOL, price=100.0, **kw):
    ts = BASE + (i + 1) * 900
    base = dict(price=price, liquidity_usd=10_000_000, volume_24h_usd=50_000_000,
                account_checked=True, cluster_verified=True, oracle_price=price,
                oracle_timestamp=ts, expected_funding_hourly=.00001,
                perp_market_verified=True, source='SIM_AZ', top10_account_share=.2,
                sell_simulated=True, route_buy=True, route_sell=True, extensions_decoded=True)
    base.update(kw)
    return Snapshot(ts, mint=mint, **base)


class Fixed:
    mode = 'rules'
    client = type('Client', (), {'calls': 0})()

    def decide(self, f, s, book, cfg, now):
        return Proposal('LONG', 'spot', .8, .02, .06, 24, 'Simulação', 'trend_following', mint=s.mint), {'mode': 'fixed'}


def open_service(cfg=None, council=None, **kw):
    folder = tempfile.TemporaryDirectory()
    service = Service(cfg or Config(fee_bps=0, slippage_bps=0, fixed_cost_usdc=0),
                      Path(folder.name) / 's.sqlite', council=council or Fixed(), **kw)
    return folder, service


def ingest(service, n, price=100.0, mint=SOL, snap_kw=None):
    for i in range(n):
        p = price(i) if callable(price) else price
        service.command('ingest', {'candle': asdict(bar(i, mint, p)), 'snapshot': asdict(snap(i, mint, p, **(snap_kw or {})))}, f'{i}:{mint[:6]}')


def record(code, name, layer, started, ok, detail, **extra):
    row = {'level': code, 'name': name, 'layer': layer, 'ok': ok, 'detail': detail,
           'seconds': round(time.perf_counter() - started, 3)}
    row.update(extra)
    return row


def run_levels():
    rows = []

    def run(code, name, layer, fn):
        started = time.perf_counter()
        print(f'start {code}', flush=True)
        try:
            detail, extra = fn()
            rows.append(record(code, name, layer, started, True, detail, **extra))
        except Exception as exc:
            rows.append(record(code, name, layer, started, False, str(exc)[:240]))
        print(f'done {code} {rows[-1]["ok"]} {rows[-1]["seconds"]}', flush=True)

    def a():
        folder, service = open_service()
        try:
            ingest(service, 40)
            status = service.status()
            assert status['positions'] == []
            assert status['last_decision']['approval']['reasons'] == ['warmup'] or status['last_decision']['council'].get('gate') == 'warmup' or 'warmup' in str(status['last_decision'])
            return '40 barras, sem posição', {'equity': status['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def b():
        folder, service = open_service()
        try:
            ingest(service, 82)
            status = service.status()
            assert len(status['positions']) == 1
            return 'posição spot aberta depois do aquecimento', {'equity': status['equity_usdc'], 'positions': 1}
        finally:
            folder.cleanup()

    def c():
        folder, service = open_service()
        try:
            ingest(service, 80)
            before = service.status()
            assert before['positions'] == []
            assert before['pending']
            ingest_one = 80
            service.command('ingest', {'candle': asdict(bar(ingest_one)), 'snapshot': asdict(snap(ingest_one))}, 'fill')
            after = service.status()
            assert len(after['positions']) == 1
            return 'decisão na barra 80, fill na 81', {'equity': after['equity_usdc'], 'positions': 1}
        finally:
            folder.cleanup()

    def d():
        folder, service = open_service()
        try:
            ingest(service, 82)
            halted = service.command('halt', {}, 'halt')
            assert halted['result'] == 'halted'
            service.command('ingest', {'candle': asdict(bar(82)), 'snapshot': asdict(snap(82))}, 'flat')
            status = service.status()
            assert status['positions'] == [] and status['halted']
            return 'halt fecha na barra seguinte', {'equity': status['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def e():
        folder, service = open_service()
        try:
            ingest(service, 82, snap_kw={'liquidity_usd': 100})
            status = service.status()
            reasons = status['last_decision']['approval']['reasons']
            assert status['positions'] == [] and 'insufficient_liquidity' in reasons
            return 'liquidez abaixo do mínimo veta a entrada', {'equity': status['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def f():
        folder, service = open_service()
        try:
            ingest(service, 1)
            try:
                service.command('ingest', {'candle': asdict(bar(1)), 'snapshot': asdict(Snapshot(**{**asdict(snap(1)), 'available_at': BASE + 3 * 900 + 1}))}, 'future')
            except ValueError as exc:
                assert 'available' in str(exc).lower() or 'lookahead' in str(exc).lower() or exc
                return 'snapshot futuro recusado', {'equity': service.status()['equity_usdc'], 'positions': 0}
            raise AssertionError('lookahead aceito')
        finally:
            folder.cleanup()

    def g():
        folder, service = open_service()
        try:
            body = {'candle': asdict(bar(0)), 'snapshot': asdict(snap(0))}
            first = service.command('ingest', body, 'same')
            second = service.command('ingest', body, 'same')
            assert first == second
            assert service.status()['bars_processed'] == 1
            return 'a mesma chave não reprocessa a barra', {'equity': service.status()['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def h():
        folder, service = open_service()
        try:
            service.command('admit', {'snapshot': asdict(snap(0, USDC, 1))}, 'admit')
            service.command('watch', {'mint': USDC, 'arm': True}, 'watch')
            for i in range(81):
                service.command('ingest', {'candle': asdict(bar(i)), 'snapshot': asdict(snap(i))}, f's{i}')
                service.command('ingest', {'candle': asdict(bar(i, USDC, 1)), 'snapshot': asdict(snap(i, USDC, 1))}, f'u{i}')
            service.command('ingest', {'candle': asdict(bar(81, price=1)), 'snapshot': asdict(snap(81, price=1))}, 'gap')
            left = {p['mint'] for p in service.status()['positions']}
            assert left == {USDC}
            return 'gap do SOL não fecha o USDC', {'equity': service.status()['equity_usdc'], 'positions': 1}
        finally:
            folder.cleanup()

    def i():
        def down(_mint):
            raise RuntimeError('fonte fora')
        folder, service = open_service(Config(execution='shadow', fee_bps=0, slippage_bps=0, fixed_cost_usdc=0), quoter=down)
        try:
            ingest(service, 82)
            status = service.status()
            assert status['positions'] == []
            assert 'shadow_source_down' in status['last_decision']['approval']['reasons']
            return 'sombra sem cotação bloqueia a entrada', {'equity': status['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def j():
        try:
            Config(execution='live')
        except ValueError as exc:
            assert 'live_arm' in str(exc)
            return 'live sem live_arm é recusado na configuração', {'equity': None, 'positions': 0}
        raise AssertionError('live sem arm foi aceito')

    def k():
        data = bytearray(82)
        data[44], data[45] = 6, 1
        data.extend(bytes(83))
        data.append(1)
        data.extend((9, 0, 0, 0))
        decoded = decode_mint_account(bytes(data))
        inst = classify_snapshot(snap(0, USDC, token_program=TOKEN_2022, extensions=decoded['extensions'], extensions_decoded=True), Config())
        assert inst['status'] == 'classified'
        assert 'dangerous_token2022_extension' in inst['reasons']
        return 'extensão non-transferable fica fora do livro', {'equity': None, 'positions': 0}

    def l():
        folder, service = open_service()
        try:
            ingest(service, 82)
            service.command('ingest', {'candle': asdict(bar(82, price=1)), 'snapshot': asdict(snap(82, price=1))}, 'crash')
            status = service.status()
            assert status['halted'] and status['halt_reason'] in {'maximum_drawdown', 'daily_loss'}
            return f"circuit breaker {status['halt_reason']}", {'equity': status['equity_usdc'], 'positions': len(status['positions'])}
        finally:
            folder.cleanup()

    def m():
        folder, service = open_service(Config(max_drawdown=.50, max_daily_loss=.02, fee_bps=0, slippage_bps=0, fixed_cost_usdc=0))
        try:
            ingest(service, 82)
            service.command('ingest', {'candle': asdict(bar(82, price=1)), 'snapshot': asdict(snap(82, price=1))}, 'day')
            status = service.status()
            assert status['halt_reason'] == 'daily_loss'
            return 'perda diária trava antes do drawdown largo', {'equity': status['equity_usdc'], 'positions': len(status['positions'])}
        finally:
            folder.cleanup()

    def n():
        folder, service = open_service()
        try:
            ingest(service, 1)
            result = service.command('evaluate', {'proposal': asdict(Proposal('SHORT', 'spot', .8, .02, .06, 24, 'venda', 'sim'))}, 'short')
            assert result['approval']['approved'] is False
            assert 'spot_cannot_short' in result['approval']['reasons']
            return 'spot não vende a descoberto', {'equity': service.status()['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def o():
        folder, service = open_service()
        try:
            service.command('ingest', {'candle': asdict(bar(0)), 'snapshot': asdict(snap(0, oracle_price=None, oracle_timestamp=None, expected_funding_hourly=None, perp_market_verified=False))}, 'o')
            result = service.command('evaluate', {'proposal': asdict(Proposal('SHORT', 'perp', .8, .02, .06, 24, 'perp', 'sim'))}, 'perp')
            assert 'missing_perp_oracle_or_funding' in result['approval']['reasons']
            return 'perp sem oracle e funding é vetado', {'equity': service.status()['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def p():
        folder = tempfile.TemporaryDirectory()
        try:
            service = Service(Config(), Path(folder.name) / 'p.sqlite', council=Council('rules'))
            for i, (candle, snapshot) in enumerate(demo_feed(120, seed=7)):
                service.command('ingest', {'candle': asdict(candle), 'snapshot': asdict(snapshot)}, f'p{i}')
            status = service.status()
            return f"conselho de regras, {status['bars_processed']} barras, modo {status['agent_mode']}", {'equity': status['equity_usdc'], 'positions': len(status['positions'])}
        finally:
            folder.cleanup()

    def q():
        folder, service = open_service()
        try:
            ingest(service, 5)
            done = service.command('finalize', {}, 'end')
            assert done['result'] == 'finalized'
            assert service.status()['halt_reason'] == 'research_finalized'
            return 'pesquisa encerrada no caixa restante', {'equity': done['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def r():
        view = build_views([
            {'source': 'binance', 'symbol': 'SOLUSDT', 'base': 'SOL', 'price': 150, 'change_24h_pct': 6, 'volume_24h': 2e9, 'market_cap': None, 'liquidity': None, 'chain': None},
            {'source': 'okx', 'symbol': 'SOL-USDT', 'base': 'SOL', 'price': 151, 'change_24h_pct': 5, 'volume_24h': 1e9, 'market_cap': None, 'liquidity': None, 'chain': None},
        ], 10)
        assert view['execution'] == 'coinbase' and view['alpha'][0]['executed'] is False
        return 'alpha observado, execução marcada coinbase', {'equity': None, 'positions': 0}

    def s():
        reset_session()
        os.environ['COINBASE_OAUTH_CLIENT_ID'] = 'abc12345'
        os.environ['COINBASE_OAUTH_REDIRECT_URI'] = 'http://127.0.0.1:8080/oauth/coinbase/callback'
        try:
            action = connect_request()
            assert action['type'] == 'action_request' and 'client_secret' not in action['url']
            return 'link Connect account sem segredo', {'equity': None, 'positions': 0}
        finally:
            reset_session()
            os.environ.pop('COINBASE_OAUTH_CLIENT_ID', None)
            os.environ.pop('COINBASE_OAUTH_REDIRECT_URI', None)

    def t():
        folder, service = open_service()
        try:
            called = handle(service, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'desks', 'arguments': {'desk': 'risk'}}})
            assert called['isError'] is False
            status = handle(service, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'alladin_status', 'arguments': {}}})
            body = json.loads(status['content'][0]['text'])
            assert body['venue'] == 'coinbase'
            return 'MCP entrega mesa e status', {'equity': body['equity_usdc'], 'positions': 0}
        finally:
            folder.cleanup()

    def u():
        mega = tier_of({'market_cap': 20_000_000_000, 'volume_24h': 1})
        micro = tier_of({'market_cap': 1_000, 'volume_24h': 1})
        assert mega == 'mega' and micro == 'micro'
        return 'classificação mega e micro', {'equity': None, 'positions': 0}

    def v():
        view = build_views([
            {'source': 'gmgn', 'symbol': 'WIF', 'base': 'WIF', 'price': 2, 'change_24h_pct': 12, 'volume_24h': 1e6, 'market_cap': None, 'liquidity': 1e5, 'chain': 'sol'},
        ], 5)
        assert view['alpha'] == []
        return 'uma fonte só não vira alpha', {'equity': None, 'positions': 0}

    def w():
        view = build_views([
            {'source': 'coingecko', 'symbol': 'btc', 'base': 'BTC', 'price': 100, 'change_24h_pct': 1, 'volume_24h': 10, 'market_cap': 1e12, 'liquidity': None, 'chain': None},
            {'source': 'coinmarketcap', 'symbol': 'BTC', 'base': 'BTC', 'price': 110, 'change_24h_pct': 1, 'volume_24h': 10, 'market_cap': 1e12, 'liquidity': None, 'chain': None},
        ], 5)
        assert view['tracker'][0]['dispersion'] > 0.09
        return 'dispersão de 10% entre duas fontes', {'equity': None, 'positions': 0}

    def x():
        class Once:
            def __init__(self):
                self.calls = 0
            def json(self, url, payload=None, headers=None, retry=True):
                self.calls += 1
                return {'success': True}
        http = Once()
        result = Coinbase(http, authorize=lambda *a: {'Authorization': 'Bearer test'}).create_order(
            'BTC-USD', 'BUY', '10', 'client-0001', armed=True)
        assert result['status'] == 'unknown' and http.calls == 1 and 'retried' not in result
        return 'ordem sem id não é reenviada', {'equity': None, 'positions': 0}

    def y():
        folder = tempfile.TemporaryDirectory()
        try:
            store = Store(Path(folder.name) / 'a.sqlite')
            with store.transaction() as db:
                store.event(db, 1, 'decision', {'action': 'HOLD'})
            assert store.verify_audit()['valid']
            with store.transaction() as db:
                db.execute("UPDATE events SET payload='{}' WHERE seq=1")
            assert store.verify_audit()['valid'] is False
            return 'alteração do evento quebra a cadeia', {'equity': None, 'positions': 0}
        finally:
            folder.cleanup()

    def z():
        folder, service = open_service()
        try:
            admitted = service.command('admit', {'snapshot': asdict(snap(0, USDC, 1))}, 'admit')
            assert admitted['status'] == 'eligible'
            service.command('watch', {'mint': USDC, 'arm': True}, 'watch')
            for i in range(82):
                service.command('ingest', {'candle': asdict(bar(i)), 'snapshot': asdict(snap(i))}, f'z{i}')
            status = service.status()
            assert status['venue'] == 'coinbase' and status['execution'] == 'paper'
            assert len(status['positions']) == 1
            return 'funil, papel e venue coinbase no mesmo ciclo', {'equity': status['equity_usdc'], 'positions': 1}
        finally:
            folder.cleanup()

    catalog = [
        ('A', 'Aquecimento', 'motor', a),
        ('B', 'Entrada paper', 'motor', b),
        ('C', 'Fill na barra seguinte', 'negociação', c),
        ('D', 'Halt', 'negociação', d),
        ('E', 'Veto de liquidez', 'risco', e),
        ('F', 'Lookahead', 'pesquisa', f),
        ('G', 'Idempotência', 'controle', g),
        ('H', 'Dois spots isolados', 'negociação', h),
        ('I', 'Sombra sem fonte', 'execução', i),
        ('J', 'Live sem arm', 'execução', j),
        ('K', 'Token perigoso', 'universo', k),
        ('L', 'Drawdown', 'risco', l),
        ('M', 'Perda diária', 'risco', m),
        ('N', 'Spot sem short', 'risco', n),
        ('O', 'Perp sem oracle', 'risco', o),
        ('P', 'Conselho de regras', 'conselho', p),
        ('Q', 'Finalize', 'pesquisa', q),
        ('R', 'Alpha observado', 'visão', r),
        ('S', 'Connect account', 'coinbase', s),
        ('T', 'Ferramenta MCP', 'mcp', t),
        ('U', 'Classificação', 'visão', u),
        ('V', 'Alpha com uma fonte', 'visão', v),
        ('W', 'Dispersão', 'visão', w),
        ('X', 'Ordem desconhecida', 'coinbase', x),
        ('Y', 'Cadeia de auditoria', 'auditoria', y),
        ('Z', 'Ciclo completo', 'negociação', z),
    ]
    chosen = set(sys.argv[1:])
    for item in catalog:
        if chosen and item[0] not in chosen:
            continue
        run(*item)
    return rows


def summarize(rows):
    equities = [row['equity'] for row in rows if isinstance(row.get('equity'), (int, float))]
    return {
        'generated_at': datetime.now(timezone.utc).date().isoformat(),
        'source': 'tests/sim_az.py',
        'data': 'SYNTHETIC',
        'levels': len(rows),
        'passed': sum(row['ok'] for row in rows),
        'failed': sum(not row['ok'] for row in rows),
        'seconds': round(sum(row['seconds'] for row in rows), 3),
        'equity_min': min(equities) if equities else None,
        'equity_max': max(equities) if equities else None,
        'rows': rows,
    }


if __name__ == '__main__':
    fresh = run_levels()
    out = Path('results/sim_az.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and out.exists():
        raw = out.read_bytes()
        try:
            previous = json.loads(raw.decode('utf-8'))
        except UnicodeDecodeError:
            previous = json.loads(raw.decode('cp1252'))
        by_level = {row['level']: row for row in previous['rows']}
        for row in fresh:
            by_level[row['level']] = row
        rows = [by_level[letter] for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
    else:
        rows = fresh
    report = summarize(rows)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('levels', 'passed', 'failed', 'seconds')}, ensure_ascii=False))
    raise SystemExit(0 if report['failed'] == 0 else 1)
