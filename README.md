# Análise de Dados de Enchentes do INCT SiMAI

Projeto extensionista da disciplina Coleta, Preparação e Análise de Dados (PUCRS). O dashboard tem duas telas:

1. **Tela 1 — Simulação do INCT:** se o Guaíba chegar a X metros, quais bairros e quantas pessoas são afetados?
2. **Tela 2 — Bases da equipe:** como o nível do Guaíba variou ao longo dos anos, com que frequência passou da cota de inundação e como evoluíram os gastos estaduais com prevenção de enchentes?

**Grupo:** João Vitor Baldi e Marcelo Daronco Ribas

**Dashboard:** https://projetoext20262-betxb7u5qgwssczbv5gwvv.streamlit.app/

## Como rodar

```bash
pip install -r requirements.txt
```

### 1. Coleta (opcional: os dados brutos já estão no repositório)

```bash
python scripts/coleta_ana_hidroweb.py
```

A API da ANA exige usuário e senha. Crie um arquivo `.env` na raiz do projeto (ele está no `.gitignore` e **nunca** deve ser commitado):

```
ANA_IDENTIFICADOR=seu_usuario
ANA_SENHA=sua_senha
```

### 2. Limpeza

```bash
python scripts/limpeza_inct.py
python scripts/limpeza_ana.py
```

### 3. Gastos do Estado com prevenção (Portal da Transparência RS)

Os arquivos de despesas são grandes e por isso não estão no repositório (`dados_<ANO>/`, `dados_tratados/`, `resultados/` e `validacao/` estão no `.gitignore`). O resumo anual que o dashboard usa, `dados/processados/gastos_prevencao_anual.csv`, está versionado. Para refazê-lo:

1. Baixe os ZIPs de **Despesas do Estado** de 2020 a 2026 em [Dados abertos](https://www.transparencia.rs.gov.br/dados-abertos/) do Portal da Transparência RS (coleta usada no dashboard: 09/11/2026) e coloque os de cada ano em `dados_<ANO>/` na raiz do projeto, por exemplo `dados_2024/`.
2. Para cada ano, ajuste `ANO` em `scripts/config.py` e rode `python scripts/coletar_dados.py`. O script filtra as despesas ligadas a enchentes e grava `dados_tratados/despesas_enchentes_<ANO>.csv`.
3. Rode a listagem e a classificação das ações orçamentárias:

```bash
python scripts/listar_acoes.py
python scripts/classificar_acoes.py
```

O `classificar_acoes.py` separa os pagamentos em obras de prevenção, estudos e projetos e transferências para proteção, mostra as conferências (valores inválidos, negativos e duplicados) e grava o resumo anual em `dados/processados/gastos_prevencao_anual.csv`.

Scripts auxiliares de conferência, rodados ano a ano: `analisar_gastos.py`, `selecionar_pagamentos.py`, `validar_pagamentos.py`, `verificar_pagamentos.py` e `verificar_maiores_pagamentos.py`.

### 4. Análise exploratória

Abra `notebooks/eda.ipynb`, que lê apenas os arquivos de `dados/processados/`.

### 5. Dashboard

```bash
streamlit run app/app.py
```

Abre em http://localhost:8501. O app lê apenas os arquivos de `dados/processados/`.

- **Tela 1** (`app/tela1_simulacao.py`): simulação do INCT, com controle do nível de 3,0 m a 10,0 m.
- **Tela 2** (`app/tela2_guaiba.py`): nível do Guaíba ao longo dos anos (ANA), com filtro de período, dias por ano acima das cotas e ligação com a Tela 1 pela cheia de 2024; depois, os gastos estaduais com prevenção de 2020 a 2026, comparados no mesmo gráfico com os dias de inundação de cada ano.

Para publicar no Streamlit Community Cloud, use `app/app.py` como arquivo principal.

## Fontes de dados

| Base | Fonte | Coleta | Dados brutos |
|---|---|---|---|
| Simulação de enchentes por bairro | INCT SiMAI (`data.json`, fornecido pela professora) | — | `dados/originais/inct/` |
| Nível do Guaíba (principal) | ANA, [HidroWebService](https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html) | `scripts/coleta_ana_hidroweb.py` | `dados/originais/ana_hidroweb/` |
| Nível do Guaíba (serviço antigo, para conferência) | ANA, [ServiceANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx) | `scripts/coleta_ana_guaiba.py` | `dados/originais/ana/` |
| Gastos do Estado com prevenção de enchentes | Portal da Transparência RS, [Dados abertos – Despesas do Estado](https://www.transparencia.rs.gov.br/dados-abertos/) | download manual em 09/11/2026 | `dados_<ANO>/` (fora do repositório, ver item 3) |

A data de cada requisição à ANA fica em `coleta_log.csv`, dentro da pasta de dados brutos de cada fonte.

Os dois serviços da ANA trazem os mesmos dados. A API nova é a fonte principal. O serviço antigo, que não exige cadastro, continua no repositório para conferência e como alternativa caso a API fique indisponível. Para limpar os dados dele, use `python scripts/limpeza_ana.py --fonte servico_antigo`; as saídas vão para `dados/processados/servico_antigo/`.

### Estações da ANA usadas

| Código | Estação | Tipo | Período |
|---|---|---|---|
| 87450004 | Cais Mauá C6 | telemétrica (15 min) | 2014–hoje; régua das cotas de alerta (2,55 m) e inundação (3,00 m) |
| 87444000 | Usina do Gasômetro (cheia 2024) | telemétrica | 2024–2025; registrou o pico de 5,35 m |
| 87450020 | Usina do Gasômetro | telemétrica | 2024–hoje |
| 87450000 | Porto Alegre | convencional (diária) | 1929–1980; inclui a cheia de 1941 |
| 87450003 | Praça da Harmonia | convencional (diária) | 1941–2008 |

Cada régua tem o seu próprio zero, por isso os níveis de estações diferentes não são comparados diretamente.

## Estrutura

```
├── dados/
│   ├── originais/      # dados como vieram das fontes
│   └── processados/    # dados limpos usados na EDA e no dashboard
├── scripts/            # coleta, limpeza e classificação dos gastos
├── notebooks/          # EDA
├── app/                # código do dashboard (Streamlit)
└── relatorios/         # relatórios das entregas
```

## Inconsistências encontradas

Cada problema encontrado na limpeza, e o tratamento escolhido, fica registrado em:

- `dados/processados/inct_inconsistencias.csv`: dados do INCT, para a devolutiva.
- `dados/processados/ana_inconsistencias.csv`: dados da ANA.
