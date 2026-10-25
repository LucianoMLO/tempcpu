"""Textos de navegação e das telas de informação: Glossário e Sobre e privacidade (importados por `lab.textos`)."""

NAV_INICIO = "Início"
NAV_GLOSSARIO = "Glossário"
NAV_SOBRE = "Sobre e privacidade"
GLOSSARIO_TITULO = "Glossário"
GLOSSARIO_INTRO = "Todos os termos usados nas lições, com uma explicação simples e um exemplo. Digite para filtrar."
GLOSSARIO_BUSCA = "Buscar:"
GLOSSARIO_NADA = "Nenhum termo encontrado."
GLOSSARIO_EXEMPLO = "Exemplo: {exemplo}"

SOBRE_TITULO = "Sobre e privacidade"
SOBRE_BLOCOS = [
    ("O que o Laboratório lê",
     "O histórico do TempCPU, que fica na sua pasta de usuário (arquivo historico.db), **somente para leitura**. Só números entram: "
     "temperatura, uso e frequência da CPU, se estava na tomada, rotação da ventoinha e a hora. **Nomes de programas nunca são lidos.**"),
    ("O que o Laboratório grava",
     "Na pasta TempCPU\\lab do seu usuário: um arquivo pequeno de progresso (lições concluídas e perguntas acertadas) e o registro do último "
     "erro, que pode conter caminhos de pastas do seu usuário e não sai do computador. Na pasta do programa, o Python guarda arquivos "
     "temporários seus. Você pode apagar o progresso a qualquer momento para recomeçar. Nada do seu histórico é copiado. O banco do TempCPU "
     "não é alterado, mas, com o TempCPU fechado, o SQLite pode deixar dois arquivos auxiliares (historico.db-wal e historico.db-shm) ao lado "
     "dele; eles não mudam os seus dados."),
    ("Seu histórico é só seu",
     "O histórico fica na pasta do seu usuário do Windows. O Laboratório não o envia, não o exporta e não o compartilha com ninguém. Quem usa "
     "este computador com outra conta do Windows tem o próprio histórico e o próprio progresso. (Administradores do computador conseguem abrir "
     "arquivos de outras contas pelo próprio Windows; isso não depende do Laboratório.)"),
    ("O que o Laboratório não faz",
     "Não envia nada pela internet, não altera configurações do Windows e não muda o TempCPU. A única conexão acontece uma vez, na "
     "preparação do Laboratório, para baixar a biblioteca de aprendizado de máquina, e só depois da sua confirmação."),
    ("Limites do que você aprende aqui",
     "Os dados são de um só computador e de poucos dias. Um modelo encontra **padrões**, não **causas**, e o que ele acha pode ser acaso. "
     "As sugestões das lições são indícios, não diagnóstico: para decidir sobre limpeza ou conserto, confirme na prática."),
    ("Dados sintéticos",
     "Nas lições e na Lição 3 você pode usar ⟦dados_sinteticos⟧: são inventados, têm gabarito conhecido e **não dizem nada sobre o seu "
     "computador**. Sempre que estiverem em uso, aparece a faixa \"DADOS DE MENTIRA\" no alto da janela."),
]
SOBRE_VERSAO = "Laboratório do TempCPU, versão {versao}."
