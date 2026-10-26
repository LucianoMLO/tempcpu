// Páginas em HTML. Todo texto vindo do usuário ou do banco passa por escapar(); os trechos já seguros usam seguro().
import { faixa, notaPct, recomendarLicao, type Banco, type Resultado } from "./avaliacao.ts";
import { escapar } from "./seguranca.ts";
import type { Aluno, Env, Glossario, LinhaCertificado } from "./tipos.ts";

const e = escapar;

export function fmtData(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo", day: "2-digit", month: "long", year: "numeric" });
}

/** Termos do glossário entre ⟦chave⟧ ou ⟦chave|texto⟧ viram <abbr> com a definição. */
export function termos(texto: string, glossario: Glossario): string {
  return e(texto).replace(/⟦([^|⟧]+)(?:\|([^⟧]*))?⟧/g, (_m, chave: string, mostra?: string) => {
    const t = glossario[chave];
    const rotulo = mostra || t?.nome || chave;
    return t ? `<abbr class="termo" tabindex="0" title="${e(t.definicao)}">${rotulo}</abbr>` : rotulo;
  });
}

export interface Contexto {
  env: Env;
  aluno: Aluno | null;
}

export function pagina(ctx: Contexto, titulo: string, corpo: string, opts: { turnstile?: boolean; scripts?: string[]; imprimir?: boolean } = {}): string {
  const nav = ctx.aluno
    ? `<a href="/painel">Meu painel</a><a href="/conta">Conta</a><button type="button" class="link" data-sair>Sair</button>`
    : `<a href="/entrar">Entrar</a>`;
  const scripts = ["/formulario.js", ...(opts.scripts ?? [])].map((s) => `<script src="${s}" defer></script>`).join("");
  const ts = opts.turnstile && ctx.env.TURNSTILE_SITEKEY ? `<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>` : "";
  return `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${e(titulo)} — Avaliação do Laboratório TempCPU</title><meta name="robots" content="noindex">
<link rel="stylesheet" href="/estilo.css">${ts}</head>
<body${opts.imprimir ? ' class="imprimir"' : ""}>
<header class="topo"><a class="marca" href="/"><span class="ponto"></span>TempCPU · Avaliação</a>
<nav><a href="/verificar">Verificar certificado</a>${nav}</nav></header>
<main>${corpo}</main>
<footer><p>${e(ctx.env.EMISSOR_NOME || "Mais Valor Consultoria e Serviços")} · <a href="/privacidade">Privacidade</a></p></footer>
${scripts}</body></html>`;
}

function widgetTurnstile(env: Env): string {
  return env.TURNSTILE_SITEKEY ? `<div class="cf-turnstile" data-sitekey="${e(env.TURNSTILE_SITEKEY)}"></div>` : "";
}

export function inicio(ctx: Contexto): string {
  const final = ctx.aluno
    ? `<a class="botao" href="/prova/final">Fazer a avaliação final</a>`
    : `<a class="botao" href="/cadastro">Criar cadastro para a avaliação final</a> <a class="botao claro" href="/entrar">Já tenho cadastro</a>`;
  return pagina(ctx, "Início", `
<section class="heroi"><h1>Avaliação e certificado do Laboratório</h1>
<p class="lead">Teste o que você aprendeu nas lições de machine learning do TempCPU. Se acertar pelo menos 80%, você recebe um certificado gratuito, com página de verificação válida por 12 meses.</p></section>
<section class="grade">
<article class="cartao"><h2>1. Nivelamento</h2><p>10 questões, sem cadastro e sem nota mínima. Mostra por qual lição começar. Não guarda nenhum dado pessoal.</p>
<p><a class="botao" href="/prova/nivelamento">Fazer o nivelamento</a></p></article>
<article class="cartao"><h2>2. Avaliação final</h2><p>20 questões de múltipla escolha, depois das 3 lições. Exige cadastro com e-mail confirmado. Aprovação: 80% de acertos e pelo menos metade das questões de cada tema.</p>
<p>${final}</p></article>
<article class="cartao"><h2>3. Certificado</h2><p>Emitido pela ${e(ctx.env.EMISSOR_NOME || "Mais Valor Consultoria e Serviços")}. É um certificado de aproveitamento, <strong>sem acreditação</strong> de instituição de ensino e sem carga horária oficial.</p></article>
</section>
<p class="nota">Os dados do seu aprendizado (histórico do computador, lições, gráficos) ficam só no seu computador. Aqui entram apenas o cadastro, as respostas da prova e o certificado. Veja a <a href="/privacidade">política de privacidade</a>.</p>`);
}

export function paginaCadastro(ctx: Contexto): string {
  return pagina(ctx, "Cadastro", `
<h1>Cadastro</h1>
<p>Usamos seu nome e e-mail só para a avaliação final e o certificado. Você confirma o e-mail por um link.</p>
<form class="form" data-api="/api/cadastro">
<label>Nome<input name="nome" required minlength="3" maxlength="80" autocomplete="name"></label>
<label>E-mail<input name="email" type="email" required maxlength="254" autocomplete="email"></label>
<label class="check"><input type="checkbox" name="consentimento" required> Li e aceito a <a href="/privacidade" target="_blank">política de privacidade</a> e autorizo o uso do meu nome e e-mail para emitir e verificar o certificado. (obrigatório)</label>
<label class="check"><input type="checkbox" name="marketing"> Quero receber novidades e ofertas de treinamento por e-mail. (opcional)</label>
${widgetTurnstile(ctx.env)}
<button class="botao" type="submit">Criar cadastro</button><p class="msg" role="status" aria-live="polite"></p></form>`, { turnstile: true });
}

export function paginaEntrar(ctx: Contexto): string {
  return pagina(ctx, "Entrar", `
<h1>Entrar</h1>
<p>Informe seu e-mail e enviaremos um link de acesso. Não há senha.</p>
<form class="form" data-api="/api/entrar">
<label>E-mail<input name="email" type="email" required maxlength="254" autocomplete="email"></label>
${widgetTurnstile(ctx.env)}
<button class="botao" type="submit">Enviar link</button><p class="msg" role="status" aria-live="polite"></p></form>
<p class="nota">Ainda não tem cadastro? <a href="/cadastro">Criar cadastro</a>.</p>`, { turnstile: true });
}

export function paginaConfirmar(ctx: Contexto, token: string): string {
  return pagina(ctx, "Confirmar", `
<h1>Confirmar acesso</h1><p>Clique para entrar e confirmar o seu e-mail.</p>
<form class="form" data-api="/api/confirmar"><input type="hidden" name="t" value="${e(token)}">
<button class="botao" type="submit">Entrar</button><p class="msg" role="status" aria-live="polite"></p></form>`);
}

export function aviso(ctx: Contexto, titulo: string, texto: string, link?: { href: string; texto: string }): string {
  return pagina(ctx, titulo, `<h1>${e(titulo)}</h1><p>${e(texto)}</p>${link ? `<p><a class="botao" href="${e(link.href)}">${e(link.texto)}</a></p>` : ""}`);
}

export interface ResumoProva {
  id: string;
  tipo: string;
  entregue_em: number;
  resultado: Resultado;
  certificado: LinhaCertificado | null;
}

export function painel(ctx: Contexto, provas: ResumoProva[], certs: LinhaCertificado[], banco: Banco, agora: number): string {
  const linhas = provas
    .map((p) => {
      const nota = notaPct(p.resultado).toFixed(0);
      const sit = p.tipo === "final" ? (p.resultado.aprovado ? "aprovado" : "não aprovado") : "nivelamento";
      return `<tr><td>${fmtData(p.entregue_em)}</td><td>${p.tipo === "final" ? "Final" : "Nivelamento"}</td><td>${nota}%</td><td>${sit}</td><td><a href="/resultado/${e(p.id)}">ver</a></td></tr>`;
    })
    .join("");
  const certHtml = certs
    .map((c) => `<li><a href="/certificado/${e(c.codigo)}">Certificado ${e(c.codigo)}</a> — emitido em ${fmtData(c.emitido_em)}, ${c.valido_ate > agora ? `válido até ${fmtData(c.valido_ate)}` : "expirado"}</li>`)
    .join("");
  return pagina(ctx, "Meu painel", `
<h1>Olá, ${e(ctx.aluno?.nome ?? "")}</h1>
<p><a class="botao" href="/prova/final">Fazer a avaliação final</a> <a class="botao claro" href="/prova/nivelamento">Fazer o nivelamento</a></p>
<h2>Meus certificados</h2>${certHtml ? `<ul>${certHtml}</ul>` : `<p class="nota">Você ainda não emitiu certificado.</p>`}
<h2>Minhas provas</h2>${linhas ? `<table><thead><tr><th>Data</th><th>Prova</th><th>Nota</th><th>Situação</th><th></th></tr></thead><tbody>${linhas}</tbody></table>` : `<p class="nota">Nenhuma prova entregue ainda.</p>`}
<p class="nota">Banco de questões, versão ${e(banco.versao)}.</p>`);
}

export function paginaProva(ctx: Contexto, id: string, tipo: string, itens: { id: string; tema: string; pergunta: string; opcoes: string[] }[], glossario: Glossario, banco: Banco): string {
  const titulo = tipo === "final" ? "Avaliação final" : "Teste de nivelamento";
  const questoes = itens
    .map(
      (q, i) => `<fieldset class="questao" data-id="${e(q.id)}"><legend><span class="num">${i + 1}.</span> ${termos(q.pergunta, glossario)}</legend>
${q.opcoes.map((o, k) => `<label class="opcao"><input type="radio" name="q-${e(q.id)}" value="${k}"> <span>${termos(o, glossario)}</span></label>`).join("")}</fieldset>`,
    )
    .join("");
  void banco;
  return pagina(
    ctx,
    titulo,
    `<h1>${titulo}</h1>
<p class="nota">${itens.length} questões de múltipla escolha, uma única resposta correta em cada. Passe o mouse ou toque nos termos sublinhados para ver o que significam. Você pode consultar o Glossário do Laboratório durante a prova.</p>
<form id="prova" data-id="${e(id)}" data-total="${itens.length}">${questoes}
<div class="barra"><span id="contagem" role="status" aria-live="polite">0 de ${itens.length} respondidas</span><button class="botao" type="submit">Entregar</button></div>
<p class="msg" role="status" aria-live="polite"></p></form>`,
    { scripts: ["/prova.js"] },
  );
}

export function paginaResultado(ctx: Contexto, provaId: string, r: Resultado, banco: Banco, glossario: Glossario, certificado: LinhaCertificado | null, dono: boolean): string {
  const nota = notaPct(r);
  const temas = Object.entries(r.porTema)
    .map(([t, [a, n]]) => {
      const f = faixa(a, n);
      const rot = f === "dominado" ? "dominado" : f === "revisar" ? "revisar" : "refazer a lição";
      return `<li class="tema ${f}"><span>${e(banco.temas[t] ?? t)}</span><span class="barra-tema"><i style="width:${(100 * a) / n}%"></i></span><span>${a} de ${n} · ${rot}</span></li>`;
    })
    .join("");
  const erradas = r.erradas
    .map((x) => {
      const marcada = x.marcada === null ? "<em>em branco</em>" : termos(x.opcoes[x.marcada] ?? "", glossario);
      return `<li class="errada"><p><strong>${termos(x.pergunta, glossario)}</strong></p><p>Sua resposta: ${marcada}</p><p>Resposta correta: ${termos(x.opcoes[x.correta] ?? "", glossario)}</p><p class="nota">${termos(x.explicacao, glossario)} <em>Revisar: Lição ${x.revisar[0]}, passo ${x.revisar[1]}.</em></p></li>`;
    })
    .join("");
  let fecho = "";
  if (r.tipo === "final" && r.aprovado) {
    fecho = certificado
      ? `<p><a class="botao" href="/certificado/${e(certificado.codigo)}">Ver meu certificado</a></p>`
      : dono
        ? `<p class="ok">Parabéns! Você foi aprovado(a).</p><p><a class="botao" href="/certificado/emitir/${e(provaId)}">Emitir certificado</a></p>`
        : "";
  } else if (r.tipo === "final") {
    fecho = `<div class="aviso"><p>Ainda não foi desta vez. Para ser aprovado(a):</p><ul>${r.motivos.map((m) => `<li>${e(m)}</li>`).join("")}</ul></div><p><a class="botao" href="/prova/final">Tentar de novo (questões diferentes)</a></p>`;
  } else {
    const l = recomendarLicao(r);
    fecho = `<p class="${l ? "aviso" : "ok"}">${l ? `Sugestão: comece pela <strong>Lição ${l}</strong> do Laboratório.` : "Você já domina o básico. Faça as lições para fixar e depois a avaliação final."}</p><p><a class="botao claro" href="/">Voltar ao início</a></p>`;
  }
  return pagina(ctx, "Resultado", `
<h1>${r.tipo === "final" ? "Resultado da avaliação final" : "Resultado do nivelamento"}</h1>
<p class="nota-grande">${nota.toFixed(0)}% <small>(${r.acertos} de ${r.total})</small></p>
<h2>Por tema</h2><ul class="temas">${temas}</ul>${fecho}
${erradas ? `<h2>O que revisar</h2><ol class="erradas">${erradas}</ol>` : `<p class="ok">Nenhuma questão errada.</p>`}`);
}

export function paginaEmitir(ctx: Contexto, provaId: string, nomeSugerido: string): string {
  return pagina(ctx, "Emitir certificado", `
<h1>Emitir certificado</h1>
<p>Confira como seu nome deve aparecer no documento. Depois de emitido, o nome não pode ser alterado.</p>
<form class="form" data-api="/api/certificado"><input type="hidden" name="provaId" value="${e(provaId)}">
<label>Nome no certificado<input name="nome" required minlength="3" maxlength="80" value="${e(nomeSugerido)}"></label>
<button class="botao" type="submit">Emitir</button><p class="msg" role="status" aria-live="polite"></p></form>`);
}

export function paginaCertificado(ctx: Contexto, c: LinhaCertificado, banco: Banco, agora: number): string {
  const emissor = ctx.env.EMISSOR_NOME || "Mais Valor Consultoria e Serviços";
  const porTema = JSON.parse(c.por_tema_json) as Record<string, [number, number]>;
  const base = ctx.env.ORIGEM_PUBLICA || "";
  const linhas = Object.entries(porTema).map(([t, [a, n]]) => `<li>${e(banco.temas[t] ?? t)}: ${a} de ${n}</li>`).join("");
  const expirado = c.valido_ate <= agora;
  return pagina(
    ctx,
    "Certificado",
    `<div class="folha">
<p class="sup">${e(emissor)}${ctx.env.EMISSOR_CNPJ ? ` · CNPJ ${e(ctx.env.EMISSOR_CNPJ)}` : ""}</p>
<h1>Certificado de aproveitamento</h1>
<p class="sub">Laboratório de Machine Learning do TempCPU</p>
<p class="texto">Certificamos que</p><p class="nome">${e(c.nome)}</p>
<p class="texto">concluiu as lições do Laboratório e obteve <strong>${c.nota_pct.toFixed(0)}%</strong> de aproveitamento na avaliação final.</p>
<ul class="temas-cert">${linhas}</ul>
<p class="meta">Emitido em ${fmtData(c.emitido_em)} · Verificação válida até ${fmtData(c.valido_ate)}${expirado ? " (expirada)" : ""} · Banco de questões ${e(c.versao_banco)}</p>
<p class="codigo">Código de verificação: <strong>${e(c.codigo)}</strong><br>${e(base)}/verificar/${e(c.codigo)}</p>
<p class="aviso-fixo">Certificado de aproveitamento emitido pela ${e(emissor)}, sem supervisão e sem acreditação de instituição de ensino. Não indica carga horária oficial nem constitui curso regulamentado.</p></div>
<div class="acoes nao-imprimir"><button class="botao" type="button" onclick="window.print()">Imprimir ou salvar em PDF</button>
<details class="linkedin"><summary>Como adicionar ao LinkedIn</summary><ol>
<li>No seu perfil, escolha <strong>Adicionar seção do perfil</strong> → <strong>Licenças e certificados</strong>.</li>
<li><strong>Nome:</strong> Laboratório de Machine Learning do TempCPU (aproveitamento)</li>
<li><strong>Organização emissora:</strong> ${e(emissor)}</li>
<li><strong>Data de emissão:</strong> ${fmtData(c.emitido_em)}</li>
<li><strong>ID da credencial:</strong> ${e(c.codigo)}</li>
<li><strong>URL da credencial:</strong> ${e(base)}/verificar/${e(c.codigo)}</li></ol>
<p class="nota">Descreva como aproveitamento em curso autoguiado. Não use como diploma ou certificação profissional.</p></details></div>`,
    { imprimir: true },
  );
}

export function paginaVerificar(ctx: Contexto, estado: "formulario" | "nao_encontrado" | "revogado" | "expirado" | "valido", c?: LinhaCertificado): string {
  if (estado === "formulario") {
    return pagina(ctx, "Verificar certificado", `<h1>Verificar certificado</h1>
<form class="form" data-api="/api/verificar"><label>Código de verificação<input name="codigo" required maxlength="12" pattern="[A-Za-z0-9]{12}" placeholder="12 caracteres"></label>
<button class="botao" type="submit">Verificar</button><p class="msg" role="status" aria-live="polite"></p></form>`);
  }
  const mensagens = {
    nao_encontrado: ["Certificado não encontrado", "Não existe certificado com este código. Confira se digitou corretamente."],
    revogado: ["Certificado revogado", "Este certificado foi revogado e não é mais válido."],
    expirado: ["Verificação expirada", "Este certificado foi emitido, mas o prazo de 12 meses de verificação já passou."],
    valido: ["Certificado válido", ""],
  } as const;
  const [titulo, texto] = mensagens[estado];
  const detalhe = c && (estado === "valido" || estado === "expirado")
    ? `<dl><dt>Nome</dt><dd>${e(c.nome)}</dd><dt>Aproveitamento</dt><dd>${c.nota_pct.toFixed(0)}%</dd><dt>Emitido em</dt><dd>${fmtData(c.emitido_em)}</dd><dt>Verificação válida até</dt><dd>${fmtData(c.valido_ate)}</dd><dt>Emissor</dt><dd>${e(ctx.env.EMISSOR_NOME || "Mais Valor Consultoria e Serviços")}</dd></dl>`
    : "";
  return pagina(ctx, titulo, `<h1 class="${estado === "valido" ? "ok" : ""}">${titulo}</h1>${texto ? `<p>${e(texto)}</p>` : ""}${detalhe}<p class="nota">Certificado de aproveitamento, sem acreditação de instituição de ensino.</p>`);
}

export function paginaConta(ctx: Contexto): string {
  return pagina(ctx, "Minha conta", `
<h1>Minha conta</h1>
<p>Nome: <strong>${e(ctx.aluno?.nome ?? "")}</strong><br>E-mail: <strong>${e(ctx.aluno?.email ?? "")}</strong></p>
<h2>Excluir meus dados</h2>
<p>Apaga seu cadastro, suas provas e seus certificados. Os certificados deixam de ser verificáveis. Isso não pode ser desfeito.</p>
<form class="form" data-api="/api/conta/excluir"><label>Digite EXCLUIR para confirmar<input name="confirmar" required autocomplete="off"></label>
<button class="botao perigo" type="submit">Excluir tudo</button><p class="msg" role="status" aria-live="polite"></p></form>`);
}

export function paginaPrivacidade(ctx: Contexto): string {
  const emissor = e(ctx.env.EMISSOR_NOME || "Mais Valor Consultoria e Serviços");
  const contato = ctx.env.CONTATO_PRIVACIDADE ? e(ctx.env.CONTATO_PRIVACIDADE) : "<em>(e-mail do encarregado: a preencher)</em>";
  return pagina(ctx, "Privacidade", `
<h1>Política de privacidade</h1>
<p class="aviso"><strong>Rascunho para revisão jurídica.</strong> Este texto ainda não foi revisado por advogado e deve ser revisado antes da divulgação pública.</p>
<h2>Quem é o controlador</h2><p>${emissor}${ctx.env.EMISSOR_CNPJ ? `, CNPJ ${e(ctx.env.EMISSOR_CNPJ)}` : ""}. Contato do encarregado de dados: ${contato}.</p>
<h2>O que fica no seu computador</h2><p>O Laboratório e o histórico do computador funcionam localmente. Nada do seu aprendizado (histórico, temperaturas, lições, gráficos, modelos) é enviado para esta avaliação.</p>
<h2>O que coletamos aqui</h2><ul>
<li><strong>Nivelamento:</strong> as respostas da prova, sem nome nem e-mail. O endereço IP é usado só para limitar abusos e não é guardado com a prova.</li>
<li><strong>Avaliação final e certificado:</strong> nome, e-mail, o aceite desta política, as respostas e o resultado, o nome escrito no certificado e a data de emissão.</li>
<li><strong>Comunicações:</strong> só se você marcar a opção opcional de receber novidades.</li></ul>
<h2>Para quê</h2><p>Aplicar a prova, corrigi-la, emitir o certificado e permitir a verificação pública por 12 meses. A verificação mostra nome, nota geral, datas e emissor, nunca o seu e-mail.</p>
<h2>Base legal</h2><p>Execução do serviço que você solicitou (a avaliação e o certificado) e o seu consentimento, que pode ser retirado a qualquer momento.</p>
<h2>Quanto tempo guardamos</h2><p>Enquanto o cadastro existir. Você pode excluir tudo na página <a href="/conta">Minha conta</a>; ao excluir, os certificados deixam de ser verificáveis. Sessões e tokens de acesso expiram sozinhos.</p>
<h2>Com quem compartilhamos</h2><p>Os dados ficam na infraestrutura da Cloudflare (operadora) e o e-mail de acesso é enviado por um provedor de e-mail contratado. Não vendemos dados.</p>
<h2>Seus direitos</h2><p>Acesso, correção, exclusão, portabilidade e informação sobre o tratamento, pelo contato acima.</p>`);
}
