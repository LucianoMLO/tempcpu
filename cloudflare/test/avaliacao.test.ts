import assert from "node:assert/strict";
import { test } from "node:test";
import * as A from "../src/avaliacao.ts";
import { bancoFalso } from "./ajuda.ts";

const TEMAS = ["T1", "T2", "T3", "T4", "T5"];
const BANCO = bancoFalso();

function certo(prova: A.Prova, errar: string[] = []): Record<string, number> {
  return Object.fromEntries(prova.itens.map((i) => [i.id, errar.includes(i.id) ? (i.correta + 1) % i.opcoes.length : i.correta]));
}
const errosEm = (prova: A.Prova, porTema: Record<string, number>): string[] =>
  Object.entries(porTema).flatMap(([t, n]) => prova.itens.filter((i) => i.tema === t).slice(0, n).map((i) => i.id));

test("a final tem 4 por tema, é reprodutível pela semente e muda com outra", () => {
  const p = A.sortearFinal(123, [], BANCO);
  assert.equal(p.itens.length, 20);
  for (const t of TEMAS) assert.equal(p.itens.filter((i) => i.tema === t).length, 4);
  assert.equal(new Set(p.itens.map((i) => i.id)).size, 20);
  assert.deepEqual(p, A.sortearFinal(123, [], BANCO));
  assert.notDeepEqual(p.itens.map((i) => i.id), A.sortearFinal(124, [], BANCO).itens.map((i) => i.id));
});

test("nivelamento usa só questões de nivelamento e a final só as da final", () => {
  const niv = new Set(BANCO.questoes.filter((q) => q.uso === "nivelamento").map((q) => q.id));
  const fin = A.sortearFinal(1, [], BANCO);
  const n = A.sortearNivelamento(1, BANCO);
  assert.equal(n.itens.length, 10);
  assert.ok(n.itens.every((i) => niv.has(i.id)));
  assert.ok(fin.itens.every((i) => !niv.has(i.id)));
});

test("não repete a tentativa anterior quando há outras; completa com repetidas quando falta", () => {
  const ids = A.sortearFinal(1, [], BANCO).itens.map((i) => i.id);
  for (let s = 2; s < 12; s++) assert.equal(A.sortearFinal(s, ids, BANCO).itens.filter((i) => ids.includes(i.id)).length, 0);
  const pequeno = bancoFalso(7); // 5 finais por tema
  const p1 = A.sortearFinal(1, [], pequeno).itens.map((i) => i.id);
  const p2 = A.sortearFinal(2, p1, pequeno);
  assert.equal(p2.itens.filter((i) => p1.includes(i.id)).length, 15);
  assert.equal(p2.itens.length, 20);
  assert.throws(() => A.sortearFinal(1, [], bancoFalso(4)), /só 2 questões/);
});

test("cada tema tem pelo menos uma questão de nível 2 ou 3", () => {
  const porId = new Map(BANCO.questoes.map((q) => [q.id, q]));
  for (let s = 1; s < 40; s++) {
    const p = A.sortearFinal(s, [], BANCO);
    for (const t of TEMAS) assert.ok(p.itens.some((i) => i.tema === t && porId.get(i.id)!.nivel >= 2), `${s} ${t}`);
  }
});

test("a correta acompanha o embaralhamento e a posição varia", () => {
  const porId = new Map(BANCO.questoes.map((q) => [q.id, q]));
  const posicoes = new Set<number>();
  for (let s = 1; s < 30; s++) {
    for (const i of A.sortearFinal(s, [], BANCO).itens) {
      const q = porId.get(i.id)!;
      assert.equal(i.opcoes[i.correta], q.opcoes[q.correta]);
      assert.deepEqual([...i.opcoes].sort(), [...q.opcoes].sort());
      posicoes.add(i.correta);
    }
  }
  assert.ok(posicoes.size >= 3);
});

test("a prova pública não vaza resposta nem explicação", () => {
  const texto = JSON.stringify(A.publica(A.sortearFinal(5, [], BANCO)));
  assert.ok(!texto.includes("correta"));
  assert.ok(!texto.includes("SEGREDO-EXPLICACAO"));
});

test("banco inválido é recusado", () => {
  const ruim = bancoFalso();
  ruim.questoes[0]!.correta = 9;
  assert.throws(() => A.sortearFinal(1, [], ruim));
  const repetido = bancoFalso();
  repetido.questoes[1]!.id = repetido.questoes[0]!.id;
  assert.throws(() => A.sortearNivelamento(1, repetido));
});

test("aprovação: 16/20 equilibrado aprova; 15/20 reprova; 16/20 com tema em 1/4 reprova", () => {
  const p = A.sortearFinal(7, [], BANCO);
  assert.equal(A.corrigir(p, certo(p)).aprovado, true);
  const ok = A.corrigir(p, certo(p, errosEm(p, { T1: 1, T2: 1, T3: 1, T4: 1 })));
  assert.deepEqual([ok.acertos, ok.aprovado], [16, true]);
  const nota = A.corrigir(p, certo(p, errosEm(p, { T1: 1, T2: 1, T3: 1, T4: 1, T5: 1 })));
  assert.deepEqual([nota.acertos, nota.aprovado], [15, false]);
  assert.ok(nota.motivos.some((m) => m.includes("80%")));
  const tema = A.corrigir(p, certo(p, errosEm(p, { T3: 3, T1: 1 })));
  assert.equal(tema.acertos, 16);
  assert.deepEqual(tema.porTema.T3, [1, 4]);
  assert.equal(tema.aprovado, false);
  assert.equal(tema.motivos.length, 1);
  assert.equal(A.corrigir(p, certo(p, errosEm(p, { T3: 2 }))).aprovado, true); // 2 de 4 é o limite
});

test("em branco conta como errada e respostas inválidas são recusadas", () => {
  const p = A.sortearFinal(7, [], BANCO);
  const r = certo(p) as Record<string, number | null>;
  delete r[p.itens[0]!.id];
  r[p.itens[1]!.id] = null;
  const res = A.corrigir(p, r);
  assert.deepEqual([res.acertos, res.emBranco], [18, 2]);
  const item = p.itens[0]!;
  for (const ruim of [item.opcoes.length, -1, "1", 1.5, true]) assert.throws(() => A.corrigir(p, { [item.id]: ruim }), A.ErroDeEntrada);
  assert.throws(() => A.corrigir(p, { "X-99": 0 }), A.ErroDeEntrada);
});

test("o nivelamento nunca aprova nem reprova e recomenda a lição", () => {
  const p = A.sortearNivelamento(3, BANCO);
  const ids = (t: string) => p.itens.filter((i) => i.tema === t).map((i) => i.id);
  assert.equal(A.corrigir(p, certo(p)).aprovado, null);
  assert.equal(A.recomendarLicao(A.corrigir(p, certo(p))), null);
  assert.equal(A.recomendarLicao(A.corrigir(p, certo(p, [...ids("T4"), ...ids("T5")]))), 2);
  assert.equal(A.recomendarLicao(A.corrigir(p, certo(p, ids("T5")))), 3);
  assert.equal(A.recomendarLicao(A.corrigir(p, certo(p, [...ids("T1"), ...ids("T2"), ...ids("T3")]))), 1);
});

test("faixas e nome", () => {
  assert.deepEqual([A.faixa(3, 4), A.faixa(2, 4), A.faixa(1, 4), A.faixa(0, 0)], ["dominado", "revisar", "refazer", "refazer"]);
  assert.equal(A.validarNome("  Maria   Exemplo \n"), "Maria Exemplo");
  assert.equal(A.validarNome("Maria\u0000 Ex\u0007emplo"), "Maria Exemplo");
  assert.equal(A.validarNome("José d'Ávila"), "José d'Ávila");
  for (const ruim of ["", "ab", " a ", "x".repeat(81), "123 456", "\u0000\u0001\u0002\u0003", 7, null]) assert.throws(() => A.validarNome(ruim), A.ErroDeEntrada, String(ruim));
  assert.equal(A.validarNome("x".repeat(80)).length, 80);
  assert.equal(A.validarEmail("  Maria@Exemplo.COM "), "maria@exemplo.com");
  for (const ruim of ["", "sem-arroba", "a@b", "a b@c.com", 5]) assert.throws(() => A.validarEmail(ruim), A.ErroDeEntrada);
});

test("com 8 temas a final tem 24 questões (3 por tema) e a aprovação é 20 de 24 com 2 de 3 por tema", () => {
  const temas = { T1: "a", T2: "b", T3: "c", T4: "d", T5: "e", T6: "f", T7: "g", T8: "h" };
  const base = bancoFalso();
  const questoes = Object.keys(temas).flatMap((t) =>
    Array.from({ length: 10 }, (_, k) => ({
      ...base.questoes[0]!, id: `${t}-${String(k + 1).padStart(2, "0")}`, tema: t, uso: (k < 2 ? "nivelamento" : "final") as "nivelamento" | "final",
      nivel: k < 2 ? 1 : 1 + (k % 3), correta: k % 3, opcoes: ["a", "b", "c", "d"], explicacao: "x", revisar: [1, 2] as [number, number],
    })),
  );
  const banco = { versao: "t", temas, questoes };
  assert.equal(A.porTemaPadrao(5), 4);
  assert.equal(A.porTemaPadrao(8), 3);
  const p = A.sortearFinal(9, [], banco);
  assert.equal(p.itens.length, 24);
  for (const t of Object.keys(temas)) assert.equal(p.itens.filter((i) => i.tema === t).length, 3);
  assert.equal(A.sortearNivelamento(9, banco).itens.length, 16);
  const erra = (porTema: Record<string, number>) => Object.entries(porTema).flatMap(([t, n]) => p.itens.filter((i) => i.tema === t).slice(0, n).map((i) => i.id));
  assert.deepEqual([A.corrigir(p, certo(p, erra({ T1: 1, T2: 1, T3: 1, T4: 1 }))).acertos, A.corrigir(p, certo(p, erra({ T1: 1, T2: 1, T3: 1, T4: 1 }))).aprovado], [20, true]);
  assert.equal(A.corrigir(p, certo(p, erra({ T1: 1, T2: 1, T3: 1, T4: 1, T5: 1 }))).aprovado, false);
  const tema = A.corrigir(p, certo(p, erra({ T7: 2 })));
  assert.deepEqual([tema.acertos, tema.porTema.T7, tema.aprovado], [22, [1, 3], false]);
  assert.equal(A.recomendarLicao(A.corrigir(A.sortearNivelamento(3, banco), Object.fromEntries(A.sortearNivelamento(3, banco).itens.map((i) => [i.id, i.tema === "T6" ? (i.correta + 1) % i.opcoes.length : i.correta])))), 4);
});
