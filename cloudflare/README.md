# Avaliação e certificado (Cloudflare Worker + D1)

Páginas e API do nivelamento, da avaliação final e do certificado do Laboratório do TempCPU. Todas as questões são de múltipla escolha. Emissor: Mais Valor Consultoria e Serviços. Especificação: `docs/SPEC-avaliacao.md`.

**O que vai para a nuvem:** cadastro (nome e e-mail), respostas da prova, resultado e certificado. **O que nunca vai:** histórico do computador, lições, gráficos e modelos do Laboratório.

## Como funciona
| Rota | O que faz |
|---|---|
| `/` | apresentação |
| `/prova/nivelamento` | 16 questões, **sem cadastro** (prova anônima, sem dado pessoal) |
| `/cadastro`, `/entrar`, `/confirmar` | cadastro com consentimento, link de acesso por e-mail (20 min, uso único), sem senha |
| `/prova/final` | 24 questões (3 por tema, 8 temas), exige login; intervalo mínimo e limite diário entre tentativas |
| `/resultado/:id` | nota, por tema, o que revisar (a explicação só aparece depois da entrega) |
| `/certificado/emitir/:id` → `/certificado/:codigo` | só para quem tem 80% e pelo menos metade de cada tema; página imprimível (salvar em PDF) com passo a passo do LinkedIn |
| `/verificar/:codigo` | pública: nome, nota, datas e emissor (nunca o e-mail); válido, expirado (12 meses), revogado ou não encontrado |
| `/conta` | exclusão de todos os dados (o certificado deixa de ser verificável) |
| `/privacidade` | **rascunho para revisão jurídica** |

A correção é feita no servidor: o aluno nunca recebe a resposta certa antes de entregar. O código do certificado é um HMAC-SHA256 com segredo do servidor.

## Rodar localmente
```powershell
cd cloudflare
npm install
npm run banco:exemplo      # questões de mentira em banco/ativo.json (não versionado)
npm run d1:local           # cria as tabelas no D1 local
npm run dev                # http://localhost:8787  (o link de e-mail aparece no log, AMBIENTE=dev)
npm test                   # 36 testes (D1 de mentira sobre node:sqlite)
npm run tipos
```
Para usar as 80 questões reais (privadas): `npm run banco:real` (executa `tools/exportar_banco.py` com o ambiente do Laboratório). O arquivo `banco/ativo.json` tem as respostas e **não vai para o Git**.

## Publicar (o que só você pode fazer)
1. Conta Cloudflare e `npx wrangler login`.
2. `npx wrangler d1 create tempcpu-avaliacao` e colocar o `database_id` em `wrangler.toml`.
3. `npx wrangler d1 execute tempcpu-avaliacao --remote --file=schema.sql`.
4. Segredos: `npx wrangler secret put SEGREDO_ASSINATURA` (texto longo e aleatório), `RESEND_API_KEY` (ou outro provedor, ver `src/externos.ts`), `TURNSTILE_SECRET`.
5. Em `wrangler.toml`: **apagar** `AMBIENTE = "dev"` (em dev o Turnstile é dispensado e o e-mail não sai), e definir `EMAIL_REMETENTE` (domínio verificado), `TURNSTILE_SITEKEY`, `ORIGEM_PUBLICA`, `EMISSOR_CNPJ`, `CONTATO_PRIVACIDADE`.
6. `npm run banco:real` e `npm run deploy`.
7. Revisão jurídica do texto de `/privacidade` e dos termos antes de divulgar.

## Pendências conhecidas
- Provedor de e-mail e domínio ainda não escolhidos (há adaptador para o Resend).
- Certificado é uma página para imprimir/salvar em PDF; PDF gerado no servidor fica para depois.
- O Laboratório (tkinter) ainda não tem botão que abra estas páginas.
- Não foi publicado nem testado na conta Cloudflare real.
