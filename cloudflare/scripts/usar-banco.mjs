// Escolhe o banco de questões que o Worker empacota: "exemplo" (público, de mentira) ou "real" (privado, gerado do Laboratório).
import { copyFileSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const modo = process.argv[2];
if (modo === "exemplo") {
  copyFileSync(join(raiz, "banco", "exemplo.json"), join(raiz, "banco", "ativo.json"));
  console.log("banco/ativo.json = questões de exemplo (de mentira)");
} else if (modo === "real") {
  const py = join(raiz, "..", ".venv-lab", "Scripts", "python.exe");
  const r = spawnSync(existsSync(py) ? py : "python", ["-X", "utf8", join(raiz, "..", "tools", "exportar_banco.py")], { stdio: "inherit" });
  process.exit(r.status ?? 1);
} else {
  console.error("uso: node scripts/usar-banco.mjs exemplo|real");
  process.exit(2);
}
