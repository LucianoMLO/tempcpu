"""Textos da Lição 5 · "Descobrir grupos sem gabarito" (agrupamento e componentes principais). Importado por `lab.textos`."""

L5_PASSOS = ["A ideia", "k-means", "Quantos grupos?", "Dar nome aos grupos", "Conferir com o gabarito", "Componentes principais",
             "Resumo e perguntas"]

L5_P1 = ("Nas outras lições havia uma resposta a prever (o ⟦alvo⟧). Aqui **não há nenhuma**: é o ⟦sem_rotulos|aprendizado sem rótulos⟧. "
         "A pergunta é: olhando só os números, o computador consegue achar sozinho **modos de uso** do seu computador "
         "(parado, trabalho leve, carga pesada)?\n\n"
         "Cada ponto abaixo é um minuto. Nenhum foi marcado com um nome.")
L5_P1_GRAF = "Cada ponto é um minuto: uso da CPU e temperatura"
L5_P1_EIXO_X = "uso da CPU (%)"
L5_P1_EIXO_Y = "temperatura (°C)"
L5_P1_NOTA = "{n} minutos úteis. Não existe resposta certa para conferir: o objetivo é descobrir estrutura."

L5_P2 = ("O ⟦kmeans|k-means⟧ é o ⟦agrupamento⟧ mais simples: você escolhe quantos grupos (k); o programa sorteia k ⟦centro|centros⟧, "
         "junta cada minuto ao centro mais próximo, move cada centro para o meio do seu grupo e repete até parar. As variáveis "
         "são colocadas na mesma escala antes, para a frequência (milhares de MHz) não atropelar o uso.")
L5_P2_ROTULO = "Número de grupos (k): {k}"
L5_P2_GRAF = "Os minutos pintados por grupo; o X marca o centro de cada um"
L5_P2_TAMANHOS = "Tamanho dos grupos: {t}."

L5_P3 = ("Qual é o k certo? **Não existe um k certo**, existe o mais útil. Duas pistas ajudam:\n"
         "•  a ⟦inercia|inércia⟧ mede o quão espalhados ficam os minutos dentro dos grupos: sempre cai quando k cresce, e o "
         "\"cotovelo\" da curva sugere onde parar de ganhar muito;\n"
         "•  a ⟦silhueta⟧ vai de -1 a 1 e mede o quão bem separados estão os grupos: quanto maior, melhor.")
L5_P3_GRAF_INERCIA = "Inércia (menor = grupos mais compactos)"
L5_P3_GRAF_SILHUETA = "Silhueta (maior = grupos mais separados)"
L5_P3_MELHOR = ("A silhueta é maior com **k = {k}**. Mas silhueta alta não significa grupos úteis: veja se os grupos fazem sentido "
                "para você (próximo passo).")
L5_P3_EIXO_K = "k"

L5_P4 = ("Agora a parte humana: olhe o que cada grupo tem em média e dê um nome. O programa só entrega números; "
         "**o significado é seu**. Você pode renomear (os nomes valem só nesta tela).")
L5_P4_COLUNAS = ["Grupo", "Minutos", "Uso médio", "Frequência", "Temperatura"]
L5_P4_NOME_OCIOSO = "quase parado"
L5_P4_NOME_LEVE = "trabalho leve"
L5_P4_NOME_PESADO = "carga pesada"
L5_P4_NOME_GENERICO = "grupo {n}"
L5_P4_DICA = "Escolha k = 3 no passo anterior para ver os três modos clássicos (parado, leve, pesado)."

L5_P5_SINTETICO = ("Como os ⟦dados_sinteticos⟧ têm ⟦gabarito⟧, dá para conferir: o gerador sabe em qual dos 3 regimes cada minuto "
                   "foi criado. A ⟦pureza⟧ mede quanto de cada grupo pertence a um mesmo regime verdadeiro.")
L5_P5_GRAF = "Pureza para cada k"
L5_P5_LEGENDA = "pureza"
L5_P5_VALOR = "Com **k = {k}** a pureza é de **{p}%** (100% seria cada grupo igual a um regime verdadeiro)."
L5_P5_RUIDO = ("Os regimes se misturam porque o uso muda dentro de cada um e o ⟦ruido|ruído⟧ embaralha as bordas. Na Lição 3 você pode "
               "aumentar o ruído e ver a pureza cair.")
L5_P5_TABELA = "Regime verdadeiro × grupo (minutos)"
L5_P5_REGIMES = ["Parado", "Leve", "Pesado"]
L5_P5_REAL = ("Com o seu histórico real **não há gabarito**: ninguém sabe qual é o agrupamento certo. Compare os grupos com o que você "
              "lembra do dia (reuniões, jogos, compilações) e desconfie de grupos que você não consegue explicar.")

L5_P6 = ("Os ⟦pca|componentes principais⟧ (PCA) resumem várias variáveis em poucas: o 1º ⟦componente⟧ é a direção em que os minutos "
         "mais se espalham, o 2º é a seguinte, e assim por diante. É útil para **ver** dados com muitas colunas e para descobrir "
         "que duas variáveis contam quase a mesma história.")
L5_P6_GRAF_VAR = "Quanto da variação cada componente explica"
L5_P6_GRAF_PROJ = "Os minutos nos 2 primeiros componentes"
L5_P6_VAR = "O 1º componente explica **{a}%** da variação e o 2º **{b}%**: juntos, {c}%."
L5_P6_CARGAS = "O 1º componente mistura: {lista}."
L5_P6_JUNTAS = ("Uso, frequência e temperatura entram com o **mesmo sinal**: eles sobem e descem juntos, e quase contam a mesma história "
                "(a ⟦colinearidade⟧ da Lição 3).")
L5_P6_EIXO_X = "componente 1"
L5_P6_EIXO_Y = "componente 2"

L5_P7 = "O que você viu nesta lição:"
L5_RESUMO = [
    "No ⟦sem_rotulos|aprendizado sem rótulos⟧ não há resposta certa para conferir; o ⟦agrupamento⟧ só descobre estrutura.",
    "O ⟦kmeans|k-means⟧ precisa que você escolha k; ⟦inercia|inércia⟧ e ⟦silhueta⟧ ajudam, mas quem decide é a utilidade dos grupos.",
    "Os nomes dos grupos são interpretação sua; com ⟦dados_sinteticos⟧ dá para medir a ⟦pureza⟧ contra o ⟦gabarito⟧.",
    "Os ⟦pca|componentes principais⟧ resumem variáveis que andam juntas e mostram o que é redundante.",
]
L5_QUIZ = [
    {"pergunta": "Por que não existe um número de grupos \"certo\" no ⟦kmeans|k-means⟧?",
     "opcoes": ["Porque não há resposta correta para conferir: o melhor k é o que dá grupos úteis e explicáveis.",
                "Porque o k-means só funciona com k = 3.",
                "Porque o computador sorteia o k.",
                "Porque a inércia nunca muda."],
     "correta": 0,
     "explicacao": "É ⟦sem_rotulos|aprendizado sem rótulos⟧: ⟦inercia|inércia⟧ e ⟦silhueta⟧ são pistas, não sentenças."},
    {"pergunta": "Os dados são colocados na mesma escala antes de agrupar. Por quê?",
     "opcoes": ["Senão a variável com números grandes (frequência em MHz) dominaria a distância e as outras quase não contariam.",
                "Para o gráfico ficar mais bonito.",
                "Para o computador rodar mais rápido.",
                "Para eliminar o ruído."],
     "correta": 0,
     "explicacao": "O ⟦agrupamento⟧ mede distâncias: quem tem números maiores pesa mais, a menos que as escalas sejam igualadas."},
    {"pergunta": "O 1º ⟦componente⟧ explica 60% da variação e mistura uso, frequência e temperatura com o mesmo sinal. O que isso mostra?",
     "opcoes": ["Que essas variáveis andam juntas e contam quase a mesma história.",
                "Que a temperatura causa o uso.",
                "Que o modelo errou.",
                "Que só há 60% dos dados."],
     "correta": 0,
     "explicacao": "Os ⟦pca|componentes principais⟧ revelam redundância: quando várias variáveis sobem e descem juntas, um só componente resume bem."},
]
