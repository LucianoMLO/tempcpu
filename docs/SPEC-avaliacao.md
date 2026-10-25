# Laboratório — avaliação e certificado (especificação)

**Status:** decisões tomadas em 2026-10-25 (emissor Mais Valor, gratuito, Cloudflare); nada implementado · nada implementado · **Depende de:** `docs/SPEC-laboratorio.md` (v1, 3 lições) · **Versão alvo:** v1.1 do Laboratório

## Objetivo e usuário
- **Objetivo:** medir o aproveitamento de quem fez o Laboratório com um **teste de nivelamento** (antes) e uma **avaliação final** (depois), e emitir um **certificado de conclusão** para quem atingir **80% ou mais**.
- **Usuário:** o mesmo do Laboratório, qualquer pessoa, sem pressupor conhecimento. O texto das questões segue a regra do Glossário (todo termo técnico marcado e explicado).
- **Não é** curso acreditado, certificação profissional nem prova supervisionada. O certificado é de **participação/aproveitamento autodeclarado, emitido localmente pelo software**, e diz isso no próprio documento.

## Princípios
1. **Tudo local.** Questões, respostas, notas e certificado ficam no computador. Nenhuma conexão de rede, nenhum envio de nome ou nota (teste automático já existente: `lab/` não importa módulos de rede).
2. **Honestidade sobre o valor.** O certificado não pode sugerir verificação por terceiros que não existe. O código de conferência (ver abaixo) detecta erro de digitação, não fraude.
3. **Avaliar o que foi ensinado.** Cada questão mede uma competência que uma lição trabalha; nada de pegadinha nem de jargão que o Laboratório não explicou.
4. **Sem punição.** Sem limite de tentativas; o resultado mostra o que revisar e leva à lição certa.
5. **Reprodutível.** Toda prova guarda a semente do sorteio; a mesma semente reproduz as mesmas questões e a mesma ordem.

## Jornada principal
1. No Início, o aprendiz vê dois cartões novos: **Teste de nivelamento** e **Avaliação final**.
2. **Nivelamento** (opcional, ~5 min): 10 questões, sem nota mínima. Termina com o resultado por tema e uma recomendação ("comece pela Lição 1" / "você já domina X; pule para a Lição 2").
3. O aprendiz faz as 3 lições no ritmo que quiser.
4. **Avaliação final** (liberada após concluir as 3 lições; ~15 min): 20 questões sorteadas.
5. Resultado: nota geral, nota por tema, quais questões errou, com a explicação e o link para o passo da lição que trata do assunto.
6. Se **aprovado** (regra abaixo), o botão **Emitir certificado** pede o nome como o aprendiz quer que apareça e gera um PDF.
7. Se **reprovado**, o botão **Tentar de novo** sorteia questões diferentes das da tentativa anterior sempre que o banco permitir.

## Temas (as competências avaliadas)
| Tema | Lição | O que mede |
|---|---|---|
| T1 Dados e variáveis | 1 | o que é entrada e alvo, minuto útil, qualidade dos dados, por que dado ruim estraga o resultado |
| T2 Treino, teste e sobreajuste | 1 | dividir por tempo × embaralhar, decorar × aprender, curva de erro, profundidade |
| T3 Avaliar um modelo | 1 e 3 | erro médio, R² (e quando é negativo), palpite de referência (baseline), vazamento (consequência × causa), importância |
| T4 Anomalia e tendência | 2 | temperatura esperada, resíduo, episódio, sensibilidade (falso alarme × alarme perdido), tendência semanal |
| T5 Dados de mentira com gabarito | 3 | gabarito, ruído, poucos dados, entradas que andam juntas (correlação), o que um modelo pode ou não descobrir |

## Banco de questões
- **50 questões na v1.1**: 10 por tema. Em cada tema, **2 são do nivelamento** (nível básico, fixas) e **8 da avaliação final** (nível básico a intermediário).
- **Formato** (o mesmo das perguntas das lições, com campos novos), em `lab/questoes.py`:
  `id` (ex.: `T2-07`), `tema`, `uso` (`nivelamento` | `final`), `nivel` (1 a 3), `pergunta`, `opcoes` (3 ou 4), `correta`, `explicacao`, `revisar` (lição e passo).
- **Regras de qualidade** (verificadas por teste, ver critérios): exatamente uma correta; sem "todas as anteriores"/"nenhuma"; opções com tamanho parecido; sem repetir as 9 perguntas de fixação das lições; explicação obrigatória; termos técnicos marcados no glossário.
- **Embaralhamento:** a ordem das opções é sorteada por prova, para a posição da correta não virar pista.
- **Sorteio da final:** 4 questões por tema (20 no total), mistura de níveis (≥ 1 de nível 2 ou 3 por tema), sem repetir as da última tentativa enquanto houver outras.

## Regras de nota e aprovação
- **Nota geral** = acertos ÷ 20, em %.
- **Aprovado** = nota geral **≥ 80%** (16 de 20) **e** pelo menos **2 de 4** acertos em **cada** tema. A segunda condição impede aprovação com um tema inteiro ignorado.
- O nivelamento **nunca** reprova nem emite certificado. Seus resultados não entram na nota da final.
- Questão em branco conta como errada; a prova só termina com "Entregar", que avisa quando há questões sem resposta.
- Resultado por tema usa as faixas: ≥ 75% "dominado", 50–74% "revisar", < 50% "refazer a lição".

## Telas
- **Início:** dois cartões novos. Avaliação final aparece bloqueada com o motivo ("conclua as lições 1, 2 e 3") até as 3 estarem concluídas; o nivelamento está sempre liberado.
- **Prova:** uma questão por vez com barra de progresso, botão Anterior/Próxima, mapa de questões (respondida/em branco), Entregar. Sem cronômetro. O Glossário continua acessível (consulta permitida, dito na tela); as lições ficam bloqueadas durante a prova para evitar abrir uma lição e perder a prova.
- **Resultado:** nota geral, barra por tema, lista de erradas com explicação e botão "Revisar este assunto" que abre a lição e o passo correspondente. Para aprovados: botão "Emitir certificado".
- **Emitir certificado:** campo de nome (obrigatório, 3 a 80 caracteres), pré-visualização dos dados que irão no documento, botão Gerar PDF, depois "Abrir pasta" e instruções do LinkedIn.
- **Histórico de provas** (em "Meu progresso"): data, tipo, nota, aprovado ou não. Sem nome.

## Estados obrigatórios de tela
- **Carregando/gerando PDF:** mensagem com o que está acontecendo.
- **Vazio:** sem tentativas anteriores: "Você ainda não fez a avaliação".
- **Bloqueado:** avaliação final antes das 3 lições, com o que falta.
- **Prova interrompida:** fechar a janela no meio descarta a prova (aviso antes de sair); o progresso das lições não é afetado. Não há retomada na v1.1.
- **Erro ao gravar PDF** (pasta sem permissão, disco cheio): diz o que houve e oferece escolher outra pasta.
- **Progresso ilegível:** o arquivo é recriado sem apagar nada que o usuário possa ter fora dele (comportamento atual de `Progresso`).

## Certificado
- **Formato:** PDF de 1 página, A4 paisagem, gerado **sem dependência nova** (escrita direta do PDF com fonte padrão Helvetica, WinAnsi para acentos). Alternativa avaliada e descartada: Pillow/ReportLab (mais ~10 MB no ambiente do Laboratório sem ganho real).
- **Conteúdo, nesta ordem:**
  1. Título: "Certificado de conclusão — Laboratório de Machine Learning do TempCPU".
  2. "Certificamos que **{nome}** concluiu as 3 lições do Laboratório e obteve **{nota}%** na avaliação final".
  3. Nota por tema (5 linhas curtas).
  4. Data de emissão (dia/mês/ano) e versões: Laboratório `{versão}`, banco de questões `{versão}`.
  5. **Código de conferência** de 12 caracteres: `SHA-256(nome | data | nota | versões | semente)`, truncado. Serve para o aprendiz conferir se o PDF e o registro dele batem (o app recalcula e compara na tela "Meu progresso").
  6. **Aviso fixo:** "Certificado de aproveitamento emitido localmente pelo software, sem supervisão e sem validade como curso acreditado. Não indica carga horária oficial."
- **O que o certificado NÃO traz:** carga horária, número de registro, logotipo de instituição de ensino, selo de acreditação, QR code de "verificação" (não existe verificação externa).
- **Emissor:** Mais Valor Consultoria e Serviços (decisão 1).
- **Nome do aprendiz:** digitado na hora de emitir. **Não é gravado** no `progresso.json`; só aparece no PDF. Quem reemitir digita de novo. (A opção "lembrar meu nome" fica fora da v1.1.)
- **Reemissão:** permitida enquanto houver o registro da aprovação (nota, data, semente); o PDF gerado de novo tem a mesma data da aprovação e o mesmo código.
- **Local do arquivo:** `Documentos\TempCPU\Certificados\` por padrão, com nome `certificado-laboratorio-AAAA-MM-DD.pdf`; o aprendiz pode escolher outra pasta. Nunca sobrescreve: se existe, acrescenta `-2`, `-3`.

### Uso no LinkedIn
A tela de sucesso mostra o passo a passo e os campos prontos para copiar da seção **Perfil → Licenças e certificados → Adicionar**:
- **Nome:** Laboratório de Machine Learning do TempCPU (conclusão).
- **Organização emissora:** Mais Valor Consultoria e Serviços.
- **Data de emissão:** a do certificado.
- **ID da credencial:** o código de conferência.
- **URL da credencial:** a página do projeto (não é verificação; o aviso diz isso).
- Recomendação escrita na tela: "descreva como aproveitamento em curso autoguiado; não use como diploma ou certificação profissional".

## Persistência
Em `%LOCALAPPDATA%\TempCPU\lab\progresso.json`, com validação de tipos já existente, novas chaves:
- `provas`: lista de `{tipo, data, semente, nota, por_tema, aprovado, versao_banco}` (últimas 20).
- `certificado`: `{data, nota, semente, versao_banco, codigo}` da melhor aprovação, sem o nome.
Os mesmos limites de privacidade de hoje: nada sai do computador. O arquivo de progresso não contém nome.

## Segurança, privacidade e limites
- **Fraude local:** quem editar o `progresso.json` ou o PDF pode alterar a nota. A spec **aceita** isso e o documento é rotulado como autodeclarado. Proteções fracas (assinatura com chave embutida no programa) são deliberadamente **não** feitas: dariam falsa sensação de segurança.
- **Dado pessoal:** o nome só existe na memória enquanto o PDF é gerado e dentro do PDF. Não vai para log, `progresso.json` nem mensagens de erro.
- **Respostas certas no código:** o banco de questões está em arquivo legível; quem quiser pode ler. Não é um problema para um instrumento de autoavaliação.
- **Linguagem do certificado:** revisada para não afirmar mais do que é (checagem de fatos antes de publicar).

## Fora do escopo (v1.1)
Verificação online de certificados; contas ou login; envio de nota a qualquer servidor; supervisão ou cronômetro; banco de questões editável pelo usuário; retomada de prova interrompida; certificado em inglês (o Laboratório hoje é só em português; ver aberto); nota por questão com banco adaptativo; ranking.

## Critérios de aceite
- **B1** O banco tem 50 questões, 10 por tema, 2 do nivelamento e 8 da final por tema, ids únicos (teste).
- **B2** Toda questão tem exatamente uma resposta correta válida, 3 ou 4 opções, explicação e destino de revisão existente (teste).
- **B3** Nenhuma pergunta repete o texto das 9 perguntas de fixação das lições (teste).
- **B4** Termos vigiados do Glossário estão marcados nas questões (o teste A11 passa a cobrir `questoes.py`).
- **B5** A posição da resposta correta fica distribuída: nenhuma posição concentra mais de 40% do banco (teste).
- **B6** O sorteio da final traz 4 por tema, é reprodutível pela semente e não repete a tentativa anterior quando há outras disponíveis (teste).
- **B7** Aprovação exige ≥ 16/20 **e** ≥ 2/4 em cada tema (teste com casos limite: 16/20 com tema em 1/4 reprova; 15/20 reprova; 16/20 equilibrado aprova).
- **B8** O nivelamento nunca reprova, nunca emite certificado e não altera a nota da final (teste).
- **B9** A avaliação final só abre com as 3 lições concluídas (teste de interface).
- **B10** O PDF é gerado sem dependência nova, abre em leitor de PDF comum, tem 1 página e contém nome, nota, data, versões, código e o aviso fixo (teste que lê o texto do PDF).
- **B11** O código de conferência recalculado bate com o registrado e muda se nome, nota, data ou semente mudarem (teste).
- **B12** O nome não aparece em `progresso.json`, em logs nem em exceções (teste que procura o nome nos arquivos gravados).
- **B13** Nome vazio, curto (< 3) ou longo (> 80) é recusado com explicação; caracteres de controle são removidos (teste).
- **B14** Arquivo existente nunca é sobrescrito (teste); pasta sem permissão mostra erro claro e oferece outra.
- **B15** Fechar a janela no meio da prova avisa e descarta sem tocar nas lições concluídas (teste de interface).
- **B16** Nenhum módulo de rede é importado (teste existente cobre `lab/`).
- **B17** Roteiro manual: fazer o nivelamento, as lições, a final aprovada, emitir, abrir o PDF e adicionar ao LinkedIn seguindo as instruções da tela.

## Dados de exemplo (fictícios)
- Aprendiz "Maria Exemplo": nivelamento 6/10 (T1 2/2, T2 1/2, T3 1/2, T4 1/2, T5 1/2) → "comece pela Lição 1".
- Final aprovada: 17/20 (85%), por tema 4/4, 3/4, 3/4, 3/4, 4/4 → certificado.
- Final reprovada: 16/20 com T3 em 1/4 → não aprova; mensagem "revise Avaliar um modelo" com link para a Lição 1, passo 4.

## Plano de construção (quando aprovada)
1. **B-0** Banco: escrever as 50 questões (revisão humana obrigatória: é o conteúdo que sustenta o certificado) + testes B1 a B5.
2. **B-1** Núcleo sem interface: sorteio, correção, aprovação, persistência (B6 a B8, B11) em `lab/avaliacao.py`.
3. **B-2** Telas: cartões, prova, resultado, histórico (B9, B15).
4. **B-3** Certificado em PDF e telas de emissão e LinkedIn (B10, B12 a B14).
5. **B-4** Revisão independente, roteiro manual B17, atualização de README, ONDE_ESTAMOS e Sobre/privacidade.
Esforço estimado: B-0 é o maior (conteúdo); B-1 a B-3 são código moderado. Paralelizável: B-0 (conteúdo) com B-1 (núcleo).

## Banco de questões: onde fica (2026-10-25)
O banco (`lab/questoes.py`, 50 questões, versão 1.1) **não é versionado no repositório público**: ele traz as respostas, e na fase online a correção é feita no servidor. Está no `.gitignore` (junto de `tests_lab/test_questoes.py`). Ele será levado para o Worker (D1 ou arquivo privado) na implementação. Se as questões do **nivelamento** forem abertas depois, só essas 10 poderão ir ao repositório.

## Decisões (2026-10-25)
1. **Emissor:** Mais Valor Consultoria e Serviços (nome da empresa no certificado; o texto exato da razão social e o CNPJ são informados pelo autor antes da implementação).
2. **Acreditação:** o certificado é emitido pela Mais Valor, sem chancela de instituição de ensino. O aviso fixo passa a dizer "emitido pela Mais Valor Consultoria e Serviços; não é curso regulamentado nem carga horária oficial". Não alegar acreditação que não existe.
3. **Idioma:** questões e certificado só em português nesta versão.
4. **Verificação online:** decidida em seguida para a fase online abaixo (Cloudflare, gratuita, 12 meses). Esta decisão supera as partes "100% local" desta spec.
5. **Regra de aprovação:** 80% global e pelo menos 2 de 4 acertos por tema, como especificado.
6. **Consulta ao Glossário durante a final:** permitida.

## Fase online (decidida em 2026-10-25) — supera as partes "100% local" desta spec
**Decisões:** a avaliação e o certificado passam a funcionar pela **Cloudflare**; o certificado é **gratuito** (sem cobrança, sem pagamento) e emitido pela **Mais Valor Consultoria e Serviços**; o ambiente de aprendizado e os dados do usuário continuam **100% no computador**. O nivelamento e a regra de nota (80% global e ≥ 2 de 4 por tema, ou o equivalente quando as lições novas existirem) não mudam. A verificação vale **12 meses**.

**Onde cada coisa fica**
| Fica no computador | Vai para a Cloudflare |
|---|---|
| histórico, lições, progresso, gráficos, modelos | nome, e-mail, consentimentos, respostas da avaliação, nota, certificado emitido |

**Arquitetura proposta (a confirmar na implementação)**
- **Cloudflare Worker** (TypeScript) com **D1** (SQLite gerenciado): tabelas `aluno`, `consentimento`, `prova`, `resposta`, `certificado`. O banco de questões fica no servidor; o app pede a prova e recebe as questões **sem a resposta correta**; envia as respostas; o servidor corrige e devolve nota por tema.
- **Cadastro:** nome e e-mail, com confirmação do e-mail por link (evita e-mail de terceiros). Consentimentos separados: (a) tratamento para emitir e verificar o certificado (necessário); (b) comunicações da Mais Valor (opcional, **desmarcado**).
- **Antiabuso:** Cloudflare Turnstile no cadastro, limite de tentativas por e-mail e por IP, intervalo mínimo entre provas.
- **Certificado:** o servidor gera o PDF e um **código de verificação** assinado com uma chave guardada como segredo do Worker (nunca no código nem no repositório). Página pública `verificar/{código}` mostra nome, data, nota geral e validade, sem e-mail.
- **Validade:** 12 meses a partir da emissão; depois a página mostra "expirado". Renovar = refazer a avaliação (gratuito).
- **App:** tela de cadastro/login simples por e-mail com link; o token fica no computador; sem conta, o aprendiz usa o Laboratório inteiro normalmente (só a avaliação e o certificado exigem cadastro).
- **E-mail transacional:** exige um provedor (a definir) e domínio com SPF/DKIM/DMARC configurados.

**Obrigações novas (LGPD e transparência)**
- Política de privacidade pública: controlador (Mais Valor Consultoria e Serviços, CNPJ), finalidades, base legal, dados coletados, retenção, compartilhamento (Cloudflare como operador), direitos do titular e contato do encarregado.
- Exclusão da conta e dos dados a pedido (inclui invalidar o certificado).
- **Textos que hoje dizem "nada é enviado pela internet"** (Sobre e privacidade no Laboratório, README, site, FAQ) precisam ser reescritos para: "seus dados do aprendizado nunca saem do computador; só a avaliação e o certificado usam a internet, se você optar por eles". O teste que proíbe módulos de rede em `lab/` passa a ter uma exceção explícita e isolada (um único módulo `lab/nuvem.py`), com teste que garante que ele só envia os campos permitidos (nunca histórico, lições nem resultados de modelo).
- Pesquisar antes: retenção de dados de usuários de menor idade (o público pode incluir menores; definir idade mínima declarada).

**Critérios de aceite adicionais**
- **N1** O servidor nunca envia a resposta correta antes da entrega; reenvio da mesma prova não altera a nota.
- **N2** O app não envia nada além de nome, e-mail, consentimentos e respostas (teste de contrato do payload; teste que procura caminhos de arquivo, temperaturas e nomes de programas no tráfego simulado e não encontra).
- **N3** Verificação pública não expõe e-mail nem respostas.
- **N4** Código de verificação inválido, adulterado ou expirado mostra mensagens distintas.
- **N5** Limite de tentativas e Turnstile bloqueiam abuso em teste.
- **N6** Exclusão de conta remove cadastro, respostas e certificado e a verificação passa a "não encontrado".
- **N7** Sem internet, o Laboratório inteiro funciona; só a avaliação mostra "precisa de conexão".
- **N8** Segredos (chave de assinatura, chaves de e-mail) fora do repositório, em `wrangler secret`/`.dev.vars` ignorado pelo Git.

**Esforço realista:** Worker + D1 + e-mail + Turnstile + geração de PDF + tela de cadastro + textos legais + 50 questões revisadas + testes: da ordem de dias a poucas semanas. **Não é viável fazer com qualidade e sem revisão jurídica em um dia.**
