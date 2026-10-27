"""Textos da Lição 3 · Dados sintéticos com gabarito (importados por `lab.textos`)."""

L3_PASSOS = ["Gerar os dados", "O que o modelo descobre", "Estragar de propósito", "Poeira escondida",
             "Usar nas outras lições", "Resumo e perguntas"]

# ---- passo 1 ----
L3_P1 = ("Nas outras lições você não sabia a resposta certa. Aqui você **inventa os dados**, então sabe exatamente como a "
         "temperatura é calculada: esse é o ⟦gabarito⟧. Isso permite conferir o que o modelo descobre. Mexa nos controles: os "
         "dados são gerados na hora, e a mesma ⟦semente⟧ dá sempre os mesmos dados.")
L3_CONTROLES = {
    "dias": "Dias de dados: {v}",
    "ruido_c": "Ruído: {v} °C",
    "efeito_uso": "Efeito do uso: {v} °C por 1% de uso",
    "efeito_tomada": "Efeito de estar na tomada: {v} °C",
    "poeira_por_dia": "Poeira acumulando: {v} °C por dia",
    "episodios": "Episódios estranhos escondidos (Lição 2): {v}",
    "correlacao_uso_freq": "Uso e frequência andam juntos: {v}",
}
L3_SEMENTE = "Semente do sorteio:"
L3_NOVO_SORTEIO = "Novo sorteio"
L3_PADRAO = "Valores padrão"
L3_P1_GABARITO_TITULO = "O gabarito (a verdade)"
L3_P1_GABARITO = ("temperatura = {base} °C + variação do dia (±{amp} °C) + **{uso}** °C × uso (%) + **{tomada}** °C se estiver na tomada "
                  "+ **{poeira}** °C × dia + uma ⟦deriva⟧ lenta de ±{deriva} °C + ⟦ruido⟧ de {ruido} °C.\n"
                  "A frequência da CPU **não esquenta nada** (efeito 0): ela só anda junto com o uso.")
L3_P1_GRAFICO = "Temperatura × uso nos dados gerados"
L3_P1_NOTA = "{n} minutos em {dias} dias (das 07h às 22h)."

# ---- passo 2 ----
L3_P2 = ("Agora um ⟦modelo⟧ linear tenta **descobrir** esses números olhando só as ⟦entradas⟧ (uso, frequência, tomada, hora e dia), "
         "sem ver o gabarito. Cada ⟦coeficiente⟧ diz quanto a previsão muda quando a entrada aumenta uma unidade. "
         "Compare o que ele achou com a verdade.")
L3_TAB_COLUNAS = ("Entrada", "Verdade", "Descoberto", "Erro")
L3_TAB_LINHAS = {
    "intercepto": "Temperatura base (°C)",
    "uso": "Uso da CPU (°C por 1%)",
    "freq": "Frequência (°C por MHz)",
    "tomada": "Na tomada (°C)",
    "dia": "Dia (°C por dia)",
    "hora_sen": "Hora do dia: seno",
    "hora_cos": "Hora do dia: cosseno",
}
L3_P2_METRICAS = ("Nos minutos de ⟦teste⟧, o ⟦erro_medio⟧ foi de **{mae} °C** · nota ⟦r2⟧ **{r2}**. "
                  "O que sobra é o ⟦ruido⟧ e a ⟦deriva⟧ lenta, que nenhum modelo consegue prever.")
L3_P2_PERTO = "O uso e a tomada ficaram perto do gabarito: com bastante dado e pouco ruído, o modelo descobre a relação."
L3_P2_LONGE = "Alguma linha ficou longe do gabarito: veja os controles do passo 1 (menos dados ou mais ruído pioram a descoberta)."
L3_P2_FREQ = "Repare na frequência: a verdade é zero, mas o modelo pode achar um valor pequeno por acaso."
L3_ERRO_ABS = "{v} (abs.)"

# ---- passo 3 ----
L3_P3 = ("Vamos **estragar de propósito** para ver o que atrapalha o modelo. Cada barra é o erro médio, em %, do coeficiente do "
         "**uso** (verdade: 0,35), em 8 sorteios diferentes, para não depender de sorte.")
L3_P3_GRAF = "Erro médio do coeficiente do uso (%), média de 8 sorteios"
L3_CENARIOS = ["Padrão (14 dias)", "Muito ruído (6 °C)", "Poucos dados (60 minutos)",
               "Poucos dados + uso e frequência quase iguais (0,95)"]
L3_P3_TAB = "{cenario}: frequência \"esquenta\" {freq} °C por 500 MHz (verdade 0) · erro médio de previsão {mae} °C"
L3_P3_RUIDO = ("**Ruído:** o erro de previsão sobe de {a} para {b} °C, porque o ⟦ruido⟧ não tem como ser previsto. Mas, com muitos dados, "
               "o coeficiente do uso ainda é achado (erro de {ec}%). Dado em abundância protege a descoberta.")
L3_P3_POUCOS = ("**Poucos dados:** com 60 minutos, o erro do coeficiente do uso sobe de {a}% para {b}%: o acaso pesa mais e o "
                "resultado oscila de sorteio para sorteio.")
L3_P3_COLINEAR = ("**Entradas que andam juntas** (⟦colinearidade⟧): o erro do coeficiente do uso vai de {a}% para {b}% e a frequência "
                  "passa a \"esquentar\" {freq} °C por 500 MHz, sem esquentar nada de verdade. O modelo não sabe a quem atribuir o efeito.")
L3_P3_PREVISAO_IGUAL = "E repare: o erro de previsão praticamente não mudou ({a} → {b} °C). A previsão pode continuar boa mesmo com os coeficientes errados."
L3_P3_PREVISAO_MUDOU = "O erro de previsão passou de {a} para {b} °C."
L3_P3_CALCULANDO = "Calculando os cenários…"

# ---- passo 4 ----
L3_P4 = ("A poeira vai se acumulando e a máquina esquenta um pouco mais **a cada dia**, sem que ninguém perceba. Escolha quanto e "
         "veja se os modelos acham: o da Lição 2 (que olha o ⟦residuo⟧ semanal e não conhece o dia) e o linear deste passo "
         "(que tem a coluna \"dia\").")
L3_P4_CONTROLE = "Poeira: {v} °C por dia (21 dias)"
L3_P4_BOTAO = "Treinar e ver a tendência"
L3_P4_RESULT = ("Verdade: **{verdade} °C por semana**. O modelo da Lição 2 achou **{achada} °C por semana**. "
                "O modelo linear, com a coluna \"dia\", achou **{dia} °C por dia** (verdade {poeira}). "
                "Os números não batem exatamente porque o acaso sempre mexe um pouco.")
L3_P4_SEM_POEIRA = "Sem poeira, os dois modelos devem achar quase zero: o que sobrar é acaso."
L3_P4_GRAF = "Resíduo mediano de cada semana (°C)"

# ---- passo 5 ----
L3_P5 = ("Os dados que você montou valem também para as outras lições. Escolha uma e veja o mesmo assunto com os seus números: "
         "na Lição 1, o erro de teste muda com o ruído; na Lição 2, o que é normal muda com a poeira e os episódios.")
L3_P5_ABRIR_1 = "Abrir a Lição 1 com estes dados"
L3_P5_ABRIR_2 = "Abrir a Lição 2 com estes dados"
L3_P5_NOTA = ("A Lição 2 precisa de 21 dias ou mais e de episódios estranhos escondidos: se você não escolheu esses valores, ela usa "
              "21 dias, 10 episódios e poeira de 0,2 °C por dia.")

# ---- passo 6 ----
L3_P6 = "O que você viu nesta lição:"
L3_RESUMO = [
    "Com ⟦dados_sinteticos⟧ você conhece o ⟦gabarito⟧ e consegue **conferir** o que o modelo descobre. Com dados reais, ninguém tem o gabarito.",
    "Mais ⟦ruido⟧ e menos dados pioram a descoberta dos ⟦coeficiente|coeficientes⟧; a mesma ⟦semente⟧ repete tudo igualzinho.",
    "Entradas que andam juntas (⟦colinearidade⟧) enganam os coeficientes, mesmo quando a previsão continua boa.",
    "Um desgaste lento, como a poeira, aparece como ⟦tendencia⟧ no resíduo semanal.",
]
L3_QUIZ = [
    {"pergunta": "Por que usar dados sintéticos para aprender?",
     "opcoes": ["Porque são mais bonitos.",
                "Porque você conhece o ⟦gabarito⟧ e pode conferir o que o modelo descobre.",
                "Porque são sempre melhores que os dados reais."],
     "correta": 1,
     "explicacao": "Nos dados reais ninguém sabe a resposta certa; nos sintéticos você sabe, e por isso pode medir o acerto do modelo. Mas eles não dizem nada sobre o seu computador."},
    {"pergunta": "O modelo deu um coeficiente alto para a frequência, mas a frequência não esquenta nada. O que provavelmente aconteceu?",
     "opcoes": ["A frequência esquenta de verdade e o gabarito está errado.",
                "A ⟦colinearidade⟧: a frequência anda junto com o uso e o modelo atribuiu o efeito à entrada errada.",
                "O modelo não treinou."],
     "correta": 1,
     "explicacao": "Quando duas entradas andam juntas, os ⟦coeficiente|coeficientes⟧ ficam instáveis, embora a previsão possa continuar boa."},
    {"pergunta": "O que acontece com a descoberta do modelo se você reduz muito o número de dias?",
     "opcoes": ["Fica mais instável: o acaso pesa mais e o resultado muda de sorteio para sorteio.",
                "Fica mais precisa, porque há menos confusão.",
                "Não muda nada."],
     "correta": 0,
     "explicacao": "Poucos exemplos dão pouca informação para separar o efeito real do ⟦ruido⟧."},
]
