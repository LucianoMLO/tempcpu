"""Todos os textos das telas do Laboratório, em um só lugar (para revisar e para o teste do glossário).

Termos técnicos vão marcados como ⟦chave⟧ (ver `lab/glossario.py`). **Negrito** com dois asteriscos.
Nada aqui é concatenado com dados do usuário: valores entram por `.format(...)` nos marcadores nomeados.
"""

# ---------------- geral ----------------
TITULO_JANELA = "TempCPU — Laboratório"
FAIXA_SINTETICA = "DADOS SINTÉTICOS (inventados): servem para aprender; não dizem nada sobre o seu computador."
BARRA_GLOSSARIO_VAZIA = "Termos sublinhados têm explicação: passe o mouse sobre eles."

INICIO_TITULO = "Laboratório de machine learning"
INICIO_INTRO = ("Aqui você aprende, com os dados do seu próprio computador, como um ⟦modelo⟧ de aprendizado de máquina funciona. "
                "Não precisa saber nada antes: cada lição tem explicações curtas, experimentos que você controla e "
                "perguntas no final. Na Lição 3 você inventa os dados e conhece o ⟦gabarito⟧ (a resposta certa). "
                "Tudo roda no seu computador; nada é enviado para fora e o seu histórico só é lido.")
INICIO_FONTE = "De onde vêm os dados"
INICIO_FONTE_REAL = "Meu histórico"
INICIO_FONTE_SINT = "Dados sintéticos (inventados)"
INICIO_REAL_LENDO = "Lendo o histórico…"
INICIO_REAL_INFO = "Histórico encontrado: {minutos} minutos úteis em {dias} dias."
INICIO_REAL_POUCO = "Histórico encontrado, mas ainda curto: {minutos} minutos úteis em {dias} dias. As lições pedem mais; use dados sintéticos por enquanto."
INICIO_REAL_NENHUM = ("Nenhum histórico utilizável: {erro} Abra o TempCPU e deixe-o rodar alguns dias, "
                      "ou use dados sintéticos. Nada foi alterado.")
INICIO_LER_DE_NOVO = "Ler o histórico de novo"
INICIO_SINT_INFO = ("Os ⟦dados_sinteticos⟧ são gerados por um programa com regras conhecidas. "
                    "Na Lição 3 você cria os seus; aqui usamos o conjunto padrão.")
LICAO_CONCLUIDA = "Concluída"
LICAO_NAO_INICIADA = "Não iniciada"
LICAO_EM_BREVE = "Em breve"
BOTAO_ABRIR = "Abrir lição"
BOTAO_ANTERIOR = "‹ Anterior"
BOTAO_PROXIMO = "Próximo ›"
BOTAO_CONCLUIR = "Concluir lição"
BOTAO_VOLTAR_INICIO = "Voltar ao início"
BOTAO_CANCELAR = "Cancelar"
BOTAO_TENTAR_DE_NOVO = "Tentar de novo"
BOTAO_USAR_SINTETICOS = "Usar dados sintéticos"

LICOES = {
    1: ("Lição 1 · Dá para prever a temperatura?",
        "Veja um modelo aprender a prever a temperatura e depois decorar os dados."),
    2: ("Lição 2 · Quente para o que você faz",
        "Descubra o que é normal para o que o computador está fazendo e ache o que foge disso."),
    3: ("Lição 3 · Dados sintéticos com gabarito",
        "Invente dados com resposta conhecida e confira o que o modelo descobre."),
    4: ("Lição 4 · Em qual faixa está?",
        "Em vez de prever um número, preveja se vai passar de um limite e aprenda por que acertar muito pode enganar."),
    5: ("Lição 5 · Descobrir grupos sem gabarito",
        "Deixe o computador achar sozinho os modos de uso, sem ninguém dizer quais são."),
}

# ---------------- estados de tela ----------------
ESTADO_TREINANDO = "Treinando…"
ESTADO_CANCELADO = "O treinamento foi cancelado. Nada foi alterado; você pode tentar de novo."
ESTADO_ERRO = "Algo deu errado: {mensagem}\nNada foi alterado no seu histórico."
ESTADO_POUCOS_DADOS = ("{mensagem}\n\nVocê pode fazer a lição agora com dados sintéticos (inventados, com regras conhecidas) "
                       "e voltar ao seu histórico depois de alguns dias de uso.")
ESTADO_SEM_DADOS_AINDA = "Ainda não há dados para mostrar."

# ---------------- Lição 1 ----------------
L1_PASSOS = ["O problema", "Treino e teste", "Simples ou complexo?", "Contra quem ele ganha?", "O que ele aprendeu", "Resumo e perguntas"]

L1_P1 = ("O computador esquenta mais quando trabalha mais. Será que dá para **prever** a temperatura da CPU "
         "só sabendo o que ele está fazendo? É isso que um ⟦modelo⟧ de aprendizado de máquina tenta fazer: "
         "aprender com exemplos do passado.\n\n"
         "Cada linha dos dados é **um minuto**. A coluna que queremos prever é o ⟦alvo⟧: a temperatura da CPU. "
         "As colunas que usamos para prever são as ⟦entradas⟧: uso da CPU, frequência da CPU, se está na tomada e "
         "a hora do dia.")
L1_P1_GRAFICO = "Cada ponto é um minuto. Quanto maior o uso, maior a temperatura, mas os pontos se espalham: isso é ⟦ruido⟧."
L1_P1_EIXO_X = "uso da CPU (%)"
L1_P1_EIXO_Y = "temperatura (°C)"

L1_P2 = ("Para saber se o modelo **aprendeu de verdade**, não basta ele acertar o que já viu. Por isso separamos os dados "
         "em duas partes: o ⟦treino⟧ (os 70% primeiros no tempo, que o modelo vê) e o ⟦teste⟧ (os 30% finais, a "
         "\"prova\", que ele nunca viu). É como estudar com uma lista de exercícios e ser avaliado numa prova nova.\n\n"
         "Dividimos **pelo tempo** porque o que queremos é prever o que ainda vai acontecer.")
L1_P2_TREINO = "treino: {n} minutos"
L1_P2_TESTE = "teste: {n} minutos"

L1_P3 = ("Vamos usar uma ⟦arvore⟧: ela faz perguntas em sequência (\"o uso passa de 50%?\") e vai se ramificando. "
         "A ⟦profundidade⟧ é quantas perguntas seguidas ela pode fazer.\n\n"
         "Mexa no controle e compare o erro no **treino** (o que ela viu) com o erro no **teste** (a prova). "
         "O erro é o ⟦erro_medio⟧: quantos graus, em média, a previsão erra.")
L1_P3_CONTROLE = "Profundidade da árvore: {d}"
L1_P3_GRAF_A = "Erro médio (°C) em cada profundidade"
L1_P3_GRAF_B = "Previsto × real no período de teste (profundidade {d})"
L1_P3_LINEAR = "modelo linear (referência)"
L1_P3_ZONA = "sobreajuste"
L1_P3_LEGENDA_TREINO = "erro no treino"
L1_P3_LEGENDA_TESTE = "erro no teste"
L1_P3_LEGENDA_REAL = "real"
L1_P3_LEGENDA_PREVISTO = "previsto"
L1_P3_VALORES = "Profundidade {d}: erro no treino {tr} °C · erro no teste {te} °C."
L1_P3_SUBAJUSTE = ("Árvore simples demais: erra bastante tanto no treino quanto no teste. Isso se chama ⟦subajuste⟧: "
                   "ela ainda não tem perguntas suficientes para captar o padrão.")
L1_P3_BOM = ("Aqui o erro no teste é **praticamente o menor** de todos: o modelo captou o padrão sem decorar o acaso. "
             "Esse é o ponto de equilíbrio.")
L1_P3_SOBRE = ("⟦sobreajuste⟧: o erro no treino é pequeno ({tr} °C), mas no teste sobe para {te} °C. "
               "A árvore decorou até o ⟦ruido⟧ dos minutos de treino e, por isso, erra mais numa prova nova.")
L1_P3_MEIO = "O erro no teste ainda pode melhorar um pouco. Continue explorando."
L1_P3_NOTA_VALIDACAO = ("Uma ressalva honesta: escolher a melhor profundidade olhando o próprio teste é uma pequena trapaça, porque o teste "
                        "deixa de ser uma prova inédita. Na prática, separa-se uma terceira parte dos dados só para escolher. "
                        "Aqui o objetivo é mostrar a curva.")

L1_P2_EMBARALHAR = "Embaralhar os minutos (para ver o que dá errado)"
L1_P2_EMB_TEXTO = ("Sorteando os minutos, quase todo minuto de teste tem um **vizinho** no treino: mesma hora, uso parecido, "
                   "temperatura parecida. O modelo parece ótimo, mas só porque a prova está cheia de perguntas que ele já viu. "
                   "No mundo real você nunca terá o \"vizinho\" do futuro.")
L1_P2_EMB_COMPARA = ("Melhor erro no teste: **{tempo} °C** dividindo pelo tempo × **{emb} °C** embaralhando. "
                     "A nota embaralhada parece {pct}% melhor, mas é falsa.")
L1_P2_EMB_PEQUENA = ("Melhor erro no teste: **{tempo} °C** dividindo pelo tempo × **{emb} °C** embaralhando. Neste conjunto a "
                     "diferença foi pequena, mas ela cresce quando o que se mede tem \"memória\" no tempo, como a temperatura de verdade.")
L1_P2_EMB_CALCULANDO = "Calculando a comparação…"

L1_P4 = ("Antes de comemorar um erro de poucos graus, pergunte: **comparado a quê?** Um ⟦baseline⟧ é um palpite simples que "
         "o modelo precisa vencer. O mais simples é **chutar sempre a média** da temperatura do treino. Outra comparação "
         "útil é o modelo linear, que traça uma reta.")
L1_P4_GRAF = "Erro médio no teste (°C): quanto menor, melhor"
L1_P4_BARRAS = ("Chutar a média", "Modelo linear", "Árvore (profundidade {d})")
L1_P4_R2 = "Nota ⟦r2⟧ no teste: árvore {a} · linear {b}."
L1_P4_LINEAR_VENCE = ("O **modelo linear foi igual ou melhor** que a árvore. Isso acontece quando a relação é quase uma reta: "
                      "um modelo mais complexo nem sempre é melhor, e o simples é mais fácil de explicar.")
L1_P4_ARVORE_VENCE = "A árvore venceu o modelo linear: a relação tem curvas ou degraus que uma reta não pega."
L1_P4_NAO_VENCEU = ("Atenção: o modelo **não ganhou** de chutar a média. Os dados podem ser poucos ou muito ruidosos, ou as "
                    "entradas não explicam a temperatura.")

L1_P5 = ("Quais entradas o modelo mais usou? A ⟦importancia⟧ mede **quanto o erro piora quando os valores de uma entrada "
         "são embaralhados**: se piora muito, o modelo dependia dela.")
L1_P5_GRAF = "Quanto o erro piora (°C) se a entrada for embaralhada"
L1_P5_TOPO = "A entrada mais importante foi **{nome}**."
L1_P5_FREQ = ("Repare na **frequência**: ela anda junto com o uso (⟦correlacao⟧), então o modelo pode usar uma no lugar da outra. "
              "Importância alta **não prova** que a entrada esquenta o computador: mostra só que ela ajuda a prever.")
L1_P5_VENTOINHA = "Incluir a rotação da ventoinha como entrada"
L1_P5_VENT_ANTES = "Sem a ventoinha: erro {a} °C, nota ⟦r2⟧ {ra}."
L1_P5_VENT_DEPOIS = "Com a ventoinha: erro {b} °C, nota ⟦r2⟧ {rb}."
L1_P5_VENT_ALERTA = ("**Cuidado, é uma armadilha.** A nota subiu porque a ventoinha gira mais **depois** que a CPU esquenta: ela é "
                     "uma ⟦consequencia⟧ da temperatura, não a causa. Usar a consequência para prever a causa é ⟦vazamento⟧: "
                     "o modelo \"espia\" a resposta. Se a ideia é prever a temperatura **antes** de ela subir, a ventoinha não pode entrar.")
L1_P5_VENT_SEM_GANHO = ("Neste conjunto a nota não subiu ({ra} → {rb}). Mesmo assim, a ventoinha é uma ⟦consequencia⟧ da temperatura: "
                       "usá-la para prever a temperatura é ⟦vazamento⟧, e qualquer ganho seria enganoso.")
L1_P5_VENT_MESMAS_LINHAS = "A comparação usa exatamente os mesmos minutos nos dois casos."
L1_P5_VENT_POUCOS = "Há poucas leituras de ventoinha neste conjunto ({n} minutos úteis). Use ⟦dados_sinteticos⟧ para ver este experimento."
L1_P5_CALCULANDO = "Treinando com a ventoinha…"

L1_P6 = "O que você viu nesta lição:"
L1_RESUMO = [
    "Um ⟦modelo⟧ aprende com exemplos e é avaliado em dados que **não viu** (⟦treino⟧ e ⟦teste⟧).",
    "Dividir **pelo tempo** é o certo para prever o futuro; sortear minutos dá uma nota falsamente boa.",
    "Modelo simples demais erra tudo (⟦subajuste⟧); complexo demais decora o treino (⟦sobreajuste⟧). O melhor fica no meio.",
    "Compare sempre com um ⟦baseline⟧ e desconfie de entradas que são **consequência** do que você quer prever (⟦vazamento⟧).",
]
QUIZ_TITULO = "Perguntas para fixar"
BOTAO_RESPONDER = "Responder"
QUIZ_ACERTOU = "Correto! "
QUIZ_ERROU = "Não foi dessa vez. "
QUIZ_PLACAR = "Você acertou {a} de {n}."
L1_QUIZ = [
    {"pergunta": "Um modelo tem erro de 0,2 °C no treino e de 2,8 °C no teste. O que isso indica?",
     "opcoes": ["Que ele aprendeu muito bem e vai acertar sempre.",
                "Que ele decorou o treino (⟦sobreajuste⟧) e erra mais em dados novos.",
                "Que os dados de teste estão errados."],
     "correta": 1,
     "explicacao": "Erro baixo só no treino e alto na prova é a marca do ⟦sobreajuste⟧."},
    {"pergunta": "Por que dividimos os dados pelo tempo, e não sorteando minutos?",
     "opcoes": ["Para o modelo treinar mais rápido.",
                "Porque minutos vizinhos são parecidos: sortear enche a prova de minutos quase iguais aos do treino e dá uma nota falsamente boa.",
                "Porque o computador não sabe sortear."],
     "correta": 1,
     "explicacao": "Queremos prever o futuro, e no futuro não existem \"vizinhos\" já vistos."},
    {"pergunta": "A rotação da ventoinha melhora muito a previsão. Devemos usá-la para prever a temperatura?",
     "opcoes": ["Sim: quanto maior a nota, melhor.",
                "Não: ela é consequência da temperatura; usá-la é ⟦vazamento⟧ e dá uma nota enganosa.",
                "Sim, mas só no teste."],
     "correta": 1,
     "explicacao": "A ventoinha gira mais porque a CPU esquentou; ela entrega a resposta, e na hora de prever de verdade ela ainda não existe."},
]

from lab.textos_l2 import *  # noqa: E402,F401,F403  (textos da lição 2)
from lab.textos_l3 import *  # noqa: E402,F401,F403  (textos da lição 3)
from lab.textos_info import *  # noqa: E402,F401,F403  (navegação, glossário e sobre)
from lab.textos_qualidade import *  # noqa: E402,F401,F403  (qualidade dos dados)
from lab.textos_l4 import *  # noqa: E402,F401,F403  (textos da lição 4)
from lab.textos_l5 import *  # noqa: E402,F401,F403  (textos da lição 5)
from lab.textos_novos import *  # noqa: E402,F401,F403  (passos novos das lições 1 a 3; deve vir por último)
