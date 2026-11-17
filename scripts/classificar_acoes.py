
from pathlib import Path
import pandas as pd
import unicodedata

BASE = Path(__file__).resolve().parent.parent
ARQUIVO = BASE / "resultados" / "acoes_por_ano.csv"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(
        letra for letra in texto
        if not unicodedata.combining(letra)
    )
    return texto.upper().strip()


def contem(texto, palavras):
    return any(palavra in texto for palavra in palavras)



def classificar(acao):
    nome = normalizar(acao)

    # Outras despesas relacionadas ao enfrentamento das enchentes
    if contem(nome, [
        "ESPACOS CULTURAIS",
        "GESTAO MUSEOLOGICA",
        "INSTITUICOES CULTURAIS",
        "ESPORTE FUTURO",
        "BALADA SEGURA",
        "GESTAO E MANUTENCAO SINE",
        "APOIO ADMINISTRATIVO",
        "MANUTENCAO ORGAO CENTRAL",
        "GESTAO E MANUTENCAO PGA",
        "CAMARAS DE CONSERVACAO DE VACINAS",
        "REFORMA ESTRUTURAL DO PREDIO DA SSP",
        "FORTALECIMENTO DOS CRMS",
    ]):
        return "Outras despesas de enfrentamento"

    # Planejamento urbano relacionado às enchentes
    if "PLANOS DIRETORES" in nome and "ENCHENTE" in nome:
        return "Planejamento urbano - enchentes"


    # Aquisição de aeronaves relacionadas às enchentes
    if "AERONAVES" in nome and "ENCHENTE" in nome:
        return "Equipamentos e estrutura de resposta"

    
    # 1. Estudos e planejamento de proteção
    if contem(nome, [
        "ESTUDOS DE CONCEPCAO",
        "PROJETO CONCEITUAL DE PROTECAO CONTRA CHEIAS",
        "PROJETOS DE ENGENHARIA PARA PROTECAO CONTRA CHEIAS",
        "ESTUDOS DE ALTERNATIVAS E PROJETOS PARA MINIMIZACAO",
    ]):
        return "Estudos e projetos"


    # 2. Sistemas de proteção contra cheias
    # Separados de obras executadas
    if "SPCC" in nome:
        return "Transferências para proteção"

    # 3. Obras e intervenções
    if contem(nome, [
        "DESASSOREAMENTO",
        "DESASSOREAR",
        "MACRO-DRENAGEM",
        "MACRODRENAGEM",
        "DRENAGEM URBANA",
        "CONTENCOES RS",
    ]):
        return "Obras de prevenção"

    # 4. Resposta e recuperação
    if contem(nome, [
        "LAUDOS IMOVEIS",
        "LAUDOS ENCHENTES",
        "RECUPERACAO DE ESTRADAS",
        "RECUPERACAO E MELHORIA DE ESTRADAS",
        "MANUTENCAO ESTRADAS MUNICIPAIS",
        "AUXILIO EMERGENCIAL",
        "REAPARELHAMENTO",
        "BOMBEIROS - ENFRENTAMENTO ENCHENTES",
        "MANUTENCAO CBM - ENFRENTAMENTO",
        "AQUISICAO DE EQUIPAMENTOS PARA O CBM",
        "ACOES HABITACIONAIS - ENFRENTAMENTO",
        "ASSISTENCIA SOCIAL - ENFRENTAMENTO",
        "ESTADIA SOLIDARIA",
        "ACOLHIMENTO INSTITUCIONAL",
        "MEI RS CALAMIDADE",
        "JOVEM APRENDIZ - RECONSTRUCAO",
        "VIGILANCIA AMBIENTAL - ENFRENTAMENTO",
        "VIGILANCIA EM SAUDE DO TRABALHADOR",
        "REDE HOSPITALAR - ENFRENTAMENTO",
        "UNIDADES DE SAUDE - ENFRENTAMENTO",
        "SAUDE MENTAL - ENFRENTAMENTO",
        "VIGILANCIA EPIDEMIOLOGICA - ENFRENTAMENTO",
        "PIAPS - ATENCAO PRIMARIA - ENFRENTAMENTO",
        "COFINANCIAMENTO UNIFICADO - PISO GAUCHO",
        "ABRIGOS - ENFRENTAMENTO",
        "EVENTOS ADVERSOS - ENFRENTAMENTO",
    ]):
        return "Resposta e recuperação"

    # 5. Ações que exigem análise mais detalhada
    if contem(nome, [
        "ENCHENTE",
        "FUNRIGS",
        "PROTECAO CONTRA CHEIAS",
        "CONTENCAO",
        "CONTENCOES",
        "CONVENIOS E CONTRATOS DE REPASSE",
    ]):
        return "Revisar"

    return "Fora do escopo"


df = pd.read_csv(
    ARQUIVO,
    sep=";",
    encoding="utf-8-sig"
)

# Classifica todas as ações
df["Categoria"] = df["Acao"].apply(classificar)

# Organiza o resultado
df = df.sort_values(
    ["Ano", "Categoria", "Quantidade"],
    ascending=[True, True, False]
)

# Atualiza o mesmo arquivo
df.to_csv(
    ARQUIVO,
    sep=";",
    index=False,
    encoding="utf-8-sig"
)

print("\nCLASSIFICAÇÃO CONCLUÍDA!\n")

print("Ações por categoria:")
print(df["Categoria"].value_counts().to_string())

print("\nPagamentos por categoria:")
print(
    df.groupby("Categoria")["Quantidade"]
    .sum()
    .sort_values(ascending=False)
    .to_string()
)

print("\nAções que precisam de revisão:")
revisar = df[df["Categoria"] == "Revisar"]

print(
    revisar[["Ano", "Acao", "Quantidade"]]
    .to_string(index=False)
)

print(f"\nArquivo atualizado: {ARQUIVO}")


print("\nCONFERÊNCIA POR ANO:")
print(
    df.groupby("Ano")["Quantidade"]
    .sum()
    .to_string()
)

print("\nTOTAL GERAL:")
print(df["Quantidade"].sum())


# VALORES FINANCEIROS POR ANO E CATEGORIA

import csv
import sys

csv.field_size_limit(sys.maxsize)

print("\nVALORES POR ANO E CATEGORIA:")

for ano in range(2020, 2027):

    candidatos = [
        BASE / "dados_tratados" / f"despesas_enchentes_{ano}.csv",
        BASE / "dados_tratados" / f"despesas_enchentes_{ano}_completo.csv",
    ]

    arquivo = next(
        (p for p in candidatos if p.exists()),
        None
    )

    if arquivo is None:
        print(f"\n{ano}: arquivo não encontrado.")
        continue

    dados = pd.read_csv(
        arquivo,
        sep=None,
        engine="python",
        dtype=str
    )

    pagamentos = dados[
        dados["FaseGasto"].str.strip() == "Pagamento"
    ].copy()

    pagamentos["Categoria"] = pagamentos["Acao"].apply(classificar)

    # Utiliza a mesma conversão de valores
    # adotada nos scripts anteriores
    valores = pagamentos["Valor"].fillna("").astype(str)

    pagamentos["ValorNumerico"] = pd.to_numeric(
        valores.str.replace(".", "", regex=False)
              .str.replace(",", ".", regex=False),
        errors="coerce"
    )

    # Conferência dos valores financeiros
    valores_invalidos = pagamentos["ValorNumerico"].isna().sum()
    valores_negativos = (pagamentos["ValorNumerico"] < 0).sum()
    valores_zerados = (pagamentos["ValorNumerico"] == 0).sum()

    print(f"\nVALIDAÇÃO FINANCEIRA {ano}:")
    print(f"Pagamentos analisados: {len(pagamentos)}")
    print(f"Valores inválidos: {valores_invalidos}")
    print(f"Valores negativos: {valores_negativos}")
    print(f"Valores zerados: {valores_zerados}")


    # Verificação de registros exatamente duplicados
    duplicados = pagamentos.duplicated(
        subset=dados.columns.tolist(),
        keep="first"
    ).sum()

    print(f"\nDUPLICIDADES {ano}:")
    print(f"Registros exatamente repetidos: {duplicados}")


    # Investigação dos pagamentos negativos
    negativos = pagamentos[
        pagamentos["ValorNumerico"] < 0
    ]

    if not negativos.empty:
        print(f"\nPAGAMENTOS NEGATIVOS {ano}:")

        resumo_negativos = (
            negativos.groupby("Acao")["ValorNumerico"]
            .agg(["count", "sum"])
            .sort_values("sum")
            .head(10)
        )

        print(resumo_negativos.to_string())

        print(
            f"\nTOTAL NEGATIVO {ano}: "
            f"R$ {negativos['ValorNumerico'].sum():,.2f}"
        )

        print("\nHISTÓRICOS DOS 5 MAIORES VALORES NEGATIVOS:")

        amostra = negativos.sort_values(
            "ValorNumerico"
        ).head(5)

        for _, registro in amostra.iterrows():
            print("\n--------------------")
            print("Ação:", registro["Acao"])
            print("Valor:", registro["ValorNumerico"])
            print("Histórico:", registro.get("Historico", "Não disponível"))


    resumo = pagamentos.groupby("Categoria")["ValorNumerico"].sum()

    print(f"\nANO: {ano}")
    print(resumo.to_string())

    print(f"TOTAL: R$ {pagamentos['ValorNumerico'].sum():,.2f}")


    # Maiores ações que ainda precisam de revisão
    pendentes = pagamentos[
        pagamentos["Categoria"] == "Revisar"
    ]

    if not pendentes.empty:
        maiores = (
            pendentes.groupby("Acao")["ValorNumerico"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        print("\n10 MAIORES AÇÕES PARA REVISÃO:")
        for acao, valor in maiores.items():
            print(f"R$ {valor:,.2f} | {acao}")

    
    
    if ano in [2025, 2026]:
        print(f"\nAMOSTRA DE PLANOS DIRETORES {ano}:")

        amostra = pagamentos[
            pagamentos["Acao"].str.contains(
                "Planos Diretores",
                case=False,
                na=False
            )
        ].sort_values(
            "ValorNumerico",
            ascending=False
        ).head(5)

        colunas = [
            "Acao",
            "Orgao",
            "ValorNumerico",
            "Historico"
        ]

        for coluna in amostra.columns:
            if "COMPLEMENTAR" in normalizar(coluna):
                colunas.append(coluna)

        for _, registro in amostra[colunas].iterrows():
            print("\n--------------------")
            for coluna in colunas:
                print(f"{coluna}: {str(registro[coluna]).strip()}")


# CONSOLIDAÇÃO DOS GASTOS DE PREVENÇÃO

categorias_prevencao = [
    "Obras de prevenção",
    "Estudos e projetos",
    "Transferências para proteção"
]

print("\n" + "=" * 55)
print("CONSOLIDAÇÃO ANUAL - PREVENÇÃO DE ENCHENTES")
print("=" * 55)

for ano in range(2020, 2027):
    candidatos = [
        BASE / "dados_tratados" / f"despesas_enchentes_{ano}.csv",
        BASE / "dados_tratados" / f"despesas_enchentes_{ano}_completo.csv"
    ]

    arquivo = next((p for p in candidatos if p.exists()), None)

    if arquivo is None:
        print(f"\n{ano}: arquivo não encontrado")
        continue

    dados = pd.read_csv(
        arquivo,
        sep=";",
        encoding="utf-8-sig",
        dtype=str
    )

    pagamentos = dados[
        dados["FaseGasto"].str.strip() == "Pagamento"
    ].copy()

    pagamentos["Categoria"] = pagamentos["Acao"].apply(classificar)

    pagamentos["ValorNumerico"] = pd.to_numeric(
        pagamentos["Valor"].fillna("")
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )

    prevencao = pagamentos[
        pagamentos["Categoria"].isin(categorias_prevencao)
    ]

    print(f"\nANO {ano}")

    for categoria in categorias_prevencao:
        grupo = prevencao[
            prevencao["Categoria"] == categoria
        ]

        valor = grupo["ValorNumerico"].sum()

        print(
            f"{categoria}: "
            f"{len(grupo)} pagamentos | "
            f"R$ {valor:,.2f}"
        )

    print(
        f"TOTAL SELECIONADO: "
        f"R$ {prevencao['ValorNumerico'].sum():,.2f}"
    )


    
