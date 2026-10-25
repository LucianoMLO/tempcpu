# ADR 0001 — Fonte da temperatura

**Data:** 2026-10-22 · **Status:** substituída em parte pelo [ADR 0002](0002-fontes-sem-driver-de-kernel.md) (ordem das fontes)

## Contexto
O Windows não tem API oficial para a temperatura do núcleo. Opções:

| Fonte | Precisão | Custo |
|---|---|---|
| WMI `MSAcpi_ThermalZoneTemperature` | zona térmica da placa; atualiza em degraus | nada a instalar; exige administrador |
| LibreHardwareMonitor (WMI `root/LibreHardwareMonitor`) | núcleo real (Tctl/Tdie, Package) | programa de terceiro aberto, com driver de kernel |
| Biblioteca LHM embutida (.NET) | igual ao anterior | exige .NET, pythonnet e o driver dentro do app |

No notebook de referência (Ryzen 7 4800HS) a zona ACPI respondeu (`THRM_0`), mas ficou minutos no mesmo valor (86,1 °C).

## Decisão
Tentar o LibreHardwareMonitor primeiro, se estiver aberto; senão, usar a ACPI. Não embutir driver no app.

## Consequências
- Funciona sem instalar nada, mas sem o LHM a leitura é aproximada e lenta para reagir.
- Instalar o LHM é decisão do usuário (programa de terceiro com driver de kernel: passar pela `sentinela` antes).
- A leitura via LHM ainda não foi testada neste computador (LHM não instalado).
