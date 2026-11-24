# Rota Vital — Função Serverless (`POST /guias`)

Atividade Individual 1 (**Serverless**) · Infraestrutura de Software · ADS · CESAR School · 2026.2

Este repositório é **independente** do repositório principal do [Rotavital](https://github.com/viictorpaes/Rotavital) e implementa a função serverless de geração de guia de transporte para uma requisição hospitalar de hemocomponentes, observando na prática o ciclo de vida do ambiente de execução (*cold start* e reaproveitamento), a ausência de estado garantido entre chamadas e o limite de tempo de execução (*timeout*).

---

## Caminho escolhido

**Caminho A (recomendado): AWS SAM CLI local**

- **Sistema operacional**: Windows 11 (com Docker Desktop + WSL2)
- **Runtime / Linguagem**: Python `3.12` (empacotamento `Zip`)
- **Ferramentas usadas**:
  - Docker Desktop (`29.9.3`)
  - AWS SAM CLI (`1.174.0`)
  - Python `3.12.10`

---

## Estrutura do projeto

```text
rotavital-serverless/
├── events/
│   ├── event.json
│   └── pedido.json                      # Evento API Gateway Proxy (POST /guias)
├── evidencias/
│   ├── 01-passo3-sam-local-invoke.png
│   ├── 02-passo4-sem-warm-containers.png
│   ├── 03-passo4-warm-lazy-e-passo5-timeout3.png
│   ├── 04-passo5-timeout10-sucesso.png
│   ├── passo3_invoke.txt
│   ├── passo4_sem_warm.txt
│   ├── passo4_com_warm_e_passo5_timeout3.txt
│   └── passo5_timeout10.txt
├── hello_world/
│   ├── __init__.py
│   ├── app.py                           # Handler lambda_handler (POST /guias)
│   └── requirements.txt
├── tests/
│   └── unit/
│       └── test_handler.py              # Testes unitários com unittest
├── samconfig.toml
├── template.yaml                        # Definição SAM (POST /guias, Timeout: 10)
└── README.md
```

> **Nota sobre compatibilidade no SAM CLI 1.174.0**: o comando `sam local generate-event apigateway aws-proxy` gera eventos com `"isBase64Encoded": true` e o campo `body` codificado em Base64. Por isso, o `hello_world/app.py` decodifica o `body` quando `isBase64Encoded` é verdadeiro, funcionando tanto via `sam local invoke` (evento Base64) quanto via `sam local start-api` + `curl` (JSON em texto puro).

---

## Como rodar (reproduzível)

### 1. Pré-requisitos

- Docker Desktop em execução;
- AWS SAM CLI (`sam --version`);
- Python 3.12 (`py -3.12 --version` ou `python --version`).

*(No Windows, os exemplos com aspas simples abaixo funcionam diretamente no Git Bash ou WSL; no PowerShell, ajuste o escape das aspas do JSON).*

### 2. Build e testes unitários

```bash
sam build
python -m unittest discover -s tests/unit -v
```

### 3. Invocação por evento (Passo 3)

```bash
sam local generate-event apigateway aws-proxy --method POST --path guias \
  --body '{"requisicaoId":"R-001","hospital":"H-Recife","bolsas":["O-NEG-0142"]}' \
  > events/pedido.json

sam build
sam local invoke -e events/pedido.json
sam local invoke -e events/pedido.json
```

### 4. Acionamento por HTTP (Passo 4)

Em um terminal, suba a API local (primeiro sem `--warm-containers`, depois com `--warm-containers LAZY`):

```bash
sam local start-api
# ou:
sam local start-api --warm-containers LAZY
```

Em outro terminal, dispare três requisições seguidas:

```bash
curl -X POST http://127.0.0.1:3000/guias -H "Content-Type: application/json" \
  -d '{"requisicaoId":"R-002","hospital":"H-Caruaru"}'
```

### 5. Teste de limite de tempo (Passo 5)

Com `Timeout: 3` em `Globals.Function.Timeout` no `template.yaml`:

```bash
curl -i -X POST http://127.0.0.1:3000/guias -H "Content-Type: application/json" \
  -d '{"requisicaoId":"R-003","demorar":true}'
```

O endpoint retorna `502 Bad Gateway` (`Task timed out after 3 seconds`). Em seguida, alterando `Timeout: 10` no `template.yaml` (estado atual do repositório), rodando `sam build` e repetindo a requisição, a função retorna `201 Created` após ~5 segundos.

---

## Resumo dos experimentos executados

| Experimento | Tempo total (cliente) | Duração Lambda (REPORT) | `invocacaoNesteAmbiente` | Resultado | Evidência |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `sam local invoke` (1ª vez) | `73,573 s` *(inclui pull da imagem)* | `109,08 ms` (Init: `0,04 ms`) | `1` | `201` (`G-R-001`) | [passo3_invoke.txt](./evidencias/passo3_invoke.txt) |
| `sam local invoke` (2ª vez) | `12,977 s` *(novo container)* | `88,73 ms` (Init: `0,05 ms`) | `1` | `201` (`G-R-001`) | [passo3_invoke.txt](./evidencias/passo3_invoke.txt) |
| `start-api` padrão (3 chamadas) | `1,238 s` / `1,112 s` / `1,079 s` | `86,04 ms` / `3,53 ms` / `1,58 ms` | `1` → `2` → `3` | `201` (`G-R-002`) | [passo4_sem_warm.txt](./evidencias/passo4_sem_warm.txt) |
| `start-api --warm-containers LAZY` (3 chamadas) | `4,285 s` / `1,122 s` / `1,098 s` | `104,87 ms` / `1,47 ms` / `1,21 ms` | `1` → `2` → `3` | `201` (`G-R-002`) | [passo4_com_warm_e_passo5_timeout3.txt](./evidencias/passo4_com_warm_e_passo5_timeout3.txt) |
| `demorar: true` com `Timeout: 3` | `4,209 s` | `3000,00 ms` *(timeout)* | — | `502 Bad Gateway` | [passo4_com_warm_e_passo5_timeout3.txt](./evidencias/passo4_com_warm_e_passo5_timeout3.txt) |
| `demorar: true` com `Timeout: 10` | `10,152 s` *(inclui cold start LAZY)* | `5078,63 ms` | `1` | `201` (`G-R-003`) | [passo5_timeout10.txt](./evidencias/passo5_timeout10.txt) |

---

## Perguntas e respostas

### 1. Por que a primeira invocação demorou mais que a segunda? O que acontece na fase de Init?

A primeira invocação é mais lenta porque ocorre o **cold start**: o ambiente de execução ainda não existe pronto. Nos testes locais:
- Com `sam local invoke`, a 1ª execução levou `73,573 s` no total porque o Docker precisou baixar/preparar a imagem `public.ecr.aws/lambda/python:3.12-rapid-x86_64` e subir o container, enquanto a 2ª caiu para `12,977 s` com a imagem já em cache (`Duration` interna da função: `109,08 ms` na 1ª contra `88,73 ms` na 2ª).
- Com `sam local start-api --warm-containers LAZY`, a 1ª chamada HTTP levou `4,285 s` (`Duration: 104,87 ms`) para criar o container sob demanda, enquanto a 2ª (`1,122 s`, `Duration: 1,47 ms`) e a 3ª (`1,098 s`, `Duration: 1,21 ms`) apenas reutilizaram o container já aquecido (*warm start*).

Na **fase de Init**, o runtime da AWS Lambda cria o container/microVM isolado, inicializa o interpretador Python 3.12, carrega os arquivos da função e executa todo o código de nível de módulo que está **fora** do `lambda_handler` (no nosso caso: os `import`s e a inicialização `contador = 0`). Só depois dessa etapa concluída começa a fase de **Invoke**, na qual `lambda_handler(event, context)` é chamado.

### 2. O que o campo `invocacaoNesteAmbiente` mostrou com e sem `--warm-containers`? O que isso diz sobre guardar estado numa variável global da função?

- No `sam local invoke`, cada chamada sobe e destrói um container isolado (`SAM_CONTAINER_ID` diferentes: `8cad26...` e `7e1223...`), então `invocacaoNesteAmbiente` retornou `1` nas duas execuções.
- No `sam local start-api --warm-containers LAZY`, o container criado na primeira chamada (`74aab5a...`) permaneceu vivo e foi reaproveitado nas chamadas seguintes, fazendo `invocacaoNesteAmbiente` incrementar na sequência `1`, `2`, `3`.
- **Observação prática da versão `1.174.0` do SAM CLI**: mesmo ao executar `sam local start-api` sem passar `--warm-containers`, o servidor local já inicializou e manteve o container `b949c59...` ativo entre as três chamadas (`1`, `2`, `3`). Em versões/modos sem reaproveitamento de container (ou quando novos containers são criados), o valor volta para `1`.

**O que isso diz sobre estado global**: variáveis globais em memória **não oferecem persistência garantida**. Elas sobrevivem apenas enquanto o mesmo ambiente de execução estiver ativo e for reutilizado. Se houver *cold start*, escalonamento paralelo com múltiplos containers simultâneos, reciclagem do ambiente por inatividade ou falha por *timeout*, o estado em memória é perdido ou fica inconsistente entre instâncias. Qualquer dado que precise persistir (como requisições, reservas de bolsas ou guias emitidas) deve ficar fora da função, em banco de dados, cache distribuído ou fila.

### 3. O que aconteceu com `demorar = true`? Qual é o tempo máximo de uma execução no Lambda, e o que fazer com um trabalho mais longo?

Com `Timeout: 3` em `template.yaml`, o `time.sleep(5)` fez a função exceder o limite configurado: o runtime interrompeu a execução exatamente aos 3 segundos (`Function 'HelloWorldFunction' timed out after 3 seconds`, `Duration: 3000.00 ms`), registrou erro no container e o API Gateway local devolveu `HTTP 502 Bad Gateway` (`{"message":"Internal server error"}`). Depois de alterar `Timeout` para `10` e executar `sam build`, a chamada concluiu normalmente com `HTTP 201 Created` (`Duration: 5078,63 ms`) e retornou a guia `G-R-003`.

- **Tempo máximo de uma execução no AWS Lambda**: **15 minutos (900 segundos)** por invocação (observando que, atrás de um API Gateway REST síncrono, o limite de integração do gateway é menor — 29 segundos por padrão).
- **O que fazer com um trabalho mais longo**: transformar o fluxo em **processamento assíncrono** (a API valida e enfileira a tarefa em SQS/EventBridge retornando `202 Accepted` imediatamente para um worker processar), quebrar o processamento em etapas menores orquestradas (ex.: AWS Step Functions) ou executar tarefas longas em serviços de computação contínua/containers dedicados (ex.: ECS/Fargate ou backend dedicado).

### 4. Com os preços de `us-east-1` da aula (US$ 0,20 por milhão de requisições e US$ 0,0000166667 por GB-s), quanto custa um milhão de execuções desta função com 128 MB e 100 ms? Mostrem a conta.

1. **Custo por requisições**:
   $$\text{Custo}_{\text{req}} = 1\text{ milhão} \times \text{US\$ } 0{,}20 = \text{US\$ } 0{,}20$$

2. **Cálculo de consumo em GB-s**:
   - Memória configurada: $128\text{ MB} = \frac{128}{1024}\text{ GB} = 0{,}125\text{ GB}$
   - Duração por execução: $100\text{ ms} = 0{,}1\text{ s}$
   - GB-s por execução: $0{,}125\text{ GB} \times 0{,}1\text{ s} = 0{,}0125\text{ GB-s}$
   - Total em 1.000.000 de execuções:
     $$1.000.000 \times 0{,}0125\text{ GB-s} = 12.500\text{ GB-s}$$

3. **Custo de computação**:
   $$\text{Custo}_{\text{comp}} = 12.500\text{ GB-s} \times \text{US\$ } 0{,}0000166667/\text{GB-s} = \text{US\$ } 0{,}20833375$$

4. **Custo total (sem aplicar a faixa gratuita)**:
   $$\text{Total} = \text{US\$ } 0{,}20 + \text{US\$ } 0{,}20833375 = \text{US\$ } 0{,}40833375 \approx \mathbf{\text{US\$ } 0{,}41}$$

*(Na faixa sempre gratuita do AWS Lambda — 1 milhão de requisições e 400.000 GB-s por mês — esse volume ficaria totalmente coberto pela cota gratuita).*

### 5. Em que parte do Rota Vital uma função assim faria sentido, e em qual não faria?

Considerando a arquitetura real do [Rotavital](https://github.com/viictorpaes/Rotavital) (API Spring Boot + PostgreSQL/Supabase):

- **Onde faria sentido**: em tarefas **pontuais, rápidas, orientadas a eventos e sem estado em memória**, especialmente com carga intermitente:
  - Emissão assíncrona/sob demanda de **guias e comprovantes de transporte** (`POST /guias`) após o despacho de uma transferência (`TransferenciaController`);
  - **Disparo de notificações e alertas** por evento (e-mail/SMS/push) quando uma bolsa entra em temperatura fora da faixa ou próxima do vencimento (`AlertasDoEstoqueController`), ou quando uma nova campanha de doação é criada para avisar doadores compatíveis (`CampanhaController`).
- **Onde NÃO faria sentido**:
  - No **núcleo transacional de estoque, alocação FEFO e transferências** (`EstoqueService`, `SugestaoDeLoteService`, `TransferenciaService`, que dependem de transações ACID e restrições de concorrência no PostgreSQL como `uq_transferencia_bolsa_ativa`), pois múltiplas instâncias efêmeras de Lambda podem sofrer com *cold start* em operações críticas e abrir conexões em excesso com o banco sem um pool persistente;
  - Em **ingestão contínua de telemetria da cadeia fria ou jobs pesados/longos** que ultrapassem o limite síncrono de API Gateway (29 s) ou o teto do Lambda (15 min), onde um serviço contínuo (container/worker dedicado) é mais adequado.

---

## Evidências

Todos os prints e registros brutos dos comandos executados estão na pasta [`evidencias/`](./evidencias):

- [`01-passo3-sam-local-invoke.png`](./evidencias/01-passo3-sam-local-invoke.png) ([log completo](./evidencias/passo3_invoke.txt))
- [`02-passo4-sem-warm-containers.png`](./evidencias/02-passo4-sem-warm-containers.png) ([log completo](./evidencias/passo4_sem_warm.txt))
- [`03-passo4-warm-lazy-e-passo5-timeout3.png`](./evidencias/03-passo4-warm-lazy-e-passo5-timeout3.png) ([log completo](./evidencias/passo4_com_warm_e_passo5_timeout3.txt))
- [`04-passo5-timeout10-sucesso.png`](./evidencias/04-passo5-timeout10-sucesso.png) ([log completo](./evidencias/passo5_timeout10.txt))

---

## Uso de IA (PO-CESAR-021)

- **Ferramenta**: Antigravity (Google DeepMind) integrada ao ambiente local de desenvolvimento.
- **Finalidade**: apoio na inicialização e adaptação do template AWS SAM (`template.yaml` e `hello_world/app.py`, incluindo o tratamento de `isBase64Encoded` exigido pelo `sam local generate-event` do SAM CLI `1.174.0`), escrita de testes unitários (`tests/unit/test_handler.py`), automação da coleta de evidências e estruturação deste `README.md`.
- **Como foi validado**: todas as etapas do Caminho A foram executadas localmente contra o Docker Desktop e o AWS SAM CLI (`sam validate`, `sam build`, `sam local invoke` duas vezes, `sam local start-api` sem e com `--warm-containers LAZY`, requisições `curl` de sucesso e timeout de 3 s / 10 s), além da execução dos 4 testes unitários (`python -m unittest discover -s tests/unit -v`) e revisão manual de todas as respostas e do cálculo de custo.
