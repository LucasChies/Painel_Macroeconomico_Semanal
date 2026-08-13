# 📊 Painel Macroeconômico Semanal

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Repositório-black.svg)](https://github.com/SEU_USUARIO/painel-macroeconomico)

Script em Python que gera automaticamente um **relatório PDF profissional** de acompanhamento macroeconômico.

Ideal para quem quer sair do modo “reação a manchete” e passar a acompanhar o ambiente econômico de forma sistemática e disciplinada.

---

## 🎯 O que o painel monitora

### Brasil
| Indicador              | Fonte          |
|------------------------|----------------|
| IPCA (mensal e 12m)    | BCB / SGS      |
| Selic Meta             | BCB / SGS      |
| Dólar PTAX             | BCB / SGS      |
| Expectativas Focus     | BCB (Olinda)   |

### Estados Unidos
| Indicador              | Fonte          |
|------------------------|----------------|
| CPI e Core PCE         | FRED           |
| Taxa de Desemprego     | FRED           |
| Fed Funds Rate         | FRED           |

### Mercado
| Indicador              | Fonte          |
|------------------------|----------------|
| VIX                    | Yahoo Finance  |
| Petróleo WTI           | Yahoo Finance  |
| DXY (Dollar Index)     | Yahoo Finance  |
| S&P 500                | Yahoo Finance  |

---

## 🖼️ Exemplo de saída

O script gera um PDF limpo e organizado com:

- Cards de resumo no topo
- Tabelas de indicadores
- Expectativas do Boletim Focus
- Gráficos de IPCA, Dólar, VIX e Petróleo

> *(Coloque aqui um print do seu PDF gerado para deixar o README mais atrativo)*

---

## 🚀 Como usar

### 1. Clone o repositório
```bash
git clone https://github.com/SEU_USUARIO/painel-macroeconomico.git
cd painel-macroeconomico

### 2. Chave FRED
Obtenha uma chave gratuita do FRED: https://fred.stlouisfed.org/docs/api/api_key.html
Coloque-a no arquivo main.py
