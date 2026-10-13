# Arquitetura do backend

Fluxo de cada barra fechada:

1. Endpoint autentica, valida JSON e exige chave de idempotência.
2. SQLite inicia transação, verifica chave, restaura estado e valida ordem temporal.
3. Executa proposta anterior na abertura atual, revalidando com evidências anteriores.
4. Marca posições, aplica funding/saídas e verifica circuit breakers.
5. Calcula features com barras fechadas e reúne os agentes.
6. Controle de risco independente dimensiona ou recusa a proposta.
7. Persiste decisão, proposta pendente, carteira e resposta idempotente na mesma transação.

GETs usam leitura do estado confirmado. Comandos são serializados pelo lock do servidor e transação SQLite. Falha antes do commit deixa a sessão anterior intacta. Uma chamada ao modelo pode ter sido cobrada mesmo que haja rollback; a API externa não participa da transação SQLite. Por isso o cliente LLM não faz retries automáticos.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| models.py | Contratos, universo Solana, limites e validação numérica |
| providers.py | RPC, pools Solana, cotação e leitura de wallet pública |
| transport.py | HTTPS, timeout, limites de resposta, erros sem segredos |
| features.py | Indicadores e estatísticas causais |
| strategies.py | Candidatos quantitativos por regime |
| agents.py | Conselho rules/LLM e validação estruturada |
| risk.py | Gates, dimensionamento e circuit breakers |
| broker.py | Contabilidade e execução paper |
| engine.py | Máquina de estados persistida |
| storage.py | Transações, auditoria e idempotência |
| server.py | HTTP JSON autenticado, sem frontend |
| client.py | Cliente para agentes externos |
| research.py | Replay, fixtures e exportação |
| validation.py | Avaliação cronológica e estresse de custos |

## Operação

Sem banco compartilhado entre vários workers. Uma instância recebe um feed uniforme de SOL/USDC, com snapshot de cada instante. O loop autônomo é acionado por ingest; manter o serviço ativo não cria barras novas. Collect só retorna um snapshot, não aciona trade.

Use um supervisor para manter o processo e um adaptador de feed validado para enviar ingest. Falhas de feed devem bloquear entradas; o sistema recusa lacunas. Se não houver novo preço, não é possível simular uma saída fresca. Os agentes externos consomem contract/status e chamam commands pelo BackendClient.

Não há frontend, painel, código JavaScript, carteira embutida, leitura de seed ou execução arbitrária de comandos. Dockerfile é uma opção de empacotamento; a imagem não foi construída neste ambiente. O artefato fornecido roda diretamente com Python.
