"""Time-bounded live-data paper observation for an external session consumer."""
import json
import time
import uuid
from pathlib import Path
from .transport import DataError,deadline
from .external import task_is_current


def run_demo(service,seconds=60,poll_seconds=5,output='results/demo-live',emit=None):
    if type(seconds) not in (int,float) or not 0<seconds<=3600:
        raise ValueError('seconds precisa estar entre 0 e 3600')
    if type(poll_seconds) not in (int,float) or not 0<poll_seconds<=60:
        raise ValueError('poll_seconds precisa estar entre 0 e 60')
    if service.council.mode!='external':
        raise ValueError('Demo de sessão exige modo external')
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    initial=service.status()
    started=time.time();begin=time.monotonic();end=begin+seconds
    run_id=uuid.uuid4().hex
    observations=[]
    while time.monotonic()<end:
        row={'elapsed_seconds':time.monotonic()-begin,'observed_at':time.time()}
        try:
            with deadline(end-time.monotonic()):
                row['stage']='paper_tick'
                row['tick']=service.command('paper_tick',{},f'demo-{run_id}-{len(observations)}-tick')
                # Warmup already has closed bars. prepare_decision obtains the first
                # verified current snapshot; it need not wait for a later candle.
                if row['tick']['result'] in {'warmed_up','processed','resynchronized','waiting_for_closed_bar'}:
                    with service.store.connect() as db:
                        state=service._load(db)
                    task=state.get('external_task')
                    valid=task_is_current(task,state,time.time())
                    if not valid:
                        row['stage']='prepare_decision'
                        row['preparation']=service.command('prepare_decision',{},f'demo-{run_id}-{len(observations)}-prepare')
                        (root/'decision-task.json').write_text(json.dumps(row['preparation'],indent=2))
        except (DataError,ValueError) as exc:
            row['error']={'type':type(exc).__name__,'message':str(exc),**(exc.details() if isinstance(exc,DataError) else {})}
        row['completed_elapsed_seconds']=time.monotonic()-begin
        observations.append(row)
        with (root/'observations.jsonl').open('a') as stream:
            stream.write(json.dumps(row,allow_nan=False)+'\n')
        if emit:emit(row)
        remaining=end-time.monotonic()
        if remaining>0:time.sleep(min(poll_seconds,remaining))
    collection_elapsed=time.monotonic()-begin
    status=service.status()
    report=dict(requested_seconds=seconds,collection_elapsed_seconds=collection_elapsed,
                started_at=started,ended_at=time.time(),run_id=run_id,
                initial_status=initial,final_status=status,observations=observations,
                audit=service.store.verify_audit(),performance=service.performance(),
                net_equity_change_usdc=status['equity_usdc']-initial['equity_usdc'],
                decision_authority='external session only; runner never fabricates reports or plans',
                deadline_scope='collection and retry window; report serialization follows the window')
    (root/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    return report
