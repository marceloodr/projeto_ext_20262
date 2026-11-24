"""Leitura dos dados processados usados pelo dashboard (sempre de dados/processados/)."""

from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "dados" / "processados"
LOG_ANA = RAIZ / "dados" / "originais" / "ana_hidroweb" / "coleta_log.csv"

# Cores (paleta categórica do projeto, mesma ordem do EDA)
AZUL, LARANJA, VERDE_AGUA = "#2a78d6", "#eb6834", "#1baf7a"
AZUL_CLARO = "#9cc3ef"      # tom claro do azul, para a segunda série de gastos
TEXTO, TEXTO_2, CINZA, GRADE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"

PICO_2024 = 5.35            # pico de maio de 2024 (Usina do Gasômetro, 05/05/2024 05:30)
COTA_ALERTA = 2.55          # régua do Cais Mauá C6
COTA_INUNDACAO = 3.00       # régua do Cais Mauá C6
CAIS_MAUA = 87450004

ESTACOES = {
    87450004: ("Cais Mauá C6", AZUL),
    87444000: ("Gasômetro (cheia 2024)", LARANJA),
    87450020: ("Gasômetro", VERDE_AGUA),
}

URL_ANA = "https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html"
URL_RELATORIO = "https://github.com/marceloodr/projeto_ext_20262/blob/main/relatorios/limpeza_dados.pdf"
URL_TRANSPARENCIA = "https://www.transparencia.rs.gov.br/dados-abertos/"
COLETA_GASTOS = "09/11/2026"   # download dos ZIPs de despesas do Portal da Transparência RS


@st.cache_data
def inct():
    """Simulação do INCT, já limpa: uma linha por nível e bairro."""
    df = pd.read_json(PROC / "inct_longo_limpo.json")
    df["nivel_m"] = df["nivel_m"].round(1)
    return df


@st.cache_data
def inct_cidade():
    """Totais da cidade por nível."""
    df = inct()
    cidade = df.groupby("nivel_m").agg(
        pessoas=("affected_population", "sum"),
        predios=("affected_buildings", "sum"),
        bairros=("affected_buildings", lambda s: int((s > 0).sum())),
    )
    cidade["populacao_total"] = df[df["nivel_m"] == df["nivel_m"].min()]["population"].sum()
    return cidade


@st.cache_data
def nivel_diario():
    df = pd.read_csv(PROC / "ana_nivel_diario.csv", parse_dates=["data"])
    return df


@st.cache_data
def telemetria(inicio, fim):
    """Leituras de 15 min entre duas datas (texto 'AAAA-MM-DD')."""
    df = pd.read_csv(PROC / "ana_telemetria_15min.csv.gz", parse_dates=["data_hora"])
    return df[(df["data_hora"] >= inicio) & (df["data_hora"] < fim)]


@st.cache_data
def data_coleta_ana():
    """Data e hora da última requisição registrada no log da coleta da ANA."""
    log = pd.read_csv(LOG_ANA, parse_dates=["data_coleta"])
    return log["data_coleta"].max()


@st.cache_data
def gastos():
    """Pagamentos do Estado com prevenção de enchentes, por ano e categoria (em reais)."""
    df = pd.read_csv(PROC / "gastos_prevencao_anual.csv", sep=";", decimal=",", encoding="utf-8-sig")
    return df.astype({"Ano": int})


def formatar(numero, casas=0):
    """Número no formato brasileiro: 1.234,5."""
    texto = f"{numero:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def estilo(fig, altura=380):
    """Aparência comum dos gráficos plotly."""
    fig.update_layout(
        height=altura, margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Helvetica, Arial, sans-serif", color=TEXTO, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        hoverlabel=dict(bgcolor="white"),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor=CINZA, tickfont_color=TEXTO_2, title_font_color=TEXTO_2)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, tickfont_color=TEXTO_2, title_font_color=TEXTO_2)
    return fig
