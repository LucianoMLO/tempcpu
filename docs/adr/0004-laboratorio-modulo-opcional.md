# ADR 0004 — Laboratório: módulo opcional em processo separado

**Data:** 2026-10-25 · **Status:** aceita · **Spec:** `docs/SPEC-laboratorio.md`

## Contexto
Queremos ensinar machine learning básico (regressão, anomalia, dados sintéticos) com o histórico do próprio computador. Isso exige scikit-learn e numpy, que custam ~240 MB em disco e ~107 MB de RAM só ao importar. O app é pensado para ficar minimizado com ~13–19 MB (CLAUDE.md: leveza é requisito) e, no lançamento público, empacotado em um único arquivo.

## Decisão
1. **Módulo opcional, em processo separado.** O Laboratório (`lab/`) é outro programa, aberto por um botão (e por item no menu da bandeja) com `pythonw.exe -m lab`, sem console (`CREATE_NO_WINDOW`) e com a pasta do app como diretório de trabalho. O app continua igual sem ele.
2. **Ambiente próprio**, fora do app e de qualquer pacote: `%LOCALAPPDATA%\TempCPU\lab-env` (sobrescrevível por `TEMPCPU_LAB_ENV`, usado em testes e desenvolvimento). Criado com `python -m venv` a partir do Python da instalação (`sys.base_prefix`), nunca do venv do app.
3. **Nada de numpy/scikit-learn no app.** `app.py`, `bandeja.py` e `laboratorio.py` usam só a biblioteca padrão. O launcher (`laboratorio.py`) cuida do estado do ambiente (`ausente → preparando → pronto | falhou`), da criação e da abertura. Teste A8 (`tests/test_app_leve.py`) importa `app` num subprocesso e exige `numpy`/`sklearn`/`scipy` fora de `sys.modules`.
4. **Só depois de confirmação.** O download (~240 MB) só começa após o clique em **Preparar Laboratório** num diálogo que mostra o tamanho e o destino. A preparação roda em thread (a janela do app não trava), mostra as etapas, aceita **Cancelar** e, em falha ou cancelamento, apaga a pasta parcial. **Remover Laboratório** (botão direito em Laboratório) apaga só a pasta do ambiente, nunca o histórico.
5. **Apagar só o que é nosso.** A pasta do ambiente recebe o arquivo `.tempcpu-lab` (conteúdo `preparando` → `pronto`). Remoção e limpeza exigem esse marcador; uma pasta alheia (por exemplo, `TEMPCPU_LAB_ENV` apontando para outro lugar) nunca é apagada.
6. **Pacotes fixados com hash.** `lab-requirements.txt` fixa scikit-learn 1.9.1, numpy 2.5.4, scipy 1.18.1 e as dependências resolvidas (joblib, threadpoolctl, cloudpickle, narwhals), com SHA-256 dos arquivos `cp314/win_amd64` obtidos por `pip download`. A instalação usa `pip install --require-hashes --only-binary=:all: --no-cache-dir`: um arquivo adulterado ou trocado é recusado. Para atualizar uma versão, regerar os hashes.
7. **Python 3.14 de 64 bits na v1.** Os hashes são de wheels cp314/win_amd64; outra versão recebe mensagem clara ("a v1 não suporta") e nada é criado. O app empacotado (sem Python) também recebe mensagem. Como entregar a quem não tem Python fica para o lançamento público (questão aberta da spec).
8. **Após o preparo, verificação:** `import sklearn, tkinter` dentro do ambiente; sem isso, o preparo conta como falha.

9. **Verificar antes de instalar (adendo de 2026-10-25).** Antes de qualquer download, o launcher levanta, só localmente (sem rede), se o computador já tem um Python que sirva: candidatos de `py -0p`, do Python da instalação do app e do `python` do PATH (o atalho vazio da Microsoft Store é ignorado). Em cada um roda uma sonda curta (`-c`, timeout de 15 s, sem janela, **sem `-I`** para enxergar pacotes instalados com `--user`) que devolve JSON com versão, bits, `tkinter` e as versões de numpy, scipy e scikit-learn lidas de `importlib.metadata` (nada pesado é importado). A mesma instalação vista por dois caminhos conta uma vez (`sys.base_prefix`).
10. **Critério de "já está pronto":** Python ≥ 3.10 de 64 bits, tkinter, numpy ≥ 1.26, scipy ≥ 1.11, scikit-learn ≥ 1.4. **A validação completa do Laboratório foi feita só com o Python 3.14.3 e as versões fixadas em `lab-requirements.txt`.** Se as versões encontradas forem diferentes das fixadas, a tela avisa que os números das lições podem variar um pouco.
11. **Fluxo ao clicar em Laboratório:** (a) ambiente próprio pronto → abre; (b) senão, se há Python que sirva → pergunta "Usar sem instalar nada?" com *Usar o que já tem (recomendado)*, *Instalar um ambiente separado* e *Agora não*; a escolha é guardada em `%LOCALAPPDATA%\TempCPU\lab\interpretador.json` (caminho e versões vistas) e **revalidada a cada abertura** (se deixar de servir, o arquivo é apagado e a pergunta volta); (c) senão, a confirmação do preparo, agora com a lista "O que já existe no seu computador", o que será instalado, o destino e o espaço livre. Usar um Python existente não baixa nem instala nada. "Esquecer o Python escolhido" (botão direito em Laboratório) apaga só o `interpretador.json`, nunca o Python do usuário.

## Alternativas descartadas
- Importar scikit-learn no app: +107 MB de RAM permanentes e `.exe` bem maior.
- Implementar os modelos em Python puro: pouco fiel ao que a lição ensina (as bibliotecas reais) e mais código a manter.
- Instalar no Python global do usuário: poluiria o sistema (o app só sugere e não altera o computador) e dependeria de versões já presentes.
- Intervalos de versão sem hash: instalação não reproduzível e sem garantia de integridade.

## Consequências
- Primeira abertura exige internet e ~240 MB livres (verificamos ≥ 700 MB antes, por causa do download).
- Atualizar o Python do usuário para outra versão desabilita o Laboratório até a v1 ganhar novos hashes.
- Falhas possíveis e tratadas com mensagem em português: sem internet, sem espaço, hash divergente, acesso negado (antivírus), erro do pip, Python não suportado.
- Um Python existente fica sob controle do usuário: pode mudar de versão ou perder pacotes; por isso a revalidação a cada abertura.
- Dois ambientes de teste: o do app (`tests/`, sem sklearn) e o do Laboratório (`tests_lab/`).
