// Roteamento e regras de cada página/API. A dependência do banco de questões e do glossário é injetada (testável).
import {
  corrigir, ErroDeEntrada, notaPct, publica, sortearFinal, sortearNivelamento, validarEmail, validarNome,
  type Banco, type ItemProva, type Prova, type Resultado,
} from "./avaliacao.ts";
import { ESTILO, FORMULARIO_JS, PROVA_JS } from "./assets.ts";
import * as db from "./db.ts";
import { enviarEmail, verificarTurnstile } from "./externos.ts";
import * as pg from "./paginas.ts";
import { agora, aleatorio, cookie, hmacHex, lerCookie, mesmaOrigem, semente32, sha256Hex } from "./seguranca.ts";
import type { Aluno, Env, Glossario, LinhaProva } from "./tipos.ts";

const SESSAO_S = 30 * 86400;
const TOKEN_S = 20 * 60;
const PROVA_S = 3 * 3600;
const MAX_CORPO = 64 * 1024;
const CODIGO = /^[A-Z0-9]{12}$/;
const ID_PROVA = /^[A-Za-z0-9_-]{16,64}$/;

const CSP = [
  "default-src 'self'", "script-src 'self' https://challenges.cloudflare.com", "frame-src https://challenges.cloudflare.com",
  "style-src 'self'", "style-src-attr 'unsafe-inline'", "img-src 'self' data:", "connect-src 'self'", "base-uri 'none'",
  "form-action 'self'", "frame-ancestors 'none'",
].join("; ");

export interface Deps {
  banco: Banco;
  glossario: Glossario;
}

class Resposta extends Error {
  status: number;
  corpo: string;
  tipo: "json" | "html";
  extra: Record<string, string>;
  constructor(status: number, corpo: string, tipo: "json" | "html" = "json", extra: Record<string, string> = {}) {
    super(corpo);
    this.status = status;
    this.corpo = corpo;
    this.tipo = tipo;
    this.extra = extra;
  }
}

const erroJson = (status: number, erro: string) => new Resposta(status, JSON.stringify({ ok: false, erro }));

function seguro(r: Response): Response {
  const h = new Headers(r.headers);
  h.set("Content-Security-Policy", CSP);
  h.set("X-Content-Type-Options", "nosniff");
  h.set("Referrer-Policy", "same-origin");
  h.set("X-Frame-Options", "DENY");
  return new Response(r.body, { status: r.status, headers: h });
}

const html = (corpo: string, status = 200, extra: Record<string, string> = {}) =>
  new Response(corpo, { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", ...extra } });
const json = (obj: unknown, status = 200, extra: Record<string, string> = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...extra } });
const redireciona = (para: string, extra: Record<string, string> = {}) => new Response(null, { status: 302, headers: { Location: para, "Cache-Control": "no-store", ...extra } });
const estatico = (corpo: string, tipo: string) => new Response(corpo, { status: 200, headers: { "Content-Type": `${tipo}; charset=utf-8`, "Cache-Control": "public, max-age=300" } });

export function criarApp(deps: Deps) {
  const banco = (env: Env): Banco => env.BANCO_TESTE ?? deps.banco;

  async function alunoAtual(req: Request, env: Env): Promise<Aluno | null> {
    const t = lerCookie(req, "sessao");
    if (!t) return null;
    return db.alunoDaSessao(env.DB, await sha256Hex(t), agora());
  }

  async function corpoJson(req: Request): Promise<Record<string, unknown>> {
    const texto = await req.text();
    if (texto.length > MAX_CORPO) throw erroJson(413, "Pedido grande demais.");
    try {
      const v = JSON.parse(texto || "{}");
      if (v === null || typeof v !== "object" || Array.isArray(v)) throw new Error();
      return v as Record<string, unknown>;
    } catch {
      throw erroJson(400, "Pedido inválido.");
    }
  }

  function origem(req: Request, env: Env): string {
    return env.ORIGEM_PUBLICA || new URL(req.url).origin;
  }

  const ip = (req: Request) => req.headers.get("CF-Connecting-IP") ?? "local";

  /** Devolve o link só quando o ambiente é de teste E o e-mail está na lista de teste (nunca em produção). */
  async function enviarLink(req: Request, env: Env, aluno: Aluno): Promise<string | null> {
    const token = aleatorio(32);
    await db.criarToken(env.DB, await sha256Hex(token), aluno.id, agora() + TOKEN_S);
    const link = `${origem(req, env)}/confirmar?t=${token}`;
    await enviarEmail(env, {
      para: aluno.email,
      assunto: "Seu acesso à avaliação do Laboratório TempCPU",
      texto: `Olá, ${aluno.nome}.\n\nPara entrar, abra o link abaixo (vale por 20 minutos e só pode ser usado uma vez):\n\n${link}\n\nSe você não pediu este acesso, ignore esta mensagem.\n`,
    });
    const teste = (env.TESTE_EMAILS ?? "").toLowerCase().split(",").map((x) => x.trim()).filter(Boolean);
    return env.AMBIENTE === "dev" && teste.includes(aluno.email) ? link : null;
  }

  function carregarProva(l: LinhaProva): Prova {
    return { tipo: l.tipo, semente: l.semente, itens: JSON.parse(l.itens_json) as ItemProva[], versaoBanco: l.versao_banco };
  }

  /** A prova de um aluno só é vista pelo dono; a anônima (nivelamento) é acessada pelo id, que é secreto. */
  async function provaVisivel(req: Request, env: Env, id: string): Promise<{ linha: LinhaProva; aluno: Aluno | null }> {
    if (!ID_PROVA.test(id)) throw new Resposta(404, "", "html");
    const linha = await db.provaPorId(env.DB, id);
    if (!linha) throw new Resposta(404, "", "html");
    const aluno = await alunoAtual(req, env);
    if (linha.aluno_id && aluno?.id !== linha.aluno_id) throw new Resposta(302, "/entrar", "html");
    return { linha, aluno };
  }

  async function limiteOuErro(env: Env, chave: string, max: number, janela: number): Promise<void> {
    if (!(await db.limitar(env.DB, chave, max, janela, agora()))) throw erroJson(429, "Muitas tentativas. Aguarde um pouco e tente de novo.");
  }

  async function tratar(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const caminho = url.pathname.replace(/\/+$/, "") || "/";
    const m = req.method;
    const ctxBase = { env };

    if (m === "GET" && caminho === "/estilo.css") return estatico(ESTILO, "text/css");
    if (m === "GET" && caminho === "/formulario.js") return estatico(FORMULARIO_JS, "application/javascript");
    if (m === "GET" && caminho === "/prova.js") return estatico(PROVA_JS, "application/javascript");
    if (m === "GET" && caminho === "/api/saude") return json({ ok: true });

    if (m === "POST") {
      if (!mesmaOrigem(req, env.ORIGEM_PUBLICA)) throw erroJson(403, "Pedido de origem não permitida.");
    } else if (m !== "GET" && m !== "HEAD") {
      return json({ ok: false, erro: "Método não permitido." }, 405);
    }

    const aluno = await alunoAtual(req, env);
    const ctx = { ...ctxBase, aluno };
    const b = banco(env);
    const https = url.protocol === "https:";

    // ---------------- páginas públicas
    if (m === "GET" && caminho === "/") return html(pg.inicio(ctx));
    if (m === "GET" && caminho === "/privacidade") return html(pg.paginaPrivacidade(ctx));
    if (m === "GET" && caminho === "/cadastro") return html(pg.paginaCadastro(ctx));
    if (m === "GET" && caminho === "/entrar") return html(pg.paginaEntrar(ctx));
    if (m === "GET" && caminho === "/confirmar") {
      const t = url.searchParams.get("t") ?? "";
      return html(t.length >= 20 && t.length <= 100 ? pg.paginaConfirmar(ctx, t) : pg.aviso(ctx, "Link inválido", "Peça um novo link de acesso.", { href: "/entrar", texto: "Entrar" }), t ? 200 : 400);
    }

    // ---------------- cadastro e acesso
    if (m === "POST" && caminho === "/api/cadastro") {
      const c = await corpoJson(req);
      await limiteOuErro(env, `cadastro:${ip(req)}`, 10, 3600);
      if (!(await verificarTurnstile(env, c["cf-turnstile-response"], ip(req)))) throw erroJson(400, "Não foi possível verificar que você é uma pessoa. Recarregue a página.");
      let nome: string, email: string;
      try {
        nome = validarNome(c.nome);
        email = validarEmail(c.email);
      } catch (x) {
        throw erroJson(400, (x as Error).message);
      }
      if (c.consentimento !== true) throw erroJson(400, "É preciso aceitar a política de privacidade para criar o cadastro.");
      await limiteOuErro(env, `link:${email}`, 5, 3600);
      let existente = await db.alunoPorEmail(env.DB, email);
      if (!existente) {
        const id = aleatorio(16);
        await db.criarAluno(env.DB, { id, nome, email, marketing: c.marketing === true, agora: agora() });
        existente = await db.alunoPorId(env.DB, id);
      }
      const linkTeste = existente ? await enviarLink(req, env, existente) : null;
      return json({ ok: true, mensagem: "Se o e-mail estiver correto, enviamos um link de acesso. Abra-o em até 20 minutos.", ...(linkTeste ? { linkTeste } : {}) });
    }

    if (m === "POST" && caminho === "/api/entrar") {
      const c = await corpoJson(req);
      await limiteOuErro(env, `entrar:${ip(req)}`, 20, 3600);
      if (!(await verificarTurnstile(env, c["cf-turnstile-response"], ip(req)))) throw erroJson(400, "Não foi possível verificar que você é uma pessoa. Recarregue a página.");
      let email: string;
      try {
        email = validarEmail(c.email);
      } catch (x) {
        throw erroJson(400, (x as Error).message);
      }
      await limiteOuErro(env, `link:${email}`, 5, 3600);
      const existente = await db.alunoPorEmail(env.DB, email);
      const linkTeste = existente ? await enviarLink(req, env, existente) : null;
      return json({ ok: true, mensagem: "Se este e-mail tiver cadastro, enviamos um link de acesso. Abra-o em até 20 minutos.", ...(linkTeste ? { linkTeste } : {}) });
    }

    if (m === "POST" && caminho === "/api/confirmar") {
      const c = await corpoJson(req);
      await limiteOuErro(env, `confirmar:${ip(req)}`, 30, 3600);
      const t = typeof c.t === "string" ? c.t : "";
      const alunoId = t.length >= 20 && t.length <= 100 ? await db.consumirToken(env.DB, await sha256Hex(t), agora()) : null;
      if (!alunoId) throw erroJson(400, "Link inválido, expirado ou já usado. Peça um novo.");
      await db.confirmarEmail(env.DB, alunoId, agora());
      const sessao = aleatorio(32);
      await db.criarSessao(env.DB, await sha256Hex(sessao), alunoId, agora() + SESSAO_S);
      return json({ ok: true, redirect: "/painel" }, 200, { "Set-Cookie": cookie("sessao", sessao, { seguro: https, maxAge: SESSAO_S }) });
    }

    if (m === "POST" && caminho === "/api/sair") {
      const t = lerCookie(req, "sessao");
      if (t) await db.apagarSessao(env.DB, await sha256Hex(t));
      return json({ ok: true }, 200, { "Set-Cookie": cookie("sessao", "", { seguro: https, maxAge: 0 }) });
    }

    // ---------------- painel e conta
    if (m === "GET" && caminho === "/painel") {
      if (!aluno) return redireciona("/entrar");
      const linhas = await db.provasDoAluno(env.DB, aluno.id);
      const certs = await db.certificadosDoAluno(env.DB, aluno.id);
      const porProva = new Map(certs.map((c) => [c.prova_id, c]));
      const resumos = linhas.map((l) => ({ id: l.id, tipo: l.tipo, entregue_em: l.entregue_em ?? 0, resultado: JSON.parse(l.resultado_json ?? "{}") as Resultado, certificado: porProva.get(l.id) ?? null }));
      return html(pg.painel(ctx, resumos, certs, b, agora()));
    }
    if (m === "GET" && caminho === "/conta") return aluno ? html(pg.paginaConta(ctx)) : redireciona("/entrar");
    if (m === "POST" && caminho === "/api/conta/excluir") {
      if (!aluno) throw erroJson(401, "Entre para continuar.");
      const c = await corpoJson(req);
      if (c.confirmar !== "EXCLUIR") throw erroJson(400, "Digite EXCLUIR para confirmar.");
      await db.excluirAluno(env.DB, aluno.id);
      return json({ ok: true, redirect: "/" }, 200, { "Set-Cookie": cookie("sessao", "", { seguro: https, maxAge: 0 }) });
    }

    // ---------------- provas
    if (m === "GET" && caminho === "/prova/nivelamento") {
      await limiteOuErro(env, `niv:${ip(req)}`, 30, 3600).catch(() => { throw new Resposta(429, pg.aviso(ctx, "Muitas tentativas", "Aguarde um pouco e tente de novo."), "html"); });
      const aberta = aluno ? await db.provaAbertaDoAluno(env.DB, aluno.id, "nivelamento", agora()) : null;
      if (aberta) return redireciona(`/p/${aberta.id}`);
      const prova = sortearNivelamento(semente32(), b);
      const id = aleatorio(16);
      await db.criarProva(env.DB, { id, aluno_id: aluno?.id ?? null, tipo: "nivelamento", semente: prova.semente, versao_banco: prova.versaoBanco, itens_json: JSON.stringify(prova.itens), criada_em: agora(), expira_em: agora() + PROVA_S });
      return redireciona(`/p/${id}`);
    }

    if (m === "GET" && caminho === "/prova/final") {
      if (!aluno) return redireciona("/entrar");
      const aberta = await db.provaAbertaDoAluno(env.DB, aluno.id, "final", agora());
      if (aberta) return redireciona(`/p/${aberta.id}`);
      const intervalo = Number(env.INTERVALO_MIN_FINAL_S ?? 600);
      const ultima = (await db.provasDoAluno(env.DB, aluno.id)).find((p) => p.tipo === "final");
      if (ultima?.entregue_em && agora() - ultima.entregue_em < intervalo) {
        const espera = Math.ceil((intervalo - (agora() - ultima.entregue_em)) / 60);
        return html(pg.aviso(ctx, "Aguarde um pouco", `Para fixar o conteúdo, a próxima tentativa abre em cerca de ${espera} minuto(s). Aproveite para revisar as lições indicadas no resultado.`, { href: `/resultado/${ultima.id}`, texto: "Ver o resultado" }), 429);
      }
      const maxDia = Number(env.MAX_FINAIS_POR_DIA ?? 5);
      if (!(await db.limitar(env.DB, `final:${aluno.id}`, maxDia, 86400, agora()))) {
        return html(pg.aviso(ctx, "Limite diário", "Você já fez o máximo de tentativas de hoje. Volte amanhã.", { href: "/painel", texto: "Meu painel" }), 429);
      }
      if (!aluno.email_confirmado_em) return redireciona("/entrar");
      const prova = sortearFinal(semente32(), await db.idsDaUltimaFinal(env.DB, aluno.id), b);
      const id = aleatorio(16);
      await db.criarProva(env.DB, { id, aluno_id: aluno.id, tipo: "final", semente: prova.semente, versao_banco: prova.versaoBanco, itens_json: JSON.stringify(prova.itens), criada_em: agora(), expira_em: agora() + PROVA_S });
      return redireciona(`/p/${id}`);
    }

    const rotaProva = caminho.match(/^\/p\/([^/]+)$/);
    if (m === "GET" && rotaProva) {
      const { linha } = await provaVisivel(req, env, rotaProva[1]!);
      if (linha.entregue_em) return redireciona(`/resultado/${linha.id}`);
      if (linha.expira_em <= agora()) {
        return html(pg.aviso(ctx, "Prova expirada", "O tempo desta prova acabou. Comece uma nova.", { href: `/prova/${linha.tipo}`, texto: "Nova prova" }), 410);
      }
      return html(pg.paginaProva(ctx, linha.id, linha.tipo, publica(carregarProva(linha)).itens, deps.glossario, b));
    }

    const rotaEntrega = caminho.match(/^\/api\/prova\/([^/]+)\/entregar$/);
    if (m === "POST" && rotaEntrega) {
      const { linha } = await provaVisivel(req, env, rotaEntrega[1]!).catch((x) => {
        if (x instanceof Resposta && x.tipo === "html") throw erroJson(x.status === 404 ? 404 : 401, x.status === 404 ? "Prova não encontrada." : "Entre para continuar.");
        throw x;
      });
      if (linha.entregue_em) throw erroJson(409, "Esta prova já foi entregue; a nota não muda.");
      if (linha.expira_em <= agora()) throw erroJson(410, "O tempo desta prova acabou.");
      const c = await corpoJson(req);
      const respostas = c.respostas;
      if (respostas === null || typeof respostas !== "object" || Array.isArray(respostas)) throw erroJson(400, "Respostas inválidas.");
      let r: Resultado;
      try {
        r = corrigir(carregarProva(linha), respostas as Record<string, unknown>);
      } catch (x) {
        if (x instanceof ErroDeEntrada) throw erroJson(400, "Respostas inválidas.");
        throw x;
      }
      if (!(await db.entregarProva(env.DB, linha.id, JSON.stringify(respostas), JSON.stringify(r), agora()))) throw erroJson(409, "Esta prova já foi entregue; a nota não muda.");
      return json({ ok: true, redirect: `/resultado/${linha.id}` });
    }

    const rotaResultado = caminho.match(/^\/resultado\/([^/]+)$/);
    if (m === "GET" && rotaResultado) {
      const { linha, aluno: a } = await provaVisivel(req, env, rotaResultado[1]!);
      if (!linha.entregue_em || !linha.resultado_json) return redireciona(`/p/${linha.id}`);
      const cert = await db.certificadoDaProva(env.DB, linha.id);
      return html(pg.paginaResultado({ env, aluno: a }, linha.id, JSON.parse(linha.resultado_json) as Resultado, b, deps.glossario, cert, !!a && a.id === linha.aluno_id));
    }

    // ---------------- certificado
    const rotaEmitir = caminho.match(/^\/certificado\/emitir\/([^/]+)$/);
    if (m === "GET" && rotaEmitir) {
      if (!aluno) return redireciona("/entrar");
      const { linha } = await provaVisivel(req, env, rotaEmitir[1]!);
      const r = linha.resultado_json ? (JSON.parse(linha.resultado_json) as Resultado) : null;
      if (linha.tipo !== "final" || !r?.aprovado) return html(pg.aviso(ctx, "Certificado indisponível", "O certificado só é emitido para quem é aprovado(a) na avaliação final."), 403);
      const ja = await db.certificadoDaProva(env.DB, linha.id);
      if (ja) return redireciona(`/certificado/${ja.codigo}`);
      return html(pg.paginaEmitir(ctx, linha.id, aluno.nome));
    }

    if (m === "POST" && caminho === "/api/certificado") {
      if (!aluno) throw erroJson(401, "Entre para continuar.");
      const c = await corpoJson(req);
      const provaId = typeof c.provaId === "string" ? c.provaId : "";
      const linha = ID_PROVA.test(provaId) ? await db.provaPorId(env.DB, provaId) : null;
      if (!linha || linha.aluno_id !== aluno.id) throw erroJson(404, "Prova não encontrada.");
      const r = linha.resultado_json ? (JSON.parse(linha.resultado_json) as Resultado) : null;
      if (linha.tipo !== "final" || !r?.aprovado) throw erroJson(403, "O certificado só é emitido para quem é aprovado(a) na avaliação final.");
      const existente = await db.certificadoDaProva(env.DB, linha.id);
      if (existente) return json({ ok: true, redirect: `/certificado/${existente.codigo}` });
      let nome: string;
      try {
        nome = validarNome(c.nome);
      } catch (x) {
        throw erroJson(400, (x as Error).message);
      }
      const segredo = env.SEGREDO_ASSINATURA || (env.AMBIENTE === "dev" ? "segredo-de-desenvolvimento" : "");
      if (!segredo) throw erroJson(500, "Serviço de certificados não configurado.");
      const emitido = agora();
      const d = new Date(emitido * 1000);
      d.setUTCMonth(d.getUTCMonth() + 12);
      const nota = notaPct(r);
      const codigo = (await hmacHex(segredo, `${linha.id}|${nome}|${emitido}|${nota.toFixed(1)}|${linha.versao_banco}`)).slice(0, 12).toUpperCase();
      const ok = await db.criarCertificado(env.DB, { codigo, aluno_id: aluno.id, prova_id: linha.id, nome, nota_pct: nota, por_tema_json: JSON.stringify(r.porTema), versao_banco: linha.versao_banco, emitido_em: emitido, valido_ate: Math.floor(d.getTime() / 1000), revogado_em: null });
      if (!ok) {
        const ja = await db.certificadoDaProva(env.DB, linha.id);
        if (!ja) throw erroJson(500, "Não foi possível emitir o certificado. Tente de novo.");
        return json({ ok: true, redirect: `/certificado/${ja.codigo}` });
      }
      return json({ ok: true, redirect: `/certificado/${codigo}` });
    }

    const rotaVer = caminho.match(/^\/certificado\/([^/]+)$/);
    if (m === "GET" && rotaVer && rotaVer[1] !== "emitir") {
      if (!aluno) return redireciona("/entrar");
      const codigo = rotaVer[1]!.toUpperCase();
      const c = CODIGO.test(codigo) ? await db.certificadoPorCodigo(env.DB, codigo) : null;
      if (!c || c.aluno_id !== aluno.id) return html(pg.aviso(ctx, "Certificado não encontrado", "Este certificado não existe ou não é seu."), 404);
      return html(pg.paginaCertificado({ env: { ...env, ORIGEM_PUBLICA: origem(req, env) }, aluno }, c, b, agora()));
    }

    // ---------------- verificação pública
    if (m === "GET" && caminho === "/verificar") return html(pg.paginaVerificar(ctx, "formulario"));
    if (m === "POST" && caminho === "/api/verificar") {
      const c = await corpoJson(req);
      const codigo = typeof c.codigo === "string" ? c.codigo.trim().toUpperCase() : "";
      if (!CODIGO.test(codigo)) throw erroJson(400, "O código tem 12 letras e números.");
      return json({ ok: true, redirect: `/verificar/${codigo}` });
    }
    const rotaVerificar = caminho.match(/^\/verificar\/([^/]+)$/);
    if (m === "GET" && rotaVerificar) {
      await limiteOuErro(env, `verificar:${ip(req)}`, 120, 3600).catch(() => { throw new Resposta(429, pg.aviso(ctx, "Muitas consultas", "Aguarde um pouco e tente de novo."), "html"); });
      const codigo = rotaVerificar[1]!.toUpperCase();
      const c = CODIGO.test(codigo) ? await db.certificadoPorCodigo(env.DB, codigo) : null;
      if (!c) return html(pg.paginaVerificar(ctx, "nao_encontrado"), 404);
      if (c.revogado_em) return html(pg.paginaVerificar(ctx, "revogado", c));
      return html(pg.paginaVerificar(ctx, c.valido_ate <= agora() ? "expirado" : "valido", c));
    }

    return html(pg.aviso(ctx, "Página não encontrada", "O endereço não existe.", { href: "/", texto: "Início" }), 404);
  }

  return {
    async fetch(req: Request, env: Env): Promise<Response> {
      try {
        return seguro(await tratar(req, env));
      } catch (x) {
        if (x instanceof Resposta) {
          if (x.status === 302) return seguro(redireciona(x.corpo));
          const tipo = x.tipo === "json" ? "application/json; charset=utf-8" : "text/html; charset=utf-8";
          return seguro(new Response(x.corpo || (x.tipo === "html" ? pg.aviso({ env, aluno: null }, "Não encontrado", "Esta página não existe.") : ""), { status: x.status, headers: { "Content-Type": tipo, "Cache-Control": "no-store", ...x.extra } }));
        }
        console.error("erro não tratado", x instanceof Error ? x.message : x);
        return seguro(json({ ok: false, erro: "Erro interno. Tente de novo em instantes." }, 500));
      }
    },
  };
}
