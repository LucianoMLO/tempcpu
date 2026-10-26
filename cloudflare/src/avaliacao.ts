// Regras da avaliação, iguais às de lab/avaliacao.py (a referência em Python). Todas as questões são de múltipla escolha.
import { criarRng, embaralhar, type Rng } from "./rng.ts";

export const NOTA_MINIMA_PCT = 80;
export const MINIMO_POR_TEMA_PCT = 50;
export const POR_TEMA_NA_FINAL = 4;
export const FAIXA_DOMINADO_PCT = 75;
export const FAIXA_REVISAR_PCT = 50;
export const LICAO_DO_TEMA: Record<string, number> = { T1: 1, T2: 1, T3: 1, T4: 2, T5: 3 };
export const NOME_MIN = 3;
export const NOME_MAX = 80;

export interface Questao {
  id: string;
  tema: string;
  uso: "nivelamento" | "final";
  nivel: number;
  pergunta: string;
  opcoes: string[];
  correta: number;
  explicacao: string;
  revisar: [number, number];
}

export interface Banco {
  versao: string;
  temas: Record<string, string>;
  questoes: Questao[];
}

export interface ItemProva {
  id: string;
  tema: string;
  pergunta: string;
  opcoes: string[];
  correta: number; // posição na ordem sorteada; nunca sai do servidor
  explicacao: string;
  revisar: [number, number];
}

export interface Prova {
  tipo: "nivelamento" | "final";
  semente: number;
  itens: ItemProva[];
  versaoBanco: string;
}

export interface Erro {
  id: string;
  tema: string;
  pergunta: string;
  marcada: number | null;
  correta: number;
  opcoes: string[];
  explicacao: string;
  revisar: [number, number];
}

export interface Resultado {
  tipo: "nivelamento" | "final";
  acertos: number;
  total: number;
  emBranco: number;
  porTema: Record<string, [number, number]>;
  erradas: Erro[];
  aprovado: boolean | null;
  motivos: string[];
}

export function validarBanco(banco: Banco): void {
  const ids = new Set<string>();
  for (const q of banco.questoes) {
    if (ids.has(q.id)) throw new Error(`banco com ids repetidos: ${q.id}`);
    ids.add(q.id);
    if (!Number.isInteger(q.correta) || q.correta < 0 || q.correta >= q.opcoes.length) {
      throw new Error(`${q.id}: índice da correta fora das opções`);
    }
  }
}

function montar(q: Questao, rng: Rng): ItemProva {
  const ordem = embaralhar(q.opcoes.map((_, i) => i), rng);
  return {
    id: q.id,
    tema: q.tema,
    pergunta: q.pergunta,
    opcoes: ordem.map((i) => q.opcoes[i]!),
    correta: ordem.indexOf(q.correta),
    explicacao: q.explicacao,
    revisar: q.revisar,
  };
}

export function sortearNivelamento(semente: number, banco: Banco): Prova {
  validarBanco(banco);
  const escolhidas = banco.questoes.filter((q) => q.uso === "nivelamento");
  if (escolhidas.length === 0) throw new Error("o banco não tem questões de nivelamento");
  const rng = criarRng(semente);
  const ordem = embaralhar(escolhidas, rng);
  return { tipo: "nivelamento", semente, itens: ordem.map((q) => montar(q, rng)), versaoBanco: banco.versao };
}

export function sortearFinal(semente: number, anteriores: readonly string[], banco: Banco, porTema = POR_TEMA_NA_FINAL): Prova {
  validarBanco(banco);
  const rng = criarRng(semente);
  const evitar = new Set(anteriores);
  const temas = [...new Set(banco.questoes.filter((q) => q.uso === "final").map((q) => q.tema))].sort();
  if (temas.length === 0) throw new Error("o banco não tem questões da avaliação final");
  let escolhidas: Questao[] = [];
  for (const tema of temas) {
    const pool = banco.questoes.filter((q) => q.uso === "final" && q.tema === tema);
    if (pool.length < porTema) throw new Error(`tema ${tema}: só ${pool.length} questões para sortear ${porTema}`);
    const novas = embaralhar(pool.filter((q) => !evitar.has(q.id)), rng);
    const repetidas = embaralhar(pool.filter((q) => evitar.has(q.id)), rng);
    const ordenadas = [...novas, ...repetidas];
    const pegas = ordenadas.slice(0, porTema);
    if (!pegas.some((q) => q.nivel >= 2)) {
      const reforco = ordenadas.slice(porTema).find((q) => q.nivel >= 2);
      if (reforco) pegas[pegas.length - 1] = reforco;
    }
    escolhidas = escolhidas.concat(pegas);
  }
  escolhidas = embaralhar(escolhidas, rng);
  return { tipo: "final", semente, itens: escolhidas.map((q) => montar(q, rng)), versaoBanco: banco.versao };
}

/** O que o aluno recebe: nunca a resposta nem a explicação. */
export function publica(prova: Prova): { tipo: string; itens: { id: string; tema: string; pergunta: string; opcoes: string[] }[] } {
  return { tipo: prova.tipo, itens: prova.itens.map((i) => ({ id: i.id, tema: i.tema, pergunta: i.pergunta, opcoes: i.opcoes })) };
}

export function faixa(acertos: number, total: number): "dominado" | "revisar" | "refazer" {
  if (total <= 0) return "refazer";
  if (acertos * 100 >= FAIXA_DOMINADO_PCT * total) return "dominado";
  if (acertos * 100 >= FAIXA_REVISAR_PCT * total) return "revisar";
  return "refazer";
}

export class ErroDeEntrada extends Error {}

export function corrigir(prova: Prova, respostas: Record<string, unknown>): Resultado {
  const porId = new Map(prova.itens.map((i) => [i.id, i]));
  for (const [qid, marcada] of Object.entries(respostas)) {
    const item = porId.get(qid);
    if (!item) throw new ErroDeEntrada(`resposta para questão que não está na prova: ${qid}`);
    if (marcada !== null && (typeof marcada !== "number" || !Number.isInteger(marcada) || marcada < 0 || marcada >= item.opcoes.length)) {
      throw new ErroDeEntrada(`${qid}: alternativa inválida`);
    }
  }
  let acertos = 0;
  let emBranco = 0;
  const porTema: Record<string, [number, number]> = {};
  const erradas: Erro[] = [];
  for (const item of prova.itens) {
    const marcada = (respostas[item.id] ?? null) as number | null;
    const c = (porTema[item.tema] ??= [0, 0]);
    c[1] += 1;
    if (marcada === null) emBranco += 1;
    if (marcada === item.correta) {
      acertos += 1;
      c[0] += 1;
    } else {
      erradas.push({ id: item.id, tema: item.tema, pergunta: item.pergunta, marcada, correta: item.correta, opcoes: item.opcoes, explicacao: item.explicacao, revisar: item.revisar });
    }
  }
  let aprovado: boolean | null = null;
  let motivos: string[] = [];
  if (prova.tipo === "final") {
    if (acertos * 100 < NOTA_MINIMA_PCT * prova.itens.length) motivos.push(`A nota geral precisa ser de pelo menos ${NOTA_MINIMA_PCT}%.`);
    for (const [tema, [a, n]] of Object.entries(porTema).sort()) {
      if (a * 100 < MINIMO_POR_TEMA_PCT * n) motivos.push(`Tema ${tema}: é preciso acertar pelo menos metade das questões (${a} de ${n}).`);
    }
    aprovado = motivos.length === 0;
  }
  return { tipo: prova.tipo, acertos, total: prova.itens.length, emBranco, porTema, erradas, aprovado, motivos };
}

export function notaPct(r: Pick<Resultado, "acertos" | "total">): number {
  return r.total ? (100 * r.acertos) / r.total : 0;
}

/** Do nivelamento: a primeira lição cujos temas tiveram menos de 75% de acertos; null se todas ≥ 75%. */
export function recomendarLicao(r: Resultado): number | null {
  const porLicao = new Map<number, [number, number]>();
  for (const [tema, [a, n]] of Object.entries(r.porTema)) {
    const l = LICAO_DO_TEMA[tema] ?? 1;
    const c = porLicao.get(l) ?? [0, 0];
    c[0] += a;
    c[1] += n;
    porLicao.set(l, c);
  }
  for (const l of [...porLicao.keys()].sort((x, y) => x - y)) {
    const [a, n] = porLicao.get(l)!;
    if (faixa(a, n) !== "dominado") return l;
  }
  return null;
}

/** Nome para o certificado: sem caracteres de controle, espaços normalizados, de 3 a 80 caracteres e com letras. */
export function validarNome(nome: unknown): string {
  const bruto = typeof nome === "string" ? nome : "";
  const limpo = bruto
    .normalize("NFC")
    .replace(/[\t\n\r\f\v]/g, " ")
    .replace(/\p{C}/gu, "")
    .replace(/\s+/g, " ")
    .trim();
  if ([...limpo].length < NOME_MIN) throw new ErroDeEntrada(`O nome precisa ter pelo menos ${NOME_MIN} caracteres.`);
  if ([...limpo].length > NOME_MAX) throw new ErroDeEntrada(`O nome pode ter no máximo ${NOME_MAX} caracteres.`);
  if (!/\p{L}/u.test(limpo)) throw new ErroDeEntrada("O nome precisa ter letras.");
  return limpo;
}

export function validarEmail(email: unknown): string {
  const e = typeof email === "string" ? email.trim().toLowerCase() : "";
  if (e.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e)) throw new ErroDeEntrada("Informe um e-mail válido.");
  return e;
}
