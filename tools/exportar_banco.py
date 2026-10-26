"""Exporta o banco de questões do Laboratório (privado) e o glossário (público) para o Worker da Cloudflare.

Escreve cloudflare/banco/ativo.json (NÃO versionado: tem as respostas) e cloudflare/banco/glossario.json.
Uso:  .venv-lab\Scripts\python -X utf8 tools\exportar_banco.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from lab.glossario import TERMOS  # noqa: E402
from lab.questoes import QUESTOES, TEMAS, VERSAO_BANCO  # noqa: E402

saida = RAIZ / "cloudflare" / "banco"
saida.mkdir(parents=True, exist_ok=True)
banco = {"versao": VERSAO_BANCO, "temas": TEMAS,
         "questoes": [{**q, "revisar": list(q["revisar"])} for q in QUESTOES]}
(saida / "ativo.json").write_text(json.dumps(banco, ensure_ascii=False, indent=1), encoding="utf-8")
glossario = {chave: {"nome": v[0], "definicao": v[2], "exemplo": v[3]} for chave, v in TERMOS.items()}
(saida / "glossario.json").write_text(json.dumps(glossario, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(QUESTOES)} questões (versão {VERSAO_BANCO}) e {len(glossario)} termos exportados para {saida}")
