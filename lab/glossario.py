"""Glossário do Laboratório. Todo termo técnico que aparece nas telas está aqui, com definição simples.

Nos textos das lições, um termo é marcado como ⟦chave⟧ (mostra a própria palavra) ou ⟦chave|texto⟧ (mostra
outro texto, por exemplo no plural). Passar o mouse ou clicar mostra a definição.
"""
from __future__ import annotations

import re

# chave -> (nome mostrado, nome em inglês, definição, exemplo curto)
TERMOS: dict[str, tuple[str, str, str, str]] = {
    "modelo": ("modelo", "model",
               "Uma fórmula que o computador aprende a partir de exemplos para fazer previsões.",
               "Um modelo que, dado o uso da CPU, diz qual deve ser a temperatura."),
    "alvo": ("alvo", "target",
             "O que queremos prever: a resposta que o modelo tenta acertar.",
             "Aqui, a temperatura da CPU."),
    "entradas": ("entradas", "features",
                 "As informações que o modelo usa para prever o alvo.",
                 "Uso da CPU, frequência, se está na tomada e a hora do dia."),
    "treino": ("treino", "training set",
               "A parte dos dados que o modelo vê para aprender.",
               "Os primeiros 70% do tempo."),
    "teste": ("teste", "test set",
              "A parte dos dados guardada para a \"prova\": o modelo nunca a viu durante o aprendizado.",
              "Os últimos 30% do tempo."),
    "arvore": ("árvore de decisão", "decision tree",
               "Um modelo que faz perguntas em sequência (\"o uso passa de 50%?\") e vai se ramificando até chegar a uma previsão.",
               "Se uso > 50% e na tomada, prevê 68 °C."),
    "profundidade": ("profundidade", "depth",
                     "Quantas perguntas seguidas a árvore pode fazer. Mais profundidade = modelo mais complexo.",
                     "Profundidade 3 faz até 3 perguntas por previsão; profundidade 20 faz até 20."),
    "erro_medio": ("erro médio", "mean absolute error, MAE",
                   "A diferença média, em graus, entre o que o modelo previu e o que realmente aconteceu.",
                   "Erro médio de 2 °C: em média, a previsão erra 2 graus para mais ou para menos."),
    "subajuste": ("subajuste", "underfitting",
                  "Quando o modelo é simples demais e erra tanto no treino quanto no teste.",
                  "Uma árvore com 1 pergunta só."),
    "sobreajuste": ("sobreajuste", "overfitting",
                    "Quando o modelo decora o treino, inclusive o acaso, e por isso erra mais na prova (teste).",
                    "Erro de 0,2 °C no treino e de 2,8 °C no teste."),
    "ruido": ("ruído", "noise",
              "Variação aleatória que nenhuma informação disponível explica.",
              "Dois minutos com o mesmo uso e temperaturas diferentes."),
    "baseline": ("palpite de referência", "baseline",
                 "Um palpite simples que o modelo precisa vencer para valer a pena. O mais comum é chutar sempre a média.",
                 "Chutar 55 °C para qualquer minuto."),
    "r2": ("nota R²", "R-squared",
           "Nota que diz quanto da variação da temperatura o modelo explica. 1 é acertar tudo; 0 é igual a chutar a média; abaixo de 0 é pior que chutar a média.",
           "R² de 0,91: o modelo explica 91% da variação."),
    "importancia": ("importância", "feature importance",
                    "Quanto o erro piora quando os valores de uma entrada são embaralhados. Se piora muito, o modelo dependia dela.",
                    "Embaralhar o uso da CPU faz o erro subir 7 °C."),
    "correlacao": ("correlação", "correlation",
                   "Duas coisas que variam juntas. Isso não quer dizer que uma causa a outra.",
                   "Uso e frequência da CPU sobem e descem juntos."),
    "consequencia": ("consequência", "effect (não causa)",
                     "Algo que acontece por causa de outra coisa, e não o contrário.",
                     "A ventoinha gira mais porque a CPU esquentou; ela não esquenta a CPU."),
    "vazamento": ("vazamento de dados", "data leakage",
                  "Quando o modelo recebe, sem querer, uma pista da resposta que não existiria na hora real de prever.",
                  "Usar a rotação da ventoinha para prever a temperatura."),
    "anomalia": ("anomalia", "anomaly",
                 "Algo que foge do comportamento normal esperado para aquela situação.",
                 "A CPU a 70 °C com a máquina quase parada."),
    "esperado": ("temperatura esperada", "expected value",
                 "O valor que o modelo prevê para aquele minuto, olhando o que o computador estava fazendo.",
                 "Com 90% de uso, a temperatura esperada é 72 °C."),
    "residuo": ("resíduo", "residual",
                "A diferença entre o que foi medido e o que era esperado. Resíduo alto e positivo = mais quente do que o normal.",
                "Medido 70 °C, esperado 58 °C: resíduo de +12 °C."),
    "erro_tipico": ("erro típico", "typical error",
                    "O tamanho comum do erro do modelo em minutos normais. Variações menores que isso não são notícia.",
                    "Erro típico de 2,7 °C: um resíduo de 1 °C é normal."),
    "falso_alarme": ("falso alarme", "false alarm",
                     "Quando o sistema avisa que há um problema, mas estava tudo normal.",
                     "Marcar como estranho um minuto comum."),
    "alarme_perdido": ("alarme perdido", "missed detection",
                       "Quando existe um problema de verdade e o sistema não avisa.",
                       "Um episódio de 15 minutos a 10 °C acima do normal que passa sem marcação."),
    "mediana": ("mediana", "median",
                "O valor do meio quando os números são colocados em ordem. Não se deixa levar por poucos valores extremos.",
                "A mediana de 1, 2, 3, 4 e 100 é 3."),
    "tendencia": ("tendência", "trend",
                  "Para onde os valores vão com o tempo: subindo, descendo ou estáveis.",
                  "O resíduo semanal subindo 1,4 °C por semana."),
    "gabarito": ("gabarito", "ground truth",
                 "A resposta certa, conhecida de antemão. Só existe em dados inventados; nos dados reais ninguém tem o gabarito.",
                 "Nos dados sintéticos, o efeito do uso é exatamente 0,35 °C por 1%."),
    "coeficiente": ("coeficiente", "coefficient",
                    "Quanto a previsão muda quando uma entrada aumenta uma unidade, mantendo as outras iguais.",
                    "Coeficiente do uso = 0,35: cada 1% a mais de uso soma 0,35 °C."),
    "colinearidade": ("colinearidade", "collinearity",
                      "Quando duas entradas andam juntas. O modelo não sabe a qual delas atribuir o efeito, e os coeficientes ficam errados mesmo com boas previsões.",
                      "Uso e frequência da CPU quase iguais."),
    "semente": ("semente", "random seed",
                "Um número que fixa o sorteio: a mesma semente gera sempre os mesmos dados.",
                "Semente 7 sempre gera a mesma jornada de 14 dias."),
    "deriva": ("deriva lenta", "drift",
               "Uma variação que muda aos poucos, ao longo de horas, por motivos que o modelo não enxerga (ambiente, outros programas).",
               "A temperatura sobe 2 °C por uma hora sem nenhuma mudança no uso."),
    "dados_sinteticos": ("dados sintéticos", "synthetic data",
                         "Dados inventados por um programa, com regras conhecidas. Servem para aprender, mas não dizem nada sobre o seu computador.",
                         "Uma jornada de trabalho fictícia de 14 dias."),
    "validacao_cruzada": ("validação cruzada", "cross-validation",
                          "Um jeito de escolher o modelo usando só o treino: ele é dividido em blocos; treina-se em alguns e confere-se no que sobrou, e repete-se até todo bloco ter sido a conferência.",
                          "Escolher a profundidade da árvore sem abrir o teste."),
    "bloco": ("bloco", "fold",
              "Uma fatia do treino usada, por vez, como conferência na validação cruzada.",
              "Cinco blocos seguidos no tempo."),
    "boosting": ("boosting", "boosting",
                 "Muitas árvores pequenas em fila, cada uma tentando corrigir o erro que as anteriores deixaram.",
                 "A 1ª árvore erra 6 °C; a 2ª corrige parte disso; e assim por diante."),
    "isolation_forest": ("Isolation Forest", "isolation forest",
                         "Um método que acha minutos raros sem prever nada: faz perguntas aleatórias e conta quantas bastam para isolar cada minuto. Minutos raros são isolados rápido.",
                         "Um minuto com 8% de uso e 92 °C é isolado com poucas perguntas."),
    "regularizacao": ("regularização", "regularization",
                      "Penalizar coeficientes grandes para o modelo ficar mais estável, aceitando um pequeno erro a mais.",
                      "Encolher o efeito do uso de 0,40 para 0,36 °C por 1%."),
    "ridge": ("ridge", "ridge regression",
              "Modelo linear com regularização que encolhe todos os coeficientes, sem zerá-los.",
              "Uso e frequência dividem o mérito, ambos com coeficientes menores."),
    "lasso": ("lasso", "lasso",
              "Modelo linear com regularização que encolhe os coeficientes e pode levar alguns exatamente a zero, escolhendo entradas.",
              "Ele zera a frequência e fica só com o uso."),
    "regressao_logistica": ("regressão logística", "logistic regression",
                            "Modelo que calcula a probabilidade de uma classe (de 0% a 100%). Apesar do nome, serve para classificar.",
                            "70% de chance de o minuto estar quente."),
    "classificacao": ("classificação", "classification",
                      "Prever uma categoria em vez de um número.",
                      "Passou do limite de temperatura: sim ou não."),
    "classe": ("classe", "class",
               "Cada categoria possível que a classificação escolhe.",
               "Normal e quente."),
    "desbalanceada": ("classe desbalanceada", "imbalanced class",
                      "Quando uma classe é muito mais rara que a outra, e por isso a acurácia engana.",
                      "Só 10% dos minutos estão quentes."),
    "acuracia": ("acurácia", "accuracy",
                 "A fração de previsões certas entre todas. Engana quando uma classe é rara.",
                 "Acertou 98 de 100 minutos."),
    "matriz_confusao": ("matriz de confusão", "confusion matrix",
                        "Uma tabela que conta os acertos e os dois tipos de erro: alarme falso e alarme perdido.",
                        "Avisou calor em 600 minutos; perdeu 20; deu alarme falso em 100."),
    "precisao": ("precisão", "precision",
                 "Dos avisos que o modelo deu, quantos eram verdadeiros.",
                 "Avisou 700 vezes e 600 eram calor de verdade: precisão de 86%."),
    "revocacao": ("revocação", "recall",
                  "Dos casos que realmente aconteceram, quantos o modelo avisou.",
                  "Havia 620 minutos quentes e ele avisou 600: revocação de 97%."),
    "vizinhos": ("k-vizinhos", "k-nearest neighbors",
                 "Modelo que olha os k exemplos mais parecidos e decide por votação.",
                 "Dos 15 minutos mais parecidos, 12 estavam quentes: avisa calor."),
    "sem_rotulos": ("aprendizado sem rótulos", "unsupervised learning",
                    "Aprender estrutura nos dados sem ter uma resposta certa para prever ou conferir.",
                    "Descobrir modos de uso sem que ninguém tenha dito quais são."),
    "agrupamento": ("agrupamento", "clustering",
                    "Juntar exemplos parecidos em grupos, sem rótulos prévios.",
                    "Grupos de minutos: parado, leve e pesado."),
    "kmeans": ("k-means", "k-means",
               "O agrupamento mais simples: escolhe k centros e junta cada exemplo ao centro mais próximo, repetindo até estabilizar.",
               "k = 3 gera três grupos."),
    "centro": ("centro", "centroid",
               "O ponto médio de um grupo.",
               "Uso 75%, 3.700 MHz e 70 °C no grupo da carga pesada."),
    "inercia": ("inércia", "inertia",
                "Quão espalhados ficam os exemplos dentro dos seus grupos. Cai quando k aumenta.",
                "Menor inércia, grupos mais compactos."),
    "silhueta": ("silhueta", "silhouette",
                 "Uma nota de -1 a 1 para o quão bem separados estão os grupos: quanto maior, melhor separados.",
                 "Silhueta de 0,6: grupos bem distintos."),
    "pureza": ("pureza", "purity",
               "Só com gabarito: a fração dos exemplos de cada grupo que pertence ao mesmo grupo verdadeiro.",
               "Pureza de 90%: quase todo grupo corresponde a um regime verdadeiro."),
    "pca": ("componentes principais", "principal components, PCA",
            "Um jeito de resumir várias variáveis em poucas, achando as direções em que os dados mais se espalham.",
            "Resumir uso, frequência e temperatura em um só componente."),
    "componente": ("componente", "component",
                   "Uma das direções que a análise de componentes principais encontra, da que mais explica a variação para a que menos explica.",
                   "O 1º componente explica 60% da variação."),
}

_PADRAO = re.compile(r"⟦([a-z0-9_]+)(?:\|([^⟧]+))?⟧")


def definicao(chave: str) -> tuple[str, str, str, str]:
    return TERMOS[chave]


def segmentos(texto: str) -> list[tuple[str, str | None]]:
    """Quebra um texto em pedaços (texto, chave do glossário ou None)."""
    saida: list[tuple[str, str | None]] = []
    fim = 0
    for m in _PADRAO.finditer(texto):
        if m.start() > fim:
            saida.append((texto[fim:m.start()], None))
        chave = m.group(1)
        if chave not in TERMOS:
            raise KeyError(f"termo fora do glossário: {chave}")
        saida.append((m.group(2) or TERMOS[chave][0], chave))
        fim = m.end()
    if fim < len(texto):
        saida.append((texto[fim:], None))
    return saida


def chaves_usadas(texto: str) -> set[str]:
    return {m.group(1) for m in _PADRAO.finditer(texto)}


def texto_puro(texto: str) -> str:
    return "".join(t for t, _ in segmentos(texto))
