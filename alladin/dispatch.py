"""One Coinbase SOL-USDC paper command path shared by HTTP and MCP."""


def execute(service, name, args, key):
    if not isinstance(name, str) or not isinstance(args, dict):
        raise ValueError('Invalid command')
    return service.command(name, args, key)
