# TempCPU

App desktop Python + tkinter (Windows) que mostra a temperatura da CPU, gráfico por zonas e diagnóstico com sugestões.

## Estrutura
- `sensores.py`: fontes de temperatura (AMD ADL → LibreHardwareMonitor, se já aberto → zona ACPI), `DetectorParada` (ACPI congelada) e `limites_firmware()`. Funções puras testáveis: `acpi_para_celsius`, `zona_mais_quente`, `escolher_sensor_lhm`, `escolher_sensor_gpu`.
- `amd.py`: ADL via ctypes (`System32\atiadlxx.dll` por caminho absoluto). `interpretar()` é puro.
- `asus.py`: ventoinha pela WMI da ASUS (ATK). **Somente `DSTS`, IDs fixos em `IDS_LEITURA`.** Há teste garantindo isso.
- `diagnostico.py`: `Coletor` (psutil + powercfg, roda em thread) e `analisar()` (puro: retrato + temperatura + ventoinha + parada → causas e sugestões).
- `app.py`: janela (minimizada por padrão), zonas (`zona_de`), config do `.env`, modos `--janela` e `--cli`. Ações de outras threads entram por `App.pedidos` (fila); tkinter só é tocado na thread principal.
- `bandeja.py`: ícone pystray com número + cor da zona (`desenhar_icone` também alimenta o ícone da janela na barra de tarefas).
- `sistema.py`: instância única (mutex + evento nomeado), `liberar_memoria()` (working set), tarefa agendada de início automático.
- `motivos.py`: tipologia fechada dos motivos de aquecimento (`Motivo`, `Categoria`). Códigos nunca são renomeados nem reaproveitados.
- `historico.py`: SQLite (`minuto`, `minuto_motivo`, `agregado`), `AcumuladorMinuto` (Welford), `combinar`/`resumo_texto` (puros), `Gravador` (liga o app ao banco; nunca levanta erro para o app).
- `linha_do_tempo.py`: janela Histórico (gráfico no Canvas, hover/clique, granularidade).
- `tema.py`: paleta, zonas e formatadores compartilhados.
- `tests/`: unittest (stdlib), rodam no `.venv` do app (sem scikit-learn).
- `laboratorio.py`: **launcher** do Laboratório (só biblioteca padrão): estados do ambiente, confirmação, `Preparo` (venv + `pip --require-hashes`), `abrir_processo`, remover. Nunca importar numpy/scikit-learn aqui nem no `app.py` (teste `tests/test_app_leve.py`, critério A8).
- `lab/`: o Laboratório em si (roda só no ambiente próprio, `%LOCALAPPDATA%\TempCPU\lab-env`, ou em `.venv-lab` no desenvolvimento). `dados.py` (leitura somente leitura, minuto útil), `sintetico.py` (gerador + gabarito), `modelos.py` (núcleo de ML, sem interface), `estado.py`, `progresso.py`, `tarefa.py` (treino em thread com cancelar), `glossario.py`, `textos*.py` (todos os textos das telas), `ui/` (janela, passos, `licao1..3.py`, quiz, gráficos em Canvas).
- `tests_lab/`: testes do Laboratório (com janelas reais, ~2 min): `.venv-lab\Scripts\python -m unittest discover -s tests_lab`.
- Especificação, calibração e decisões: `docs/SPEC-laboratorio.md` e `docs/adr/0004`.

## Regras
- **Nenhum driver no núcleo do Windows** (decisão do usuário; sentinela reprovou o LibreHardwareMonitor). Fonte nova só em modo usuário, com componentes que já vieram no sistema. Ver `docs/adr/0002`.
- Na ASUS ATK, nunca chamar `DEVS` ou outro método de escrita; IDs nunca vêm de configuração.
- DLLs de terceiros só por caminho absoluto em System32.
- O app **só sugere**; nunca altera plano de energia, estado do processador ou qualquer configuração do Windows. Única exceção: a tarefa agendada `TempCPU`, criada/removida só por clique do usuário no menu.
- Leveza é requisito: com a janela minimizada, só leitura, gravação do histórico e ícone (medido ~19 MB, ~0,3% de um núcleo). Ícone (barra e bandeja) redesenhado a cada `ICONE_ATUALIZA_S` (60 s) ou quando a faixa/estado muda; ventoinha (WMI, ~7 ms) a cada 10 s.
- O banco do histórico fica em `%LOCALAPPDATA%\TempCPU`, nunca na pasta do app nem em pacote distribuído. Nome de programa só com `SALVAR_PROGRAMAS=sim`.
- Média e desvio de períodos maiores vêm de `combinar` (ponderado por `n`), nunca de média das médias. Mudança de esquema = nova `VERSAO_ESQUEMA` + migração (ADR 0003).
- O eixo do gráfico nunca pode ficar abaixo do maior valor (teste em `test_linha_do_tempo`): já houve bug em que RPM > 3.000 sumia do histórico.
- Fechar (X) minimiza; a bandeja e o botão da barra mostram o mesmo número e cor.
- Limites de zona ficam no `.env`, não no código (defaults em `CONFIG_PADRAO`; `DANO_C=auto` usa o firmware).
- Leitura parada nunca é apresentada como temperatura atual nem usada para conclusões.
- Sem dependência nova sem motivo: hoje `wmi` (pywin32), `psutil`, `pystray`, `Pillow` (`sqlite3` é da biblioteca padrão).
- **Laboratório:** só lê `historico.db` (`mode=ro` + `query_only`); **nunca** lê `programa_principal`; só grava `progresso.json` em `%LOCALAPPDATA%\TempCPU\lab`; nada pela rede (exceto o pip do `laboratorio.py`, após confirmação). Só remove pasta que tenha o marcador `.tempcpu-lab`.
- **Laboratório, textos:** todo texto de tela fica em `lab/textos*.py`; termo técnico entra como `⟦chave⟧` e precisa existir em `lab/glossario.py` (teste A11 em `tests_lab/test_glossario.py` exige o termo marcado em cada lição e proíbe jargão em inglês solto). **Afirmação na tela precisa de número que a sustente**: a Lição 3 foi reescrita porque, com 12.600 minutos, ruído e colinearidade quase não estragavam os coeficientes; os cenários usam 60 minutos justamente para o efeito aparecer, e as frases são montadas com os números medidos.
- **Laboratório, calibração:** limiares A1, A6 e A7 valem para o gerador padrão (`lab/sintetico.py`). Mudou o gerador ou o modelo, recalibre e atualize a spec; não enfraqueça o teste em silêncio.
- **tkinter:** `after` pendente precisa ser cancelado ao destruir o widget; texto que mede altura só mede com largura definida; tamanho forçado de um item de Canvas não gera evento, então a rolagem é reajustada por temporizador.
- Rodar testes: `.venv\Scripts\python -m unittest discover -s tests`.
