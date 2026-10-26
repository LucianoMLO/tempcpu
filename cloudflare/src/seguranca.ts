// Aleatoriedade, hash, assinatura, cookies e proteção de origem. Só Web Crypto: roda no Worker e no Node.
const enc = new TextEncoder();

function hex(buf: ArrayBuffer): string {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function sha256Hex(texto: string): Promise<string> {
  return hex(await crypto.subtle.digest("SHA-256", enc.encode(texto)));
}

export async function hmacHex(chave: string, mensagem: string): Promise<string> {
  const k = await crypto.subtle.importKey("raw", enc.encode(chave), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", k, enc.encode(mensagem)));
}

function base64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Segredo imprevisível de `n` bytes em base64url (tokens, ids, cookies). */
export function aleatorio(n = 24): string {
  return base64url(crypto.getRandomValues(new Uint8Array(n)));
}

export function semente32(): number {
  return crypto.getRandomValues(new Uint32Array(1))[0]!;
}

export function lerCookie(req: Request, nome: string): string | null {
  const bruto = req.headers.get("Cookie");
  if (!bruto) return null;
  for (const parte of bruto.split(";")) {
    const i = parte.indexOf("=");
    if (i > 0 && parte.slice(0, i).trim() === nome) return decodeURIComponent(parte.slice(i + 1).trim());
  }
  return null;
}

export function cookie(nome: string, valor: string, opts: { seguro: boolean; maxAge: number }): string {
  return `${nome}=${encodeURIComponent(valor)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${opts.maxAge}${opts.seguro ? "; Secure" : ""}`;
}

/** Pedidos que alteram dados só valem se vierem da própria página (Origin ou Referer iguais à origem do site). */
export function mesmaOrigem(req: Request, origemPublica?: string): boolean {
  const esperada = origemPublica || new URL(req.url).origin;
  const origin = req.headers.get("Origin");
  if (origin) return origin === esperada;
  const ref = req.headers.get("Referer");
  if (ref) {
    try {
      return new URL(ref).origin === esperada;
    } catch {
      return false;
    }
  }
  return false;
}

export function escapar(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export const agora = (): number => Math.floor(Date.now() / 1000);
