# ADR 0005 — Distribuição gratuita com apoio opcional

**Data:** 2026-10-25 · **Status:** aceita (revisar após o lançamento)

## Contexto
Era preciso decidir nome público, preço e modelo antes de publicar a página. A ideia inicial foi "aberto para doação acima de R$ 5,00". Um valor mínimo deixa de ser doação e vira preço, com consequências fiscais (nota, enquadramento), de suporte e de conversão (taxas pesam em valores pequenos). Além disso, o app foi testado só em Windows 11 com Ryzen/Radeon e ASUS; em Intel cai na leitura ACPI, que pode ficar parada. Cobrar agora geraria expectativa de suporte e de reembolso que o produto ainda não sustenta.

## Decisão
1. **O TempCPU é gratuito, sem restrição de recursos**, incluindo o Laboratório.
2. **Apoio opcional, sem valor mínimo**, apresentado na página (bloco "Apoie o projeto") e nunca como pop-up ou bloqueio dentro do app. A chave Pix e o link de plataforma são preenchidos pelo autor; até lá a página mostra o bloco sem chave.
3. **Nome:** mantém **TempCPU** (provisório; é descritivo, mas genérico para marca). Alternativas consideradas: "Termoscópio", "Calorzinho". Antes de fixar um nome novo, pesquisar conflito no INPI, GitHub e buscadores.
4. **Uma versão paga ("Pro") fica adiada.** Só será reavaliada quando: (a) o Laboratório rodar sem exigir Python instalado; (b) houver executável assinado; (c) houver CNPJ/MEI para emitir nota; (d) a compatibilidade além de Ryzen/ASUS estiver testada; (e) houver sinal de demanda (instalações e pedidos).

## Consequências
- Sem receita direta no curto prazo; o custo de suporte e fiscal é mínimo.
- A página não promete suporte nem compatibilidade além do testado (já declarado na seção de requisitos).
- Receber apoio por Pix de pessoa física tem implicações fiscais que o autor deve confirmar com um contador antes de divulgar a chave.
- Reversível: cobrar depois é possível; retirar uma cobrança já feita não é.
