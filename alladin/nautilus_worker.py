"""One approved, isolated native-engine paper execution. Never networked."""
import json
import sys
from .nautilus_engine import execute


def main():
    try:
        raw=sys.stdin.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('Native request too large')
        args=json.loads(raw)
        result=execute(**args)
        response=dict(ok=True,result=result)
    except Exception as exc:
        response=dict(ok=False,error=type(exc).__name__,message=str(exc)[:500])
    print('ALLADIN_NAUTILUS_RESULT '+json.dumps(response,allow_nan=False),flush=True)


if __name__=='__main__':main()
