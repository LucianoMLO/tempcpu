"""Textos da análise de qualidade dos dados (importados por `lab.textos`).

Cada item tem: título, explicação (o que significa e por que importa) e sugestões por nota. As explicações aceitam
termos do glossário (⟦chave⟧). Valores entram por `.format(...)`.
"""

NAV_QUALIDADE = "Meus dados"
QUAL_TITULO = "Qualidade dos seus dados"
QUAL_INTRO = ("Antes de aprender com o seu histórico, vale saber se ele **serve**. Esta análise acontece só no seu computador e mostra, em "
              "números e em palavras, o que há de bom e o que falta. Um ⟦modelo⟧ só aprende o que os dados mostram.")
QUAL_NOTA = {"boa": "Boa", "regular": "Regular", "fraca": "Fraca"}
QUAL_SIMBOLO = {"boa": "✓", "regular": "!", "fraca": "✗", None: "i"}
QUAL_GERAL = {
    "boa": "Seus dados são suficientes e variados: as lições vão mostrar resultados confiáveis.",
    "regular": "Seus dados dão para fazer as lições, mas alguns resultados podem oscilar. Veja o que melhorar.",
    "fraca": "Seus dados ainda não bastam para resultados confiáveis. Veja o que falta; enquanto isso, use os dados sintéticos.",
}
QUAL_GERAL_ROTULO = "Qualidade geral: {nota}"
QUAL_O_QUE_FAZER = "O que fazer"
QUAL_SEM_DADOS = ("Não há histórico real para analisar: {motivo} Abra o TempCPU e deixe-o rodar durante o uso normal do computador. "
                  "Enquanto isso, as lições funcionam com dados sintéticos.")
QUAL_VOLTAR = "Voltar ao início"
QUAL_LER_DE_NOVO = "Ler o histórico de novo"
QUAL_VER = "Ver qualidade dos dados"
QUAL_RESUMO_INICIO = "Qualidade dos seus dados: {nota}. {minutos} minutos úteis em {dias} dias."
QUAL_AVISO_LICAO = "Atenção: a qualidade dos seus dados é **{nota}**. {frase} Os resultados desta lição podem oscilar."
QUAL_GRAFICO_HORAS = "Minutos úteis por hora do dia"
QUAL_GRAFICO_USO = "Quantos minutos em cada faixa de uso da CPU"
QUAL_PRONTIDAO_TITULO = "E as lições?"
QUAL_PRONTIDAO = {
    "recomendada": "Lição {n}: pode fazer, e os dados são adequados.",
    "pode": "Lição {n}: pode fazer, mas com ressalvas.",
    "nao": "Lição {n}: ainda não, faltam dados.",
    "sintetica": "Lição {n}: usa sempre dados sintéticos.",
}
QUAL_PRONTIDAO_MOTIVO_MIN = "Faltam dados: ela pede {dias} dias e {minutos} minutos úteis; você tem {tem_dias} dias e {tem_minutos} minutos."
QUAL_PRONTIDAO_TENDENCIA = "A tendência semanal pede 3 semanas (21 dias); com menos, essa parte mostra só um exemplo com poeira simulada."

# chave -> (título, explicação, sugestão por nota)
QUAL_ITENS = {
    "minutos": (
        "Quantidade de dados",
        "Cada minuto útil é um exemplo para o ⟦modelo⟧ aprender. Com poucos exemplos, o resultado oscila de um dia para o outro.",
        {"regular": "Mais alguns dias de uso deixam os resultados mais estáveis.",
         "fraca": "Deixe o TempCPU rodando durante o uso normal. A Lição 1 pede 2.000 minutos úteis e a Lição 2, 5.000."}),
    "periodo": (
        "Período coberto",
        "Para aprender o que é normal e perceber mudanças com o tempo, é preciso um período longo. A ⟦tendencia⟧ semanal da Lição 2 pede 3 semanas.",
        {"regular": "Com 3 semanas ou mais, a tendência semanal da Lição 2 passa a funcionar com os seus dados.",
         "fraca": "Use o computador normalmente por mais alguns dias: a Lição 1 pede 3 dias e a Lição 2, 7 dias."}),
    "cobertura": (
        "Dias com dados",
        "Lacunas aparecem quando o computador ficou desligado ou o TempCPU fechado. Elas não estragam nada, mas dias isolados trazem pouca variedade.",
        {"regular": "Quanto mais dias diferentes, melhor o retrato da sua rotina.",
         "fraca": "Deixe o TempCPU abrir junto com o Windows (menu do ícone, \"Iniciar com o Windows\") para registrar todos os dias de uso."}),
    "uso": (
        "Variedade do uso da CPU",
        "Para aprender como a temperatura responde ao esforço, o uso da CPU precisa variar, de ocioso a pesado.",
        {"regular": "Um pouco mais de variedade (momentos de uso pesado) melhora o aprendizado.",
         "fraca": "Se o uso é quase sempre leve, o ⟦modelo⟧ não tem como aprender o efeito de uma carga alta. Inclua tarefas mais pesadas no uso normal, "
                  "ou faça as lições com dados sintéticos."}),
    "temperatura": (
        "Variedade da temperatura",
        "Se a temperatura quase não muda, não há o que prever: o ⟦modelo⟧ tende a empatar com o ⟦baseline⟧.",
        {"regular": "A temperatura variou pouco; momentos de carga mais alta ajudam.",
         "fraca": "Temperatura estável demais para aprender. Os dados sintéticos mostram melhor o que a lição ensina."}),
    "tomada": (
        "Tomada e bateria",
        "O efeito de estar na tomada só pode ser aprendido se houver minutos nas duas situações.",
        {"regular": "Quase sempre na mesma situação: o efeito da tomada será pouco confiável.",
         "fraca": "Só uma situação registrada: o ⟦modelo⟧ vai ignorar essa ⟦entradas|entrada⟧. Se este computador não tem bateria, isso é esperado."}),
    "horas": (
        "Horas do dia",
        "A hora do dia influencia a temperatura (rotina, ambiente). O ideal é ter dados em várias horas.",
        {"regular": "Use o computador em mais horários para o ⟦modelo⟧ conhecer o dia todo.",
         "fraca": "Poucas horas do dia registradas: o que o ⟦modelo⟧ aprender sobre a hora do dia será pouco confiável."}),
    "aproveitamento": (
        "Aproveitamento dos minutos gravados",
        "Nem todo minuto gravado serve: os de leitura parada (ACPI), com poucas amostras de temperatura ou sem uso medido são descartados.",
        {"regular": "Parte dos minutos foi descartada; veja o motivo abaixo.",
         "fraca": "Muitos minutos foram descartados. Em computadores sem leitura de temperatura em tempo real, a qualidade fica limitada."}),
    "ventoinha": (
        "Rotação da ventoinha",
        "Só é usada no experimento da armadilha da ventoinha (Lição 1, passo 5). Sem ela, esse passo usa dados sintéticos.",
        {}),
}
QUAL_VALORES = {
    "minutos": "{v} minutos úteis",
    "periodo": "{v} dias do calendário entre o primeiro e o último minuto",
    "cobertura": "{k} de {n} dias com dados suficientes",
    "uso": "em 90% dos minutos o uso ficou entre {a}% e {b}%",
    "temperatura": "em 90% dos minutos a temperatura ficou entre {a} e {b} °C",
    "tomada": "na tomada em {pct}% do tempo",
    "horas": "dados em {k} das 24 horas do dia",
    "aproveitamento": "{uteis} de {total} minutos gravados serviram ({pct}%); descartados por leitura parada: {acpi}, poucas amostras: {poucas}, sem uso: {sem_uso}",
    "ventoinha": "disponível em {pct}% dos minutos úteis",
}
QUAL_VENTOINHA_DISPONIVEL = "Disponível: o experimento da Lição 1 pode usar o seu histórico."
QUAL_VENTOINHA_INDISPONIVEL = "Indisponível ou rara: o experimento da ventoinha usará dados sintéticos."
