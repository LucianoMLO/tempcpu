# Laboratório — lições novas (especificação)

**Status:** proposta para aprovação, 2026-10-25 · nada implementado · **Depende de:** `docs/SPEC-laboratorio.md` (v1) · **Versão alvo:** v1.2 do Laboratório
**Sem dependência nova:** tudo abaixo existe no scikit-learn já instalado no ambiente do Laboratório (`LogisticRegression`, `DecisionTreeClassifier`, `KNeighborsClassifier`, `Ridge`, `Lasso`, `HistGradientBoostingRegressor`, `IsolationForest`, `KMeans`, `PCA`, `silhouette_score`). Peso do ambiente e do app não mudam.

## Objetivo e usuário
- **Objetivo:** cobrir os conceitos básicos que a v1 não explora: classificação, aprendizado sem rótulos (agrupamento e redução de dimensão), regularização, modelos mais fortes e validação cruzada, e outra forma de achar anomalia.
- **Usuário:** o mesmo da v1, qualquer pessoa, sem pressupor nada. Valem os mesmos princípios: tudo local, só lê o histórico, termos explicados no Glossário (teste A11), semente visível, dado sintético com faixa "DADOS SINTÉTICOS", resultado fraco mostrado como fraco.

## Resumo do que entra
| Conceito | Onde entra | Tipo |
|---|---|---|
| Regularização (Ridge, Lasso) | Lição 3, passo 7 | passo novo |
| Isolation Forest (anomalia sem prever) | Lição 2, passo 7 | passo novo |
| Validação cruzada e escolha de hiperparâmetro | Lição 1, passo 7 | passo novo |
| Gradient boosting | Lição 1, passo 8 | passo novo |
| **Classificação** | **Lição 4** | lição nova |
| **Agrupamento (k-means) e PCA** | **Lição 5** | lição nova |
| Redes neurais, séries temporais formais | fora do escopo (ver abaixo) | — |

Cada passo novo e cada lição termina com 3 perguntas de fixação (mesmo formato de hoje).

## Passos novos nas lições existentes

### Lição 1, passo 7 · "Escolher sem olhar a prova" (validação cruzada)
- **Ensina:** escolher a profundidade olhando o próprio teste vira pequena trapaça (a ressalva já existe no passo 3). A solução é a **validação cruzada**: dividir o treino em blocos, treinar em uns e conferir nos outros, e só no fim abrir o teste.
- **Experimento:** botão "Escolher com validação cruzada" (5 blocos **em ordem de tempo**, não sorteados); gráfico com o erro médio por profundidade e a variação entre blocos (faixa); mostra a profundidade escolhida e o erro no teste, que continua inédito.
- **Verdade a mostrar:** a profundidade escolhida pode ser diferente da que o teste "preferiria"; a diferença de erro entre as duas é pequena (número medido na tela).

### Lição 1, passo 8 · "Muitas árvores pequenas" (boosting)
- **Ensina:** floresta aleatória = árvores independentes cuja média decide; **boosting** = árvores pequenas em sequência, cada uma corrigindo o erro da anterior.
- **Experimento:** controle "quantas rodadas" (1 a 200) mostrando erro no treino e no teste de um `HistGradientBoostingRegressor`; compara com a melhor árvore e com a floresta (quando existir no cache da Lição 2, senão calcula).
- **Verdade a mostrar:** com poucas rodadas é subajuste; com muitas e sem freio, também pode sobreajustar; nenhum modelo vence o linear num mundo linear por margem grande (medir e dizer).

### Lição 2, passo 7 · "Achar o estranho sem prever" (Isolation Forest)
- **Ensina:** outro jeito de achar anomalia, sem estimar a temperatura esperada: isolar pontos raros por perguntas aleatórias.
- **Experimento:** roda `IsolationForest` sobre (uso, frequência, temperatura, hora); controle "quantos % são estranhos" (contaminação); marca no gráfico do período de prova; no sintético, mostra **recall e falsos alarmes** contra os episódios injetados, lado a lado com o método da lição (resíduo suavizado).
- **Verdade a mostrar (medir antes de escrever):** qual dos dois acha mais episódios e quantos falsos alarmes gera. O texto da tela é montado com os números medidos, nunca fixo (regra da v1: afirmação precisa de número).

### Lição 3, passo 7 · "Domar entradas que andam juntas" (Ridge e Lasso)
- **Ensina:** com entradas muito parecidas (uso e frequência), os coeficientes ficam instáveis. A **regularização** aceita um erro pequeno para estabilizar. Ridge encolhe todos; Lasso zera os que não ajudam.
- **Experimento:** reaproveita os dados da lição (com `correlacao_uso_freq` alta); controle de "força da regularização" (escala logarítmica); gráfico dos coeficientes descobertos × gabarito para linear, Ridge e Lasso; tabela do erro de previsão de cada um.
- **Verdade a mostrar:** a previsão quase não muda, mas o erro do coeficiente em relação ao gabarito cai com Ridge; Lasso zera entradas (diz quais). Também mostra que regularizar demais piora (subajuste), com a mesma curva em U.

## Lição 4 · "Em qual faixa está?" (classificação)
**Pergunta guia:** em vez de prever o número, dá para prever em qual **zona** (normal, atenção, quente, crítico) o computador estará?

| Passo | Conteúdo |
|---|---|
| 1 O problema | Classificar × prever número. Alvo: zona da temperatura (limites do `.env`). Mostra a distribuição das classes (quase tudo é "normal"). |
| 2 Um primeiro classificador | Regressão logística (apesar do nome, classifica): entradas uso, frequência, tomada, hora; mostra acertos. |
| 3 Acurácia engana | Palpite "sempre normal" acerta ~X% (medido) e não serve. Introduz **classes desbalanceadas**. |
| 4 Matriz de confusão | Quadro de acertos e erros por classe; o que é pior: alarme falso ou alarme perdido (liga com a Lição 2). |
| 5 Precisão e revocação | **Precisão** (dos alarmes, quantos eram reais) e **revocação** (dos reais, quantos achei) com o controle de "limite de decisão". |
| 6 Outros classificadores | Árvore e k-vizinhos (k-NN), com o mesmo experimento; k-NN mostra "decidir olhando vizinhos" e a necessidade de escalar as entradas. |
| 7 Resumo e 3 perguntas | |

- **Dados:** sintéticos por padrão (a lição 4 precisa de episódios quentes suficientes; se o histórico real quase não tem "quente", a tela diz isso e usa sintético); real quando a qualidade (`lab/qualidade.py`) é boa **e** há ≥ 50 minutos nas zonas "quente" ou "crítico".
- **Divisão:** sempre por tempo (a lição 1 já ensina o porquê).

## Lição 5 · "Descobrir grupos sem gabarito" (agrupamento e PCA)
**Pergunta guia:** sem ninguém dizer o que é o quê, o computador consegue achar "modos de uso" sozinho?

| Passo | Conteúdo |
|---|---|
| 1 O problema | Aprendizado **sem rótulos**: não há resposta certa para conferir. Mostra os minutos como nuvem (uso × temperatura). |
| 2 k-means | O programa escolhe k centros e agrupa; controle de k (2 a 8); cores no gráfico. |
| 3 Quantos grupos? | **Inércia** (cotovelo) e **silhueta**; "o número certo de grupos não existe, existe o mais útil". |
| 4 Dar nome aos grupos | Para cada grupo mostra média de uso, frequência, temperatura e hora, e sugere nomes ("ocioso", "trabalho leve", "carga alta"); o aprendiz pode renomear (só na sessão). |
| 5 Gabarito (sintético) | No sintético os modos reais são conhecidos (gerados em 3 regimes); mostra o quão bem os grupos recuperam os regimes (**pureza**) e o que acontece com ruído alto ou k errado. |
| 6 PCA | Reduzir várias entradas a 2 componentes; mostra quanta informação cada componente guarda e que uso e frequência quase dizem a mesma coisa (liga com a Lição 3). |
| 7 Resumo e 3 perguntas | |

- **Dados:** sintéticos com regimes conhecidos (novo parâmetro do gerador); histórico real quando a qualidade é boa (os grupos reais são descobertos, sem gabarito, e a tela diz que não há resposta certa para conferir).
- **Gerador:** novo parâmetro `regimes` (2 a 5) no `ParametrosSinteticos`, com gabarito `regime` por minuto. Não muda os padrões das lições existentes (padrão = comportamento atual).

## Fora do escopo (v1.2)
Redes neurais (exigem escala, épocas e mais cuidado do que um passo curto comporta), séries temporais formais (ARIMA etc.), aprendizado por reforço, aprendizado profundo, ajuste de hiperparâmetros automático além da validação cruzada, explicabilidade avançada (SHAP). Ficam como "para saber que existe" no Glossário, sem experimento.

## Impacto
- **Glossário:** +~25 termos (classificação, classe, acurácia, matriz de confusão, precisão, revocação, limite de decisão, k-vizinhos, validação cruzada, bloco, boosting, regularização, Ridge, Lasso, agrupamento, centro, inércia, silhueta, pureza, PCA, componente, isolation forest, contaminação, aprendizado sem rótulos, classe desbalanceada).
- **Avaliação (`docs/SPEC-avaliacao.md`):** novos temas T6 Classificação, T7 Agrupamento e redução de dimensão, T8 Regularização e modelos mais fortes (que também cobre os passos 7 e 8 da Lição 1 e o passo 7 da Lição 2). Banco passa de 50 para 80 questões; a final vira 24 questões (3 por tema), aprovação 80% (20/24) e ≥ 2 de 3 por tema.
- **Início:** 5 lições; o cartão de avaliação só libera com as 5 concluídas.
- **Desempenho:** novos treinos devem respeitar A10 (pico ≤ 300 MB, treino ≤ 10 s); k-means e PCA são rápidos; validação cruzada com 5 blocos e 20 profundidades é o mais pesado e será medido.

## Critérios de aceite
- **C1** Cada passo novo abre sem erro com dados sintéticos e, quando elegível, com reais (teste de interface, como nas lições atuais).
- **C2** Validação cruzada em blocos de tempo: nenhum minuto de um bloco de validação é anterior a minutos do treino daquele bloco além do permitido pela divisão em ordem (teste que verifica a ordem).
- **C3** Boosting: erro de treino não cresce com as rodadas e o de teste tem mínimo interior ou platô (calibrar com 8 sementes e atualizar a spec com os números).
- **C4** Isolation Forest: com os parâmetros padrão do gerador e 8 sementes, recall e falsos alarmes **medidos e registrados**; o texto da tela só afirma o que o número sustenta.
- **C5** Ridge: erro do coeficiente do uso (vs gabarito) com colinearidade alta é menor que o do linear em ≥ 6 de 8 sementes; senão a afirmação é removida do texto.
- **C6** Lasso zera ao menos a entrada sem efeito no gabarito (`dia` com poeira 0) em ≥ 6 de 8 sementes.
- **C7** Classificação: o palpite "sempre normal" tem acurácia mostrada e é pior que o modelo em revocação das zonas quentes (teste com sintético padrão); matriz de confusão soma o total de minutos do teste.
- **C8** Precisão e revocação variam de forma monótona esperada com o limite de decisão (teste de propriedade).
- **C9** k-means com `regimes=3` e ruído padrão recupera os regimes com pureza ≥ limiar calibrado; com ruído máximo a pureza cai (teste das duas pontas).
- **C10** PCA: componentes explicam variância em ordem decrescente e somam ≤ 1 (teste); com `correlacao_uso_freq` alta o 1º componente carrega uso e frequência com o mesmo sinal.
- **C11** Teste A11 (termos vigiados marcados) cobre todos os textos novos; nenhum jargão em inglês solto.
- **C12** Nenhum módulo de rede importado; medidas A10 repetidas para os treinos novos.
- **C13** Uma lição concluída continua marcada após atualizar o Laboratório (o formato de `progresso.json` aceita as lições 4 e 5).

## Plano de construção
1. **L-0** Calibração com o gerador (C3 a C6, C9, C10) e atualização desta spec com os números medidos.
2. **L-1** Núcleo em `lab/modelos.py` (ou `lab/modelos2.py`), sem interface, com testes.
3. **L-2** Passos novos nas lições 1 a 3.
4. **L-3** Lições 4 e 5 (interface, textos, quiz, glossário).
5. **L-4** Revisão independente, medições A10, README e ONDE_ESTAMOS.

## Questões em aberto
1. Priorizar tudo na v1.2 ou entregar em duas levas (1ª: Ridge, Isolation Forest, classificação; 2ª: k-means/PCA, boosting, validação cruzada)?
2. Os nomes das lições novas ("Em qual faixa está?", "Descobrir grupos sem gabarito") estão bons?

## Estado de verificação (2026-10-27) — construído e calibrado
**Status:** implementado (núcleo `lab/modelos2.py`, textos `lab/textos_novos.py`, `textos_l4.py`, `textos_l5.py`, telas `lab/ui/passos_novos.py`, `licao4.py`, `licao5.py`). As duas questões em aberto foram decididas assim: tudo de uma vez, e os nomes "Em qual faixa está?" e "Descobrir grupos sem gabarito" mantidos. Os passos novos entram **antes** do "Resumo e perguntas" (Lição 1 tem 8 passos; Lições 2 e 3, 7). Os regimes verdadeiros da Lição 5 vêm do próprio gerador (`Conjunto.regime`: ocioso, trabalho leve, carga pesada), sem parâmetro novo.

Números medidos com o gerador (sementes 1 a 8, parâmetros padrão salvo indicação) e o que cada critério virou:
| Critério | Medido | Resultado |
|---|---|---|
| C2 validação cruzada | escolhe profundidade 8 ou 9 em todas as sementes; o teste escolheria 7 a 9; diferença de erro no teste ≤ 0,016 °C | **Aprovado**; blocos contíguos em ordem de tempo (`KFold` sem embaralhar) |
| C3 boosting | erro de treino só cai; teste cai de ~6 a 7 °C na rodada 1 para ~2,0 °C e fica em platô (melhor rodada 68 a 166 de 200); mínimo 1,92 a 2,10 °C contra 2,16 a 2,37 da melhor árvore e 1,81 a 2,06 do linear | **Aprovado**; sem sobreajuste forte em 200 rodadas |
| C4 Isolation Forest (21 dias, 10 episódios, poeira 0,2) | acha 0 a 40% dos episódios com 1 a 10% de minutos estranhos e 1 a 6% de falsos alarmes; o método do resíduo acha **10 de 10** com ≤ 1,6% de falsos | **O texto da tela mostra os números medidos**: o Isolation Forest perde, porque calor com carga alta não é raro |
| C5 Ridge | **não melhora** o coeficiente do uso (erro de 17 a 64% contra 5,6 a 8,5% do linear, com 150 minutos e correlação 0,95): reparte o mérito com a frequência e encolhe tudo | **Afirmação removida**; a tela mostra o que acontece e o teste `test_o_ridge_nao_melhora_o_coeficiente_do_uso_aqui` registra o fato |
| C6 Lasso | erro do uso 12,6% → 9,9% → 7,8% (λ = 0, 0,03, 0,1; 60 minutos); com 300 minutos 5,9% → 1,5% (λ = 0,1); zera a frequência em 2 a 5 de 20 sorteios com λ = 0,03 | **Aprovado em média, não em toda amostra**; a tela diz que varia de amostra para amostra |
| C7 classificação (limite no percentil 90, ~66 °C) | "nunca avisa" 0,89 a 0,90 de acurácia e 0% de revocação; os três modelos 0,97 a 0,98 de acurácia, precisão 0,84 a 0,94, revocação 0,82 a 0,98 | **Aprovado** |
| C8 limite de decisão | revocação e número de avisos não aumentam com o limite; precisão em 0,9 maior que em 0,1 | **Aprovado** |
| C9 k-means (21 dias) | pureza com k = 3: 0,72 a 0,76; k = 4: 0,88 a 0,90; k = 2: 0,71 a 0,76; ruído 6 °C derruba a pureza (k = 4: 0,82 a 0,84). A silhueta é maior em **k = 2** (0,56 a 0,61) | **Aprovado**; é uma boa lição: a silhueta não aponta para os 3 regimes verdadeiros |
| C10 PCA | 1º componente explica 57 a 61%, 2 componentes ~86%; uso, frequência e temperatura entram com o mesmo sinal (cargas 0,49 a 0,61) | **Aprovado** |
| C11 glossário | 25 termos novos; teste A11 cobre os textos novos | **Aprovado** |
| C12 rede e desempenho | nenhum módulo de rede; passos novos rodam em segundos | **Aprovado** (A10 não foi remedido formalmente) |
| C13 progresso | lições 4 e 5 gravam e releem conclusão | **Aprovado** |

**Não feito:** as questões da **avaliação** para os novos temas (T6 a T8) e o ajuste do banco para 80 questões e da final para 24; o Worker da avaliação continua cobrindo só as lições 1 a 3 (o texto da página já diz isso). **Não testado:** as lições novas com histórico real de verdade (poucos dias de dados) e a medição A10 formal de pico de memória e tempo dos novos treinos.
