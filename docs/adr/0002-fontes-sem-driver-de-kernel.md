# ADR 0002 — Fontes sem driver de kernel (AMD ADL + ASUS ATK), ACPI como último recurso

**Data:** 2026-10-23 · **Status:** aceita · substitui a ordem de fontes do ADR 0001

## Contexto
- Regra do usuário: **nada instalado no núcleo do Windows**. A sentinela reprovou o LibreHardwareMonitor (WinRing0 vulnerável; PawnIO ainda é driver de kernel, com serviço persistente).
- Medido em 2026-10-22/23 (ASUS, Ryzen 7 4800HS):
  - ACPI `THRM_0`: o Windows só relê quando o firmware avisa (`ThermalStamp` = 17 desde o boot). Ficou em 86,1 °C durante 45 s de carga total; a ventoinha subiu de 2.800 para 3.700 RPM. Limites do firmware: redução de desempenho a 101,1 °C e desligamento a 103,1 °C.
  - ASUS ATK WMI (`AsusAtkWmi_WMNB.DSTS`): os IDs de temperatura (0x00120094, 0x00120097, 0x00110011) devolvem 0xFFFFFFFE (não suportado neste modelo). A ventoinha da CPU (0x00110013) funciona.
  - AMD ADL (`System32\atiadlxx.dll`, assinada pela Microsoft como driver homologado): `ADL2_New_QueryPMLogData_Get` expõe TEMP_CPU, TEMP_GFX, TEMP_SOC, TEMP_EDGE e a frequência da CPU, atualizados a cada segundo. Sob carga, a CPU foi de 54 para 79 °C em 2 s e voltou a 58 °C ao fim.

## Decisão
1. CPU: **AMD ADL** → LibreHardwareMonitor (só se o usuário já o tiver aberto; o app não o instala nem recomenda) → ACPI.
2. GPU: AMD ADL (GFX, ou EDGE se não houver) → LHM → `nvidia-smi` por caminho fixo em System32.
3. Ventoinha: ASUS ATK, **somente `DSTS`**, IDs fixos em `asus.py` (`IDS_LEITURA`), nunca vindos de configuração. Há teste garantindo que nenhum outro método é chamado. Falha = sem ventoinha, em silêncio.
4. ACPI: `DetectorParada`. Valor e `ThermalStamp` iguais por `PARADA_MIN` = "leitura parada". O número fica cinza, o ícone mostra "--" e o diagnóstico não tira conclusões dele.
5. Zona crítica (`DANO_C=auto`): o limite de redução de desempenho do firmware. A linha "desliga" vem do limite crítico do firmware.
6. A DLL da AMD é carregada só pelo caminho absoluto (evita sequestro de DLL).

## Consequências
- Temperatura real e ao vivo sem nenhum driver novo neste notebook. Em PCs Intel ou sem AMD, volta-se à ACPI, que pode ficar parada, e isso é mostrado ao usuário.
- O sensor TEMP_CPU da ADL não foi comparado ao Tctl lido diretamente (exigiria driver de kernel). O comportamento sob carga é coerente com o do núcleo.
- Os índices do enum ADL_PMLOG vêm do `adl_defines.h`. Se a AMD mudar o enum, `interpretar()` descarta valores fora de 0–150 °C.
