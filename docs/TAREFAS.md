# Tarefas de otimização (consumo de recursos)

Origem: lista da seção 6 da análise de consumo (2026-10-25). Regime estável medido: 0,30% de CPU, 13 MB. Cada tarefa só entra se o ganho medido justificar o risco. Medir antes e depois com o mesmo roteiro (app aberto 10 min, janela minimizada).

| # | Tarefa | Benefício estimado | Risco | Critério de pronto |
|---|--------|--------------------|-------|--------------------|
| 1 | Trocar o polling de 250 ms da fila de pedidos por evento (`event_generate`/fila com despertar) | menos acordadas por segundo (4 → 0 em repouso) | baixo | CPU em repouso não piora; pedidos da bandeja e do Laboratório continuam atendidos (teste) |
| 2 | Intervalo adaptativo: 2 s com a janela visível, 5 s minimizado ou só na bandeja | ~50% menos leituras em segundo plano | médio: gráfico fica mais grosso e o histórico por minuto tem menos amostras (`poucas_amostras`) | histórico por minuto continua com ≥ 10 amostras; usuário pode fixar o intervalo no `.env` |
| 3 | `powercfg` (plano de energia) a cada 10 min em vez de a cada ciclo | menos processos filhos | baixo | diagnóstico continua mostrando o plano certo após mudá-lo manualmente (no máximo 10 min de atraso, documentado) |
| 4 | Modo econômico na bateria (intervalo maior, ícone a cada 2 min) | mais autonomia em notebook | médio: usuário vê dados menos frescos | só ativa na bateria; indicado na tela; desativável |
| 5 | Substituir `pystray` por chamadas diretas (ctypes/`Shell_NotifyIcon`) | tira dependência LGPL e ~2 MB | alto: código de janela nativa, mais difícil de manter | menu, ícone dinâmico e encerramento iguais aos atuais; teste manual em reinício do Explorer |
| 6 | Gerar o ícone da bandeja só quando o número ou a faixa muda (já a cada 60 s) | já feito em parte | baixo | manter o teste de custo do ícone (~10 ms) |
| 7 | Carregar `linha_do_tempo.py` e Pillow sob demanda | menos memória até abrir o Histórico | baixo | memória ao iniciar cai; Histórico abre sem erro |

Ordem sugerida: 3 → 1 → 7 → 2 → 4 → 6 → 5 (a 5 só se o licenciamento pesar no lançamento).
