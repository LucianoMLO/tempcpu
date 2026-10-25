"""Histórico em SQLite: um registro por minuto e resumos por hora, dia, semana e mês.

- `AcumuladorMinuto`: junta as amostras de 2 s do minuto (média e desvio padrão pelo método de Welford).
- `Historico`: grava o minuto, recalcula os resumos e apaga minutos antigos (os resumos ficam).
- `combinar`: junta períodos menores num maior sem perder precisão (média ponderada e desvio padrão
  agregado, não "média das médias").
- `resumo_texto`: o que ocorreu no período, em português.

Tudo fica em `%LOCALAPPDATA%\\TempCPU\\historico.db`, fora da pasta do app e de qualquer pacote distribuído.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from motivos import Motivo, categoria_de, rotulo_de

# variável -> (rótulo, unidade)
VARIAVEIS: dict[str, tuple[str, str]] = {
    "cpu_c": ("Temperatura da CPU", "°C"),
    "gpu_c": ("Temperatura da GPU", "°C"),
    "soc_c": ("Temperatura do SoC", "°C"),
    "uso_cpu": ("Uso da CPU", "%"),
    "clk_mhz": ("Frequência da CPU", "MHz"),
    "ventoinha_rpm": ("Ventoinha da CPU", "RPM"),
    "bateria_pct": ("Bateria", "%"),
    "tomada": ("Na tomada (fração do tempo)", ""),
}
ESTATISTICAS = ("min", "max", "med", "dp", "n")
ZONAS = ("normal", "atencao", "quente", "dano")
NOME_ZONA = {"normal": "Normal", "atencao": "Atenção", "quente": "Quente", "dano": "Crítico"}
NIVEIS = ("minuto", "hora", "dia", "semana", "mes")
ROTULO_NIVEL = {"minuto": "Minuto", "hora": "Hora", "dia": "Dia", "semana": "Semana", "mes": "Mês"}
VERSAO_ESQUEMA = 1


def pasta_dados() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "TempCPU"


def _colunas_stats() -> list[str]:
    return [f"{v}_{e}" for v in VARIAVEIS for e in ESTATISTICAS]


# ---------------- tempo (sempre hora local) ----------------
def inicio_periodo(ts: float, nivel: str) -> int:
    if nivel == "minuto":
        return int(ts // 60 * 60)
    d = datetime.fromtimestamp(ts)
    if nivel == "hora":
        d = d.replace(minute=0, second=0, microsecond=0)
    else:
        d = d.replace(hour=0, minute=0, second=0, microsecond=0)
        if nivel == "semana":
            d -= timedelta(days=d.weekday())
        elif nivel == "mes":
            d = d.replace(day=1)
    return int(d.timestamp())


def fim_periodo(inicio: int, nivel: str) -> int:
    d = datetime.fromtimestamp(inicio)
    if nivel == "minuto":
        d += timedelta(minutes=1)
    elif nivel == "hora":
        d += timedelta(hours=1)
    elif nivel == "dia":
        d += timedelta(days=1)
    elif nivel == "semana":
        d += timedelta(days=7)
    else:
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return int(d.timestamp())


# ---------------- acumulador do minuto ----------------
class AcumuladorMinuto:
    def __init__(self, ts: int) -> None:
        self.ts = ts
        self._st: dict[str, list[float]] = {}  # variável -> [n, média, M2, mín, máx]
        self.amostras = 0
        self.descartadas = 0
        self.fontes: Counter[str] = Counter()
        self.motivos: Counter[str] = Counter()
        self.principais: Counter[str] = Counter()
        self.programas: Counter[str] = Counter()
        self.pct_programa: dict[str, float] = {}
        self.planos: Counter[str] = Counter()
        self.estado_max: int | None = None
        self.pico_ts: int | None = None

    def valor(self, var: str, x: float | None, ts: float | None = None) -> None:
        if x is None:
            return
        st = self._st.setdefault(var, [0, 0.0, 0.0, math.inf, -math.inf])
        st[0] += 1
        delta = x - st[1]
        st[1] += delta / st[0]
        st[2] += delta * (x - st[1])
        if x > st[4]:
            st[4] = x
            if var == "cpu_c" and ts is not None:
                self.pico_ts = int(ts)
        st[3] = min(st[3], x)

    def vazio(self) -> bool:
        return not self._st and not self.descartadas

    def fechar(self, zona_fn) -> dict:
        """Devolve o registro plano do minuto. `zona_fn(°C)` classifica o pico de temperatura."""
        reg: dict = {"ts": self.ts, "amostras": self.amostras, "descartadas": self.descartadas}
        for var in VARIAVEIS:
            st = self._st.get(var)
            if st and st[0]:
                n = int(st[0])
                reg.update({f"{var}_n": n, f"{var}_min": st[3], f"{var}_max": st[4],
                            f"{var}_med": round(st[1], 3), f"{var}_dp": round(math.sqrt(st[2] / n), 3)})
            else:
                reg.update({f"{var}_n": 0, f"{var}_min": None, f"{var}_max": None,
                            f"{var}_med": None, f"{var}_dp": None})
        pico = reg["cpu_c_max"]
        zona = zona_fn(pico) if pico is not None else None
        for z in ZONAS:
            reg[f"z_{z}"] = 1 if z == zona else 0
        reg["zona"] = zona
        reg["fonte"] = self.fontes.most_common(1)[0][0] if self.fontes else None
        reg["plano"] = self.planos.most_common(1)[0][0] if self.planos else None
        reg["estado_max_ac"] = self.estado_max
        reg["pico_ts"] = self.pico_ts
        principal = self.principais.most_common(1)[0][0] if self.principais else None
        reg["motivo_principal"] = principal
        cat = categoria_de(principal) if principal else None
        reg["categoria_motivo"] = cat.value if cat else None
        reg["motivos"] = sorted(self.motivos, key=lambda m: -self.motivos[m])
        prog = self.programas.most_common(1)[0][0] if self.programas else None
        reg["programa_principal"] = prog
        reg["programa_pct"] = round(self.pct_programa[prog], 1) if prog else None
        return reg


# ---------------- combinação e resumo (puros) ----------------
def combinar(linhas: list[dict]) -> dict:
    """Junta linhas (minutos ou períodos menores) num período maior.
    Cada linha traz, por variável, n/min/max/med/dp; o resultado usa média ponderada por n e
    desvio padrão agregado: var = Σ n·(dp² + med²) / N − med²."""
    out: dict = {"minutos": sum(l.get("minutos", 1) for l in linhas),
                 "amostras": sum(l.get("amostras") or 0 for l in linhas),
                 "descartadas": sum(l.get("descartadas") or 0 for l in linhas)}
    for var in VARIAVEIS:
        com_dado = [l for l in linhas if l.get(f"{var}_n")]
        n = sum(l[f"{var}_n"] for l in com_dado)
        if not n:
            out.update({f"{var}_n": 0, f"{var}_min": None, f"{var}_max": None,
                        f"{var}_med": None, f"{var}_dp": None})
            continue
        med = sum(l[f"{var}_n"] * l[f"{var}_med"] for l in com_dado) / n
        quad = sum(l[f"{var}_n"] * (l[f"{var}_dp"] ** 2 + l[f"{var}_med"] ** 2) for l in com_dado) / n
        out.update({f"{var}_n": n, f"{var}_min": min(l[f"{var}_min"] for l in com_dado),
                    f"{var}_max": max(l[f"{var}_max"] for l in com_dado), f"{var}_med": round(med, 3),
                    f"{var}_dp": round(math.sqrt(max(quad - med * med, 0.0)), 3)})
    for z in ZONAS:
        out[f"z_{z}"] = sum(l.get(f"z_{z}") or 0 for l in linhas)
    picos = [l for l in linhas if l.get("cpu_c_max") is not None and l.get("pico_ts")]
    out["pico_ts"] = max(picos, key=lambda l: l["cpu_c_max"])["pico_ts"] if picos else None
    motivos: Counter[str] = Counter()
    programas: Counter[str] = Counter()
    for l in linhas:
        motivos.update(l.get("motivos_dict") or {})
        programas.update(l.get("programas_dict") or {})
    out["motivos_dict"] = dict(motivos)
    out["programas_dict"] = dict(programas.most_common(5))
    return out


def _br(x: float, casas: int = 1) -> str:
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resumo_texto(a: dict, nivel: str = "periodo") -> str:
    """O que ocorreu no período, a partir de uma linha combinada."""
    partes: list[str] = []
    if a.get("cpu_c_n"):
        t = f"CPU {_br(a['cpu_c_med'])} °C em média (mín {_br(a['cpu_c_min'])} · máx {_br(a['cpu_c_max'])}"
        if a.get("pico_ts"):
            fmt = "%H:%M" if nivel in ("minuto", "hora") else "%d/%m %H:%M"
            t += f" às {time.strftime(fmt, time.localtime(a['pico_ts']))}"
        partes.append(t + ").")
    total_z = sum(a.get(f"z_{z}") or 0 for z in ZONAS)
    if total_z:
        z = " · ".join(f"{NOME_ZONA[k]} {round(100 * (a.get(f'z_{k}') or 0) / total_z)}%"
                       for k in ZONAS if a.get(f"z_{k}"))
        partes.append(f"Tempo por zona: {z}.")
    motivos = a.get("motivos_dict") or {}
    if motivos:
        top = sorted(motivos.items(), key=lambda kv: -kv[1])[:3]
        partes.append("Motivos de aquecimento: " + ", ".join(f"{rotulo_de(k)} ({v} min)" for k, v in top) + ".")
    elif a.get("cpu_c_n"):
        partes.append("Nenhum motivo de aquecimento registrado.")
    programas = a.get("programas_dict") or {}
    if programas:
        nome, qtd = max(programas.items(), key=lambda kv: kv[1])
        partes.append(f"Programa que mais apareceu: {nome} ({qtd} min).")
    if a.get("ventoinha_rpm_n"):
        partes.append(f"Ventoinha: média {_br(a['ventoinha_rpm_med'], 0)} RPM (máx {_br(a['ventoinha_rpm_max'], 0)}).")
    if a.get("uso_cpu_n"):
        partes.append(f"Uso da CPU: média {_br(a['uso_cpu_med'], 0)}%.")
    if a.get("descartadas"):
        partes.append(f"{a['descartadas']} leituras descartadas por estarem paradas.")
    if a.get("minutos") and nivel != "minuto":
        partes.append(f"Base: {a['minutos']} min medidos.")
    return " ".join(partes) if partes else "Sem dados neste período."


# ---------------- banco ----------------
def _ddl_stats() -> str:
    return ", ".join(f"{c} REAL" if not c.endswith("_n") else f"{c} INTEGER DEFAULT 0" for c in _colunas_stats())


class Historico:
    def __init__(self, caminho: Path | str | None = None, retencao_dias: int = 365) -> None:
        if caminho is None:
            pasta = pasta_dados()
            pasta.mkdir(parents=True, exist_ok=True)
            caminho = pasta / "historico.db"
        self.caminho = Path(caminho) if str(caminho) != ":memory:" else caminho
        self.retencao_dias = retencao_dias
        self.con = sqlite3.connect(str(caminho))
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA synchronous=NORMAL")
        self._criar()
        self._ultima_limpeza = 0.0

    def _criar(self) -> None:
        z = ", ".join(f"z_{k} INTEGER DEFAULT 0" for k in ZONAS)
        self.con.executescript(f"""
            CREATE TABLE IF NOT EXISTS minuto (
                ts INTEGER PRIMARY KEY, amostras INTEGER, descartadas INTEGER, fonte TEXT, zona TEXT,
                plano TEXT, estado_max_ac INTEGER, motivo_principal TEXT, categoria_motivo TEXT,
                programa_principal TEXT, programa_pct REAL, pico_ts INTEGER, {z}, {_ddl_stats()});
            CREATE TABLE IF NOT EXISTS minuto_motivo (
                ts INTEGER NOT NULL, motivo TEXT NOT NULL, PRIMARY KEY (ts, motivo));
            CREATE INDEX IF NOT EXISTS ix_minuto_motivo ON minuto_motivo (motivo);
            CREATE TABLE IF NOT EXISTS agregado (
                nivel TEXT NOT NULL, ts INTEGER NOT NULL, minutos INTEGER, amostras INTEGER, descartadas INTEGER,
                pico_ts INTEGER, {z}, motivos_json TEXT, programas_json TEXT, resumo TEXT, {_ddl_stats()},
                PRIMARY KEY (nivel, ts));
            PRAGMA user_version = {VERSAO_ESQUEMA};""")
        self.con.commit()

    # ---------- escrita ----------
    def gravar_minuto(self, reg: dict) -> None:
        cols = ["ts", "amostras", "descartadas", "fonte", "zona", "plano", "estado_max_ac", "motivo_principal",
                "categoria_motivo", "programa_principal", "programa_pct", "pico_ts",
                *(f"z_{k}" for k in ZONAS), *_colunas_stats()]
        with self.con:
            self.con.execute(f"INSERT OR REPLACE INTO minuto ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                             [reg.get(c) for c in cols])
            self.con.execute("DELETE FROM minuto_motivo WHERE ts = ?", (reg["ts"],))
            self.con.executemany("INSERT INTO minuto_motivo (ts, motivo) VALUES (?, ?)",
                                 [(reg["ts"], m) for m in reg.get("motivos", [])])
            self._atualizar_agregados(reg["ts"])

    def _linhas_minuto(self, inicio: int, fim: int) -> list[dict]:
        motivos: dict[int, dict] = {}
        for r in self.con.execute("SELECT ts, motivo FROM minuto_motivo WHERE ts >= ? AND ts < ?", (inicio, fim)):
            motivos.setdefault(r["ts"], {})[r["motivo"]] = 1
        out = []
        for r in self.con.execute("SELECT * FROM minuto WHERE ts >= ? AND ts < ? ORDER BY ts", (inicio, fim)):
            l = dict(r)
            l["minutos"] = 1
            l["motivos_dict"] = motivos.get(l["ts"], {})
            l["programas_dict"] = {l["programa_principal"]: 1} if l["programa_principal"] else {}
            out.append(l)
        return out

    def _linhas_agregado(self, nivel: str, inicio: int, fim: int) -> list[dict]:
        out = []
        for r in self.con.execute("SELECT * FROM agregado WHERE nivel = ? AND ts >= ? AND ts < ? ORDER BY ts",
                                  (nivel, inicio, fim)):
            l = dict(r)
            l["motivos_dict"] = json.loads(l["motivos_json"] or "{}")
            l["programas_dict"] = json.loads(l["programas_json"] or "{}")
            out.append(l)
        return out

    def linhas(self, nivel: str, inicio: int, fim: int) -> list[dict]:
        """Linhas completas do nível entre `inicio` e `fim` (períodos que se sobrepõem ao intervalo)."""
        if nivel == "minuto":
            return self._linhas_minuto(inicio, fim)
        return self._linhas_agregado(nivel, inicio_periodo(inicio, nivel), fim)

    def _gravar_agregado(self, nivel: str, ts: int, fontes: list[dict]) -> None:
        if not fontes:
            return
        a = combinar(fontes)
        resumo = resumo_texto(a, nivel)
        cols = ["nivel", "ts", "minutos", "amostras", "descartadas", "pico_ts", *(f"z_{k}" for k in ZONAS),
                "motivos_json", "programas_json", "resumo", *_colunas_stats()]
        a.update({"nivel": nivel, "ts": ts, "resumo": resumo,
                  "motivos_json": json.dumps(a["motivos_dict"]), "programas_json": json.dumps(a["programas_dict"])})
        self.con.execute(f"INSERT OR REPLACE INTO agregado ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                         [a.get(c) for c in cols])

    def _atualizar_agregados(self, ts: int) -> None:
        """Recalcula hora, dia, semana e mês que contêm `ts` (idempotente; poucas dezenas de linhas)."""
        h = inicio_periodo(ts, "hora")
        self._gravar_agregado("hora", h, self._linhas_minuto(h, fim_periodo(h, "hora")))
        d = inicio_periodo(ts, "dia")
        self._gravar_agregado("dia", d, self._linhas_agregado("hora", d, fim_periodo(d, "dia")))
        for nivel in ("semana", "mes"):
            ini = inicio_periodo(ts, nivel)
            self._gravar_agregado(nivel, ini, self._linhas_agregado("dia", ini, fim_periodo(ini, nivel)))

    def limpar(self, agora: float | None = None, forcar: bool = False) -> int:
        """Apaga minutos além da retenção (no máximo uma vez por dia). Resumos ficam. Devolve minutos apagados."""
        agora = time.time() if agora is None else agora
        if not forcar and agora - self._ultima_limpeza < 86400:
            return 0
        self._ultima_limpeza = agora
        limite = int(agora - self.retencao_dias * 86400)
        with self.con:
            apagados = self.con.execute("DELETE FROM minuto WHERE ts < ?", (limite,)).rowcount
            self.con.execute("DELETE FROM minuto_motivo WHERE ts < ?", (limite,))
        return apagados

    # ---------- leitura ----------
    def serie(self, var: str, inicio: int, fim: int, nivel: str) -> list[dict]:
        """Pontos para o gráfico: ts, min, max, med, dp, n, motivo (principal), pico_ts, zona e resumo."""
        if var not in VARIAVEIS or nivel not in NIVEIS:
            raise ValueError("variável ou nível inválido")
        pontos = []
        for l in self.linhas(nivel, inicio, fim):
            if not l.get(f"{var}_n"):
                continue
            motivos = l.get("motivos_dict") or {}
            motivo = l.get("motivo_principal") or (max(motivos, key=motivos.get) if motivos else None)
            pontos.append({"ts": l["ts"], "min": l[f"{var}_min"], "max": l[f"{var}_max"], "med": l[f"{var}_med"],
                           "dp": l[f"{var}_dp"], "n": l[f"{var}_n"], "motivo": motivo, "pico_ts": l.get("pico_ts"),
                           "resumo": l.get("resumo") or resumo_texto(combinar([l]), nivel)})
        return pontos

    def resumir(self, inicio: int, fim: int, nivel: str) -> str:
        linhas = self.linhas(nivel, inicio, fim)
        return resumo_texto(combinar(linhas), "periodo") if linhas else "Sem dados neste período."

    def primeiro_ts(self) -> int | None:
        """Início do dado mais antigo (os resumos por hora duram mais que os minutos)."""
        r = self.con.execute("SELECT MIN(ts) FROM agregado WHERE nivel = 'hora'").fetchone()[0]
        m = self.con.execute("SELECT MIN(ts) FROM minuto").fetchone()[0]
        candidatos = [x for x in (r, m) if x is not None]
        return min(candidatos) if candidatos else None

    def contagem(self) -> dict[str, int]:
        c = {"minuto": self.con.execute("SELECT COUNT(*) FROM minuto").fetchone()[0]}
        for r in self.con.execute("SELECT nivel, COUNT(*) AS n FROM agregado GROUP BY nivel"):
            c[r["nivel"]] = r["n"]
        return c

    def fechar(self) -> None:
        try:
            self.con.close()
        except Exception:
            pass


class Gravador:
    """Liga as leituras do app ao acumulador do minuto e ao banco. Nunca levanta erro para o app."""

    def __init__(self, historico: Historico, zona_fn, salvar_programas: bool = True) -> None:
        self.h = historico
        self.zona_fn = zona_fn
        self.salvar_programas = salvar_programas
        self.acc: AcumuladorMinuto | None = None
        self.erro = ""
        self._ultimo_diag = 0.0

    def _minuto(self, agora: float) -> AcumuladorMinuto:
        ts = int(agora // 60 * 60)
        if self.acc is not None and self.acc.ts != ts:
            self.fechar()
        if self.acc is None:
            self.acc = AcumuladorMinuto(ts)
        return self.acc

    def amostra(self, agora: float, cpu_c: float | None, fonte: str | None, parada: bool, gpu_c=None,
                soc_c=None, clk_mhz=None, rpm=None) -> None:
        try:
            acc = self._minuto(agora)
            acc.amostras += 1
            if parada:
                acc.descartadas += 1
            elif cpu_c is not None:
                acc.valor("cpu_c", cpu_c, agora)
                if fonte:
                    acc.fontes[fonte] += 1
            acc.valor("gpu_c", gpu_c)
            acc.valor("soc_c", soc_c)
            acc.valor("clk_mhz", clk_mhz)
            acc.valor("ventoinha_rpm", rpm)
        except Exception as e:
            self.erro = f"{type(e).__name__}: {e}"

    def diagnostico(self, agora: float, retrato, causas: list) -> None:
        """Uma coleta nova do diagnóstico (use uma vez por `retrato.coletado_em`)."""
        if retrato.coletado_em == self._ultimo_diag:
            return
        self._ultimo_diag = retrato.coletado_em
        try:
            acc = self._minuto(agora)
            acc.valor("uso_cpu", retrato.uso_cpu)
            acc.valor("bateria_pct", retrato.bateria)
            if retrato.na_tomada is not None:
                acc.valor("tomada", 1.0 if retrato.na_tomada else 0.0)
            if retrato.plano_energia:
                acc.planos[retrato.plano_energia] += 1
            if retrato.estado_max_ac is not None:
                acc.estado_max = retrato.estado_max_ac
            motivos = [c.motivo for c in causas if c.motivo is not None]
            for m in motivos:
                acc.motivos[m.value] += 1
            if motivos:
                acc.principais[motivos[0].value] += 1
            if self.salvar_programas and retrato.processos:
                nome, pct = retrato.processos[0]
                acc.programas[nome] += 1
                acc.pct_programa[nome] = max(acc.pct_programa.get(nome, 0.0), pct)
        except Exception as e:
            self.erro = f"{type(e).__name__}: {e}"

    def fechar(self) -> None:
        """Grava o minuto em curso (ao virar o minuto, pausar ou sair)."""
        acc, self.acc = self.acc, None
        if acc is None or acc.vazio():
            return
        try:
            self.h.gravar_minuto(acc.fechar(self.zona_fn))
            self.h.limpar()
        except Exception as e:
            self.erro = f"{type(e).__name__}: {e}"


__all__ = ["VARIAVEIS", "Historico", "Gravador", "AcumuladorMinuto", "combinar", "resumo_texto", "Motivo"]
