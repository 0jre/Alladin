# Protocolo para agentes da sessão

Alladin é um servidor de ferramentas Python. ChatGPT Work, Claude, Grok, Codex,
Claude CLI ou um processo de automação fornece o raciocínio usando os recursos da
própria sessão. Não há inferência interna, seleção de modelo ou chave de provedor.
Uma sessão precisa ter acesso efetivo ao transporte; este projeto não instala
conectores automaticamente nessas plataformas.

## Início via MCP stdio, sem credenciais

```bash
python -m alladin --config config.json --db data/external.sqlite mcp
```

Configure esse comando como servidor MCP no consumidor compatível. O transporte
existente usa frames Content-Length; confirme compatibilidade no cliente. Em
plataformas que só aceitam MCP remoto, integre o HTTP autenticado por uma ponte
compatível. O token HTTP protege o backend e não pertence a um provedor de IA.

## Ciclo

Chame `paper_tick` com chave idempotente nova por ciclo, até aquecer e processar
uma barra. Chame `prepare_decision` sem argumentos. A resposta contém `task`:

| Campo | Finalidade |
|---|---|
| `id`, `protocol` | Identidade da tarefa e versão do protocolo |
| `context_sha256`, `evidence_sha256` | Vínculo com autoridade material da conta e evidências congeladas |
| `created_at`, `expires_at`, `status`, `binding_version` | Prazo de `min(300, 2 × timeframe)` segundos e consumo único; vínculo versão 2 |
| `evidence` | Indicadores, snapshot, carteira, candidatos, custos, riscos e lacunas |
| `instructions` | Prompts revisados dos cinco papéis |
| `report_schema`, `decision_schema` | Contratos JSON exatos de saída |
| `stages` | Mercado/qualidade/fluxo, contestador, gestor |

O coordenador fornece a cada um dos três analistas apenas o envelope e seu prompt.
Depois entrega os três relatórios ao contestador e os quatro ao gestor. Pode usar
subagentes da sessão quando disponíveis. Sem subagentes, declare que os pareceres
foram produzidos pela mesma sessão; não invente independência. O backend valida o
conteúdo, mas a identidade declarada não autentica a plataforma ou o agente.

Envie em `POST /v1/commands` com Idempotency-Key ou em `tools/call` no MCP:

```json
{
  "command": "submit_decision",
  "args": {
    "task_id": "copiar task.id",
    "evidence_sha256": "copiar task.evidence_sha256",
    "session_id": "identificador opaco da sessão, sem segredos",
    "reports": {
      "market": {},
      "quality": {},
      "flow": {},
      "challenger": {}
    },
    "decision": {}
  }
}
```

Os objetos vazios acima são marcadores de documentação: preencha todos os campos
dos schemas retornados. Valores extras são recusados; os agentes não escolhem o
tamanho. Cite apenas chaves existentes em `evidence.evidence_registry`. Não trate
score/confiança como probabilidade de ganho. Plano inválido é consumido como HOLD.

Em paper-live, a preparação atualiza o snapshot e a submissão coleta outro antes
da transação. O plano continua vinculado às evidências originais. Se o preço
ultrapassar `max_entry_gap_fraction`, a cotação estiver velha, uma nova barra tiver
fechado, o estado tiver mudado ou o prazo tiver vencido, prepare novamente. Não
altere timestamps para tornar dados antigos aparentemente novos. Replay conserva
a decisão N para abertura N+1, com revalidação existente.

Repetir a mesma submissão com a mesma chave devolve a resposta persistida sem
nova coleta ou fill. Usar outra chave para a mesma tarefa consumida é recusado.
Preparar novamente substitui a tarefa anterior. Halt, mudança de saldo, novo ciclo
ou outro estado material invalidam o vínculo anterior. Nunca aguarde o raciocínio
externo com uma transação de escrita aberta.

O worker sem consumidor continua coletando e gerenciando stops/breakers; não cria
análises automaticamente. Automações precisam executar o ciclo de chamadas na
própria plataforma. O modo `rules` só é ativado explicitamente para pesquisa.

## Continuidade

Bancos persistidos preservam seu modo e saldo. Reabra bancos `rules` com
`--agents rules`; não mude o modo editando o SQLite. A migração de um banco antigo
com inferência embutida exige transferência auditada para uma sessão externa,
conservando custos, perdas e limites consumidos; não há migração automática.
Todas as operações continuam spot paper, exclusivamente Solana.

Após `warmed_up`, já é permitido chamar `prepare_decision`: o comando coleta o
primeiro snapshot verificado antes de verificar a disponibilidade do contexto.
`waiting_for_closed_bar` também não impede essa preparação. Com dados válidos, a preparação entrega uma tarefa mesmo sem candidato das regras
internas. Candidatos são sugestões; a sessão pode propor uma estratégia própria
com evidências, consenso e aprovação final de risco. Falhas de segurança continuam
retornando `abstained`. Comandos de coleta compartilham um prazo total de 45 segundos; consumidores
podem repetir falhas transitórias com a mesma chave, sem usar dados fabricados.

A partir de `external-session-v2`, os pareceres são `market`, `quality`, `flow` e `challenger`. O papel `onchain` não é aceito. Use nova preparação para tarefas do protocolo anterior; saldos e histórico não são zerados. A única fonte de dados é a Coinbase; não existe RPC ou verificação blockchain.

## Coordenação com worker ativo

`prepare_decision` retorna a mesma tarefa enquanto ela permanecer válida, mesmo
com novas chaves idempotentes e chamadas concorrentes. `reused=true` não renova o
prazo nem o instante das observações. O worker continua atualizando candles, marks,
stops e circuit breakers. Essas observações não substituem uma análise em curso.
Mudanças de caixa, identidade/tamanho de posições, fills, permissões, modo,
configuração ou bloqueio de risco invalidam a autorização anterior.

A decisão é verificada contra o envelope original, com hash reproduzido. Uma nova
barra não torna automaticamente inválida uma tese ainda dentro do prazo. Para
LONG, o backend coleta indicadores fechados atuais e uma cotação Coinbase de no
máximo 30 segundos, limita o desvio em relação ao preço analisado e revalida todo o
risco contra a conta atual. `analysis_as_of`, `risk_bar_closed_at` e
`execution_snapshot` distinguem esses instantes; não representam análises novas
dos agentes. O consumidor continua responsável pela validade da tese.

HOLD é registrado sem coletar preço nem aplicar marks. CLOSE usa somente um livro
Coinbase atual, dispensando candles, volume e trades; a restrição de desvio de
preço para entrada não bloqueia a redução de exposição. A cotação de saída não
contém volume/fluxo coletados e não autoriza uma compra posterior. A preparação
seguinte coleta o contexto completo quando necessário.

`submit_decision` mantém `result=submitted` e informa `outcome` (`opened`, `closed`,
`abstained`, `risk_rejected` ou `scheduled` no replay). Se o preço de entrada sair
do contexto, retorna `result=reprepare_required`, `outcome=context_rejected`,
invalida a tarefa e não gera fill. Nesse caso prepare novamente, reanalise e use
nova chave para o novo plano. Não repita relatórios antigos com hashes novos.
Falhas transitórias de coleta não consomem tarefa nem chave: repita o mesmo pedido
com a mesma chave enquanto a tarefa estiver válida. Tarefas anteriores ao vínculo
versão 2 exigem nova preparação; carteira e histórico permanecem intactos.

Uma sessão pode validar deliberadamente OPEN/CLOSE pelo protocolo externo usando
`strategy=execution_validation`. A finalidade deve ficar explícita nos relatórios;
o plano continua passando por todos os controles. Entradas são marcadas como
`validation_only`; esses roundtrips ficam separados das estatísticas de estratégia,
mas custos, PnL, perdas diárias e drawdown continuam afetando a conta. Essa checagem
não é evidência de alpha. `demo-live` sozinho continua sendo um coletor de tarefas,
e não um consumidor inteligente que envia planos.
