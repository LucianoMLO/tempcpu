import type { Banco } from "./avaliacao.ts";

export interface Glossario {
  [chave: string]: { nome: string; definicao: string; exemplo: string };
}

export interface Env {
  DB: D1Database;
  AMBIENTE?: string;
  SEGREDO_ASSINATURA?: string;
  RESEND_API_KEY?: string;
  EMAIL_REMETENTE?: string;
  TURNSTILE_SECRET?: string;
  TURNSTILE_SITEKEY?: string;
  ORIGEM_PUBLICA?: string;
  EMISSOR_NOME?: string;
  EMISSOR_CNPJ?: string;
  CONTATO_PRIVACIDADE?: string;
  INTERVALO_MIN_FINAL_S?: string;
  MAX_FINAIS_POR_DIA?: string;
  /** Segredo (lista separada por vírgulas): em AMBIENTE=dev, o link de acesso dessas contas aparece na tela, sem e-mail. */
  TESTE_EMAILS?: string;
  PAGINA_PROJETO?: string;
  /** Só em testes: substitui o banco empacotado. */
  BANCO_TESTE?: Banco;
}

export interface Aluno {
  id: string;
  nome: string;
  email: string;
  email_confirmado_em: number | null;
  marketing: number;
}

export interface LinhaProva {
  id: string;
  aluno_id: string | null;
  tipo: "nivelamento" | "final";
  semente: number;
  versao_banco: string;
  itens_json: string;
  respostas_json: string | null;
  resultado_json: string | null;
  criada_em: number;
  expira_em: number;
  entregue_em: number | null;
}

export interface LinhaCertificado {
  codigo: string;
  aluno_id: string;
  prova_id: string;
  nome: string;
  nota_pct: number;
  por_tema_json: string;
  versao_banco: string;
  emitido_em: number;
  valido_ate: number;
  revogado_em: number | null;
}
