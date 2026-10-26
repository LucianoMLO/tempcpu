-- Avaliação e certificado do Laboratório do TempCPU. Datas em segundos desde 1970 (UTC).
CREATE TABLE IF NOT EXISTS aluno (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  email_confirmado_em INTEGER,
  consentimento_em INTEGER NOT NULL,
  marketing INTEGER NOT NULL DEFAULT 0,
  marketing_em INTEGER,
  criado_em INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS token_email (
  hash TEXT PRIMARY KEY,
  aluno_id TEXT NOT NULL REFERENCES aluno(id) ON DELETE CASCADE,
  expira_em INTEGER NOT NULL,
  usado_em INTEGER
);

CREATE TABLE IF NOT EXISTS sessao (
  hash TEXT PRIMARY KEY,
  aluno_id TEXT NOT NULL REFERENCES aluno(id) ON DELETE CASCADE,
  expira_em INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prova (
  id TEXT PRIMARY KEY,
  aluno_id TEXT REFERENCES aluno(id) ON DELETE CASCADE,   -- nulo no nivelamento anônimo
  tipo TEXT NOT NULL CHECK (tipo IN ('nivelamento','final')),
  semente INTEGER NOT NULL,
  versao_banco TEXT NOT NULL,
  itens_json TEXT NOT NULL,            -- itens na ordem sorteada, com a posição da correta (nunca sai do servidor)
  respostas_json TEXT,
  resultado_json TEXT,
  criada_em INTEGER NOT NULL,
  expira_em INTEGER NOT NULL,
  entregue_em INTEGER
);
CREATE INDEX IF NOT EXISTS prova_aluno ON prova(aluno_id, tipo, criada_em);

CREATE TABLE IF NOT EXISTS certificado (
  codigo TEXT PRIMARY KEY,
  aluno_id TEXT NOT NULL REFERENCES aluno(id) ON DELETE CASCADE,
  prova_id TEXT NOT NULL UNIQUE REFERENCES prova(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  nota_pct REAL NOT NULL,
  por_tema_json TEXT NOT NULL,
  versao_banco TEXT NOT NULL,
  emitido_em INTEGER NOT NULL,
  valido_ate INTEGER NOT NULL,
  revogado_em INTEGER
);

CREATE TABLE IF NOT EXISTS evento (
  chave TEXT NOT NULL,
  ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS evento_chave ON evento(chave, ts);
