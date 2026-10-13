"""Contratos de ferramenta para chats com execução ou computador sandbox.

Os textos das mesas são do Alladin. As categorias seguem a organização pública de
https://github.com/devfinprojects/awesome-claude-finance-prompts sem copiar os prompts.
Cada mesa lê o mercado pelas ferramentas e só opera pela Coinbase.
"""

DESKS = (
    {
        'id': 'equity',
        'title': 'Mesa de pesquisa',
        'task': 'Leia market_radar e market_prices. Cite fonte, preço e horário implícito da resposta. Não invente cotação.',
    },
    {
        'id': 'macro',
        'title': 'Mesa de risco macro',
        'task': 'Use o rastreador e a dispersão entre fontes. Dispersão alta vira abstenção, não uma ordem.',
    },
    {
        'id': 'quant',
        'title': 'Mesa quantitativa',
        'task': 'Sinais impulso, firme, neutro, fraco e queda são rótulos. Eles não autorizam notional.',
    },
    {
        'id': 'portfolio',
        'title': 'Mesa de carteira',
        'task': 'Use a tabela de classificação. O tamanho continua no risco do Alladin.',
    },
    {
        'id': 'alpha',
        'title': 'Radar alpha',
        'task': 'Alpha é ativo visto em duas ou mais fontes com variação firme. A lista não envia ordem.',
    },
    {
        'id': 'copy',
        'title': 'Copy trading observado',
        'task': 'Candidatos públicos não são contas da Binance ou da OKX. Se houver operação, o caminho é coinbase_preview e, só com live_arm, coinbase_order.',
    },
    {
        'id': 'credit',
        'title': 'Mesa de crédito',
        'task': 'Descreva liquidez e volume informados. Não transforme isso em alavancagem.',
    },
    {
        'id': 'risk',
        'title': 'Mesa de risco',
        'task': 'Se a fonte falhar ou o sinal for queda com posição aberta, proponha halt. Não reenvie ordem desconhecida.',
    },
)

PLATFORMS = ('cursor', 'chatgpt', 'chatgpt_work', 'claude', 'claude_work', 'sandbox', 'mcp')

COMMANDS = [
    'ingest', 'analyze', 'evaluate', 'halt', 'finalize', 'universe', 'admit', 'watch', 'unwatch',
    'coinbase_products', 'coinbase_candles', 'coinbase_quote', 'coinbase_preview', 'coinbase_order',
    'coinbase_connect', 'coinbase_connection', 'market_radar', 'market_prices', 'desks', 'platforms',
]


def desks(desk=None):
    if desk is None:
        return {'desks': list(DESKS), 'execution': 'coinbase', 'source_prompts': 'categorias públicas; texto próprio do Alladin'}
    found = [item for item in DESKS if item['id'] == desk]
    if not found:
        raise ValueError('Mesa desconhecida')
    return found[0]


def _parameters():
    return {
        'type': 'object',
        'properties': {
            'command': {'type': 'string', 'enum': COMMANDS},
            'args': {'type': 'object'},
            'idempotency_key': {'type': 'string'},
        },
        'required': ['command', 'args', 'idempotency_key'],
        'additionalProperties': False,
    }


def platforms(name=None):
    if name is not None and name not in PLATFORMS:
        raise ValueError('Plataforma desconhecida')
    tool = {
        'name': 'alladin_command',
        'description': 'Envia um comando ao Alladin em 127.0.0.1. Visão de mercado é leitura. Ordem só na Coinbase, com live_arm. Se a resposta tiver type=action_request, mostre o URL Connect account e não troque o code no sandbox.',
        'parameters': _parameters(),
    }
    catalog = {
        'chatgpt': {'type': 'openai_tools', 'tools': [{'type': 'function', **tool, 'strict': False}]},
        'chatgpt_work': {'type': 'openai_tools', 'tools': [{'type': 'function', **tool, 'strict': False}]},
        'claude': {'type': 'anthropic_tools', 'tools': [{
            'name': tool['name'], 'description': tool['description'], 'input_schema': tool['parameters']}]},
        'claude_work': {'type': 'anthropic_tools', 'tools': [{
            'name': tool['name'], 'description': tool['description'], 'input_schema': tool['parameters']}]},
        'cursor': {'type': 'cursor_tools', 'tools': [tool]},
        'mcp': {
            'type': 'mcp_stdio',
            'command': 'python -m alladin mcp',
            'tools': [tool],
        },
        'sandbox': {
            'type': 'computer_sandbox',
            'rules': [
                'Pode chamar o HTTP local do Alladin.',
                'Não imprima JWT, access token, client secret nem code OAuth.',
                'Quando receber action_request, mostre o link Connect account para a pessoa.',
                'Não navegue até login.coinbase.com/oauth2/token.',
            ],
            'tools': [tool],
        },
    }
    if name is None:
        return {'platforms': catalog, 'desks': [item['id'] for item in DESKS]}
    return catalog[name]
