"""External session protocol. No provider SDK, credentials or inference requests."""
import hashlib
from .storage import canonical


def context_hash(state):
    return hashlib.sha256(canonical({k:v for k,v in state.items() if k!='external_task'}).encode()).hexdigest()
