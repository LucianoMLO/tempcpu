// D1 de mentira sobre node:sqlite (só o subconjunto que o Worker usa) e um cliente HTTP com cookies.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { criarApp } from "../src/app.ts";
import type { Banco } from "../src/avaliacao.ts";
import type { Env, Glossario } from "../src/tipos.ts";

type Valor = string | number | null;

class Stmt {
  private args: Valor[] = [];
  private banco: DatabaseSync;
  private sql: string;
  constructor(banco: DatabaseSync, sql: string) {
    this.banco = banco;
    this.sql = sql;
  }
  bind(...args: Valor[]) {
    this.args = args;
    return this;
  }
  async first<T>(): Promise<T | null> {
    return (this.banco.prepare(this.sql).get(...this.args) as T | undefined) ?? null;
  }
  async all<T>() {
    return { results: this.banco.prepare(this.sql).all(...this.args) as T[] };
  }
  async run() {
    const r = this.banco.prepare(this.sql).run(...this.args);
    return { meta: { changes: Number(r.changes) } };
  }
  exec() {
    return this.banco.prepare(this.sql).run(...this.args);
  }
}

export function criarD1(): { d1: D1Database; banco: DatabaseSync } {
  const banco = new DatabaseSync(":memory:");
  banco.exec("PRAGMA foreign_keys = ON");
  banco.exec(readFileSync(join(import.meta.dirname, "..", "schema.sql"), "utf8"));
  const d1 = {
    prepare: (sql: string) => new Stmt(banco, sql),
    async batch(lista: Stmt[]) {
      banco.exec("BEGIN");
      try {
        for (const s of lista) s.exec();
        banco.exec("COMMIT");
      } catch (e) {
        banco.exec("ROLLBACK");
        throw e;
      }
      return [];
    },
  } as unknown as D1Database;
  return { d1, banco };
}

export function bancoFalso(porTema = 10): Banco {
  const temas = { T1: "Dados e variáveis", T2: "Treino e teste", T3: "Avaliar um modelo", T4: "Anomalia", T5: "Gabarito" };
  const questoes = Object.keys(temas).flatMap((t) =>
    Array.from({ length: porTema }, (_, k) => {
      const i = k + 1;
      const niv = i <= 2;
      return {
        id: `${t}-${String(i).padStart(2, "0")}`, tema: t, uso: niv ? "nivelamento" : "final", nivel: niv ? 1 : 1 + (i % 3),
        pergunta: `Pergunta ${t}-${i} sobre ⟦modelo⟧?`, opcoes: [`${t}-${i} a`, `${t}-${i} b`, `${t}-${i} c`, `${t}-${i} d`].slice(0, 3 + (i % 2)),
        correta: i % 3, explicacao: `SEGREDO-EXPLICACAO-${t}-${i}`, revisar: [1, 2] as [number, number],
      };
    }),
  ) as Banco["questoes"];
  return { versao: "teste", temas, questoes };
}

export const glossarioFalso: Glossario = { modelo: { nome: "modelo", definicao: "Uma fórmula aprendida.", exemplo: "ex" } };

export const ORIGEM = "https://avaliacao.test";

export function criarAmbiente(extra: Partial<Env> = {}) {
  const { d1, banco } = criarD1();
  const env: Env = { DB: d1, AMBIENTE: "dev", INTERVALO_MIN_FINAL_S: "0", BANCO_TESTE: bancoFalso(), ...extra };
  (globalThis as Record<string, unknown>).__emails = [];
  return { env, banco, app: criarApp({ banco: env.BANCO_TESTE!, glossario: glossarioFalso }) };
}

export function emails(): { para: string; assunto: string; texto: string }[] {
  return (globalThis as Record<string, unknown>).__emails as { para: string; assunto: string; texto: string }[];
}

export class Cliente {
  cookies = new Map<string, string>();
  app: { fetch(r: Request, e: Env): Promise<Response> };
  env: Env;
  ip: string;
  constructor(app: { fetch(r: Request, e: Env): Promise<Response> }, env: Env, ip = "203.0.113.1") {
    this.app = app;
    this.env = env;
    this.ip = ip;
  }

  async pedir(caminho: string, opts: { metodo?: string; corpo?: unknown; origem?: string | null } = {}): Promise<Response> {
    const metodo = opts.metodo ?? (opts.corpo !== undefined ? "POST" : "GET");
    const h: Record<string, string> = { "CF-Connecting-IP": this.ip };
    if (this.cookies.size) h.Cookie = [...this.cookies].map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("; ");
    if (opts.corpo !== undefined) h["Content-Type"] = "application/json";
    if (metodo === "POST" && opts.origem !== null) h.Origin = opts.origem ?? ORIGEM;
    const r = await this.app.fetch(new Request(ORIGEM + caminho, { method: metodo, headers: h, body: opts.corpo !== undefined ? JSON.stringify(opts.corpo) : undefined, redirect: "manual" }), this.env);
    for (const sc of r.headers.getSetCookie?.() ?? []) {
      const [par] = sc.split(";");
      const i = par!.indexOf("=");
      const nome = par!.slice(0, i);
      const valor = decodeURIComponent(par!.slice(i + 1));
      if (valor) this.cookies.set(nome, valor);
      else this.cookies.delete(nome);
    }
    return r;
  }

  async json(caminho: string, corpo: unknown): Promise<{ status: number; j: Record<string, unknown> }> {
    const r = await this.pedir(caminho, { corpo });
    return { status: r.status, j: (await r.json()) as Record<string, unknown> };
  }

  /** Cadastra, abre o link do e-mail e confirma: deixa o cliente logado. */
  async entrarComo(nome: string, email: string): Promise<void> {
    const antes = emails().length;
    const cad = await this.json("/api/cadastro", { nome, email, consentimento: true, marketing: false });
    if (cad.status !== 200) throw new Error(`cadastro falhou: ${JSON.stringify(cad.j)}`);
    const msg = emails()[antes]!;
    const token = new URL(/https?:\/\/\S+/.exec(msg.texto)![0]).searchParams.get("t")!;
    const conf = await this.json("/api/confirmar", { t: token });
    if (conf.status !== 200) throw new Error(`confirmação falhou: ${JSON.stringify(conf.j)}`);
  }

  /** Abre uma prova e devolve o id e as questões como o aluno as vê. */
  async abrirProva(tipo: "final" | "nivelamento"): Promise<{ id: string; ids: string[]; html: string }> {
    const r = await this.pedir(`/prova/${tipo}`);
    if (r.status !== 302) throw new Error(`prova ${tipo}: status ${r.status}`);
    const loc = r.headers.get("Location")!;
    const pagina = await (await this.pedir(loc)).text();
    const ids = [...pagina.matchAll(/data-id="([A-Z0-9-]+)"/g)].map((m) => m[1]!);
    return { id: loc.split("/").pop()!, ids, html: pagina };
  }
}
