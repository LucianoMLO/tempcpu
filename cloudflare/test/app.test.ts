import assert from "node:assert/strict";
import { test } from "node:test";
import { Cliente, criarAmbiente, emails, ORIGEM } from "./ajuda.ts";
import type { ItemProva } from "../src/avaliacao.ts";

function novo(extra = {}) {
  const x = criarAmbiente(extra);
  return { ...x, c: new Cliente(x.app, x.env) };
}

/** Respostas certas lidas direto do banco (o aluno nunca as vê), errando nos ids pedidos. */
function respostas(banco: ReturnType<typeof criarAmbiente>["banco"], provaId: string, errar: string[] = []): Record<string, number> {
  const linha = banco.prepare("SELECT itens_json FROM prova WHERE id = ?").get(provaId) as { itens_json: string };
  const itens = JSON.parse(linha.itens_json) as ItemProva[];
  return Object.fromEntries(itens.map((i) => [i.id, errar.includes(i.id) ? (i.correta + 1) % i.opcoes.length : i.correta]));
}

async function aprovar(x: ReturnType<typeof novo>): Promise<string> {
  const p = await x.c.abrirProva("final");
  const r = await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: respostas(x.banco, p.id) });
  assert.equal(r.status, 200);
  return p.id;
}

test("páginas públicas respondem e trazem cabeçalhos de segurança", async () => {
  const { c } = novo();
  for (const caminho of ["/", "/privacidade", "/cadastro", "/entrar", "/verificar", "/estilo.css", "/formulario.js", "/prova.js", "/api/saude"]) {
    const r = await c.pedir(caminho);
    assert.equal(r.status, 200, caminho);
  }
  const r = await c.pedir("/");
  assert.match(r.headers.get("Content-Security-Policy")!, /default-src 'self'/);
  assert.equal(r.headers.get("X-Content-Type-Options"), "nosniff");
  assert.equal(r.headers.get("X-Frame-Options"), "DENY");
  assert.equal((await c.pedir("/nao-existe")).status, 404);
});

test("POST de outra origem ou sem origem é recusado", async () => {
  const { c } = novo();
  assert.equal((await c.pedir("/api/entrar", { corpo: { email: "a@b.co" }, origem: "https://mal.test" })).status, 403);
  assert.equal((await c.pedir("/api/entrar", { corpo: { email: "a@b.co" }, origem: null })).status, 403);
  assert.equal(emails().length, 0);
});

test("cadastro exige consentimento, dados válidos, e o link só vale uma vez", async () => {
  const { c } = novo();
  assert.equal((await c.json("/api/cadastro", { nome: "Maria Exemplo", email: "maria@exemplo.com", consentimento: false })).status, 400);
  assert.equal((await c.json("/api/cadastro", { nome: "x", email: "maria@exemplo.com", consentimento: true })).status, 400);
  assert.equal((await c.json("/api/cadastro", { nome: "Maria Exemplo", email: "invalido", consentimento: true })).status, 400);
  assert.equal(emails().length, 0);
  assert.equal((await c.json("/api/cadastro", { nome: "Maria Exemplo", email: "Maria@Exemplo.com", consentimento: true, marketing: true })).status, 200);
  assert.equal(emails().length, 1);
  assert.equal(emails()[0]!.para, "maria@exemplo.com");
  const link = /https?:\/\/\S+/.exec(emails()[0]!.texto)![0];
  assert.match(link, /\/confirmar\?t=/);
  const token = new URL(link).searchParams.get("t")!;
  const pagina = await c.pedir(`/confirmar?t=${token}`);
  assert.match(await pagina.text(), /data-api="\/api\/confirmar"/);       // abrir o link não consome o token (anti-prefetch)
  assert.equal((await c.pedir("/painel")).status, 302);                    // ainda sem sessão
  const ok = await c.json("/api/confirmar", { t: token });
  assert.equal(ok.status, 200);
  assert.equal((await c.pedir("/painel")).status, 200);
  const outro = new Cliente(c.app, c.env);
  assert.equal((await outro.json("/api/confirmar", { t: token })).status, 400);   // reutilizar falha
  assert.equal((await outro.json("/api/confirmar", { t: "x".repeat(30) })).status, 400);
});

test("token expirado não entra", async () => {
  const { c, banco } = novo();
  await c.json("/api/cadastro", { nome: "Maria Exemplo", email: "m@exemplo.com", consentimento: true });
  const token = new URL(/https?:\/\/\S+/.exec(emails()[0]!.texto)![0]).searchParams.get("t")!;
  banco.exec("UPDATE token_email SET expira_em = 1");
  assert.equal((await c.json("/api/confirmar", { t: token })).status, 400);
});

test("entrar não revela se o e-mail existe", async () => {
  const { c } = novo();
  const a = await c.json("/api/entrar", { email: "ninguem@exemplo.com" });
  assert.equal(a.status, 200);
  assert.equal(emails().length, 0);
  await new Cliente(c.app, c.env, "203.0.113.9").entrarComo("Maria Exemplo", "maria@exemplo.com");
  const b = await c.json("/api/entrar", { email: "maria@exemplo.com" });
  assert.equal(b.status, 200);
  assert.equal(a.j.mensagem !== undefined && b.j.mensagem !== undefined, true);
  assert.equal(emails().length, 2);
});

test("a final exige login; a prova que o aluno recebe não traz respostas nem explicações", async () => {
  const { c, banco } = novo();
  const r = await c.pedir("/prova/final");
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), "/entrar");
  await c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const p = await c.abrirProva("final");
  assert.equal(p.ids.length, 20);
  assert.ok(!p.html.includes("SEGREDO-EXPLICACAO"));
  assert.match(p.html, /<abbr class="termo"[^>]*title="Uma fórmula aprendida\.">modelo<\/abbr>/);
  const again = await c.pedir("/prova/final");                              // a prova aberta é reaproveitada
  assert.equal(again.headers.get("Location"), `/p/${p.id}`);
  assert.equal(banco.prepare("SELECT COUNT(*) AS n FROM prova WHERE tipo='final'").get()!.n, 1);
});

test("entrega aprovada, resultado e reenvio que não altera a nota", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const id = await aprovar(x);
  const res = await (await x.c.pedir(`/resultado/${id}`)).text();
  assert.match(res, /100%/);
  assert.match(res, /Emitir certificado/);
  const dnv = await x.c.json(`/api/prova/${id}/entregar`, { respostas: {} });
  assert.equal(dnv.status, 409);
  assert.match(await (await x.c.pedir(`/resultado/${id}`)).text(), /100%/);
  assert.equal((await x.c.pedir(`/p/${id}`)).headers.get("Location"), `/resultado/${id}`);
});

test("respostas inválidas são recusadas e a prova continua aberta", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const p = await x.c.abrirProva("final");
  for (const ruim of [{ [p.ids[0]!]: 99 }, { "X-99": 0 }, { [p.ids[0]!]: "1" }]) assert.equal((await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: ruim })).status, 400);
  assert.equal((await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: [1] })).status, 400);
  assert.equal((await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: {} })).status, 200); // tudo em branco é válido e reprova
});

test("reprovada mostra o que revisar e a nova tentativa traz questões diferentes", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const p1 = await x.c.abrirProva("final");
  const erros = p1.ids.slice(0, 6);
  await x.c.json(`/api/prova/${p1.id}/entregar`, { respostas: respostas(x.banco, p1.id, erros) });
  const res = await (await x.c.pedir(`/resultado/${p1.id}`)).text();
  assert.match(res, /Ainda não foi desta vez/);
  assert.match(res, /SEGREDO-EXPLICACAO/);                                     // a explicação só aparece depois da entrega
  assert.ok(!res.includes("Emitir certificado"));
  const p2 = await x.c.abrirProva("final");
  assert.notEqual(p2.id, p1.id);
  assert.equal(p2.ids.filter((i) => p1.ids.includes(i)).length, 0);
});

test("intervalo mínimo e limite diário entre tentativas da final", async () => {
  const x = novo({ INTERVALO_MIN_FINAL_S: "600" });
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const p = await x.c.abrirProva("final");
  await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: {} });
  assert.equal((await x.c.pedir("/prova/final")).status, 429);
  const y = novo({ MAX_FINAIS_POR_DIA: "2" });
  await y.c.entrarComo("João Exemplo", "joao@exemplo.com");
  for (let i = 0; i < 2; i++) {
    const q = await y.c.abrirProva("final");
    await y.c.json(`/api/prova/${q.id}/entregar`, { respostas: {} });
  }
  assert.equal((await y.c.pedir("/prova/final")).status, 429);
});

test("prova expirada não é entregue", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const p = await x.c.abrirProva("final");
  x.banco.exec("UPDATE prova SET expira_em = 1");
  assert.equal((await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: {} })).status, 410);
  assert.equal((await x.c.pedir(`/p/${p.id}`)).status, 410);
});

test("nivelamento funciona sem cadastro, não guarda dado pessoal e recomenda a lição", async () => {
  const x = novo();
  const p = await x.c.abrirProva("nivelamento");
  assert.equal(p.ids.length, 10);
  const linha = x.banco.prepare("SELECT aluno_id FROM prova WHERE id = ?").get(p.id) as { aluno_id: string | null };
  assert.equal(linha.aluno_id, null);
  const r = await x.c.json(`/api/prova/${p.id}/entregar`, { respostas: respostas(x.banco, p.id) });
  assert.equal(r.status, 200);
  const res = await (await x.c.pedir(`/resultado/${p.id}`)).text();
  assert.match(res, /domina o básico/);
  assert.equal(x.banco.prepare("SELECT COUNT(*) AS n FROM aluno").get()!.n, 0);
});

test("a prova de um aluno não é vista por outro", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const id = await aprovar(x);
  const outro = new Cliente(x.app, x.env, "203.0.113.50");
  await outro.entrarComo("João Exemplo", "joao@exemplo.com");
  assert.equal((await outro.pedir(`/resultado/${id}`)).headers.get("Location"), "/entrar");
  assert.equal((await outro.json(`/api/prova/${id}/entregar`, { respostas: {} })).status, 401);
  const anonimo = new Cliente(x.app, x.env, "203.0.113.51");
  assert.equal((await anonimo.pedir(`/p/${id}`)).headers.get("Location"), "/entrar");
});

test("certificado: só para aprovado, nome validado, verificação pública sem e-mail", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const reprovada = await x.c.abrirProva("final");
  await x.c.json(`/api/prova/${reprovada.id}/entregar`, { respostas: {} });
  assert.equal((await x.c.pedir(`/certificado/emitir/${reprovada.id}`)).status, 403);
  assert.equal((await x.c.json("/api/certificado", { provaId: reprovada.id, nome: "Maria Exemplo" })).status, 403);

  const id = await aprovar(x);
  assert.equal((await x.c.pedir(`/certificado/emitir/${id}`)).status, 200);
  assert.equal((await x.c.json("/api/certificado", { provaId: id, nome: "ab" })).status, 400);
  const emitido = await x.c.json("/api/certificado", { provaId: id, nome: "  Maria   da Silva Exemplo " });
  assert.equal(emitido.status, 200);
  const codigo = String(emitido.j.redirect).split("/").pop()!;
  assert.match(codigo, /^[0-9A-F]{12}$/);
  const igual = await x.c.json("/api/certificado", { provaId: id, nome: "Outro Nome" });   // reemitir devolve o mesmo
  assert.equal(String(igual.j.redirect).split("/").pop(), codigo);

  const cert = await (await x.c.pedir(`/certificado/${codigo}`)).text();
  assert.match(cert, /Maria da Silva Exemplo/);
  assert.match(cert, /sem acreditação/);
  assert.match(cert, /Mais Valor Consultoria e Serviços/);

  const publico = new Cliente(x.app, x.env, "203.0.113.77");
  const v = await publico.pedir(`/verificar/${codigo.toLowerCase()}`);
  assert.equal(v.status, 200);
  const vt = await v.text();
  assert.match(vt, /Certificado válido/);
  assert.match(vt, /Maria da Silva Exemplo/);
  assert.ok(!vt.includes("maria@exemplo.com"));
  assert.equal((await publico.pedir(`/certificado/${codigo}`)).headers.get("Location"), "/entrar");   // o documento é só do dono

  const nao = await publico.pedir("/verificar/AAAAAAAAAAAA");
  assert.equal(nao.status, 404);
  assert.match(await nao.text(), /não encontrado/);
  assert.equal((await publico.pedir("/verificar/ABC")).status, 404);
  const ver = await publico.json("/api/verificar", { codigo: codigo.toLowerCase() });
  assert.equal(ver.j.redirect, `/verificar/${codigo}`);
  assert.equal((await publico.json("/api/verificar", { codigo: "curto" })).status, 400);

  x.banco.exec("UPDATE certificado SET valido_ate = 1");
  assert.match(await (await publico.pedir(`/verificar/${codigo}`)).text(), /Verificação expirada/);
  x.banco.exec("UPDATE certificado SET valido_ate = 9999999999, revogado_em = 5");
  assert.match(await (await publico.pedir(`/verificar/${codigo}`)).text(), /Certificado revogado/);
});

test("o certificado de uma pessoa não aparece para outra", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const id = await aprovar(x);
  const e = await x.c.json("/api/certificado", { provaId: id, nome: "Maria Exemplo" });
  const codigo = String(e.j.redirect).split("/").pop()!;
  const outro = new Cliente(x.app, x.env, "203.0.113.60");
  await outro.entrarComo("João Exemplo", "joao@exemplo.com");
  assert.equal((await outro.pedir(`/certificado/${codigo}`)).status, 404);
  assert.equal((await outro.json("/api/certificado", { provaId: id, nome: "João" })).status, 404);
});

test("nome com HTML é escapado no certificado", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const id = await aprovar(x);
  const e = await x.c.json("/api/certificado", { provaId: id, nome: `<script>alert(1)</script> Maria` });
  const codigo = String(e.j.redirect).split("/").pop()!;
  const pagina = await (await x.c.pedir(`/certificado/${codigo}`)).text();
  assert.ok(!pagina.includes("<script>alert(1)"));
  assert.match(pagina, /&lt;script&gt;alert\(1\)&lt;\/script&gt; Maria/);
  assert.ok(!(await (await x.c.pedir(`/verificar/${codigo}`)).text()).includes("<script>alert"));
});

test("excluir a conta apaga tudo e o certificado deixa de ser verificável", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const id = await aprovar(x);
  const e = await x.c.json("/api/certificado", { provaId: id, nome: "Maria Exemplo" });
  const codigo = String(e.j.redirect).split("/").pop()!;
  assert.equal((await x.c.json("/api/conta/excluir", { confirmar: "excluir" })).status, 400);
  assert.equal((await x.c.json("/api/conta/excluir", { confirmar: "EXCLUIR" })).status, 200);
  for (const tabela of ["aluno", "prova", "certificado", "sessao", "token_email"]) assert.equal(x.banco.prepare(`SELECT COUNT(*) AS n FROM ${tabela}`).get()!.n, 0, tabela);
  assert.equal((await new Cliente(x.app, x.env).pedir(`/verificar/${codigo}`)).status, 404);
  assert.equal((await x.c.pedir("/painel")).status, 302);
});

test("sair encerra a sessão", async () => {
  const x = novo();
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  assert.equal((await x.c.pedir("/painel")).status, 200);
  const sessao = x.c.cookies.get("sessao")!;
  await x.c.pedir("/api/sair", { metodo: "POST", corpo: {} });
  const velho = new Cliente(x.app, x.env);
  velho.cookies.set("sessao", sessao);
  assert.equal((await velho.pedir("/painel")).status, 302);
});

test("limite de cadastros por IP", async () => {
  const x = novo();
  let ultimo = 0;
  for (let i = 0; i < 11; i++) ultimo = (await x.c.json("/api/cadastro", { nome: "Pessoa Teste", email: `p${i}@exemplo.com`, consentimento: true })).status;
  assert.equal(ultimo, 429);
});

test("em produção sem Turnstile configurado o cadastro falha fechado", async () => {
  const x = novo({ AMBIENTE: undefined });
  const r = await x.c.json("/api/cadastro", { nome: "Maria Exemplo", email: "m@exemplo.com", consentimento: true });
  assert.equal(r.status, 400);
  assert.equal(emails().length, 0);
});

test("o cookie de sessão é HttpOnly, SameSite e Secure em https", async () => {
  const x = novo();
  await x.c.json("/api/cadastro", { nome: "Maria Exemplo", email: "m@exemplo.com", consentimento: true });
  const token = new URL(/https?:\/\/\S+/.exec(emails()[0]!.texto)![0]).searchParams.get("t")!;
  const r = await x.c.pedir("/api/confirmar", { corpo: { t: token } });
  const sc = r.headers.get("Set-Cookie")!;
  assert.match(sc, /HttpOnly/);
  assert.match(sc, /SameSite=Lax/);
  assert.match(sc, /Secure/);
  assert.ok(sc.startsWith("sessao="));
  assert.ok(!sc.includes(token));
});

test("sem o segredo de assinatura, em produção, o certificado não é emitido", async () => {
  const x = novo({ AMBIENTE: "dev" });
  await x.c.entrarComo("Maria Exemplo", "maria@exemplo.com");
  const id = await aprovar(x);
  x.env.AMBIENTE = "producao";
  assert.equal((await x.c.json("/api/certificado", { provaId: id, nome: "Maria Exemplo" })).status, 500);
  void ORIGEM;
});

test("o link aparece na tela só em ambiente de teste e só para e-mails da lista de teste", async () => {
  const x = novo({ TESTE_EMAILS: "teste@exemplo.com, Outro@Exemplo.com" });
  const a = await x.c.json("/api/cadastro", { nome: "Pessoa Teste", email: "teste@exemplo.com", consentimento: true });
  assert.match(String(a.j.linkTeste), /\/confirmar\?t=/);
  const b = await x.c.json("/api/cadastro", { nome: "Outra Pessoa", email: "fora@exemplo.com", consentimento: true });
  assert.equal(b.j.linkTeste, undefined);
  const c2 = await x.c.json("/api/entrar", { email: "teste@exemplo.com" });
  assert.match(String(c2.j.linkTeste), /\/confirmar\?t=/);
  assert.equal((await x.c.json("/api/entrar", { email: "ninguem@exemplo.com" })).j.linkTeste, undefined); // não revela cadastro
  const prod = novo({ AMBIENTE: "producao", TESTE_EMAILS: "teste@exemplo.com", TURNSTILE_SECRET: "x" });
  assert.equal((await prod.c.json("/api/entrar", { email: "teste@exemplo.com" })).j.linkTeste, undefined);   // em produção nunca
});

test("as páginas ligam à página do projeto", async () => {
  const { c } = novo();
  assert.match(await (await c.pedir("/")).text(), /href="https:\/\/lucianomlo\.github\.io\/tempcpu\/">Página do projeto</);
});
