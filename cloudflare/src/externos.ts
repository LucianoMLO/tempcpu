// Serviços de fora: e-mail (Resend) e Turnstile. Em ambiente "dev" nada sai da máquina.
import type { Env } from "./tipos.ts";

export interface Mensagem {
  para: string;
  assunto: string;
  texto: string;
}

/** Em dev, as mensagens ficam em `globalThis.__emails` (e no log) em vez de serem enviadas. */
export async function enviarEmail(env: Env, msg: Mensagem): Promise<boolean> {
  if (env.AMBIENTE === "dev") {
    const caixa = ((globalThis as Record<string, unknown>).__emails ??= []) as Mensagem[];
    caixa.push(msg);
    console.log(`[e-mail de desenvolvimento] para ${msg.para}: ${msg.assunto}\n${msg.texto}`);
    return true;
  }
  if (!env.RESEND_API_KEY || !env.EMAIL_REMETENTE) return false;
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: env.EMAIL_REMETENTE, to: [msg.para], subject: msg.assunto, text: msg.texto }),
  });
  return r.ok;
}

/** Verifica o Turnstile. Sem segredo configurado só passa em dev; em produção falha fechado. */
export async function verificarTurnstile(env: Env, token: unknown, ip: string | null): Promise<boolean> {
  if (!env.TURNSTILE_SECRET) return env.AMBIENTE === "dev";
  if (typeof token !== "string" || token.length < 10 || token.length > 4096) return false;
  const corpo = new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token });
  if (ip) corpo.set("remoteip", ip);
  try {
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: corpo });
    const j = (await r.json()) as { success?: boolean };
    return j.success === true;
  } catch {
    return false;
  }
}
