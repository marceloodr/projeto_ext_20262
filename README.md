# Análise de Dados de Enchentes do INCT SiMAI

Projeto extensionista da disciplina Coleta, Preparação e Análise de Dados (PUCRS). O dashboard tem duas telas:

1. **Tela 1 — Simulação do INCT:** se o Guaíba chegar a X metros, quais bairros e quantas pessoas são afetados?
2. **Tela 2 — Bases da equipe:** como o nível do Guaíba variou ao longo dos anos, com que frequência passou da cota de inundação e como evoluíram os gastos estaduais com prevenção de enchentes?

**Grupo:** João Vitor Baldi e Marcelo Daronco Ribas

**Dashboard:** _link a definir_

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

### 3. Análise exploratória

Abra `notebooks/eda.ipynb`, que lê apenas os arquivos de `dados/processados/`.

## Fontes de dados

| Base | Fonte | Coleta | Dados brutos |
|---|---|---|---|
| Simulação de enchentes por bairro | INCT SiMAI (`data.json`, fornecido pela professora) | — | `dados/originais/inct/` |
| Nível do Guaíba (principal) | ANA, [HidroWebService](https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html) | `scripts/coleta_ana_hidroweb.py` | `dados/originais/ana_hidroweb/` |
| Nível do Guaíba (serviço antigo, para conferência) | ANA, [ServiceANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx) | `scripts/coleta_ana_guaiba.py` | `dados/originais/ana/` |

A data de cada requisição fica em `coleta_log.csv`, dentro da pasta de dados brutos de cada fonte.

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
├── scripts/            # coleta e limpeza
├── notebooks/          # EDA
└── relatorios/         # relatórios das entregas
```

## Inconsistências encontradas

Cada problema encontrado na limpeza, e o tratamento escolhido, fica registrado em:

- `dados/processados/inct_inconsistencias.csv`: dados do INCT, para a devolutiva.
- `dados/processados/ana_inconsistencias.csv`: dados da ANA.
