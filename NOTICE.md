# Avisos de terceiros

O TempCPU é distribuído sob a licença MIT (`LICENSE`). Ele usa as bibliotecas abaixo, instaladas pelo `pip` (não são redistribuídas neste repositório), cada uma com a sua própria licença. Confira a licença exata da versão instalada antes de redistribuir um executável.

| Biblioteca | Uso | Licença (conforme o projeto declara) |
|---|---|---|
| pystray | ícone na bandeja | LGPL-3.0 |
| pywin32 | WMI/COM do Windows | PSF |
| WMI | leitura ACPI/ASUS | MIT |
| psutil | uso de CPU e processos | BSD-3-Clause |
| Pillow | desenho do ícone | HPND |
| six | dependência de pystray | MIT |
| scikit-learn, numpy, scipy, joblib, threadpoolctl | só no Laboratório (ambiente separado) | BSD-3-Clause |

**Atenção ao distribuir um executável:** a LGPL do `pystray` impõe condições (por exemplo, permitir substituir a biblioteca). Há uma tarefa para trocá-lo por chamadas diretas (`docs/TAREFAS.md`, item 5).

Nomes de marcas (AMD, ASUS, Windows, Intel) pertencem aos seus donos e aparecem apenas para descrever compatibilidade. O projeto não é afiliado a eles.
