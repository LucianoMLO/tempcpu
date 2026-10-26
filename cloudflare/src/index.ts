// Ponto de entrada do Worker. O banco de questões ativo (banco/ativo.json) não é versionado: contém as respostas.
// Gere-o com `npm run banco:exemplo` (questões de mentira, para desenvolvimento) ou `npm run banco:real`.
import { criarApp } from "./app.ts";
import type { Banco } from "./avaliacao.ts";
import banco from "../banco/ativo.json" with { type: "json" };
import glossario from "../banco/glossario.json" with { type: "json" };
import type { Env, Glossario } from "./tipos.ts";

const app = criarApp({ banco: banco as unknown as Banco, glossario: glossario as unknown as Glossario });

export default {
  fetch: (req: Request, env: Env) => app.fetch(req, env),
} satisfies ExportedHandler<Env>;
