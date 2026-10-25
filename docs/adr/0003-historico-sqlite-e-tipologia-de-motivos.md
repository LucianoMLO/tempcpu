# ADR 0003 — Histórico em SQLite e tipologia dos motivos

**Data:** 2026-10-25 · **Status:** aceita

## Contexto
Pedido: um registro por minuto com maior, menor, média e desvio padrão de cada variável, mais o motivo do aquecimento; uma classificação dos motivos para entender quais variáveis se relacionam com a temperatura; resumos por hora, dia, semana e mês; e um botão com a linha do tempo.

## Decisão
**Armazenamento.** SQLite em `%LOCALAPPDATA%\TempCPU\historico.db`, fora da pasta do app e de qualquer pacote distribuído. Tabelas:
- `minuto`: uma linha por minuto (chave = início do minuto, epoch UTC). Por variável: `_min`, `_max`, `_med`, `_dp` (desvio padrão populacional) e `_n` (amostras). Mais zona, fonte, plano de energia, estado máximo do processador, programa principal e `motivo_principal`.
- `minuto_motivo`: um registro por minuto e motivo (formato longo, pronto para análise).
- `agregado`: hora, dia, semana e mês, com as mesmas colunas, minutos por zona, motivos e programas (JSON) e o texto de resumo.

**Variáveis:** temperatura da CPU, GPU e SoC, uso da CPU, frequência, rotação da ventoinha, bateria e fração do tempo na tomada.

**Coleta.** As leituras de 2 s entram num acumulador em memória (método de Welford) e viram um registro quando o minuto vira ou ao sair do app. Pausar o monitoramento só interrompe as amostras; o minuto em curso fecha normalmente quando a coleta volta. Leitura ACPI parada não entra nas estatísticas: conta em `descartadas`. Variáveis lidas com menos frequência (uso da CPU a cada 4 ou 30 s, ventoinha a cada 10 s) têm seu próprio `_n`.

**Agregação.** Períodos maiores são calculados a partir dos menores com média ponderada por `n` e desvio padrão agregado (`var = Σ n·(dp² + med²)/N − med²`), nunca "média das médias". Hora vem dos minutos, dia das horas, semana e mês dos dias; tudo é recalculado de forma idempotente a cada minuto gravado. Dias, semanas e meses seguem a hora local (semana começa na segunda).

**Retenção.** Minutos por 365 dias (`RETENCAO_DIAS`), apagados no máximo uma vez por dia. Os resumos por hora, dia, semana e mês ficam para sempre (cerca de 5 MB por ano). Medido em dados sintéticos: ~0,30 KB por minuto, ~150 MB por ano, e 3 ms por gravação.

**Tipologia (`motivos.py`).** Lista fechada com 11 códigos em 7 categorias:

| Categoria | Motivos |
|---|---|
| carga | `processo_pesado`, `cpu_carga_alta` |
| refrigeracao | `refrigeracao_suspeita`, `ventoinha_parada`, `ventoinha_alta` |
| configuracao | `turbo_liberado`, `plano_alto_desempenho` |
| energia | `carregando_bateria` |
| sensor | `leitura_parada` |
| limite | `limite_firmware` |
| indefinida | `sem_causa_evidente` |

Cada diagnóstico já devolve os códigos junto com o texto (`Item.motivo`). O `motivo_principal` do minuto é o mais frequente entre as causas de maior prioridade de cada coleta; a categoria dele vai em `categoria_motivo`. Códigos nunca são renomeados nem reaproveitados.

**Privacidade.** O nome do programa que mais consome CPU é guardado só se `SALVAR_PROGRAMAS=sim` (padrão local). Na versão pública o padrão deve ser `nao` (fase 1 do lançamento). O banco nunca vai no pacote.

**Barra de tarefas.** O botão do app usa o ícone da janela, trocado a cada atualização pelo mesmo número e cor da bandeja; `AppUserModelID` próprio separa o botão do agrupamento do Python. Fechar (X) minimiza em vez de ocultar, para o botão ficar sempre na barra; o app inicia minimizado. O ícone (barra e bandeja) é redesenhado a cada 60 s com o valor daquele instante, ou de imediato quando a faixa de cor ou o estado mudam, porque cada redesenho custa ~10 ms. Na barra o estilo é "suave" (fundo pastel, número na cor da faixa, tira colorida na base); na bandeja continua o estilo forte, que se lê melhor em 16 px.

## Consequências
- Com a janela minimizada o diagnóstico passa a rodar a cada 30 s (`DIAGNOSTICO_OCULTO_S`). Em regime estável: ~13–19 MB e ~0,3% de um núcleo (medido a cada 5 s por 150 s); nos primeiros 2 minutos após abrir o custo é maior (importações e primeira coleta).
- A cobertura de `uso_cpu` e dos motivos tem resolução de 30 s com a janela minimizada.
- Se o app for encerrado e reiniciado dentro do mesmo minuto, o segundo registro substitui o primeiro (perda de até um minuto, só nessa situação).
- Gravar o minuto ao pausar ou ao abrir o histórico foi descartado de propósito: reabria o mesmo minuto e o registro seguinte sobrescrevia o anterior.
- Mudar o esquema exige nova versão em `PRAGMA user_version` e migração (versão atual: 1).
