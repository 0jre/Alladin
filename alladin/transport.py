"""Bounded JSON HTTP transport. Never logs auth headers, URLs or response bodies."""
import json
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit, urlencode

class DataError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DataError('Redirect HTTP recusado')

class HTTP:
    def __init__(self, timeout=15, retries=2):
        self.timeout, self.retries = timeout, retries
    def json(self,url,payload=None,headers=None,retry=True):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise DataError('Endpoint HTTPS obrigatório, sem credenciais na URL')
        body = None if payload is None else json.dumps(payload,allow_nan=False).encode()
        request = urllib.request.Request(url, data=body,
                    headers={'Content-Type':'application/json','User-Agent':'Alladin/0.5',**(headers or {})})
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
            'User-Agent': 'Alladin/0.5', **(headers or {})})
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
                if e.code not in {429,500,502,503,504} or attempt == attempts-1:
                    raise DataError(f'HTTP {e.code}; conteúdo omitido') from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == attempts-1:
                    raise DataError('Falha de rede/timeout; endpoint omitido') from None
            except (json.JSONDecodeError,ValueError):
                raise DataError('JSON inválido') from None
            time.sleep(min(2**attempt,4))
