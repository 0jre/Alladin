"""Minimal client for agents calling backend endpoints; no shell execution."""
import json
import os
import urllib.request
from urllib.parse import urlsplit

class BackendClient:
    def __init__(self,url='http://127.0.0.1:8080',token=None):
        u = urlsplit(url)
        if u.scheme != 'https' and not (u.scheme == 'http' and u.hostname in {'127.0.0.1','localhost'}):
            raise ValueError('HTTP somente loopback; remoto requer HTTPS')
        if u.username or u.password or u.query or u.fragment:
            raise ValueError('URL inválida')
        self.url,self.token = url.rstrip('/'),token or os.environ.get('LAB_API_TOKEN')
        if not self.token:
            raise ValueError('LAB_API_TOKEN ausente')
    def _request(self,path,payload=None,key=None):
        headers = {'Authorization':'Bearer '+self.token,'Content-Type':'application/json'}
        if key:
            headers['Idempotency-Key'] = key
        data = None if payload is None else json.dumps(payload,allow_nan=False).encode()
        request = urllib.request.Request(self.url+path,data=data,headers=headers)
        # No retries: caller retries with same idempotency key after a timeout.
        with urllib.request.urlopen(request,timeout=180) as response:
            return json.load(response)
    def status(self):
        return self._request('/v1/status')
    def performance(self):
        return self._request('/v1/performance')
    def command(self,name,args,key):
        response=self._request('/v1/commands',{'command':name,'args':args},key)
        if not isinstance(response,dict) or set(response)!={'result'} or not isinstance(response['result'],dict):
            raise ValueError('Resposta de comando do backend inválida')
        return response['result']
