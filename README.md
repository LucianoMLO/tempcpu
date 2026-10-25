# TempCPU

App desktop (Windows) que lê a temperatura do processador a cada 2 segundos, **sem instalar nenhum driver no núcleo do Windows**, e mostra:

- **Card** com a temperatura atual, a zona (Normal · Atenção · Quente · Crítico) e a régua das zonas; abaixo, GPU, SoC, frequência da CPU e rotação da ventoinha;
- **Gráfico** dos últimos 5 minutos sobre as faixas verde, amarela, vermelha e a zona crítica (a partir do limite em que o firmware reduz o desempenho), com a linha de desligamento do firmware;
- **Diagnóstico**: uso da CPU, os 5 processos que mais consomem, plano de energia, tomada/bateria, estado máximo do processador e ventoinha;
- **Sugestões** para baixar a temperatura, por prioridade (vermelho = agir agora, amarelo = recomendado, verde = preventivo);
- **Botão na barra de tarefas**, discreto: fundo pastel, número na cor da faixa e uma tira colorida na base. O número é atualizado a cada minuto (`ICONE_ATUALIZA_S`) com o valor daquele instante, ou na hora em que a faixa de cor muda. Fechar a janela (X) a **minimiza**, então o botão fica sempre na barra; o app inicia minimizado.
- **Ícone na área de notificação** (perto do relógio) com o mesmo número e cor. Fica cinza com `||` quando pausado e com `--` quando a leitura está parada. Clique abre a janela.
- **Menu do ícone** (botão direito): Abrir · Histórico · Monitoramento ativo (liga/desliga) · Iniciar com o Windows · Sair.
- **Histórico** (botão na janela ou no menu): linha do tempo de qualquer variável, com período, granularidade e resumo. Veja a seção abaixo.

O app só sugere: não altera nenhuma configuração do Windows. A única exceção é a opção "Iniciar com o Windows", que você ativa no menu: ela cria (ou remove) a tarefa agendada `TempCPU`.

## Histórico

Um registro por minuto no SQLite `%LOCALAPPDATA%\TempCPU\historico.db` (fora da pasta do app): mínimo, máximo, média e desvio padrão de cada variável (temperatura da CPU, GPU e SoC, uso da CPU, frequência, ventoinha, bateria, tomada), a zona, o plano de energia, o programa que mais consome e o **motivo do aquecimento**.

- **Tipologia dos motivos** (`motivos.py`): lista fechada de 11 códigos em 7 categorias (carga, refrigeração, configuração, energia, sensor, limite, indefinida). Fica nas colunas `motivo_principal` e `categoria_motivo` e na tabela `minuto_motivo`, para analisar quais variáveis acompanham a temperatura.
- **Resumos** por hora, dia, semana e mês (média ponderada e desvio padrão agregado, não média das médias), com um texto do que ocorreu: temperatura, tempo por zona, motivos, programa mais frequente, ventoinha.
- **Retenção:** minutos por 1 ano (`RETENCAO_DIAS`); os resumos ficam para sempre. Cerca de 150 MB por ano.
- **Janela Histórico:** escolha as variáveis (botões coloridos; várias ao mesmo tempo, com eixo esquerdo e direito para até 2 unidades diferentes), o período (1 hora a 1 ano, ou tudo) e a granularidade (automática, minuto, hora, dia, semana, mês). Mostra a faixa mínimo–máximo, a linha da média, as zonas de temperatura, uma tira de motivos por categoria, e o resumo do período. Passe o mouse para ver os valores; clique para ver o resumo daquele ponto. Lacunas (computador desligado ou monitoramento pausado) aparecem como quebras na linha.
- **Privacidade:** `SALVAR_PROGRAMAS=nao` impede que nomes de programas sejam gravados.

## Laboratório (opcional): aprenda machine learning com o seu histórico

Botão **Laboratório** na janela (e item no menu do ícone). É um módulo **opcional e separado**: o TempCPU continua igual, e leve, sem ele. Três lições para quem **não sabe nada** de aprendizado de máquina, com explicações curtas, experimentos que você controla, termos sublinhados com definição, glossário e três perguntas no final de cada uma:

1. **Dá para prever a temperatura?** Treino e teste, o erro de avaliar com minutos embaralhados, árvore simples × complexa (subajuste e sobreajuste), comparação com o palpite de referência e a armadilha da ventoinha (consequência, não causa).
2. **Quente para o que você faz.** Aprende o que é normal para o que o computador está fazendo, mede o **resíduo** (medido − esperado), ajusta o limite do "estranho" (falsos alarmes × alarmes perdidos) e acompanha a tendência semanal (poeira, pasta térmica).
3. **Dados de mentira com gabarito.** Você inventa os dados, sabe a resposta certa e confere o que o modelo descobre; estraga de propósito (ruído, poucos dados, entradas que andam juntas) e vê o efeito de verdade.

- **Instalação sob demanda:** ao clicar pela primeira vez, o app mostra o tamanho (~240 MB) e só instala depois da sua confirmação. Cria um ambiente próprio em `%LOCALAPPDATA%\TempCPU\lab-env` com versões e hashes fixados (`lab-requirements.txt`). Exige o Python 3.14 de 64 bits instalado. Para remover: botão direito em **Laboratório**.
- **Privacidade:** só lê o histórico, somente leitura, e só números (**nomes de programas nunca são lidos**). Guarda apenas um arquivo de progresso em `%LOCALAPPDATA%\TempCPU\lab`. Não envia nada pela internet (a única conexão é o download da instalação, depois do seu ok).
- **Seus dados, só seus:** o Laboratório trabalha com o histórico deste computador (opção "Meus dados" no Início) e nada dele é compartilhado entre usuários. A tela **Meus dados** analisa a qualidade do histórico, em números e em palavras (quantidade, período, variedade de uso e de temperatura, tomada, horas do dia, aproveitamento dos minutos gravados) e diz, por lição, se dá para fazer, com ressalvas ou ainda não, e o que fazer para melhorar. As lições 1 e 2 avisam quando a qualidade não é boa.
- **Dados sintéticos:** quando estão em uso, aparece a faixa "DADOS DE MENTIRA". Com poucos dias de histórico real, as lições 1 e 2 oferecem os sintéticos (a lição 1 pede 3 dias e 2.000 minutos úteis; a 2, 7 dias e 5.000).
- **Desenvolvimento:** `py -m venv .venv-lab` e `.venv-lab\Scripts\pip install -r lab-requirements.txt`; testes com `.venv-lab\Scripts\python -m unittest discover -s tests_lab` (abrem janelas, ~2 min). Para abrir direto: `python -m lab --sintetico --licao 2`.

## De onde vem a temperatura

| Ordem | Fonte | Atualização | Observação |
|---|---|---|---|
| 1 | **AMD ADL**: DLL do driver de vídeo AMD já instalado | a cada segundo | CPU, GPU integrada e SoC nos Ryzen com Radeon. Modo usuário, sem driver novo. |
| 2 | LibreHardwareMonitor | a cada segundo | só se você já o tiver aberto. O app não o instala nem recomenda (driver de núcleo). |
| 3 | Zona térmica ACPI | só quando o firmware avisa | último recurso. Pode ficar horas parada; o app detecta e mostra "leitura parada". |

- **Ventoinha:** pela interface WMI da ASUS que veio de fábrica, somente leitura (método `DSTS`, códigos fixos). Se não conseguir ler, a janela diz o motivo e o app tenta de novo a cada 5 minutos.
- **GPU NVIDIA dedicada:** `nvidia-smi` em System32.

Motivos e medições: [ADR 0002](docs/adr/0002-fontes-sem-driver-de-kernel.md) (substitui a ordem do [ADR 0001](docs/adr/0001-fonte-de-temperatura.md)).

## Consumo

Medido no Ryzen 7 4800HS, minimizado e gravando o histórico: cerca de **19 MB de RAM e 0,3% de um núcleo**. Com a janela aberta, ~40 MB. Com a janela minimizada o diagnóstico roda a cada 30 s (alimenta o histórico), o ícone é redesenhado a cada 6 s no máximo e a memória sem uso volta para o Windows a cada minuto. Só roda uma cópia por vez: abrir de novo apenas mostra a janela da que já está rodando.

## Instalar (passo a passo, sem precisar entender de programação)

**Antes de começar:** o TempCPU ainda não tem instalador. Ele roda a partir dos arquivos deste projeto e precisa do **Python**, um programa gratuito. Funciona no **Windows 11**; foi testado só em notebook ASUS com processador AMD Ryzen. Em outros computadores pode mostrar menos informações.

1. **Instale o Python** (só se ainda não tiver): entre em <https://www.python.org/downloads/>, clique em **Download Python** e abra o arquivo baixado. Clique em **Install Now** e espere terminar.
2. **Baixe o TempCPU:** nesta página do GitHub, clique no botão verde **Code** e depois em **Download ZIP**. Quando baixar, clique com o botão direito no arquivo e escolha **Extrair tudo**. Isso cria uma pasta; abra essa pasta.
3. **Prepare (uma vez só):** dê um duplo clique em **`instalar.bat`**. Uma janela preta aparece, baixa o que falta e termina com a mensagem "Pronto!". Leva 1 ou 2 minutos e precisa de internet.
4. **Abra o TempCPU:** dê um duplo clique em **`iniciar.bat`**. O Windows pergunta se você permite que o programa faça alterações; clique em **Sim** (ele precisa disso só para ler a temperatura, não altera nada no seu computador). A temperatura aparece na janela, na barra de tarefas e perto do relógio.

**Se algo der errado:** o Windows pode avisar "O Windows protegeu o seu computador" ao abrir o `.bat`. Clique em **Mais informações** e depois em **Executar assim mesmo**. Se o número ficar parado ou aparecer "sem leitura", veja a seção "De onde vem a temperatura" mais abaixo.

<details><summary>Para quem programa (instalação manual)</summary>

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```
</details>

## Usar

- `iniciar.bat`: abre o app (ícone + janela) como administrador (exigido pela ACPI e pela ventoinha ASUS).
- Para iniciar com o Windows: botão direito no ícone > **Iniciar com o Windows**. Cria a tarefa agendada `TempCPU` no logon, com privilégio elevado (sem aviso do UAC a cada logon), atraso de 20 s, liberada na bateria e sem limite de tempo. Desmarcar remove a tarefa.
- `.venv\Scripts\python app.py --cli`: imprime as leituras no terminal.
- Testes: `.venv\Scripts\python -m unittest discover -s tests`

## Configuração (`.env`)

| Chave | Padrão | O quê |
|---|---|---|
| `INTERVALO_S` | 2 | intervalo de leitura |
| `ALERTA_C` / `QUENTE_C` | 75 / 90 | início das zonas amarela e vermelha |
| `DANO_C` | auto | início da zona crítica: `auto` = limite do firmware (101 °C neste notebook); sem firmware, 105 |
| `JANELA_MIN` | 5 | minutos exibidos no gráfico |
| `DIAGNOSTICO_S` | 4 | intervalo da coleta de processos e energia |
| `PARADA_MIN` | 3 | minutos sem mudança para marcar a leitura ACPI como parada |
| `FAN_ALTA_RPM` | 4500 | rotação a partir da qual a ventoinha conta como alta no diagnóstico |
| `DIAGNOSTICO_OCULTO_S` | 30 | intervalo da coleta de diagnóstico com a janela minimizada |
| `RETENCAO_DIAS` | 365 | dias de minutos guardados (resumos ficam para sempre) |
| `ICONE_ATUALIZA_S` | 60 | segundos entre as atualizações do número do ícone (a mudança de faixa de cor é imediata) |
| `SALVAR_PROGRAMAS` | sim | `nao` = nunca guarda nomes de programas no histórico |

## Licença

MIT (`LICENSE`). Bibliotecas de terceiros: `NOTICE.md`. Histórico de versões: `CHANGELOG.md`. Estado de prontidão: `docs/PRONTIDAO.md`.
