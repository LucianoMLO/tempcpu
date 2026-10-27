"""Textos da Lição 4 · "Em qual faixa está?" (classificação). Importado por `lab.textos`."""

L4_PASSOS = ["A pergunta", "Um primeiro classificador", "A acurácia engana", "Matriz de confusão", "Precisão e revocação",
             "Outros classificadores", "Resumo e perguntas"]

L4_P1 = ("Até aqui o ⟦modelo⟧ previa um **número** (a temperatura). Na ⟦classificacao⟧ ele escolhe uma **categoria**: aqui, "
         "\"vai passar de um limite?\" (sim ou não). Cada categoria é uma ⟦classe⟧.\n\n"
         "Escolha o limite. Repare que quase sempre a classe que interessa (o calor) é **rara**: é a chamada "
         "⟦desbalanceada|classe desbalanceada⟧, e ela muda tudo na hora de avaliar.")
L4_P1_ROTULO = "Limite de temperatura: {c} °C"
L4_P1_GRAF = "Quantos minutos em cada temperatura (os acima do limite em vermelho)"
L4_P1_RESUMO = ("Acima de {c} °C estão **{p}%** dos minutos ({n} de {t}). No treino são {pt}% e no teste {pe}%.")
L4_P1_EIXO_X = "temperatura (°C)"
L4_P1_EIXO_Y = "minutos"
L4_P1_FONTE = ("Usamos as mesmas ⟦entradas⟧ de antes (uso, frequência, tomada e hora) e a divisão pelo tempo: os primeiros 70% "
               "formam o ⟦treino⟧ e os últimos 30% o ⟦teste⟧, a prova.")

L4_P2 = ("A ⟦regressao_logistica⟧ (apesar do nome, ela classifica) calcula, para cada minuto, uma **probabilidade** de estar "
         "acima do limite, de 0% a 100%. Se passar de 50%, ela avisa \"quente\".")
L4_P2_GRAF = "Probabilidade de estar acima do limite no período de prova (linha) e os minutos realmente acima (faixa vermelha)"
L4_P2_LEGENDA_PROB = "probabilidade"
L4_P2_LEGENDA_REAL = "acima do limite de verdade"
L4_P2_ACERTO = "Ela acertou **{a}%** dos minutos do teste ({n} minutos)."

L4_P3 = ("Acertar {a}% parece ótimo. Mas considere um \"modelo\" preguiçoso que **nunca avisa nada**: ele acerta todos os "
         "minutos normais. Como o calor é raro, isso já dá uma nota alta.")
L4_P3_BARRAS = "Comparação no teste"
L4_P3_PREGUICOSO = "Nunca avisa"
L4_P3_LOGISTICA = "Regressão logística"
L4_P3_ACURACIA = "⟦acuracia|Acurácia⟧ (acertos em todos os minutos)"
L4_P3_REVOCACAO = "Calor encontrado (dos minutos quentes, quantos foram avisados)"
L4_P3_CONCLUSAO = ("O modelo preguiçoso tem **{pa}%** de ⟦acuracia⟧ e acha **0%** do calor: a nota alta engana. O modelo de verdade "
                   "tem {la}% e acha {lr}% do calor. Com classe rara, olhe também para os erros de cada tipo.")

L4_P4 = ("A ⟦matriz_confusao⟧ conta, no teste, os quatro casos possíveis. Os dois erros são diferentes, e já os conhecemos da Lição 2: "
         "o ⟦falso_alarme|falso alarme⟧ (avisou sem haver calor) e o ⟦alarme_perdido⟧ (houve calor e ela não avisou).")
L4_P4_TITULO_REAL = "O que aconteceu de verdade"
L4_P4_TITULO_PREVISTO = "O que o modelo previu"
L4_P4_LINHAS = ["Normal", "Quente"]
L4_P4_CELULAS = ["Acertou: normal", "Falso alarme", "Alarme perdido", "Acertou: quente"]
L4_P4_FRASE = ("Dos {q} minutos quentes, o modelo avisou {vp} e perdeu {fn}. Dos {nm} minutos normais, deu alarme falso em {fp}.")

L4_P5 = ("Duas medidas resumem os erros. A ⟦precisao⟧: dos avisos que o modelo deu, quantos eram calor de verdade. A "
         "⟦revocacao⟧: dos minutos quentes, quantos o modelo avisou.\n\n"
         "O **limite de decisão** controla a troca: com limite baixo ele avisa à menor dúvida (acha mais calor, mas erra mais "
         "avisos); com limite alto só avisa quando tem certeza (avisos mais certos, mas perde calor).")
L4_P5_ROTULO = "Limite de decisão: avisar quando a probabilidade passar de {p}%"
L4_P5_GRAF = "Precisão e revocação para cada limite de decisão"
L4_P5_LEG_PRECISAO = "precisão"
L4_P5_LEG_REVOCACAO = "revocação"
L4_P5_VALORES = ("Com este limite: **{al}** avisos; precisão de **{pr}%** ({vp} dos avisos eram calor) e revocação de **{rv}%** "
                 "({vp} dos {q} minutos quentes foram achados).")
L4_P5_SEM_AVISOS = "Com este limite o modelo não avisa nenhuma vez: a precisão não existe e a revocação é 0%."
L4_P5_DICA = "Qual limite é o melhor? Depende do que custa mais: perder um calor real ou dar um alarme falso."

L4_P6 = ("Há outros jeitos de classificar. A ⟦arvore⟧ de decisão faz perguntas em sequência. Os ⟦vizinhos|k-vizinhos⟧ olham os "
         "k minutos mais parecidos (em uso, frequência, tomada e hora) e votam. Para isso as ⟦entradas⟧ precisam estar na mesma "
         "escala, senão a frequência (milhares de MHz) atropelaria o uso (0 a 100).")
L4_P6_ROTULO = "k (quantos vizinhos votam): {k}"
L4_P6_COLUNAS = ["Modelo", "Acurácia", "Precisão", "Revocação"]
L4_P6_NOMES = {"logistica": "Regressão logística", "arvore": "Árvore de decisão", "vizinhos": "k-vizinhos"}
L4_P6_CONCLUSAO = ("Neste conjunto os três ficam parecidos (acurácia entre {a1}% e {a2}%): quando o padrão é simples, o método importa "
                   "menos que a avaliação cuidadosa. Com k = 1 o k-vizinhos decora o treino; com k muito grande ele fica simples demais.")

L4_P7 = "O que você viu nesta lição:"
L4_RESUMO = [
    "A ⟦classificacao⟧ escolhe uma ⟦classe⟧; quando a classe que interessa é rara (⟦desbalanceada|classe desbalanceada⟧), a ⟦acuracia⟧ engana.",
    "A ⟦matriz_confusao⟧ separa o ⟦falso_alarme|falso alarme⟧ do ⟦alarme_perdido⟧, que têm custos diferentes.",
    "⟦precisao⟧ e ⟦revocacao⟧ trocam de lugar quando você muda o limite de decisão.",
    "Árvore, ⟦regressao_logistica|regressão logística⟧ e ⟦vizinhos|k-vizinhos⟧ são caminhos diferentes para a mesma pergunta; compare sempre com o palpite preguiçoso.",
]
L4_QUIZ = [
    {"pergunta": "Um modelo avisa \"sem calor\" o tempo todo e acerta 90% dos minutos. O que isso diz sobre ele?",
     "opcoes": ["Quase nada: com calor raro, a ⟦acuracia⟧ alta engana, e ele acha 0% do calor.",
                "Que é um ótimo modelo.",
                "Que a classe é balanceada.",
                "Que o limite está alto demais."],
     "correta": 0,
     "explicacao": "Numa ⟦classe⟧ rara, não avisar nunca já dá uma ⟦acuracia⟧ alta; por isso olhamos precisão e revocação."},
    {"pergunta": "Você baixa o limite de decisão para o modelo avisar com menos certeza. O que tende a acontecer?",
     "opcoes": ["A ⟦revocacao⟧ sobe (acha mais calor) e a ⟦precisao⟧ pode cair (mais avisos errados).",
                "Os dois sobem sempre.",
                "O modelo é treinado de novo.",
                "Os dois caem sempre."],
     "correta": 0,
     "explicacao": "Há uma troca: avisar à menor dúvida acha mais calor real, mas também dá mais ⟦falso_alarme|falsos alarmes⟧."},
    {"pergunta": "Na ⟦matriz_confusao⟧, o que é um ⟦alarme_perdido⟧?",
     "opcoes": ["Um minuto quente em que o modelo não avisou.",
                "Um aviso dado num minuto normal.",
                "Um minuto normal que ele acertou.",
                "Um minuto quente que ele acertou."],
     "correta": 0,
     "explicacao": "Houve calor e ele ficou quieto: é o erro mais perigoso quando o calor causa dano."},
]
