"""Bounded JSON HTTP transport. Never logs auth headers, URLs or response bodies."""
import json
import queue
import threading
from contextlib import contextmanager
from contextvars import ContextVar
import math
import random
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlencode

class DataError(RuntimeError):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = (min(86400.0,max(0.0,retry_after))
                            if type(retry_after) in (int,float) and math.isfinite(retry_after) else None)

# A socket timeout alone does not bound DNS, retries or a slowly streamed body.
# Only read-only HTTP runs in these daemon threads; they never mutate a ledger.
_DEADLINE = ContextVar('alladin_io_deadline',default=None)
_IO_SLOTS = threading.BoundedSemaphore(4)


def check_deadline():
    end=_DEADLINE.get()
    if end is not None and time.monotonic()>=end:
        raise DataError('Prazo total de coleta excedido; nenhuma operação aplicada')


@contextmanager
def deadline(seconds):
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0:
        raise ValueError('Prazo precisa ser positivo e finito')
    end=time.monotonic()+seconds
    parent=_DEADLINE.get()
    token=_DEADLINE.set(min(end,parent) if parent is not None else end)
    try:
        check_deadline()
        yield
    finally:
        _DEADLINE.reset(token)


def _remaining():
    check_deadline()
    return _DEADLINE.get()-time.monotonic()


def _bounded_read(request,timeout):
    remaining=_remaining()
    if not _IO_SLOTS.acquire(timeout=remaining):
        raise DataError('Capacidade de coleta esgotada dentro do prazo')
    remaining=_remaining_after_acquire()
    result=queue.Queue(maxsize=1)
    def read():
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=min(timeout,remaining)) as response:
                raw=response.read(2_000_001)
            result.put((True,raw))
        except Exception as exc:
            result.put((False,exc))
        finally:
            _IO_SLOTS.release()
    thread=threading.Thread(target=read,daemon=True,name='alladin-read-only-http')
    try:
        thread.start()
    except BaseException:
        _IO_SLOTS.release()
        raise
    try:
        ok,value=result.get(timeout=_remaining())
    except queue.Empty:
        raise DataError('Prazo total de coleta excedido; resposta tardia descartada') from None
    check_deadline()
    if not ok:
        raise value
    return value


def _remaining_after_acquire():
    try:
        return _remaining()
    except BaseException:
        _IO_SLOTS.release()
        raise


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DataError('Redirect HTTP recusado')

class HTTP:
    def __init__(self, timeout=15, retries=2, retry_cap=8, sleeper=None, random_value=None):
        if (type(retries) is not int or not 0 <= retries <= 10
                or type(retry_cap) not in (int,float) or not math.isfinite(retry_cap) or retry_cap <= 0
                or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError('Configuração de retry inválida')
        self.timeout, self.retries, self.retry_cap = timeout, retries, float(retry_cap)
        self._sleep = sleeper or time.sleep
        self._random = random_value or random.random
    def json(self,url,payload=None,headers=None,retry=True):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise DataError('Endpoint HTTPS obrigatório, sem credenciais na URL')
        body = None if payload is None else json.dumps(payload,allow_nan=False).encode()
        request = urllib.request.Request(url, data=body,
                    headers={'Content-Type':'application/json','User-Agent':'Alladin/0.6',**(headers or {})})
        return self._read(request, retry)

    def form(self, url, fields, headers=None, retry=False):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise DataError('Endpoint HTTPS obrigatório, sem credenciais na URL')
        if not isinstance(fields, dict):
            raise DataError('Formulário inválido')
        body = urlencode({k: v for k, v in fields.items()}).encode()
        request = urllib.request.Request(url, data=body, headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Alladin/0.6', **(headers or {})})
        return self._read(request, retry)

    def _read(self, request, retry):
        with deadline(self.timeout):
            return self._read_with_deadline(request,retry)

    def _pause(self,seconds):
        if seconds>=_remaining():
            raise DataError('Retry excederia prazo total de coleta',retry_after=seconds)
        self._sleep(seconds)
        check_deadline()

    def _read_with_deadline(self, request, retry):
        attempts = self.retries+1 if retry else 1
        for attempt in range(attempts):
            try:
                raw = _bounded_read(request,self.timeout)
                if len(raw) > 2_000_000:
                    raise DataError('Resposta excedeu limite de bytes')
                return json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            except urllib.error.HTTPError as e:
                e.close()
                if e.code in {429,503}:
                    retry_after = self._retry_after(e)
                    if not retry or attempt == attempts-1:
                        raise DataError('Fonte de dados temporariamente indisponível',
                                         retry_after=retry_after) from None
                    if retry_after is not None and retry_after > self.retry_cap:
                        raise DataError('Fonte de dados temporariamente indisponível',
                                         retry_after=retry_after) from None
                    delay = (retry_after + self._random() * .25 if retry_after is not None
                             else self._backoff(attempt))
                    self._pause(delay)
                    continue
                if e.code not in {500,502,503,504}:
                    raise DataError(f'HTTP {e.code}; conteúdo omitido') from None
                if attempt == attempts-1:
                    raise DataError('Fonte de dados temporariamente indisponível') from None
                self._pause(self._backoff(attempt))
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == attempts-1:
                    raise DataError('Falha de rede/timeout; endpoint omitido') from None
                self._pause(self._backoff(attempt))
            except (json.JSONDecodeError,ValueError,UnicodeError):
                raise DataError('JSON inválido') from None

    def _backoff(self, attempt):
        base = min(self.retry_cap, .5 * (2 ** attempt))
        return min(self.retry_cap, base * (.75 + self._random() * .5))

    @staticmethod
    def _retry_after(error):
        headers = error.headers
        raw = headers.get('Retry-After') if headers is not None else None
        if raw is None:
            return None
        try:
            seconds = float(raw)
            return min(86400.0, max(0.0,seconds)) if math.isfinite(seconds) else None
        except (TypeError, ValueError):
            try:
                deadline = parsedate_to_datetime(raw)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                return min(86400.0, max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                return None
