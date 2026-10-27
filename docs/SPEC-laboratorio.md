# Laboratório — especificação (módulo opcional do TempCPU)

**Status:** aprovada em 2026-10-25 · F1+F2 (dados e núcleo de ML) implementadas e calibradas em 2026-10-25 · **Versão alvo:** v1 (3 lições)

## Objetivo e usuário
- **Objetivo:** ensinar as ideias básicas de aprendizado de máquina (machine learning) usando o histórico do próprio computador, em uma janela com explicações em português, gráficos e experimentos que o usuário mexe.
- **Usuário:** qualquer pessoa que usa o TempCPU, **sem pressupor conhecimento nenhum** (decisão de 2026-10-25). Todo termo técnico é explicado na tela na primeira vez em que aparece e no Glossário; o nome em inglês vem entre parênteses.
- **Não é** uma função do monitor: o app continua igual sem o Laboratório.

## Princípios (valem para tudo abaixo)
1. **Opcional e separado.** O Laboratório é outro programa, aberto por um botão. O app **nunca** importa `scikit-learn` nem `numpy`: o app continua com ~13–19 MB (o Laboratório usa ~107 MB só ao importar a biblioteca, ~240 MB em disco).
2. **Só lê.** Abre `historico.db` somente para leitura. Nada é gravado no banco, nada é enviado pela rede.
3. **Verdade antes de graça.** Toda tela mostra de onde vêm os dados. Dado sintético tem faixa fixa "DADOS SINTÉTICOS (sintéticos)". Resultado fraco é mostrado como fraco.
4. **Reprodutível.** Todo sorteio usa uma semente visível; a mesma semente dá o mesmo resultado.
5. **Sem jargão solto.** Se um termo não está no Glossário, não aparece na tela (verificado por teste).

## Jornada principal
1. No app, o usuário clica em **Laboratório**.
2. Se o ambiente ainda não existe, vê quanto espaço será usado (~240 MB) e confirma **Preparar Laboratório**; sem confirmar, nada é instalado.
3. O Laboratório abre na **Tela inicial**: lista de lições, fonte de dados e quantos minutos reais existem.
4. O usuário escolhe uma lição. Se os dados reais forem poucos, a tela explica o porquê e oferece **Dados sintéticos**.
5. Percorre a lição por passos (explicação → experimento → resultado → o que aprendeu → 3 perguntas de fixação).
6. A lição fica marcada como concluída. Pode voltar, mudar a fonte de dados e repetir.

## Áreas (telas)
| Área | O que é |
|---|---|
| Início | Lições, fonte de dados (Meu histórico · Dados sintéticos), situação do ambiente, progresso |
| Lição 1 · Regressão e sobreajuste | Prever a temperatura e ver o modelo "decorar" os dados |
| Lição 2 · Quente para o que você faz | Descobrir o que é normal e achar minutos estranhos |
| Lição 3 · Dados sintéticos com gabarito | Gerar dados de relação conhecida e conferir o que o modelo descobre |
| Glossário | Todos os termos, com exemplo curto |
| Sobre e privacidade | O que o Laboratório lê, grava e não faz |

## Entidades e campos
**ConjuntoDeDados** (em memória; nunca gravado)

| Campo | Tipo | Regra |
|---|---|---|
| origem | `real` \| `sintetico` | decide a faixa de aviso |
| minutos | matriz numérica | uma linha por minuto, ordenada por `ts` |
| colunas | lista | ver "Variáveis" abaixo |
| periodo | início, fim | exibido na tela |
| semente | inteiro | só no sintético |
| parametros | ParametrosSinteticos | só no sintético |
| gabarito | dicionário | só no sintético: coeficientes verdadeiros |

**Variáveis** (nomes na tela entre aspas; coluna de origem em `minuto`)
| Papel | Nome na tela | Coluna |
|---|---|---|
| **Alvo** (o que se quer prever) | "Temperatura da CPU" | `cpu_c_med` |
| Entrada | "Uso da CPU" | `uso_cpu_med` |
| Entrada | "Frequência da CPU" | `clk_mhz_med` |
| Entrada | "Na tomada" | `tomada_med` |
| Entrada | "Hora do dia" | derivada de `ts` (0–23) |
| Entrada opcional (armadilha didática) | "Rotação da ventoinha" | `ventoinha_rpm_med` |

**Regras de uso dos dados**
- **Minuto útil**: `cpu_c_n ≥ 5`, `uso_cpu_n ≥ 1`, `fonte` diferente de `ACPI` e sem valor ausente nas entradas escolhidas. Só minutos úteis entram.
- **Tamanho máximo:** os 20.000 minutos mais recentes (≈14 dias); acima disso usa os mais recentes e avisa.
- Nomes de programas (`programa_principal`) **não** são lidos pelo Laboratório. Só números.
- A ventoinha **não** entra por padrão: ela *reage* à temperatura (consequência, não causa). Um botão a inclui para mostrar por que isso engana (ver lição 1).

**ParametrosSinteticos**
| Campo | Faixa | Padrão | Efeito no gabarito |
|---|---|---|---|
| dias | 3–30 | 14 | quantidade de dados |
| ruido_c | 0,5–6,0 °C | 2,0 | dispersão aleatória da temperatura |
| efeito_uso | 0,10–0,60 °C por 1% | 0,35 | quanto o uso esquenta |
| efeito_tomada | 0–10 °C | 5,0 | quanto estar na tomada esquenta |
| poeira_por_dia | 0–0,30 °C/dia | 0 | sobe a temperatura base a cada dia (sujeira, pasta térmica) |
| correlacao_uso_freq | 0–0,95 | 0,6 | quanto uso e frequência andam juntos |
| semente | inteiro | 7 | repete o mesmo sorteio |
| episodios | 0–30 | 0 | episódios "quente para o que faz" injetados, só no período de prova (últimos 30%), dentro de um dia, separados por ≥ 1 h (lição 2) |
| episodio_c | 3–20 °C | 10 | quanto cada episódio esquenta além do normal |
| episodio_min | 10–60 | 15 | duração de cada episódio, em minutos |

Fórmula (a "verdade"): `temperatura = 38 + 4·sen(2π·(hora − 8)/24) + efeito_uso × uso + efeito_tomada × tomada + poeira_por_dia × dia + deriva_lenta + ruído`.
- A **frequência não esquenta nada** (efeito verdadeiro 0): só anda junto com o uso, conforme `correlacao_uso_freq`.
- A **deriva lenta** é um fator escondido (σ 1,5 °C, memória de ~3 h) que nenhuma entrada enxerga. É ela que faz a avaliação com minutos embaralhados dar nota falsamente boa.
- A rotação da ventoinha sintética é consequência: `2400 + 45 × (temperatura − 40) + ruído`.
- Jornada fictícia das 07h às 22h: 900 minutos por dia (até 27.000 minutos em 30 dias). O limite de 20.000 minutos vale para o histórico real.

**Progresso** (arquivo local `%LOCALAPPDATA%\TempCPU\lab\progresso.json`): lições concluídas, acertos das perguntas, última fonte escolhida. Apagar o arquivo reinicia tudo.

## Lição 1 · Regressão e sobreajuste (overfitting)
**Pergunta da lição:** "Dá para prever a temperatura sabendo o que o computador está fazendo?"
**Passos**
1. **O problema.** Mostra a dispersão temperatura × uso e define alvo e entradas.
2. **Treino e teste.** Os dados são divididos **por tempo**: primeiros 70% = treino ("o que o modelo vê"), últimos 30% = teste ("a prova"). Opção "embaralhar" mostra que misturar minutos vizinhos dá nota falsamente boa (e explica por quê).
3. **Simples × complexo.** Controle de **profundidade da árvore** (1–20). Gráfico com duas curvas de erro, treino e teste, e a faixa em que o teste piora (sobreajuste). Linha de referência do **modelo linear**. Gráfico "previsto × real" no período de teste para a profundidade escolhida.
4. **Contra quem ele precisa ganhar.** Referência "chutar a média do treino"; o modelo só é bom se o erro de teste for menor.
5. **O que ele aprendeu.** Importância de cada entrada (por embaralhamento, `permutation importance`). Botão "incluir ventoinha": a nota sobe e a tela explica que isso é consequência, não causa; correlação não é causa.
6. **Resumo e 3 perguntas.**

**Achado didático (medido):** no mundo sintético o **modelo linear (erro 2,1 °C) vence a melhor árvore (2,2 °C na profundidade 9)**, porque a verdade é linear. A lição mostra isso: modelo mais complexo nem sempre é melhor.

**Medidas** (somente duas): erro médio absoluto em °C (EMA, `MAE`) e "quanto da variação o modelo explica" (`R²`, 0 = igual a chutar a média).
**Modelos:** `LinearRegression` e `DecisionTreeRegressor(max_depth, random_state=semente)`.
**Dados mínimos reais:** 3 dias e 2.000 minutos úteis. Senão, a tela explica e oferece sintético.

## Lição 2 · "Quente para o que você faz" (anomalia)
**Pergunta da lição:** "Esta temperatura é normal para o que o computador estava fazendo?"
**Passos**
1. **A ideia.** 70 °C pode ser normal numa compilação e estranho com a máquina parada: o que importa é o **esperado**.
2. **Aprender o "normal".** Treina um modelo no período inicial (padrão: primeiros 70%) com uso, frequência, tomada e hora. A ventoinha **não** entra (consequência).
3. **Medido × esperado.** Gráfico dos dois e do **resíduo** (medido − esperado) no período restante.
4. **O limite do "estranho".** Controle de sensibilidade (1,5 a 5 × o erro típico do período de treino). Mostra quantos minutos ficam marcados e, no sintético, quantos eram de fato estranhos: **falso alarme** × **alarme perdido**.
5. **Tendência por semana.** Mediana semanal do resíduo; se sobe de forma consistente, a tela diz "esta máquina está esquentando mais para o mesmo trabalho" e lista causas possíveis (poeira, pasta térmica, plano de energia) sem prometer diagnóstico.
6. **Resumo e 3 perguntas.**

**Marcação:** só vale **episódio** (resíduo suavizado acima do limite por ≥ 10 minutos seguidos, sem buraco de tempo maior que 2 minutos); minutos isolados são tratados como ruído. Só o lado quente conta.
**Modelo:** `RandomForestRegressor(n_estimators=60, min_samples_leaf=20, random_state=semente)`.
**Erro típico:** desvio robusto (1,4826 × MAD) do resíduo em previsões de blocos de tempo que o modelo não viu (validação cruzada em 5 blocos contíguos do período de treino). Resíduo calculado nos próprios minutos de treino seria otimista.
**Suavização e sensibilidade (calibradas):** o resíduo passa por média móvel de 5 minutos antes do limite; sensibilidade padrão **2,5 × erro típico** (controle de 1,5 a 5).
**Dados mínimos reais:** 7 dias e 5.000 minutos úteis; a tendência semanal pede ≥ 3 semanas, senão explica e mostra no sintético com poeira.

## Lição 3 · Dados sintéticos com gabarito
**Pergunta da lição:** "O que o modelo descobre quando eu sei a resposta certa?"
**Passos**
1. **Gerar.** Sliders dos `ParametrosSinteticos`; gráfico dos dados gerados e o **gabarito** (coeficientes verdadeiros) escrito na tela.
2. **Ajustar o modelo linear** e comparar: coeficientes descobertos × gabarito, com erro em %.
3. **Estragar de propósito.** Aumentar o ruído, reduzir os dias, subir a correlação entre uso e frequência. A tela mostra como a descoberta piora e explica **ruído**, **poucos dados** e **variáveis que andam juntas** (colinearidade): a previsão pode continuar boa mesmo com o coeficiente errado.
4. **Poeira escondida.** Ligar `poeira_por_dia` e ver o modelo da lição 2 detectar a tendência.
5. **Usar nas outras lições.** Botão que envia este conjunto para as lições 1 e 2.
6. **Resumo e 3 perguntas.**

## Fluxos e estados
- **Ambiente:** `ausente` → (confirmação) → `preparando` → `pronto` | `falhou`. Falha deixa o app intacto e a pasta parcial removida (ou oferece remover).
- **Treino:** `parado` → `treinando` (com progresso e **Cancelar**) → `pronto` | `erro`.
- **Lição:** `não iniciada` → `em andamento` → `concluída`.
- Ações sensíveis com confirmação: **Preparar Laboratório** (download de ~240 MB) e **Remover Laboratório** (apaga a pasta do ambiente, nunca o histórico).

## Estados obrigatórios de tela
| Estado | O que diz e o próximo passo |
|---|---|
| Carregando / treinando | O que está sendo feito, barra de progresso, botão Cancelar |
| Poucos dados reais | Quantos minutos existem × quantos a lição pede e **Usar dados sintéticos** |
| Sem banco | "Nenhum histórico encontrado": abra o TempCPU e deixe-o rodar; ou use sintético |
| Ambiente ausente | Mostra o tamanho (~240 MB) e confirma **Preparar Laboratório** ou **Agora não** |
| Preparando | Etapas (criando ambiente, baixando, verificando), Cancelar |
| Falhou o preparo | Motivo em português (sem internet, sem espaço, erro do pip) e **Tentar de novo** |
| Erro no treino | O que falhou e **Voltar** (nunca janela em branco) |
| Resultado fraco | Texto honesto: "o modelo não ganhou da média"; explica possíveis motivos |
| Banco em uso/corrompido | Leitura falhou, nada foi alterado, tentar de novo |
| Indisponível | App antigo sem o botão: instrução de atualização |

## Persistência
- Dados do histórico: só leitura de `historico.db` (somente leitura; `mode=ro`).
- Ambiente do Laboratório: `%LOCALAPPDATA%\TempCPU\lab-env\` (fora do projeto e de qualquer pacote).
- Progresso: `%LOCALAPPDATA%\TempCPU\lab\progresso.json`.
- Nada de dados sintéticos é gravado; modelos não são salvos.

## Segurança e dados
- Sem rede, exceto o `pip` ao **Preparar Laboratório**, só depois da confirmação, com pacotes fixados (`scikit-learn` e dependências, versões testadas) e verificação de hash quando disponível.
- Dado pessoal: nenhum nome de programa é lido; o histórico é do próprio usuário e não sai do computador.
- O Laboratório não altera nenhuma configuração do Windows.

## Fora do escopo (v1)
- Lição de classificação do `motivo_principal` (vazamento de dados), agrupamento (k-means), previsão a curto prazo, `IsolationForest`: ficam para as lições 4+.
- Alertas automáticos no app a partir de anomalias.
- Salvar ou carregar modelos; exportar resultados.
- Distribuir o Laboratório junto do `.exe` único (v1 exige Python instalado; ver Questões em aberto).
- Inglês.

## Critérios de aceite
Cada item vira teste automático (rodado no ambiente do Laboratório) ou verificação manual registrada em `docs/ONDE_ESTAMOS.md`.

| # | Critério | Como se verifica |
|---|---|---|
| A1 | Com os parâmetros padrão e semente 7, na lição 1: o erro de treino não aumenta com a profundidade; o erro de teste é mínimo entre as profundidades **5 e 12** (medido: 9); na profundidade 20 o erro de teste é ≥ 1,15 × o mínimo (medido: 1,27) | teste automático — **calibrado** |
| A2 | O modelo no melhor ponto tem erro de teste menor que metade do de "chutar a média" (medido: 2,2 contra 7,1 °C) e R² de teste > 0,85 | teste automático |
| A3 | Ligar "embaralhar" reduz o menor erro de teste em pelo menos 3% em relação à divisão por tempo (medido: 8%) e também na profundidade 20, e a tela explica | teste automático + conferência visual |
| A4 | Incluir a ventoinha faz o R² de teste subir mais de 0,04 (medido: 0,91 → 0,98) e o erro cair a menos de 70%; a tela exibe o aviso de "consequência, não causa" | teste automático + conferência visual |
| A5 | Lição 3, padrão: o coeficiente de "uso" descoberto fica a ±15% do gabarito (0,35) | teste automático |
| A6 | Lição 2 com sintético (poeira 0,20 °C/dia, 21 dias): a tendência estimada fica entre 1,0 e 1,9 °C por semana (verdade: 1,4; medido: 1,65; 1,2 a 1,9 em 6 sementes). Sem poeira, a tendência fica entre −0,6 e 0,6 | teste automático — **calibrado** |
| A7 | Lição 2 com 10 episódios injetados (+10 °C por 15 min), na sensibilidade padrão (2,5) com suavização de 5 min: recall médio ≥ 80% e falsos alarmes ≤ 3% dos minutos normais (medido em 8 sementes: recall médio 91%, mínimo 80%, falsos 0,04%; com poeira: 100% e 0,4%) | teste automático — **calibrado** |
| A8 | `import app` e o app em execução **não** carregam `numpy` nem `sklearn` | teste automático + conferência da memória do app antes/depois de abrir o Laboratório |
| A9 | O banco fica **idêntico** (hash do arquivo) depois de rodar as 3 lições; tentativa de escrever falha | teste automático |
| A10 | Qualquer treino termina em ≤ 10 s e o Laboratório usa ≤ 300 MB de RAM nesta máquina (ambiente já preparado) | **medido:** pico 146 MB; maior treino 7,9 s (lição 2 com 30 dias); importação a quente 3 s |
| A11 | Todo termo da lista do Glossário usado nas telas tem definição; nenhum termo fora da lista aparece | teste automático sobre os textos |
| A12 | Cada estado da tabela "Estados obrigatórios" existe e é alcançável | roteiro manual |
| A13 | **Preparar Laboratório**: cancelar na confirmação não cria nada; falha de rede deixa o app funcionando e sem pasta parcial | roteiro manual |
| A14 | Faixa "DADOS SINTÉTICOS" visível em toda tela que usa sintético | conferência visual |
| A15 | As 3 lições completas ponta a ponta com sintético e (se houver dados) com o histórico real | roteiro manual |

## Estado de verificação (2026-10-25)
| Critério | Situação | Como foi provado |
|---|---|---|
| A1–A7 | **Provados** | `tests_lab/test_modelos.py` e testes de interface das lições 1 a 3; limiares calibrados com 8 sementes |
| A8 | **Provado** | `tests/test_app_leve.py`: `import app` e `import laboratorio` em subprocesso, sem `numpy`/`sklearn` em `sys.modules`; varredura do código |
| A9 | **Provado** | `tests_lab/test_dados.py`: hash do arquivo idêntico, `DELETE`/`INSERT` falham (banco em modo WAL) |
| A10 | **Medido** | pico de 146 MB nos treinos; 141 MB com o Laboratório aberto na tela inicial (ambiente de produção); maior treino 7,9 s; importação a quente 3 s |
| A11 | **Provado** | `tests_lab/test_glossario.py`: termo marcado em cada lição que o usa, sem jargão em inglês solto, nenhum termo órfão |
| A12 | **Parcial** | estados treinando, cancelado, erro, poucos dados, sem banco e banco ilegível: testados. Preparo (progresso, falha, cancelar) testado com fakes em `tests/test_laboratorio.py`. Sem teste visual: "resultado fraco" (texto existe, não é disparado nos dados atuais) |
| A13 | **Parcial** | cancelar e falhar com limpeza: provado com fakes. Instalação real com sucesso: provada (36 s, 241 MB, hashes conferem). Falha real de rede e clique em "Agora não" na caixa: não exercitados |
| A14 | **Provado** | teste de interface: a faixa fica visível com dados sintéticos (inclusive na Lição 3 com fonte "real") e some ao sair |
| A15 | **Parcial** | as 3 lições ponta a ponta com dados sintéticos: provado. Com o histórico real: **pendente** (o banco real tem poucos minutos; precisa de alguns dias de uso) |

## Dados de exemplo
O gerador da lição 3 **é** o dado de exemplo: padrão `dias=14`, `semente=7`, com uma rotina diária fictícia (rajadas de trabalho em horário comercial, tarde mais quente, noite ociosa). Nenhum dado real é copiado para exemplos, testes ou documentação.

## Questões em aberto
1. **Python instalado:** na v1 o Laboratório roda com o Python do usuário (o `.exe` único não traz Python). Como entregar a quem não tem Python? Candidatos: instalador do Python embutido (~25 MB) ou distribuir só com o código-fonte. Decidir na fase 0 do lançamento público.
2. Limiares A1, A6 e A7: **calibrados** na fase 2 (valores acima). Valem para o gerador padrão; mudar o gerador exige recalibrar.
3. **Dados reais:** hoje o banco tem poucos minutos; as lições 1–2 com dados reais só serão verificadas depois de alguns dias de uso.
