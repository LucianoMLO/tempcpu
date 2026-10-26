// Acesso ao D1. Só prepare/bind/first/all/run, para o mesmo código rodar no Worker e num SQLite de teste.
import type { Aluno, LinhaCertificado, LinhaProva } from "./tipos.ts";

type DB = D1Database;

export async function limitar(db: DB, chave: string, max: number, janelaS: number, agora: number): Promise<boolean> {
  const linha = await db.prepare("SELECT COUNT(*) AS n FROM evento WHERE chave = ? AND ts > ?").bind(chave, agora - janelaS).first<{ n: number }>();
  if ((linha?.n ?? 0) >= max) return false;
  await db.prepare("INSERT INTO evento (chave, ts) VALUES (?, ?)").bind(chave, agora).run();
  return true;
}

export async function limparEventosAntigos(db: DB, agora: number): Promise<void> {
  await db.prepare("DELETE FROM evento WHERE ts < ?").bind(agora - 2 * 86400).run();
}

// ---- alunos
export async function alunoPorEmail(db: DB, email: string): Promise<Aluno | null> {
  return db.prepare("SELECT id, nome, email, email_confirmado_em, marketing FROM aluno WHERE email = ?").bind(email).first<Aluno>();
}

export async function alunoPorId(db: DB, id: string): Promise<Aluno | null> {
  return db.prepare("SELECT id, nome, email, email_confirmado_em, marketing FROM aluno WHERE id = ?").bind(id).first<Aluno>();
}

export async function criarAluno(db: DB, a: { id: string; nome: string; email: string; marketing: boolean; agora: number }): Promise<void> {
  await db
    .prepare("INSERT INTO aluno (id, nome, email, consentimento_em, marketing, marketing_em, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .bind(a.id, a.nome, a.email, a.agora, a.marketing ? 1 : 0, a.marketing ? a.agora : null, a.agora)
    .run();
}

export async function criarToken(db: DB, hash: string, alunoId: string, expiraEm: number): Promise<void> {
  await db.prepare("INSERT INTO token_email (hash, aluno_id, expira_em) VALUES (?, ?, ?)").bind(hash, alunoId, expiraEm).run();
}

/** Consome o token uma única vez; devolve o aluno dono dele ou null (inexistente, expirado ou já usado). */
export async function consumirToken(db: DB, hash: string, agora: number): Promise<string | null> {
  const linha = await db
    .prepare("UPDATE token_email SET usado_em = ? WHERE hash = ? AND usado_em IS NULL AND expira_em > ? RETURNING aluno_id")
    .bind(agora, hash, agora)
    .first<{ aluno_id: string }>();
  return linha?.aluno_id ?? null;
}

export async function confirmarEmail(db: DB, alunoId: string, agora: number): Promise<void> {
  await db.prepare("UPDATE aluno SET email_confirmado_em = COALESCE(email_confirmado_em, ?) WHERE id = ?").bind(agora, alunoId).run();
}

export async function criarSessao(db: DB, hash: string, alunoId: string, expiraEm: number): Promise<void> {
  await db.prepare("INSERT INTO sessao (hash, aluno_id, expira_em) VALUES (?, ?, ?)").bind(hash, alunoId, expiraEm).run();
}

export async function alunoDaSessao(db: DB, hash: string, agora: number): Promise<Aluno | null> {
  return db
    .prepare(
      "SELECT a.id, a.nome, a.email, a.email_confirmado_em, a.marketing FROM sessao s JOIN aluno a ON a.id = s.aluno_id WHERE s.hash = ? AND s.expira_em > ?",
    )
    .bind(hash, agora)
    .first<Aluno>();
}

export async function apagarSessao(db: DB, hash: string): Promise<void> {
  await db.prepare("DELETE FROM sessao WHERE hash = ?").bind(hash).run();
}

/** Exclui o aluno e tudo o que depende dele (sessões, tokens, provas, certificados). */
export async function excluirAluno(db: DB, alunoId: string): Promise<void> {
  await db.batch([
    db.prepare("DELETE FROM certificado WHERE aluno_id = ?").bind(alunoId),
    db.prepare("DELETE FROM prova WHERE aluno_id = ?").bind(alunoId),
    db.prepare("DELETE FROM token_email WHERE aluno_id = ?").bind(alunoId),
    db.prepare("DELETE FROM sessao WHERE aluno_id = ?").bind(alunoId),
    db.prepare("DELETE FROM aluno WHERE id = ?").bind(alunoId),
  ]);
}

// ---- provas
export async function criarProva(db: DB, p: Omit<LinhaProva, "respostas_json" | "resultado_json" | "entregue_em">): Promise<void> {
  await db
    .prepare(
      "INSERT INTO prova (id, aluno_id, tipo, semente, versao_banco, itens_json, criada_em, expira_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    )
    .bind(p.id, p.aluno_id, p.tipo, p.semente, p.versao_banco, p.itens_json, p.criada_em, p.expira_em)
    .run();
}

export async function provaPorId(db: DB, id: string): Promise<LinhaProva | null> {
  return db.prepare("SELECT * FROM prova WHERE id = ?").bind(id).first<LinhaProva>();
}

export async function provaAbertaDoAluno(db: DB, alunoId: string, tipo: string, agora: number): Promise<LinhaProva | null> {
  return db
    .prepare("SELECT * FROM prova WHERE aluno_id = ? AND tipo = ? AND entregue_em IS NULL AND expira_em > ? ORDER BY criada_em DESC LIMIT 1")
    .bind(alunoId, tipo, agora)
    .first<LinhaProva>();
}

export async function idsDaUltimaFinal(db: DB, alunoId: string): Promise<string[]> {
  const linha = await db
    .prepare("SELECT itens_json FROM prova WHERE aluno_id = ? AND tipo = 'final' ORDER BY criada_em DESC LIMIT 1")
    .bind(alunoId)
    .first<{ itens_json: string }>();
  if (!linha) return [];
  return (JSON.parse(linha.itens_json) as { id: string }[]).map((i) => i.id);
}

/** Grava a entrega uma única vez; devolve false se a prova já tinha sido entregue (reenvio não altera a nota). */
export async function entregarProva(db: DB, id: string, respostasJson: string, resultadoJson: string, agora: number): Promise<boolean> {
  const linha = await db
    .prepare("UPDATE prova SET respostas_json = ?, resultado_json = ?, entregue_em = ? WHERE id = ? AND entregue_em IS NULL AND expira_em > ? RETURNING id")
    .bind(respostasJson, resultadoJson, agora, id, agora)
    .first<{ id: string }>();
  return linha !== null;
}

export async function provasDoAluno(db: DB, alunoId: string): Promise<LinhaProva[]> {
  const r = await db.prepare("SELECT * FROM prova WHERE aluno_id = ? AND entregue_em IS NOT NULL ORDER BY entregue_em DESC LIMIT 20").bind(alunoId).all<LinhaProva>();
  return r.results ?? [];
}

// ---- certificados
export async function criarCertificado(db: DB, c: LinhaCertificado): Promise<boolean> {
  const r = await db
    .prepare(
      "INSERT OR IGNORE INTO certificado (codigo, aluno_id, prova_id, nome, nota_pct, por_tema_json, versao_banco, emitido_em, valido_ate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )
    .bind(c.codigo, c.aluno_id, c.prova_id, c.nome, c.nota_pct, c.por_tema_json, c.versao_banco, c.emitido_em, c.valido_ate)
    .run();
  return (r.meta?.changes ?? 0) > 0;
}

export async function certificadoPorCodigo(db: DB, codigo: string): Promise<LinhaCertificado | null> {
  return db.prepare("SELECT * FROM certificado WHERE codigo = ?").bind(codigo).first<LinhaCertificado>();
}

export async function certificadoDaProva(db: DB, provaId: string): Promise<LinhaCertificado | null> {
  return db.prepare("SELECT * FROM certificado WHERE prova_id = ?").bind(provaId).first<LinhaCertificado>();
}

export async function certificadosDoAluno(db: DB, alunoId: string): Promise<LinhaCertificado[]> {
  const r = await db.prepare("SELECT * FROM certificado WHERE aluno_id = ? ORDER BY emitido_em DESC").bind(alunoId).all<LinhaCertificado>();
  return r.results ?? [];
}
