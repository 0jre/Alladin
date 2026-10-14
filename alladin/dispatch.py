"""One Solana-only command path shared by HTTP and MCP."""


def execute(service, name, args, key):
    if not isinstance(name, str) or not isinstance(args, dict):
        raise ValueError('Comando inválido')
    return service.command(name, args, key)
