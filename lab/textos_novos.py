"""Textos dos passos novos das lições 1 a 3 (v1.2): validação cruzada, boosting, Isolation Forest, Ridge e Lasso.

Os passos novos entram antes do "Resumo e perguntas" de cada lição. As frases com números são montadas na tela com
valores medidos; aqui ficam só os modelos. Importado por `lab.textos`.
"""
import lab.textos as _T

# ---------------------------------------------------------------- Lição 1
L1_PASSOS = _T.L1_PASSOS[:-1] + ["Escolher sem olhar a prova", "Muitas árvores pequenas"] + _T.L1_PASSOS[-1:]

L1_P7 = ("No passo 3 você escolheu a ⟦profundidade⟧ olhando o próprio ⟦teste⟧, e a lição avisou: isso é uma pequena trapaça, "
         "porque o teste deixa de ser uma prova inédita. Há um jeito honesto de escolher: a ⟦validacao_cruzada⟧.\n\n"
         "Dividimos só o ⟦treino⟧ em 5 ⟦bloco|blocos⟧ seguidos no tempo. Treinamos com 4 deles e conferimos no que ficou de fora, "
         "e repetimos até cada bloco ter sido a conferência uma vez. A profundidade de menor erro médio nessa conferência é a "
         "escolhida, **sem abrir o teste**.")
L1_P7_GRAF = "Erro na validação (média dos 5 blocos, com a variação entre eles) para cada profundidade"
L1_P7_LEGENDA_VALIDACAO = "erro na validação"
L1_P7_LEGENDA_TESTE = "erro no teste"
L1_P7_ESCOLHA = ("A validação cruzada escolheu a **profundidade {d}**: erro de {e} °C, variando {dp} °C de um bloco para outro. "
                 "O teste ainda não foi aberto.")
L1_P7_BOTAO = "Abrir o teste agora"
L1_P7_REVELA_IGUAL = ("Abrindo o teste: com a profundidade {d} o erro é de **{et} °C**. É a mesma profundidade que o próprio teste "
                      "escolheria.")
L1_P7_REVELA_DIFERENTE = ("Abrindo o teste: com a profundidade {d} o erro é de **{et} °C**. O teste escolheria a profundidade {p} "
                          "({ep} °C), uma diferença de {dif} °C: {adjetivo}, e você chegou perto sem usar a prova.")
L1_P7_PEQUENA = "pequena"
L1_P7_NOTAVEL = "um pouco maior"
L1_P7_NOTA = ("A variação entre os blocos mostra o quanto a escolha é incerta: quando duas profundidades diferem menos que essa "
              "variação, qualquer uma serve.")

L1_P8 = ("Uma única ⟦arvore⟧ decide sozinha. No ⟦boosting⟧ são **muitas árvores pequenas em fila**: cada uma tenta corrigir o erro "
         "que as anteriores deixaram. Mexa no número de rodadas e compare com a melhor árvore única, com a floresta (da Lição 2) "
         "e com o modelo linear.")
L1_P8_ROTULO = "Rodadas de boosting: {n}"
L1_P8_GRAF = "Erro por rodada (°C)"
L1_P8_LEGENDA_TREINO = "treino"
L1_P8_LEGENDA_TESTE = "teste"
L1_P8_LINHA_ARVORE = "melhor árvore"
L1_P8_LINHA_FLORESTA = "floresta"
L1_P8_LINHA_LINEAR = "modelo linear"
L1_P8_VALORES = "Com **{n}** rodadas: erro de {tr} °C no treino e de **{te} °C** no teste."
L1_P8_COMPARA = ("Para comparar, no teste: melhor árvore única {arv} °C, floresta {flo} °C e modelo linear {lin} °C. "
                 "O menor erro do boosting foi {m} °C, com {r} rodadas.")
L1_P8_MELHOR = "Isso é melhor que a melhor árvore única ({arv} °C)."
L1_P8_PIOR = "Isso não ganha da melhor árvore única ({arv} °C)."
L1_P8_LINEAR_EMPATA = "Fica perto do modelo linear, o que faz sentido: neste mundo a temperatura depende quase em linha reta do uso."
L1_P8_LINEAR_VENCE = "O modelo linear ainda vai melhor: neste mundo o padrão é simples, e mais complexidade não compra nada."
L1_P8_POUCAS = "Com poucas rodadas o modelo ainda é simples demais (⟦subajuste⟧): o erro cai rápido nas primeiras."
L1_P8_MUITAS = ("Depois de um tempo o erro de teste para de cair e fica quase parado: mais rodadas custam tempo e não melhoram "
                "(e, sem freio, podem começar a ⟦sobreajuste|sobreajustar⟧).")

L1_RESUMO = _T.L1_RESUMO + [
    "A ⟦validacao_cruzada⟧ escolhe a complexidade usando só o ⟦treino⟧, em ⟦bloco|blocos⟧: o ⟦teste⟧ continua sendo uma prova inédita.",
    "O ⟦boosting⟧ corrige erros em sequência com árvores pequenas; ajuda, mas num mundo simples o modelo linear ainda pode empatar.",
]
L1_QUIZ = _T.L1_QUIZ + [
    {"pergunta": "Qual é a vantagem da ⟦validacao_cruzada⟧ para escolher a profundidade da árvore?",
     "opcoes": ["Escolhe usando só o treino, e o teste continua sendo uma prova inédita.",
                "Dispensa o teste, que passa a ser inútil.",
                "Faz a árvore treinar mais rápido.",
                "Garante que o erro será zero."],
     "correta": 0,
     "explicacao": "O teste só deve ser aberto no fim; a validação em ⟦bloco|blocos⟧ faz a escolha sem ele."},
    {"pergunta": "No ⟦boosting⟧, cada árvore nova tenta…",
     "opcoes": ["Corrigir o erro que as árvores anteriores deixaram.",
                "Repetir a previsão da primeira árvore.",
                "Decorar o conjunto de teste.",
                "Substituir todas as anteriores."],
     "correta": 0,
     "explicacao": "São árvores pequenas em fila, cada uma focada no que ainda está errado."},
]

# ---------------------------------------------------------------- Lição 2
L2_PASSOS = _T.L2_PASSOS[:-1] + ["Achar o estranho sem prever"] + _T.L2_PASSOS[-1:]

L2_P7 = ("O método desta lição primeiro **prevê** a temperatura esperada e olha o resíduo. Há outro jeito de achar o estranho, "
         "sem prever nada: o ⟦isolation_forest⟧. Ele faz perguntas aleatórias sobre cada minuto (\"o uso passa de 62%?\") e conta "
         "quantas perguntas bastam para **isolar** aquele minuto dos demais. Minutos raros são isolados rápido.\n\n"
         "Escolha que percentual dos minutos do ⟦treino⟧ deve ser considerado estranho e compare, no período de prova, com o "
         "método do ⟦residuo⟧.")
L2_P7_ROTULO = "Percentual de minutos considerados estranhos: {p}%"
L2_P7_FAIXA_VERDADE = "episódios injetados (gabarito)"
L2_P7_FAIXA_RESIDUO = "método do resíduo"
L2_P7_FAIXA_ISOLAMENTO = "Isolation Forest"
L2_P7_TABELA_TITULO = "Resultado no período de prova"
L2_P7_LINHA_SINT = "**{nome}:** achou {a} de {n} episódios reais e marcou {f}% dos minutos normais por engano."
L2_P7_LINHA_REAL = "**{nome}:** marcou {e} episódios no período de prova."
L2_P7_FIM_SINT_RES = ("O método do resíduo usa o que sabemos (a temperatura depende do uso) e por isso enxerga um calor "
                      "fora do lugar. O Isolation Forest não sabe disso: vê só se o minuto é raro, e um minuto quente "
                      "com carga alta não é raro.")
L2_P7_FIM_SINT_ISO_MELHOR = "Neste conjunto o Isolation Forest achou mais episódios que o método do resíduo; confira com outras sementes na Lição 3."
L2_P7_FIM_REAL = ("Com o seu histórico real não há gabarito: compare onde os dois métodos marcam. Se marcam os mesmos períodos, a "
                  "evidência é mais forte; se divergem, vale olhar o que aconteceu naqueles minutos.")
L2_METODO_RESIDUO = "Método do resíduo"
L2_METODO_ISOLAMENTO = "Isolation Forest"

L2_RESUMO = _T.L2_RESUMO + [
    "O ⟦isolation_forest⟧ acha minutos raros sem prever a temperatura; usar o que sabemos (a ⟦esperado|temperatura esperada⟧) costuma ser melhor para achar calor fora do lugar.",
]
L2_QUIZ = _T.L2_QUIZ + [
    {"pergunta": "Por que o ⟦isolation_forest⟧ pode deixar passar um episódio de calor com a CPU em carga alta?",
     "opcoes": ["Porque ele não sabe que o calor deveria ser menor para aquele uso: só vê se o minuto é raro.",
                "Porque só funciona com dados reais.",
                "Porque ignora a temperatura.",
                "Porque exige 3 semanas de dados."],
     "correta": 0,
     "explicacao": "Calor alto com carga alta é um minuto comum; o que o torna estranho é a relação com o uso."},
]

# ---------------------------------------------------------------- Lição 3
L3_PASSOS = _T.L3_PASSOS[:-1] + ["Domar entradas que andam juntas"] + _T.L3_PASSOS[-1:]

L3_P7 = ("Quando duas ⟦entradas⟧ andam quase juntas (uso e frequência), o modelo linear reparte o mérito entre elas de forma "
         "instável. A ⟦regularizacao⟧ aceita um pequeno erro para estabilizar: ela **penaliza coeficientes grandes**. O "
         "⟦ridge⟧ encolhe todos os ⟦coeficiente|coeficientes⟧; o ⟦lasso⟧ encolhe e ainda **zera** os que não ajudam.\n\n"
         "Aqui a ⟦correlacao|correlação⟧ entre uso e frequência é de 0,95 e você escolhe quantos minutos o modelo vê. Lembre: no ⟦gabarito⟧ "
         "a frequência **não esquenta nada**.")
L3_P7_FORCA = "Força da regularização: {f}"
L3_P7_MINUTOS = "Minutos de dados: {n}"
L3_P7_NOVA_AMOSTRA = "Sortear outra amostra"
L3_P7_GRAF_USO = "Efeito do uso (°C por 1%)"
L3_P7_GRAF_FREQ = "Efeito da frequência (°C por 500 MHz)"
L3_P7_GRAF_ERRO = "Erro de previsão no teste (°C)"
L3_P7_LEG_VERDADE = "verdade"
L3_P7_LEG_LINEAR = "linear"
L3_P7_LEG_RIDGE = "ridge"
L3_P7_LEG_LASSO = "lasso"
L3_P7_VALORES = ("Com força {f}: o **ridge** diz que o uso vale {ru} °C por 1% (verdade {vu}) e a frequência {rf} °C por 500 MHz; "
                 "o **lasso** diz {lu} e {lf}. Sem regularizar, o modelo linear diz {nu} e {nf}.")
L3_P7_ZEROU = "O lasso zerou: {lista}."
L3_P7_ZEROU_NADA = "O lasso não zerou nenhuma entrada com esta força."
L3_P7_FREQ_ZERADA = "Ele zerou a frequência, que é justamente a entrada sem efeito real: acertou."
L3_P7_ERRO_PREVISAO = "Erro de previsão no teste: linear {el} °C, ridge {er} °C, lasso {es} °C."
L3_P7_REGULARIZAR_DEMAIS = "Com força demais, os dois passam a errar mais: regularizar demais vira ⟦subajuste⟧."
L3_P7_NOTA = ("Medido com poucos minutos e entradas muito parecidas: o ridge reparte o mérito entre uso e frequência e encolhe o "
              "efeito do uso; o lasso tende a escolher uma das duas. Nenhum dos dois é mágico: o resultado varia de amostra para "
              "amostra, então sorteie outras.")

L3_RESUMO = _T.L3_RESUMO + [
    "A ⟦regularizacao⟧ troca um pouco de erro por estabilidade: o ⟦ridge⟧ encolhe os ⟦coeficiente|coeficientes⟧ e o ⟦lasso⟧ também os zera; regularizar demais piora a previsão.",
]
L3_QUIZ = _T.L3_QUIZ + [
    {"pergunta": "O que o ⟦lasso⟧ faz que o ⟦ridge⟧ não faz?",
     "opcoes": ["Zera os coeficientes das entradas que não ajudam.",
                "Aumenta todos os coeficientes.",
                "Dispensa o conjunto de teste.",
                "Troca o modelo por uma ⟦arvore|árvore⟧."],
     "correta": 0,
     "explicacao": "O ridge só encolhe; o lasso pode levar coeficientes exatamente a zero, escolhendo entradas."},
]
