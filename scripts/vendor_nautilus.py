"""Reproduce the complete pinned source checkout, then remove only its .git.

The compiled runtime release is installed separately with pip install '.[engine]'.
No upstream setup/build script is executed by this source materializer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def materialize(root):
    vendor=root/'vendor'
    lock=json.loads((vendor/'nautilus_trader.lock.json').read_text())
    target=vendor/'nautilus_trader'
    if target.exists():
        raise ValueError('Source already exists; it was not overwritten. Keep or move it explicitly before rebuilding.')
    with tempfile.TemporaryDirectory(prefix='nautilus-source-',dir=vendor) as tmp:
        checkout=Path(tmp)/'source'
        subprocess.run(['git','clone','--depth','1','--branch',lock['tag'],lock['repository'],str(checkout)],check=True,timeout=300)
        commit=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
        if commit!=lock['commit']:
            raise ValueError('Upstream tag does not match pinned commit; source rejected')
        tracked=subprocess.check_output(['git','-C',str(checkout),'ls-files','-z']).split(b'\0')
        files=[]
        for raw in tracked:
            if not raw:continue
            name=raw.decode('utf-8')
            path=checkout/name
            content=str(path.readlink()).encode() if path.is_symlink() else path.read_bytes()
            files.append(dict(path=name,sha256=hashlib.sha256(content).hexdigest(),symlink=path.is_symlink()))
        # This path belongs exclusively to the temporary clone above.
        shutil.rmtree(checkout/'.git')
        checkout.rename(target)
        (vendor/'nautilus_trader.provenance.json').write_text(json.dumps(dict(**lock,files=files),indent=2)+'\n')
    return dict(path=str(target),commit=commit,nested_git=False,files=len(files))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(materialize(Path(__file__).resolve().parents[1]),indent=2))
