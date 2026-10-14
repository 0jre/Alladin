"""Reviewed, versioned finance prompts. Upstream Markdown is never executed."""
import hashlib
import json
from importlib.resources import files
from pathlib import PurePosixPath

from .transport import DataError


class PromptLibrary:
    ROLES = {'market','quality','flow','challenger','manager'}

    def __init__(self,root=None):
        self.root = root if root is not None else files('alladin').joinpath('finance_prompts')
        try:
            raw=self.root.joinpath('catalog.json').read_bytes()
            if len(raw)>64000:
                raise ValueError('Catalog too large')
            catalog=json.loads(raw)
            if not isinstance(catalog.get('version'),str) or set(catalog['roles']) != self.ROLES:
                raise ValueError('Invalid roles/version')
            self._text={}
            total=0
            for name,expected in catalog['files'].items():
                path=PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name or path.suffix!='.md':
                    raise ValueError('Invalid prompt path')
                content=self.root.joinpath(*path.parts).read_bytes()
                total+=len(content)
                if len(content)>16000 or total>64000 or hashlib.sha256(content).hexdigest()!=expected:
                    raise ValueError('Prompt digest/size mismatch')
                self._text[name]=content.decode('utf-8')
            required=[catalog['system'],*catalog['regimes'].values()]
            for role in catalog['roles'].values():
                required.extend([role['file'],*role['skills']])
            if any(name not in self._text for name in required):
                raise ValueError('Unregistered prompt resource')
            self.catalog=catalog
            self.bundle_hash=hashlib.sha256(json.dumps(catalog,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        except (OSError,ValueError,TypeError,KeyError,UnicodeError,AttributeError):
            raise DataError('Prompt package is missing, invalid or modified') from None

    def render(self,role,regime=None):
        if role not in self.ROLES:
            raise DataError('Unknown agent role')
        item=self.catalog['roles'][role]
        names=[self.catalog['system'],item['file'],*item['skills']]
        if role in {'market','challenger','manager'} and regime in self.catalog['regimes']:
            names.append(self.catalog['regimes'][regime])
        return '\n\n'.join(self._text[name] for name in dict.fromkeys(names))

    def metadata(self,regime=None):
        return dict(version=self.catalog['version'],bundle_sha256=self.bundle_hash,
                    upstream_commit=self.catalog['upstream_commit'],
                    roles={role:hashlib.sha256(self.render(role,regime).encode()).hexdigest()
                           for role in sorted(self.ROLES)})
