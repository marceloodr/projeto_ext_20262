"""Limpeza da simulação de enchentes do INCT SiMAI (data.json).

Entrada:  dados/originais/inct/data.json
Saídas:   dados/processados/inct_longo_limpo.csv      (uma linha por nível e bairro)
          dados/processados/inct_inconsistencias.csv  (registro de cada problema e do tratamento)

Uso:
    python scripts/limpeza_inct.py

Inconsistências tratadas (detalhes no registro gerado):
1. Ordem dos bairros diferente em um nível: sem efeito no formato longo, só registrada.
2. `percentage` arredondado sempre para cima e para inteiro (e 2 linhas que nem
   seguem essa regra): recalculado a partir dos prédios, sem arredondar.
3. `affected_population` herda o arredondamento de `percentage`: recalculado.
4. Prédios afetados que caem para zero quando o rio sobe: interpolados.
5. Picos isolados de prédios afetados num único nível: interpolados.
6. Trechos com mais prédios afetados do que em níveis mais altos: limitados ao
   menor valor dos níveis acima (o alagamento não pode diminuir com o rio subindo).
7. Pequenas oscilações restantes (< 1% do bairro): acumulado máximo.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "originais" / "inct" / "data.json"
SAIDA_DADOS = RAIZ / "dados" / "processados" / "inct_longo_limpo.csv"
SAIDA_LOG = RAIZ / "dados" / "processados" / "inct_inconsistencias.csv"

LIMIAR_PICO = 0.10    # pico isolado: > 10% dos prédios do bairro acima dos vizinhos
LIMIAR_BLOCO = 0.05   # trecho alto demais: > 5% dos prédios acima de um nível superior
LIMIAR_PCT = 0.5      # diferença de percentual (p.p.) a partir da qual o arredondamento é registrado

registro = []


def registrar(tipo, bairro, nivel, campo, original, corrigido, tratamento):
    registro.append({"tipo": tipo, "bairro": bairro, "nivel_m": nivel, "campo": campo,
                     "valor_original": original, "valor_corrigido": corrigido,
                     "tratamento": tratamento})


def carregar():
    with open(ENTRADA, encoding="utf-8") as f:
        raw = json.load(f)

    # Ordem dos bairros: comparada com o primeiro nível
    referencia = list(next(iter(raw.values())))
    for nivel, bairros in raw.items():
        if list(bairros) != referencia:
            registrar("ordem_dos_bairros", None, float(nivel.removesuffix("m").replace("_", ".")),
                      None, None, None, "nenhum: o formato longo não depende da ordem")

    # Conjunto de bairros: todos os níveis devem ter os mesmos
    conjuntos = {nivel: set(bairros) for nivel, bairros in raw.items()}
    todos = set().union(*conjuntos.values())
    for nivel, bairros in conjuntos.items():
        for faltando in sorted(todos - bairros):
            registrar("bairro_ausente", faltando, nivel, None, None, None, "verificar")

    df = pd.DataFrame([
        {"nivel_m": float(nivel.removesuffix("m").replace("_", ".")), "bairro": bairro, **valores}
        for nivel, bairros in raw.items()
        for bairro, valores in bairros.items()
    ])
    return df.sort_values(["bairro", "nivel_m"]).reset_index(drop=True)


def checar_constantes(df):
    """total_buildings e population não podem mudar com o nível."""
    for campo in ["total_buildings", "population"]:
        variam = df.groupby("bairro")[campo].nunique()
        for bairro in variam[variam > 1].index:
            registrar("valor_constante_varia", bairro, None, campo, None, None, "verificar")


def corrigir_predios(grupo):
    """Corrige a série de prédios afetados de um bairro, do menor ao maior nível."""
    bairro = grupo.name
    total = grupo["total_buildings"].iloc[0]
    niveis = grupo["nivel_m"].to_numpy()
    original = grupo["affected_buildings"].to_numpy()
    x = original.astype(float)

    # 4. Queda para zero depois de já haver prédios afetados
    ja_afetado = np.maximum.accumulate(x) > 0
    zero = (x == 0) & np.concatenate([[False], ja_afetado[:-1]])
    for i in np.flatnonzero(zero):
        registrar("queda_para_zero", bairro, niveis[i], "affected_buildings",
                  int(original[i]), None, "interpolado entre os níveis vizinhos")

    # 5. Pico isolado: bem acima dos dois vizinhos
    pico = np.zeros(len(x), dtype=bool)
    for i in range(1, len(x) - 1):
        if x[i] - max(x[i - 1], x[i + 1]) > LIMIAR_PICO * total:
            pico[i] = True
            registrar("pico_isolado", bairro, niveis[i], "affected_buildings",
                      int(original[i]), None, "interpolado entre os níveis vizinhos")

    x[zero | pico] = np.nan
    x = pd.Series(x).interpolate(limit_area="inside").round().to_numpy(copy=True)

    # 6. Trecho com mais prédios do que algum nível mais alto (por uma margem grande)
    minimo_acima = np.minimum.accumulate(x[::-1])[::-1]
    alto = x - minimo_acima > LIMIAR_BLOCO * total
    for i in np.flatnonzero(alto):
        registrar("maior_que_nivel_superior", bairro, niveis[i], "affected_buildings",
                  int(original[i]), int(minimo_acima[i]),
                  "limitado ao menor valor dos níveis acima")
    x[alto] = minimo_acima[alto]

    # 7. Pequenas quedas restantes: o alagamento só pode aumentar com o nível
    acumulado = np.maximum.accumulate(x)
    for i in np.flatnonzero(acumulado > x):
        registrar("oscilacao_pequena", bairro, niveis[i], "affected_buildings",
                  int(original[i]), int(acumulado[i]), "acumulado máximo dos níveis abaixo")
    x = acumulado

    # Preenche o valor corrigido no registro das etapas 4 e 5
    for item in registro:
        if item["bairro"] == bairro and item["valor_corrigido"] is None and item["campo"] == "affected_buildings":
            item["valor_corrigido"] = int(x[np.flatnonzero(niveis == item["nivel_m"])[0]])

    return pd.Series(x.astype(int), index=grupo.index)


def recalcular(df):
    df["percentage"] = (df["affected_buildings"] / df["total_buildings"] * 100).round(4)
    df["affected_population"] = (df["population"] * df["percentage"] / 100).round().astype(int)

    # 2 e 3. Compara com o que veio no arquivo (antes das correções de prédios)
    pct_bruto = df["affected_buildings_original"] / df["total_buildings"] * 100
    regra_teto = np.ceil(pct_bruto.round(6))
    for _, linha in df[df["percentage_original"] != regra_teto].iterrows():
        registrar("percentual_fora_da_regra", linha["bairro"], linha["nivel_m"], "percentage",
                  linha["percentage_original"], round(pct_bruto[_], 4),
                  "recalculado: prédios afetados / total × 100")
    diferenca = (df["percentage_original"] - pct_bruto).abs()
    for _, linha in df[(diferenca > LIMIAR_PCT) & (df["percentage_original"] == regra_teto)].iterrows():
        registrar("percentual_arredondado_para_cima", linha["bairro"], linha["nivel_m"], "percentage",
                  linha["percentage_original"], round(pct_bruto[_], 4),
                  "recalculado sem arredondar; affected_population recalculada junto")
    return df


def main():
    df = carregar()
    checar_constantes(df)
    print(f"Linhas carregadas: {len(df)} ({df['nivel_m'].nunique()} níveis × {df['bairro'].nunique()} bairros)")

    for campo in ["affected_buildings", "percentage", "affected_population"]:
        df[f"{campo}_original"] = df[campo]

    df["affected_buildings"] = df.groupby("bairro", group_keys=False)[
        ["nivel_m", "affected_buildings", "total_buildings"]].apply(corrigir_predios)
    df = recalcular(df)

    alterado = df["affected_buildings"] != df["affected_buildings_original"]
    df["predios_corrigidos"] = alterado

    colunas = ["nivel_m", "bairro", "total_buildings", "affected_buildings", "percentage",
               "population", "affected_population", "predios_corrigidos",
               "affected_buildings_original", "percentage_original", "affected_population_original"]
    df = df[colunas].sort_values(["nivel_m", "bairro"])

    SAIDA_DADOS.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA_DADOS, index=False)
    log = pd.DataFrame(registro).sort_values(["tipo", "bairro", "nivel_m"], na_position="first")
    log.to_csv(SAIDA_LOG, index=False)

    print("\nInconsistências registradas:")
    print(log.groupby("tipo").agg(registros=("tipo", "size"), bairros=("bairro", "nunique")).to_string())

    print("\nCidade inteira, antes e depois da limpeza:")
    cidade = df.groupby("nivel_m")[["affected_population_original", "affected_population",
                                     "affected_buildings_original", "affected_buildings"]].sum()
    print(cidade.loc[[3.0, 4.0, 5.0, 5.3, 6.0, 8.0, 10.0]].to_string())
    quedas = (cidade["affected_population"].diff() < 0).sum()
    print(f"\nNíveis em que a população afetada da cidade cai: {quedas}")
    print(f"\nSalvo: {SAIDA_DADOS.relative_to(RAIZ)} e {SAIDA_LOG.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
