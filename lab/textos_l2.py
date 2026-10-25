"""Textos da Lição 2 · "Quente para o que você faz" (importados por `lab.textos`)."""

L2_PASSOS = ["A ideia", "Aprender o normal", "Medido × esperado", "O limite do estranho", "Tendência por semana",
             "Resumo e perguntas"]

L2_P1 = ("Uma temperatura de 70 °C é normal ou é estranha? **Depende do que o computador está fazendo.** Com a CPU a 90% de uso, "
         "70 °C é o esperado. Com a máquina quase parada, 70 °C é um sinal de alerta: algo está esquentando mais do que "
         "deveria (poeira, pasta térmica velha, um programa escondido).\n\n"
         "Por isso, em vez de olhar só a temperatura, comparamos a temperatura **medida** com a ⟦esperado⟧ para aquele "
         "momento. A diferença entre as duas é o ⟦residuo⟧. Quando o resíduo fica alto por um bom tempo, temos uma ⟦anomalia⟧.")
L2_P1_GRAFICO = "As duas bolinhas têm a mesma temperatura. A verde é normal (uso alto); a vermelha é estranha (uso baixo)."
L2_P1_NORMAL = "{temp} °C com {uso}% de uso: normal"
L2_P1_ESTRANHO = "{temp} °C com {uso}% de uso: estranho"
L2_P1_EIXO_X = "uso da CPU (%)"
L2_P1_EIXO_Y = "temperatura (°C)"
L2_P1_ESPERADO = "temperatura esperada"
L2_FONTE_SINT = ("Nesta lição, os ⟦dados_sinteticos⟧ têm {dias} dias, poeira se acumulando ({poeira} °C por dia) e {n} episódios "
                 "estranhos escondidos, para você conferir se o modelo os acha. Na Lição 3 você controla tudo isso.")
L2_FONTE_REAL = ("Com o seu histórico real não existe ⟦gabarito⟧: você não sabe quais minutos eram estranhos de verdade. "
                 "Avalie olhando os episódios que o modelo achar.")

L2_P2 = ("Primeiro o computador precisa aprender o que é **normal**. Treinamos um ⟦modelo⟧ nos primeiros 70% do tempo "
         "({n} minutos, de {ini} a {fim}) com quatro ⟦entradas⟧: uso da CPU, frequência, se está na tomada e hora do dia.\n\n"
         "A rotação da ventoinha **não entra**: ela é ⟦consequencia|consequência⟧ do calor (Lição 1) e esconderia justamente o que queremos achar.")
L2_P2_ERRO = ("Depois de treinado, o modelo prevê a temperatura de minutos que **nunca viu**. O ⟦erro_tipico⟧ dessas previsões é de "
              "**{erro} °C**: variações menores que isso são normais.")
L2_P2_COMO = ("O erro típico é medido em 5 blocos de tempo que ficaram de fora do ⟦treino⟧ em cada rodada; medi-lo nos próprios "
              "minutos de treino daria um número otimista demais.")

L2_P3 = ("Escolha um dia do período de prova e compare o que foi **medido** com o que era **esperado**. O gráfico de baixo mostra o "
         "⟦residuo⟧: quando a linha passa do limite, a máquina estava mais quente do que o normal para o que fazia.")
L2_P3_DIA = "Dia:"
L2_P3_GRAF_A = "Temperatura medida × esperada (°C)"
L2_P3_GRAF_B = "Resíduo: medido − esperado (°C)"
L2_P3_LEG_MEDIDO = "medido"
L2_P3_LEG_ESPERADO = "esperado"
L2_P3_LEG_LIMITE = "limite ({k}× erro típico)"
L2_P3_LEG_EPISODIO = "episódio marcado"
L2_P3_NENHUM = "Neste dia nenhum episódio passou do limite."
L2_P3_ACHOU = "Neste dia o modelo marcou **{n} episódio(s)**."

L2_P4 = ("Quão acima do esperado vale chamar de estranho? Esse é o limite, escolhido como múltiplo do ⟦erro_tipico⟧ "
         "(a **sensibilidade**). Limite baixo acha mais problemas, mas gera ⟦falso_alarme|falsos alarmes⟧ (avisa sem ter nada); "
         "limite alto evita alarme à toa, mas pode deixar passar um problema real (⟦alarme_perdido⟧).\n\n"
         "Só conta como episódio o que fica acima do limite por **10 minutos seguidos**, com a linha suavizada em 5 minutos.")
L2_P4_CONTROLE = "Sensibilidade: limite = {k}× o erro típico ({lim} °C acima do esperado)"
L2_P4_GRAF = "Resíduo suavizado no período de prova (°C)"
L2_P4_LEG_LIMITE = "limite"
L2_P4_LEG_MARCADO = "episódio marcado"
L2_P4_LEG_VERDADE = "episódio de verdade (gabarito)"
L2_P4_RESULT_SINT = ("Marcados: **{ep} episódio(s)** ({minutos} minutos). Dos {n} episódios escondidos você achou **{achou}** "
                     "({rec}%). Falsos alarmes: **{fa}%** dos minutos normais.")
L2_P4_RESULT_REAL = ("Marcados: **{ep} episódio(s)** ({minutos} minutos). Olhe cada um no gráfico e pergunte: o que a máquina "
                     "estava fazendo naquele momento?")
L2_P4_RESULT_SEM_GABARITO = ("Marcados: **{ep} episódio(s)** ({minutos} minutos). Nos dados que você montou não há episódios escondidos: "
                            "qualquer marcação aqui é ⟦falso_alarme|falso alarme⟧. Falsos alarmes: **{fa}%** dos minutos.")
L2_P4_BAIXA = "Com um limite tão baixo o modelo marca muita coisa que é normal: cuidado com os falsos alarmes."
L2_P4_ALTA = "Com um limite tão alto, episódios de verdade passam batido: é o alarme perdido."
L2_P4_OK = "Ponto de equilíbrio: acha a maior parte dos episódios sem gerar falsos alarmes."

L2_P5 = ("E se a máquina esquenta um pouco mais **a cada semana**, sem nenhum episódio gritante? A ⟦mediana⟧ do resíduo de cada "
         "semana mostra isso: se ela sobe semana após semana, a máquina pode estar esquentando mais para fazer o mesmo trabalho. "
         "Esse é o sinal de uma ⟦tendencia⟧ de desgaste (poeira, pasta térmica, ventoinha).")
L2_P5_GRAF = "Resíduo mediano de cada semana (°C)"
L2_P5_SEMANA = "semana {n}"
L2_P5_SOBE = ("A tendência é de **{incl} °C por semana**: para o mesmo trabalho, a máquina está esquentando mais. Vale checar poeira, "
              "saídas de ar, pasta térmica e ventoinha. Isto é um indício, não um diagnóstico.")
L2_P5_PLANA = "Sem tendência clara ({incl} °C por semana): a temperatura para o mesmo trabalho se manteve estável."
L2_P5_DESCE = ("A temperatura para o mesmo trabalho **diminuiu** ({incl} °C por semana): pode ter havido limpeza, troca de pasta "
               "ou mudança de ambiente.")
L2_P5_POUCAS = ("Para estimar a tendência são necessárias pelo menos 3 semanas com dados; este conjunto tem {n}. "
                "Dá para ver como ela aparece com dados sintéticos em que a poeira vai se acumulando.")
L2_P5_BOTAO_POEIRA = "Ver com poeira simulada (21 dias)"

L2_P6 = "O que você viu nesta lição:"
L2_RESUMO = [
    "A mesma temperatura pode ser normal ou estranha: o que importa é a diferença para a ⟦esperado|temperatura esperada⟧ (o ⟦residuo⟧).",
    "O ⟦erro_tipico⟧ diz quanto de variação é normal; só o que passa dele por vários minutos seguidos vira ⟦anomalia⟧.",
    "Baixar o limite acha mais problemas, mas cria ⟦falso_alarme|falsos alarmes⟧; subir deixa passar problemas reais (⟦alarme_perdido⟧).",
    "A ⟦mediana⟧ semanal do resíduo revela a ⟦tendencia⟧ de a máquina esquentar mais para o mesmo trabalho.",
]
L2_QUIZ = [
    {"pergunta": "Por que olhar a temperatura esperada, em vez de só a temperatura medida?",
     "opcoes": ["Porque 70 °C é sempre perigoso.",
                "Porque a mesma temperatura pode ser normal com carga alta e estranha com a máquina parada.",
                "Porque a temperatura esperada é sempre menor."],
     "correta": 1,
     "explicacao": "O que importa é o ⟦residuo⟧: a diferença para o que era esperado naquela situação."},
    {"pergunta": "Se você baixa o limite para achar mais problemas, o que tende a acontecer?",
     "opcoes": ["Aumentam os ⟦falso_alarme|falsos alarmes⟧.",
                "Nada: o modelo continua igual.",
                "O modelo fica mais preciso."],
     "correta": 0,
     "explicacao": "Há uma troca: limite baixo pega mais problemas, mas também marca minutos normais."},
    {"pergunta": "A mediana semanal do resíduo sobe 1,4 °C por semana. O que isso sugere?",
     "opcoes": ["Que a máquina está esquentando mais para o mesmo trabalho: vale checar poeira, pasta térmica e ventoinha.",
                "Que o modelo piorou.",
                "Que o sensor quebrou."],
     "correta": 0,
     "explicacao": "Uma ⟦tendencia⟧ de alta no resíduo indica desgaste ou sujeira. É um indício, não um diagnóstico."},
]
