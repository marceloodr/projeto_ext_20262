"""Tela 1: se o Guaíba chegar a X metros, quais bairros e quantas pessoas são afetados?

Usa apenas a simulação do INCT, depois de limpa (dados/processados/inct_longo_limpo.json).
"""

import plotly.graph_objects as go
import streamlit as st

import dados
from dados import AZUL, LARANJA, PICO_2024, TEXTO_2, formatar

inct = dados.inct()
cidade = dados.inct_cidade()

st.title("Se o Guaíba chegar a X metros, quem é afetado?")
st.caption("Simulação do INCT SiMAI para os 94 bairros de Porto Alegre, de 3,0 m a 10,0 m.")

nivel = st.slider("Nível do Guaíba (m)", min_value=3.0, max_value=10.0, step=0.1, format="%.1f m", key="nivel")
nivel = round(nivel, 1)
no_nivel = inct[inct["nivel_m"] == nivel]
atingidos = no_nivel[no_nivel["affected_buildings"] > 0].copy()
total = cidade.loc[nivel]

def anel(valor, total_cidade, titulo, detalhe):
    """Indicador circular: o anel se preenche na proporção valor / total da cidade (100% = anel completo)."""
    fracao = valor / total_cidade
    fig = go.Figure(go.Pie(
        values=[fracao, 1 - fracao], hole=0.74, sort=False, direction="clockwise", rotation=0,
        marker=dict(colors=[AZUL, "#e6e5e1"], line=dict(width=0)),
        textinfo="none", hoverinfo="skip", showlegend=False))
    fig.add_annotation(text=f"<b>{formatar(valor)}</b>", x=0.5, y=0.56, showarrow=False,
                       font=dict(size=26, color="#0b0b0b"))
    fig.add_annotation(text=f"{formatar(100 * fracao, 1)}% {detalhe}", x=0.5, y=0.38, showarrow=False,
                       font=dict(size=13, color=TEXTO_2))
    fig.update_layout(title=dict(text=titulo, x=0.5, xanchor="center", font=dict(size=15)),
                      height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="white",
                      separators=",.")
    return fig


# Indicadores: cada anel mostra a parte da cidade afetada no nível escolhido
c1, c2, c3 = st.columns(3)
with c1:
    st.plotly_chart(anel(total["pessoas"], total["populacao_total"], "Pessoas afetadas", "da população"),
                    width="stretch", config={"displayModeBar": False})
with c2:
    st.plotly_chart(anel(total["predios"], no_nivel["total_buildings"].sum(), "Prédios afetados", "dos prédios"),
                    width="stretch", config={"displayModeBar": False})
with c3:
    st.plotly_chart(anel(total["bairros"], 94, "Bairros atingidos", "dos 94 bairros"),
                    width="stretch", config={"displayModeBar": False})
st.caption("Cada anel se completa quando 100% da cidade é afetada. A população afetada é estimada como "
           "população do bairro × porcentagem de prédios afetados.")

st.warning(
    "**Limitações dos dados.** A população afetada é uma **estimativa**: a simulação supõe que os moradores "
    "se distribuem igualmente entre todos os prédios do bairro, inclusive os não residenciais. "
    "O arquivo original tinha inconsistências (bairros que zeravam com o rio subindo, picos isolados e "
    "percentuais arredondados para cima); elas foram corrigidas, e cada correção está no "
    f"[relatório de limpeza]({dados.URL_RELATORIO}). A simulação vai de 0,1 em 0,1 m: o recorde de maio de 2024 "
    "(5,35 m) fica entre os níveis 5,3 e 5,4 m.",
    icon="⚠️",
)

esquerda, direita = st.columns([1, 1], gap="large")

# Curva da cidade
with esquerda:
    st.subheader("Pessoas afetadas na cidade, por nível")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cidade.index, y=cidade["pessoas"], mode="lines", line=dict(color=AZUL, width=3),
        name="Pessoas afetadas", hovertemplate="%{x:.1f} m: %{y:,.0f} pessoas<extra></extra>"))
    fig.add_vline(x=PICO_2024, line=dict(color=LARANJA, dash="dash", width=1.5))
    fig.add_annotation(x=PICO_2024, y=cidade["pessoas"].max(), text="recorde de maio de 2024<br>5,35 m",
                       showarrow=False, xanchor="left", xshift=6, font=dict(color=LARANJA), align="left")
    fig.add_trace(go.Scatter(
        x=[nivel], y=[total["pessoas"]], mode="markers", marker=dict(color=AZUL, size=12, line=dict(color="white", width=2)),
        name="Nível escolhido", hovertemplate="nível escolhido: %{x:.1f} m<br>%{y:,.0f} pessoas<extra></extra>"))
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title="Nível do Guaíba (m)", range=[3, 10], dtick=1, ticksuffix=" m")
    fig.update_yaxes(title="Pessoas afetadas", rangemode="tozero", tickformat=",.0f")
    st.plotly_chart(dados.estilo(fig, 400), width="stretch")

# Ranking
with direita:
    st.subheader(f"Ranking dos bairros a {formatar(nivel, 1)} m")
    if atingidos.empty:
        st.info("Nenhum bairro atingido neste nível.")
    else:
        ranking = (atingidos.sort_values("affected_population", ascending=False).head(10)
                   [["bairro", "affected_population", "percentage", "affected_buildings"]])
        ranking.index = range(1, len(ranking) + 1)
        # Números já formatados no padrão brasileiro (o dataframe usaria o idioma do navegador)
        for coluna in ["affected_population", "affected_buildings"]:
            ranking[coluna] = ranking[coluna].map(formatar)
        ranking["percentage"] = ranking["percentage"].map(lambda p: f"{formatar(p, 1)}%")
        st.dataframe(
            ranking, width="stretch", height=388,
            column_config={
                "bairro": "Bairro",
                "affected_population": st.column_config.TextColumn("Pessoas afetadas"),
                "percentage": st.column_config.TextColumn("% dos prédios"),
                "affected_buildings": st.column_config.TextColumn("Prédios afetados"),
            },
        )
        st.caption("Ordenado pelo número de pessoas afetadas.")

# Porcentagem de prédios afetados por bairro
st.subheader(f"Porcentagem de prédios afetados em cada bairro atingido a {formatar(nivel, 1)} m")
if atingidos.empty:
    st.info("Nenhum bairro atingido neste nível.")
else:
    barras = atingidos.sort_values("percentage")
    fig = go.Figure(go.Bar(
        x=barras["percentage"], y=barras["bairro"], orientation="h", marker_color=AZUL,
        customdata=barras[["affected_buildings", "total_buildings", "affected_population"]],
        text=[f"{formatar(p, 1)}%" for p in barras["percentage"]], textposition="outside",
        textfont=dict(color=TEXTO_2, size=11), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% dos prédios (%{customdata[0]:,.0f} de %{customdata[1]:,.0f})"
                      "<br>%{customdata[2]:,.0f} pessoas afetadas<extra></extra>"))
    fig.update_xaxes(title="% dos prédios do bairro", range=[0, 112], ticksuffix="%", showgrid=True, gridcolor="#e6e5e1")
    fig.update_yaxes(title=None, showgrid=False, tickfont=dict(color="#0b0b0b"))
    st.plotly_chart(dados.estilo(fig, max(300, 22 * len(barras) + 60)), width="stretch")
    st.caption(f"{len(barras)} bairros com pelo menos um prédio afetado. Os outros {94 - len(barras)} não aparecem.")

st.divider()
st.caption(
    "Fonte: simulação de enchentes do INCT SiMAI (arquivo `data.json`, fornecido à disciplina), com prédios do "
    "OpenStreetMap e população do Censo IBGE 2022. Dados limpos pelo grupo: "
    "[`inct_longo_limpo.json`](https://github.com/marceloodr/projeto_ext_20262/blob/main/dados/processados/inct_longo_limpo.json)."
)
