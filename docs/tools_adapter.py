"""Import these two functions into an external agent's tool registry."""
from alladin.client import BackendClient

def solana_backend_status():
    return BackendClient().status()

def solana_backend_command(command,args,idempotency_key):
    return BackendClient().command(command,args,idempotency_key)
