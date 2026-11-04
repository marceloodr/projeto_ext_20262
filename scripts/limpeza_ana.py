"""Limpeza das séries de nível do Guaíba coletadas da ANA.

Entrada:  dados/originais/ana/ (gerado por scripts/coleta_ana_guaiba.py)
Saídas:   dados/processados/ana_telemetria_15min.csv.gz   leituras de 15 min válidas
          dados/processados/ana_nivel_diario.csv          resumo diário por estação telemétrica
          dados/processados/ana_historico_diario.csv      cotas diárias das estações convencionais
          dados/processados/ana_estacoes.csv              metadados das estações
          dados/processados/ana_inconsistencias.csv       registro de cada problema e do tratamento

Uso:
    python scripts/limpeza_ana.py

Cada estação (régua) é mantida separada, com o nível em metros na sua própria
referência. Não há ajuste entre réguas: valores de estações diferentes não são
comparáveis diretamente.

Inconsistências tratadas (detalhes no registro gerado):
1. Leituras com data posterior à coleta: descartadas.
2. Leituras sem nível: descartadas.
3. Picos isolados (leitura > 30 cm distante da mediana das 3 h em volta): descartados.
4. Sensor travado (variação <= 1 cm no dia por 3 dias seguidos ou mais): dias descartados.
5. Níveis negativos: mantidos, porque o nível é relativo ao zero da régua e a
   outra régua do Gasômetro registra os mesmos instantes com valores positivos.
6. Série histórica com dado bruto e consistido para o mesmo mês: fica o consistido.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ORIGINAIS = RAIZ / "dados" / "originais" / "ana"
PROCESSADOS = RAIZ / "dados" / "processados"

JANELA_PICO = "3h"
LIMIAR_PICO_CM = 30
LIMIAR_TRAVADO_CM = 1
DIAS_TRAVADO = 3

registro = []


def registrar(tipo, codigo, leituras, inicio, fim, tratamento, detalhe=None):
    registro.append({"tipo": tipo, "codigo": codigo, "leituras": leituras, "inicio": inicio,
                     "fim": fim, "detalhe": detalhe, "tratamento": tratamento})


def ler_tabela(arquivo, tag):
    """Lê as linhas <tag> de um XML DataSet do serviço da ANA em um DataFrame."""
    linhas = []
    for _, elem in ET.iterparse(arquivo):
        if elem.tag == tag:
            linhas.append({filho.tag: (filho.text or "").strip() or None for filho in elem})
            elem.clear()
    return pd.DataFrame(linhas)


def carregar_estacoes():
    inventario = pd.concat([ler_tabela(f, "Table") for f in sorted((ORIGINAIS / "inventario").glob("*.xml"))])
    colunas = {"Codigo": "codigo", "Nome": "estacao", "RioNome": "rio", "ResponsavelSigla": "responsavel",
               "Latitude": "lat", "Longitude": "lon", "PeriodoEscalaInicio": "escala_inicio",
               "PeriodoEscalaFim": "escala_fim", "Operando": "operando"}
    estacoes = inventario[list(colunas)].rename(columns=colunas)
    estacoes["codigo"] = estacoes["codigo"].astype(int)
    estacoes["tipo"] = estacoes["codigo"].map(
        lambda c: "telemetrica" if any((ORIGINAIS / "telemetria").glob(f"{c}_*.xml")) else "convencional")
    return estacoes.sort_values("codigo").reset_index(drop=True)


def limpar_telemetria(data_coleta):
    partes = [ler_tabela(f, "DadosHidrometereologicos") for f in sorted((ORIGINAIS / "telemetria").glob("*.xml"))]
    tele = pd.concat([p for p in partes if not p.empty], ignore_index=True)
    tele = pd.DataFrame({
        "codigo": tele["CodEstacao"].astype(int),
        "data_hora": pd.to_datetime(tele["DataHora"]),
        "nivel_cm": pd.to_numeric(tele["Nivel"]),
        "chuva_mm": pd.to_numeric(tele["Chuva"]),
    }).sort_values(["codigo", "data_hora"])
    print(f"Leituras brutas: {len(tele)}")

    duplicadas = tele.duplicated(["codigo", "data_hora"])
    if duplicadas.any():
        for codigo, g in tele[duplicadas].groupby("codigo"):
            registrar("leitura_duplicada", codigo, len(g), g["data_hora"].min(), g["data_hora"].max(),
                      "descartada (fica a primeira)")
        tele = tele[~duplicadas]

    # 1. Data no futuro
    futuras = tele["data_hora"] > data_coleta
    for codigo, g in tele[futuras].groupby("codigo"):
        registrar("data_posterior_a_coleta", codigo, len(g), g["data_hora"].min(), g["data_hora"].max(),
                  "descartada", f"coleta em {data_coleta:%Y-%m-%d %H:%M}")
    tele = tele[~futuras]

    # 2. Sem nível
    vazias = tele["nivel_cm"].isna()
    for codigo, g in tele[vazias].groupby("codigo"):
        registrar("nivel_vazio", codigo, len(g), g["data_hora"].min(), g["data_hora"].max(), "descartada")
    tele = tele[~vazias]

    limpas = []
    for codigo, g in tele.groupby("codigo"):
        serie = g.set_index("data_hora")["nivel_cm"]

        # 3. Picos isolados
        mediana = serie.rolling(JANELA_PICO, center=True).median()
        pico = (serie - mediana).abs() > LIMIAR_PICO_CM
        for instante in serie.index[pico]:
            registrar("pico_isolado", codigo, 1, instante, instante, "descartada",
                      f"{serie[instante]:.0f} cm, mediana em volta {mediana[instante]:.0f} cm")
        g = g[~pico.to_numpy()]

        # 4. Sensor travado: dias com variação mínima, em sequência
        dia = g["data_hora"].dt.normalize()
        amplitude = g.groupby(dia)["nivel_cm"].agg(lambda s: s.max() - s.min())
        parado = amplitude <= LIMIAR_TRAVADO_CM
        sequencia = (parado != parado.shift()).cumsum()
        dias_travados = []
        for _, bloco in amplitude[parado].groupby(sequencia[parado]):
            if len(bloco) >= DIAS_TRAVADO:
                valor = g.loc[dia.isin(bloco.index), "nivel_cm"].median()
                registrar("sensor_travado", codigo, int(dia.isin(bloco.index).sum()), bloco.index.min(),
                          bloco.index.max(), "dias descartados", f"{len(bloco)} dias parados em ~{valor:.0f} cm")
                dias_travados.extend(bloco.index)
        g = g[~dia.isin(dias_travados).to_numpy()]

        # 5. Negativos: só registro
        negativos = g[g["nivel_cm"] < 0]
        if len(negativos):
            registrar("nivel_negativo", codigo, len(negativos), negativos["data_hora"].min(),
                      negativos["data_hora"].max(), "mantida: nível relativo ao zero da régua",
                      f"mínimo {negativos['nivel_cm'].min():.0f} cm")
        limpas.append(g)

    tele = pd.concat(limpas, ignore_index=True)
    tele["nivel_m"] = tele["nivel_cm"] / 100
    print(f"Leituras válidas: {len(tele)}")
    return tele[["codigo", "data_hora", "nivel_m", "chuva_mm"]]


def resumir_por_dia(tele):
    diario = (tele.assign(data=tele["data_hora"].dt.date)
              .groupby(["codigo", "data"])
              .agg(nivel_min_m=("nivel_m", "min"), nivel_medio_m=("nivel_m", "mean"),
                   nivel_max_m=("nivel_m", "max"), chuva_mm=("chuva_mm", "sum"),
                   leituras=("nivel_m", "size"))
              .reset_index())
    diario["nivel_medio_m"] = diario["nivel_medio_m"].round(3)
    return diario


def limpar_historico():
    hist = pd.concat([ler_tabela(f, "SerieHistorica") for f in sorted((ORIGINAIS / "serie_historica").glob("*.xml"))],
                     ignore_index=True)
    hist["codigo"] = hist["EstacaoCodigo"].astype(int)
    hist["mes"] = pd.to_datetime(hist["DataHora"]).dt.to_period("M").dt.to_timestamp()
    hist["consistencia"] = hist["NivelConsistencia"].astype(int)

    # 6. Mesmo mês bruto (1) e consistido (2): fica o consistido
    consistidos = set(zip(hist.loc[hist["consistencia"] == 2, "codigo"], hist.loc[hist["consistencia"] == 2, "mes"]))
    tem_consistido = pd.Series([(c, m) in consistidos for c, m in zip(hist["codigo"], hist["mes"])], index=hist.index)
    for codigo, g in hist[tem_consistido & (hist["consistencia"] == 1)].groupby("codigo"):
        registrar("mes_bruto_e_consistido", codigo, len(g), g["mes"].min(), g["mes"].max(),
                  "fica a versão consistida", f"{len(g)} meses")
    hist = hist.sort_values("consistencia").drop_duplicates(["codigo", "mes"], keep="last")

    dias = [f"Cota{d:02d}" for d in range(1, 32)]
    longo = hist.melt(id_vars=["codigo", "mes", "consistencia"], value_vars=dias, var_name="dia", value_name="cota_cm")
    longo["data"] = longo["mes"] + pd.to_timedelta(longo["dia"].str[4:].astype(int) - 1, unit="D")
    longo = longo[longo["data"].dt.month == longo["mes"].dt.month]  # descarta dias como 30/02
    longo["nivel_m"] = pd.to_numeric(longo["cota_cm"]) / 100
    longo = longo.dropna(subset=["nivel_m"])
    longo["consistencia"] = longo["consistencia"].map({1: "bruto", 2: "consistido"})
    return longo[["codigo", "data", "nivel_m", "consistencia"]].sort_values(["codigo", "data"])


def main():
    data_coleta = pd.read_csv(ORIGINAIS / "coleta_log.csv", parse_dates=["data_coleta"])["data_coleta"].max()
    PROCESSADOS.mkdir(parents=True, exist_ok=True)

    estacoes = carregar_estacoes()
    tele = limpar_telemetria(data_coleta)
    diario = resumir_por_dia(tele)
    historico = limpar_historico()

    # Período real dos dados x período informado no inventário
    for codigo, g in historico.groupby("codigo"):
        fim_inventario = estacoes.loc[estacoes["codigo"] == codigo, "escala_fim"].iloc[0]
        if fim_inventario and g["data"].max() > pd.Timestamp(fim_inventario):
            registrar("periodo_alem_do_inventario", codigo, int((g["data"] > pd.Timestamp(fim_inventario)).sum()),
                      pd.Timestamp(fim_inventario), g["data"].max(), "mantida e documentada",
                      "o inventário indica o fim da escala antes da última leitura")

    estacoes.to_csv(PROCESSADOS / "ana_estacoes.csv", index=False)
    tele.to_csv(PROCESSADOS / "ana_telemetria_15min.csv.gz", index=False)
    diario.to_csv(PROCESSADOS / "ana_nivel_diario.csv", index=False)
    historico.to_csv(PROCESSADOS / "ana_historico_diario.csv", index=False)
    log = pd.DataFrame(registro)
    log.to_csv(PROCESSADOS / "ana_inconsistencias.csv", index=False)

    print("\nInconsistências registradas:")
    print(log.groupby(["tipo", "codigo"])["leituras"].agg(["size", "sum"])
          .rename(columns={"size": "registros", "sum": "leituras"}).to_string())
    print("\nArquivos salvos em dados/processados/:")
    for nome, df in [("ana_telemetria_15min.csv.gz", tele), ("ana_nivel_diario.csv", diario),
                     ("ana_historico_diario.csv", historico), ("ana_estacoes.csv", estacoes)]:
        print(f"  {nome}: {len(df)} linhas")


if __name__ == "__main__":
    main()
