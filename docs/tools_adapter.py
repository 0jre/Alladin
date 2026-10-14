"""Import these functions into an external agent's tool registry."""
from alladin.client import BackendClient

def alladin_status():
    return BackendClient().status()

def alladin_performance():
    return BackendClient().performance()

def alladin_command(command,args,idempotency_key):
    return BackendClient().command(command,args,idempotency_key)
