# Prontidão para lançamento — avaliação de 2026-10-25

Notas são **julgamento meu** a partir do que foi construído e testado neste projeto, não medição. Cada nota diz o que a sustenta.

## Veredito
- **Versão 0.1 pública, para entusiastas (código no GitHub + documentação + página):** pronta em horas, depois de 6 itens da lista "Para lançar hoje".
- **Lançamento para usuário comum** (o público que você definiu): **não está pronto**, porque o app só roda a partir do código-fonte com Python e ambiente virtual; não há executável nem instalador.
- **Avaliação e certificado pela Cloudflare:** **não ficam prontos hoje.** Há spec e decisões, mas zero código, zero questões escritas, e a parte de cadastro com e-mail exige texto de LGPD e provedor de e-mail. Fazer correndo, no mesmo dia, geraria risco real (dados de pessoas, certificado em nome de uma empresa).

**Recomendação:** lançar hoje a **v0.1 (app + Laboratório + site + documentação)** e anunciar a avaliação e o certificado como **próxima etapa**, sem prometer data.

## Grau de prontidão por área
| Área | Nota | O que sustenta | O que falta |
|---|---|---|---|
| Núcleo do app (leitura, janela, histórico, barra de tarefas) | 80% | funciona; 154 testes; consumo medido (0,3% CPU, 13 MB); histórico em SQLite | testado em 1 computador; "Iniciar com o Windows" sem teste |
| Laboratório (3 lições, glossário, qualidade dos dados) | 75% | 155 testes; revisão independente com 17+5 correções; instalação real provada | lições 1 e 2 nunca rodadas com histórico real (poucos dias de dados); roteiro manual F8 pendente |
| Distribuição para o usuário comum | **20%** | só `iniciar.bat` + `.venv` + `pip install` | executável/instalador (PyInstaller), assinatura de código, SmartScreen/antivírus, atualização |
| Compatibilidade | 30% | testado só em Windows 11, Ryzen e ASUS | Intel e outras marcas; execução sem administrador; Windows 10 |
| Repositório | 30% | `.gitignore` correto, `.env` ignorado; `gh` autenticado | **nenhum commit, sem remoto, sem `LICENSE`**, sem CI |
| Documentação | 70% | README, `CLAUDE.md`, 5 ADRs, 4 specs, `ONDE_ESTAMOS`, `TAREFAS` | `LICENSE`, `CHANGELOG`, política de privacidade pública, guia "primeiros passos" para quem não programa |
| Página de apresentação | 80% | `site/` PT/EN, capturas com dados de demonstração, workflow de Pages | não publicada; vista só em largura de celular |
| Segurança e privacidade | 75% | leitura somente leitura, sem rede, credenciais fora do código, sem nomes de programas | caminho pessoal no `ONDE_ESTAMOS`/testes; revisão de segurança formal (`saas-audit`) não feita |
| Avaliação (provas) | **5%** | spec | banco de 50 questões (80 com lições novas), núcleo, telas, Worker, D1, testes |
| Certificado + verificação online | **5%** | spec | PDF no servidor, assinatura, página de verificação, e-mail, Turnstile |
| LGPD / jurídico | **0%** | — | política de privacidade, base legal, consentimentos, retenção, exclusão; revisão por advogado |
| Lições novas (classificação, agrupamento, regularização…) | 5% | spec | calibração e construção |
| Divulgação (LinkedIn, Instagram, vídeo) | 0% | — | roteiro, textos, vídeo, links; ver abaixo |

## Para lançar hoje (v0.1 pública)
Itens que bloqueiam e quem decide ou faz:
1. **Licença** (decisão sua). Sem `LICENSE` ninguém pode legalmente usar ou contribuir. Opções comuns: MIT (permissiva), GPL-3.0 (copyleft), ou "todos os direitos reservados, código visível". As dependências têm licenças próprias: `pystray` é LGPL, `pywin32` PSF, `Pillow` HPND, `psutil` BSD, `WMI` MIT, `scikit-learn`/`numpy` BSD. Distribuir um `.exe` com `pystray` exige cumprir a LGPL (já está na lista de tarefas trocar por ctypes). Eu escrevo o arquivo e um `NOTICE` com as dependências depois da sua escolha.
2. **Primeiro commit** (eu faço): conferir que `.env` não entra, que não há dado pessoal, remover o caminho pessoal do `ONDE_ESTAMOS` e do teste do glossário.
3. **Criar o repositório e enviar** (precisa do seu OK explícito, é ação pública): nome, visibilidade e conta (`gh` está logado como `LucianoMLO`).
4. **Publicar a página** no GitHub Pages (o workflow já existe; precisa habilitar Pages no repositório e do passo 3).
5. **Ajustar os textos** que hoje prometem o que não existe: a página diz "Download — em breve"; manter assim e explicar "rodar a partir do código" no README para quem sabe usar Python. Dizer claramente "testado só em Windows 11 + Ryzen + ASUS".
6. **Release**: um `.zip` do código com o `iniciar.bat` serve para entusiastas; para o usuário comum falta o executável (ver abaixo).
7. **Rodar as duas suítes** no commit final e registrar o resultado (eu faço).

**Tempo estimado:** 1 a 3 horas depois das suas decisões (1 e 3), sem o executável. Com executável, mais um dia para fazer, testar em outra máquina limpa e lidar com falso positivo de antivírus.

## O que falta para o público comum (v1.0)
1. **Instalador/executável** (PyInstaller) e teste em máquina limpa; assinatura de código (certificado pago) ou aviso claro do SmartScreen.
2. **Compatibilidade**: pelo menos um teste em Intel e outro sem administrador; mensagem útil quando a fonte é só ACPI.
3. **Lições verificadas com histórico real** (precisa de dias de uso).
4. **Laboratório sem exigir Python** (ou aceitar que ele continua sendo para quem tem).
5. **Avaliação e certificado** pela Cloudflare (abaixo).
6. **Revisão jurídica** dos textos de privacidade.

## Avaliação e certificado pela Cloudflare: o que fazer e em que ordem
Spec: `docs/SPEC-avaliacao.md` (seção "Fase online"). Ordem sugerida:
1. Escrever as 50 questões (revisão sua).
2. Núcleo da prova e do certificado (Worker + D1) e testes de contrato.
3. Cadastro com e-mail confirmado + Turnstile + limites.
4. Telas do app (cadastro, prova, resultado, emissão).
5. PDF assinado e página pública de verificação.
6. Política de privacidade e textos; revisão jurídica.
7. Reescrever os textos que hoje dizem "nada é enviado" e ajustar o teste de rede.
8. Roteiro manual ponta a ponta, publicação.
**Pré-requisitos seus:** conta Cloudflare, domínio (para o e-mail e a página de verificação), provedor de e-mail transacional, CNPJ e razão social da Mais Valor, e-mail do encarregado.

## Divulgação: LinkedIn, Instagram e vídeo no YouTube com IA realista
- **Só prometa o que existe:** "monitor de temperatura da CPU para Windows, código aberto/gratuito, com Laboratório de machine learning opcional". Não anuncie certificado até ele existir, ou diga "em breve" sem data.
- **Honestidade sobre compatibilidade:** testado em Windows 11 + Ryzen + ASUS; outros computadores podem ter menos detalhes.
- **Vídeo gerado por IA realista:** use apenas para narração/apresentação do produto. Não simule depoimento de "usuário", não use rosto ou voz de pessoa real sem autorização, não mostre dados de computador real. Mostre as capturas com **dados de demonstração** (as do site). Plataformas pedem para rotular conteúdo sintético realista (YouTube, Instagram e LinkedIn têm essa marcação; confirme as regras atuais antes de publicar). Dizer no vídeo e na descrição que foi gerado por IA protege sua credibilidade.
- **Chamada para ação:** link do repositório e da página; não colocar link de download que não exista.
- **Peças:** (1) post LinkedIn (problema → solução → captura → link); (2) carrossel/post Instagram (3 a 5 imagens: temperatura na barra, gráfico por zonas, histórico, Laboratório); (3) roteiro de vídeo de 60 a 90 s (gancho: "seu notebook esquenta e você não sabe por quê").
- Posso escrever os textos, o roteiro e as legendas; **a publicação é sua**, e nada deve ir ao ar antes de o repositório e a página estarem públicos.

## Riscos a aceitar ou tratar
| Risco | Impacto | Tratamento |
|---|---|---|
| Usuário comum não consegue instalar | alto (frustração, reclamação) | lançar como "v0.1 para quem usa Python" e priorizar o executável |
| Antivírus/SmartScreen marcam o `.exe` | alto | assinatura de código e teste em máquina limpa antes de oferecer download |
| Leitura de temperatura parada em Intel | médio | já avisado na tela; documentado |
| Coleta de e-mail sem LGPD pronta | alto | não coletar até a política e a revisão jurídica |
| Certificado em nome de empresa sem controle | médio | só emitir com chave no servidor, aviso de "sem acreditação" e verificação pública |
| Texto "nada é enviado" ficar errado depois da nuvem | médio | reescrever junto com a entrega da avaliação |

## Próxima ação sugerida
Você decide **(1) licença** e **(3) criar o repositório e enviar**. Com isso, eu faço o primeiro commit limpo, escrevo `LICENSE`/`NOTICE`/`CHANGELOG`, habilito o workflow e preparo os textos de divulgação. Avaliação e certificado entram na sequência, em etapas.
