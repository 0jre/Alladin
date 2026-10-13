"""Bounded JSON HTTP transport. Never logs auth headers, URLs or response bodies."""
import json
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
        self.retry_after = retry_after

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DataError('Redirect HTTP recusado')

class HTTP:
    def __init__(self, timeout=15, retries=2, retry_cap=8, sleeper=None, random_value=None):
        if type(retries) is not int or retries < 0 or type(retry_cap) not in (int, float) or retry_cap <= 0:
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
        attempts = self.retries+1 if retry else 1
        for attempt in range(attempts):
            try:
                with urllib.request.build_opener(NoRedirect()).open(request,timeout=self.timeout) as r:
                    raw = r.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise DataError('Resposta excedeu limite de bytes')
                return json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = self._retry_after(e)
                    if not retry or attempt == attempts-1:
                        raise DataError('Fonte de dados temporariamente indisponível',
                                         retry_after=retry_after) from None
                    if retry_after is not None and retry_after > self.retry_cap:
                        raise DataError('Fonte de dados temporariamente indisponível',
                                         retry_after=retry_after) from None
                    delay = (retry_after + self._random() * .25 if retry_after is not None
                             else self._backoff(attempt))
                    self._sleep(delay)
                    continue
                if e.code not in {500,502,503,504}:
                    raise DataError(f'HTTP {e.code}; conteúdo omitido') from None
                if attempt == attempts-1:
                    raise DataError('Fonte de dados temporariamente indisponível') from None
                self._sleep(self._backoff(attempt))
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == attempts-1:
                    raise DataError('Falha de rede/timeout; endpoint omitido') from None
                self._sleep(self._backoff(attempt))
            except (json.JSONDecodeError,ValueError):
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
            return min(86400.0, max(0.0, float(raw)))
        except (TypeError, ValueError):
            try:
                deadline = parsedate_to_datetime(raw)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                return min(86400.0, max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                return None
