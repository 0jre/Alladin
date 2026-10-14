"""Interruptible paper worker; one worker per SQLite file on Linux/Unix."""
import fcntl
import json
import threading
import time
import uuid
from pathlib import Path

from .transport import DataError


class PaperRunner:
    def __init__(self,service,poll_seconds=30,stop_event=None,emit=None):
        if type(poll_seconds) is not int or not 10 <= poll_seconds <= 300:
            raise ValueError('poll-seconds must be between 10 and 300')
        if hasattr(service,'cfg') and service.cfg.timeframe_seconds not in {60,300,900}:
            raise ValueError('Paper worker requires 1-, 5- or 15-minute candles')
        if hasattr(service,'cfg'):
            service.status()  # incompatible/corrupt sessions must fail startup, not retry forever
        self.service,self.poll_seconds = service,poll_seconds
        self.stop_event = stop_event or threading.Event()
        self.emit = emit or (lambda value:print(json.dumps(value,ensure_ascii=False,allow_nan=False),flush=True))
        self._lock = threading.Lock()
        self._health = dict(running=False,cycles=0,failures=0,last_success=None,
                            last_error=None,last_result=None,retry_seconds=0)

    def health(self):
        with self._lock:
            result = dict(self._health)
        last = result['last_success']
        result['ready'] = bool(result['running'] and last is not None and not result['failures']
            and time.time()-last <= max(120,3*self.poll_seconds))
        return result

    def _update(self,**fields):
        with self._lock:
            self._health.update(fields)

    def run(self,max_cycles=None):
        if max_cycles is not None and (type(max_cycles) is not int or max_cycles<1):
            raise ValueError('cycles must be a positive integer')
        path = Path(self.service.store.path).resolve()
        with open(str(path)+'.worker.lock','a') as lease:
            try:
                fcntl.flock(lease.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                self._update(last_error='worker_already_running')
                raise ValueError('A worker already exists for this database') from None
            self._update(running=True)
            key = 'worker-'+uuid.uuid4().hex
            try:
                while not self.stop_event.is_set():
                    delay = self.poll_seconds
                    try:
                        result = self.service.command('paper_tick',{},key)
                        health = self.health()
                        self._update(cycles=health['cycles']+1,failures=0,last_success=time.time(),
                                     last_error=None,last_result=result['result'],retry_seconds=delay)
                        key = 'worker-'+uuid.uuid4().hex
                    except (DataError,ValueError) as exc:
                        failures = self.health()['failures']+1
                        delay = max(min(300,self.poll_seconds*2**min(failures-1,4)),
                                    getattr(exc,'retry_after',None) or 0)
                        self._update(failures=failures,last_error=type(exc).__name__,retry_seconds=delay)
                        result = dict(result='provider_unavailable' if isinstance(exc,DataError) else 'session_blocked',
                                      detail=str(exc)[:200],retry_seconds=delay,portfolio_unchanged=True,
                                      diagnostics=exc.details() if isinstance(exc,DataError) else {})
                    except Exception:
                        self._update(last_error='internal_error',failures=self.health()['failures']+1)
                        self.emit(dict(result='worker_failed',detail='internal_error'))
                        raise
                    self.emit(result)
                    if max_cycles is not None and self.health()['cycles'] >= max_cycles:
                        break
                    # Wait from completion, never from an overdue polling deadline.
                    if self.stop_event.wait(delay):
                        break
            finally:
                self._update(running=False)
                fcntl.flock(lease.fileno(),fcntl.LOCK_UN)
