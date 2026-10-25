# Onde estamos

**Atualizado:** 2026-10-25

## Feito
- Fontes sem driver de núcleo (ADR 0002): CPU, GPU e SoC pela AMD ADL, a cada 1 s; ventoinha pela ASUS ATK (só `DSTS`); ACPI como último recurso, com detecção de leitura parada.
- Zona crítica e linha de desligamento lidas do firmware (101,1 / 103,1 °C neste notebook).
- Card, régua, gráfico por zonas, diagnóstico (processos, energia, turbo, ventoinha, leitura parada) e sugestões; paleta suave.
- Ícone na bandeja (número + cor; `||` pausado; `--` parada), menu com monitoramento liga/desliga, iniciar com o Windows e sair. Instância única.
- Leitura parada (fonte ACPI forçada), pausa e 2ª instância conferidas.
- Histórico (ADR 0003): SQLite com 1 registro/min (mín, máx, média, desvio padrão; programa; motivo), resumos hora/dia/semana/mês, retenção de 1 ano nos minutos, tipologia fechada de 11 motivos (`motivos.py`), janela Histórico com granularidade e resumo.
- Barra de tarefas: botão discreto (pastel, tira na base) com número e cor da faixa, atualizado a cada 60 s ou quando a faixa muda; X minimiza; inicia minimizado.
- Histórico com várias variáveis ao mesmo tempo (até 2 unidades: eixos esquerdo e direito). Corrigido o eixo que escondia RPM acima de 3.000 (o dado estava no banco).
- Ventoinha: retenta a leitura ASUS a cada 5 min e mostra o motivo na tela se indisponível.
- Consumo minimizado gravando histórico (regime estável): ~13–19 MB, ~0,3% de um núcleo. Gravação: 3 ms/minuto, ~150 MB/ano.
- 61 testes unitários; fluxo real testado (menu da bandeja → histórico, reuso da janela, pausa, gravação ao sair).
- Sentinela: LibreHardwareMonitor reprovado; ASUS ATK e AMD ADL aprovados com condições (cumpridas).

## Laboratório (módulo opcional de machine learning didático) — F0 a F7 concluídas (2026-10-25)
Spec e estado de verificação por critério: `docs/SPEC-laboratorio.md` · decisões: `docs/adr/0004` · plano de implementação: arquivo local, fora do repositório.
- **Launcher (F0)** `laboratorio.py` (só biblioteca padrão): estados `ausente → preparando → pronto | falhou`, ambiente em `%LOCALAPPDATA%\TempCPU\lab-env` (ou `TEMPCPU_LAB_ENV`), confirmação com o tamanho (~240 MB), progresso por etapas, Cancelar com limpeza da pasta parcial, Remover (botão direito em Laboratório; só pasta com o marcador `.tempcpu-lab`), abre `pythonw -m lab` sem console. `lab-requirements.txt` com versões e SHA-256 fixados (Python 3.14, Windows 64 bits). Botão ao lado de Histórico e item no menu da bandeja.
- **Dados e núcleo (F1, F2)** `lab/dados.py`, `lab/sintetico.py`, `lab/modelos.py`: leitura somente leitura, só números, gerador com gabarito, deriva lenta e episódios injetados; limiares A1, A6, A7 calibrados com 8 sementes (profundidade ótima 9; sensibilidade 2,5 com média de 5 min).
- **Interface (F3 a F7)** `lab/ui/`: janela com navegação (Início, Glossário, Sobre e privacidade), faixa "DADOS DE MENTIRA", treino em thread com progresso e Cancelar, **Lição 1** (6 passos), **Lição 2** (6 passos), **Lição 3** (6 passos), 3 perguntas por lição, glossário com busca e 30 termos (`lab/glossario.py`).
- **Qualidade dos dados (2026-10-25):** `lab/qualidade.py` + `lab/ui/tela_qualidade.py` (navegação "Meus dados"), resumo no Início, aviso nas lições 1 e 2 e botão na tela de poucos dados. Limiares em `qualidade.LIMIARES`. O histórico nunca sai do computador (teste de rede ainda não escrito).
- **Revisão independente:** 17 achados, corrigidos (cache por chave de dados, fonte fixa durante a lição, validação de `Progresso`, textos mais honestos, cancelamento de `after`, etc.); F0 corrigiu mais 5 (ambiente vazio, exceção no preparo, marcador inválido, um Laboratório só, sem `__pycache__`).
- **Testes:** `tests/` (148, app sem scikit-learn, 5 s) e `tests_lab/` (134, com janelas reais, ~105 s). A instalação real foi provada: 36 s, 241 MB, hashes conferem, e a suíte do Laboratório passa também no ambiente de produção.
- **Medido:** pico de 146 MB nos treinos; 141 MB com o Laboratório na tela inicial; maior treino 7,9 s; o app não carrega numpy nem scikit-learn.
- **Pendente (F8):** revisão independente (em andamento), medição do app antes e depois de abrir o Laboratório, roteiro manual do preparo com falha de rede e do clique em "Agora não", e as lições 1 e 2 com o **histórico real** (hoje o banco tem poucos minutos; precisa de alguns dias de uso).
- **Achados que as lições ensinam (medidos):** o modelo linear vence a melhor árvore num mundo linear (2,1 contra 2,2 °C); embaralhar dá nota falsamente melhor (8%); a ventoinha infla o R² (0,91 para 0,98) por ser consequência; com 12.600 minutos o ruído quase não estraga os coeficientes (0,6% para 1,1%), mas com 60 minutos o erro do coeficiente do uso vai a 6% e, com uso e frequência quase iguais, a 14% sem o erro de previsão mudar.

## Legendas, otimizações e página (2026-10-25)
- **Legendas:** `dicas.py` (`Dica` com atraso de 500 ms, sem dependências). Passar o mouse na linha GPU/SoC/frequência/ventoinha explica só os termos presentes (SoC = System on Chip); botões Histórico e Laboratório têm dica. Testes em `tests/test_dicas.py`. A linha continua um único rótulo; dica por termo exigiria separá-los (não feito).
- **Otimizações:** fila em `docs/TAREFAS.md` (7 tarefas com benefício, risco e critério de pronto; nada implementado ainda).
- **Página de apresentação:** `site/` (HTML/CSS/JS estático, PT/EN, sem CDN), workflow `.github/workflows/pages.yml` (publica `site/` ao enviar para `main`; nada foi enviado). Capturas com dados de demonstração geradas por `tools/gerar_capturas.py` (leitor, GPU, ventoinha e processos falsos; banco em pasta temporária) e `python -m lab --sintetico --foto`. Download aparece como "em breve" sem link. **Decidido (ADR 0005):** gratuito, apoio opcional sem mínimo (bloco "Apoie o projeto", chave Pix ainda por preencher), nome TempCPU mantido. Versão paga adiada.
- **Não verificado:** a página só foi vista em largura de celular e na troca de idioma; não foi publicada.

## Specs e prontidão (2026-10-25)
- `docs/SPEC-avaliacao.md`: nivelamento, avaliação final e certificado; decisões: emissor Mais Valor Consultoria e Serviços, gratuito, só português, avaliação e certificado pela Cloudflare (Worker + D1), verificação de 12 meses. Nada implementado.
- `docs/SPEC-licoes-novas.md`: classificação, agrupamento/PCA, Ridge/Lasso, Isolation Forest, validação cruzada, boosting. Nada implementado.
- `docs/PRONTIDAO.md`: notas por área, lista "para lançar hoje" e plano de divulgação. Bloqueios: sem `LICENSE`, sem commit, sem executável.

- **Banco de questões (B-0):** `lab/questoes.py` (50 questões, 10 por tema, 2 de nivelamento e 8 da final por tema) e `tests_lab/test_questoes.py` (critérios B1 a B5 e extras: termos marcados, sem jargão, correta nunca a mais longa em mais da metade). Ambos fora do Git de propósito (respostas). **Pendente: revisão humana do conteúdo** e do destino `revisar` (lição, passo) de cada questão.

- **Núcleo da avaliação (B-1):** `lab/avaliacao.py` (sorteio do nivelamento e da final por semente, sem repetir a tentativa anterior, correção, aprovação 80% + metade de cada tema, recomendação de lição, validação do nome, código de conferência) e resumo de provas em `Progresso`. Referência das regras para o Worker. Testes públicos com banco falso em `tests_lab/test_avaliacao.py`; integração com o banco real fica no arquivo privado. Pendente: telas (B-2), Worker/D1, PDF.

## Próximas etapas: lançamento público (planejado, não iniciado)
Detalhe e checklist completo na nota do projeto no cérebro (`20-projetos/tempcpu.md`).
0. Decisões de produto: nome, licença, compatibilidade declarada, gratuito.
1. Nenhuma informação pessoal ou desta máquina no pacote; repositório público novo, sem histórico.
2. Robustez em outras máquinas: sem administrador por padrão, matriz Intel/AMD/NVIDIA, configurações pela tela.
3. Empacotar em um único arquivo (`.exe` onefile ou instalador único).
4. Integridade: assinatura de código + build no GitHub Actions + SHA-256 publicado (código aberto no GitHub).
5. Distribuição pelo GitHub Releases e contagem de downloads pela API (rotina semanal + histórico).
6. Lançamento: README público, privacidade, licença, CHANGELOG, revisão final.
7. Pós-lançamento: aviso de nova versão, suporte por Issues, revisão mensal de downloads.

## Pendente / ideias
- Gráfico de dispersão/correlação entre variáveis e temperatura (hoje a base está pronta em `minuto`/`minuto_motivo`; a análise ainda não).
- Exportar o histórico para CSV.
- Testar o histórico em dias reais de uso (hoje o banco real tem poucos minutos; a janela foi conferida com 4 dias sintéticos).
- Testar "Iniciar com o Windows" (cria tarefa agendada: aguardando ok do usuário) e um logon real.
- TEMP_CPU da ADL não comparado ao Tctl direto (exigiria driver de núcleo).
- Ver se roda sem administrador agora que a fonte principal é a ADL (ACPI e ASUS ainda pedem).
- Possível: notificação ao entrar na zona Quente.
