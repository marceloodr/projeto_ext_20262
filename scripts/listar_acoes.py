
from pathlib import Path
import pandas as pd
import csv
import sys

csv.field_size_limit(sys.maxsize)

BASE = Path(__file__).resolve().parent.parent
PASTA_DADOS = BASE / "dados_tratados"
PASTA_RESULTADOS = BASE / "resultados"

PASTA_RESULTADOS.mkdir(exist_ok=True)

anos = range(2020, 2027)
resumos = []

for ano in anos:
    candidatos = [
        PASTA_DADOS / f"despesas_enchentes_{ano}.csv",
        PASTA_DADOS / f"despesas_enchentes_{ano}_completo.csv",
    ]

    arquivo = next((p for p in candidatos if p.exists()), None)

    if arquivo is None:
        print(f"Arquivo de {ano} não encontrado.")
        continue

    df = pd.read_csv(arquivo, sep=None, engine="python", dtype=str)

    pagamentos = df[df["FaseGasto"].str.strip() == "Pagamento"].copy()

    resumo = (
        pagamentos.groupby("Acao", dropna=False)
        .size()
        .reset_index(name="Quantidade")
    )

    resumo.insert(0, "Ano", ano)
    resumos.append(resumo)

    print(f"{ano}: {len(pagamentos)} pagamentos encontrados.")

if resumos:
    resultado = pd.concat(resumos, ignore_index=True)

    resultado = resultado.sort_values(
        ["Ano", "Quantidade"],
        ascending=[True, False]
    )

    destino = PASTA_RESULTADOS / "acoes_por_ano.csv"

    resultado.to_csv(
        destino,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print(f"\nArquivo gerado: {destino}")
    print(f"Total de linhas no resumo: {len(resultado)}")
else:
    print("Nenhum arquivo encontrado.")
