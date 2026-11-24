"""Tela 2: como o nível do Guaíba variou ao longo dos anos e com que frequência passou da cota de inundação?

Usa as séries da ANA coletadas por código (scripts/coleta_ana_hidroweb.py) e limpas
(scripts/limpeza_ana.py). Liga-se à Tela 1 pela cheia de maio de 2024.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import dados
from dados import (AZUL, AZUL_CLARO, CAIS_MAUA, CINZA, COTA_ALERTA, COTA_INUNDACAO, ESTACOES, LARANJA, PICO_2024,
                   TEXTO_2, VERDE_AGUA, formatar)

diario = dados.nivel_diario()
coleta = dados.data_coleta_ana()

st.title("O Guaíba ao longo dos anos")
st.caption("Como o nível do Guaíba variou e com que frequência passou da cota de inundação de Porto Alegre.")

st.info(
    "Cada estação mede numa **régua com o seu próprio zero**, então níveis de estações diferentes não são "
    "comparáveis diretamente. As cotas de alerta (2,55 m) e de inundação (3,00 m) valem para a régua do "
    "**Cais Mauá C6**, que foi destruída na cheia de 2 de maio de 2024 e só voltou a medir em junho de 2025.",
    icon="ℹ️",
)

# ------------------------------------------------------------------ Filtro de período (Cais Mauá)
cm = diario[diario["codigo"] == CAIS_MAUA].set_index("data")["nivel_max_m"]
ano_min, ano_max = int(cm.index.year.min()), int(cm.index.year.max())
inicio, fim = st.slider("Período (Cais Mauá C6)", min_value=ano_min, max_value=ano_max, value=(ano_min, ano_max))

# Série diária completa: dias sem leitura viram lacuna no gráfico, em vez de uma linha reta
dias = pd.date_range(f"{inicio}-01-01", min(pd.Timestamp(f"{fim}-12-31"), cm.index.max()), freq="D")
serie = cm.reindex(dias)

st.subheader("Nível máximo diário no Cais Mauá")
fig = go.Figure(go.Scatter(x=serie.index, y=serie.values, mode="lines", line=dict(color=AZUL, width=1.4),
                           connectgaps=False, name="Nível máximo do dia",
                           hovertemplate="%{x|%d/%m/%Y}: %{y:.2f} m<extra></extra>"))
for cota, nome, cor in [(COTA_INUNDACAO, "cota de inundação 3,00 m", LARANJA), (COTA_ALERTA, "cota de alerta 2,55 m", CINZA)]:
    fig.add_hline(y=cota, line=dict(color=cor, width=1.2, dash="dash"))
    fig.add_annotation(x=1, xref="paper", y=cota, text=nome, showarrow=False, xanchor="right", yshift=9,
                       font=dict(color=cor, size=12))
fig.update_xaxes(title=None)
fig.update_yaxes(title="Nível (m)", rangemode="tozero")
fig.update_layout(showlegend=False)
st.plotly_chart(dados.estilo(fig, 360), width="stretch")
st.caption("Lacunas são dias sem leitura válida, como entre maio de 2024 e junho de 2025.")

# ------------------------------------------------------------------ Dias por ano acima das cotas
st.subheader("Dias por ano acima das cotas")
no_periodo = cm[(cm.index.year >= inicio) & (cm.index.year <= fim)]
por_ano = no_periodo.groupby(no_periodo.index.year).agg(
    com_dado="size",
    alerta=lambda s: int((s >= COTA_ALERTA).sum()),
    inundacao=lambda s: int((s >= COTA_INUNDACAO).sum()),
)
rotulos = [f"{a}*" if n < 300 else str(a) for a, n in por_ano["com_dado"].items()]
fig = go.Figure()
for coluna, nome, cor in [("alerta", "acima da cota de alerta (2,55 m)", CINZA),
                          ("inundacao", "acima da cota de inundação (3,00 m)", LARANJA)]:
    fig.add_trace(go.Bar(x=rotulos, y=por_ano[coluna], name=nome, marker_color=cor,
                         customdata=por_ano["com_dado"], text=por_ano[coluna], textposition="outside",
                         textfont=dict(color=TEXTO_2), cliponaxis=False,
                         hovertemplate="%{x}: %{y} dias<br>(%{customdata} dias com leitura)<extra></extra>"))
fig.update_layout(barmode="group", bargap=0.25)
fig.update_xaxes(title=None, type="category")
fig.update_yaxes(title="Dias", rangemode="tozero")
st.plotly_chart(dados.estilo(fig, 340), width="stretch")
st.caption("\\* Anos com menos de 300 dias de leitura: a contagem pode estar subestimada "
           "(2014 começa em agosto; 2024 e 2025 têm a lacuna da régua destruída).")

# ------------------------------------------------------------------ Cheia de 2024 e ligação com a Tela 1
st.subheader("A cheia de maio de 2024 e a simulação do INCT")
esquerda, direita = st.columns([3, 1], gap="large")
with esquerda:
    tele = dados.telemetria("2024-04-25", "2024-06-15")
    fig = go.Figure()
    for codigo in [87450004, 87444000, 87450020]:
        nome, cor = ESTACOES[codigo]
        s = tele[tele["codigo"] == codigo].set_index("data_hora")["nivel_m"]
        s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="15min"))
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=nome, line=dict(color=cor, width=1.8),
                                 connectgaps=False, hovertemplate=f"{nome}<br>%{{x|%d/%m %H:%M}}: %{{y:.2f}} m<extra></extra>"))
    fig.add_annotation(x=pd.Timestamp("2024-05-05 05:30"), y=PICO_2024, text="pico de 5,35 m<br>05/05, 05h30",
                       showarrow=True, arrowhead=0, ax=60, ay=-10, font=dict(color=LARANJA), xanchor="left")
    fig.add_annotation(x=pd.Timestamp("2024-05-02 18:00"), y=3.6, text="régua do Cais Mauá<br>destruída",
                       showarrow=True, arrowhead=0, ax=-70, ay=-30, font=dict(color=AZUL), xanchor="right")
    fig.update_xaxes(title=None, tickformat="%d/%m")
    fig.update_yaxes(title="Nível (m), cada régua no seu zero", range=[0, 6])
    st.plotly_chart(dados.estilo(fig, 380), width="stretch")
with direita:
    cidade = dados.inct_cidade()
    st.markdown("**No pico, a simulação do INCT estima:**")
    st.metric("Pessoas afetadas a 5,3 m", formatar(cidade.loc[5.3, "pessoas"]))
    st.metric("Bairros atingidos a 5,3 m", int(cidade.loc[5.3, "bairros"]))

    def ir_para_tela1():
        st.session_state["nivel"] = 5.3

    if st.button("Ver 5,3 m na Tela 1", type="primary", on_click=ir_para_tela1, width="stretch"):
        st.switch_page("tela1_simulacao.py")
    st.caption("5,3 m é o nível da simulação mais próximo do pico registrado (5,35 m).")

# ------------------------------------------------------------------ Gastos do Estado x inundações
st.divider()
st.subheader("Gastos do Estado com prevenção de enchentes")
st.caption("Pagamentos do Governo do RS em obras, estudos e transferências para proteção contra cheias, "
           "comparados com os dias em que o Guaíba passou da cota de inundação no Cais Mauá.")

gastos = dados.gastos()
g_ini, g_fim = st.slider("Período dos gastos", min_value=int(gastos["Ano"].min()), max_value=int(gastos["Ano"].max()),
                         value=(int(gastos["Ano"].min()), int(gastos["Ano"].max())))
filtrado = gastos[gastos["Ano"].between(g_ini, g_fim)].copy()

c1, c2, c3 = st.columns(3)
c1.metric("Total pago no período", f"R$ {formatar(filtrado['Total'].sum() / 1e6, 2)} mi")
c2.metric("Obras de prevenção", f"R$ {formatar(filtrado['Obras'].sum() / 1e6, 2)} mi")
c3.metric("Transferências para proteção", f"R$ {formatar(filtrado['Transferencias'].sum() / 1e6, 2)} mi")

# Dias de inundação de cada ano no Cais Mauá (ano inteiro, independente do filtro de período do Guaíba)
inundacao_ano = cm.groupby(cm.index.year).agg(
    com_dado="size",
    inundacao=lambda s: int((s >= COTA_INUNDACAO).sum()),
)
filtrado = filtrado.join(inundacao_ano, on="Ano")
rotulos = [f"{a}*" if (n < 300 or a == 2026) else str(a) for a, n in zip(filtrado["Ano"], filtrado["com_dado"])]

# Dois painéis alinhados pelo ano: os valores têm escalas muito diferentes, então cada um ganha o seu eixo
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.12,
                    subplot_titles=("Pagamentos (R$ milhões)", "Dias com o Guaíba acima de 3,00 m no Cais Mauá"))
for coluna, nome, cor in [("Obras", "Obras de prevenção", AZUL),
                          ("Transferencias", "Transferências para proteção", AZUL_CLARO),
                          ("Estudos", "Estudos e projetos", VERDE_AGUA)]:
    fig.add_trace(go.Bar(x=rotulos, y=filtrado[coluna] / 1e6, name=nome, marker_color=cor,
                         hovertemplate=f"{nome}<br>%{{x}}: R$ %{{y:,.2f}} mi<extra></extra>"), row=1, col=1)
# Total escrito acima de cada barra, para que os anos com valores pequenos também possam ser lidos
fig.add_trace(go.Scatter(x=rotulos, y=filtrado["Total"] / 1e6, mode="text", showlegend=False, hoverinfo="skip",
                         text=[f"R$ {formatar(v / 1e6, 1)} mi" for v in filtrado["Total"]],
                         textposition="top center", textfont=dict(color=TEXTO_2, size=12)), row=1, col=1)
fig.add_trace(go.Bar(x=rotulos, y=filtrado["inundacao"], name="Dias acima de 3,00 m", marker_color=LARANJA,
                     showlegend=False, text=filtrado["inundacao"], textposition="outside", cliponaxis=False,
                     textfont=dict(color=LARANJA), customdata=filtrado["com_dado"],
                     hovertemplate="%{x}: %{y} dias acima de 3,00 m<br>(%{customdata} dias com leitura)"
                                   "<extra></extra>"), row=2, col=1)
fig.update_layout(barmode="stack", bargap=0.3, legend_traceorder="normal")
fig.update_xaxes(type="category", title=None)
fig.update_yaxes(rangemode="tozero", range=[0, filtrado["Total"].max() / 1e6 * 1.15], row=1, col=1)
fig.update_yaxes(range=[0, max(filtrado["inundacao"].max(), 1) * 1.35], dtick=2, row=2, col=1)
fig.update_annotations(font=dict(size=13, color=TEXTO_2), xanchor="left", x=0)
dados.estilo(fig, 540)
fig.update_layout(margin=dict(t=70), legend=dict(y=1.06))   # legenda acima do título do primeiro painel
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
st.caption("\\* 2024 e 2025 têm a lacuna da régua destruída, então os dias de inundação podem estar subestimados; "
           "2026 tem gastos e leituras parciais.")

tabela = pd.DataFrame({
    "Ano": rotulos,
    "Obras": filtrado["Obras"].map(lambda v: f"R$ {formatar(v, 2)}"),
    "Estudos e projetos": filtrado["Estudos"].map(lambda v: f"R$ {formatar(v, 2)}"),
    "Transferências": filtrado["Transferencias"].map(lambda v: f"R$ {formatar(v, 2)}"),
    "Total": filtrado["Total"].map(lambda v: f"R$ {formatar(v, 2)}"),
    "Dias acima de 3,00 m": filtrado["inundacao"],
    "Dias com leitura": filtrado["com_dado"],
})
with st.expander("Ver valores por ano"):
    st.dataframe(tabela, hide_index=True, width="stretch")

st.warning(
    "**Limitações:** os valores são nominais (sem correção pela inflação) e dependem das ações orçamentárias "
    "que o grupo classificou como prevenção. Pagamento e transferência não comprovam que a obra foi executada. "
    "A comparação mostra os dois dados lado a lado e não estabelece relação de causa e efeito.",
    icon="⚠️",
)

# ------------------------------------------------------------------ Fontes
st.divider()
st.caption(
    f"Fonte: Agência Nacional de Águas e Saneamento Básico (ANA), [API HidroWebService]({dados.URL_ANA}), "
    f"coletada por código em {coleta:%d/%m/%Y} (`scripts/coleta_ana_hidroweb.py`). Estações 87450004 (Cais Mauá C6), "
    "87444000 e 87450020 (Usina do Gasômetro). Leituras inválidas (sem nível, picos isolados e sensor travado) foram "
    "descartadas na limpeza."
)
st.caption(
    f"Fonte dos gastos: Portal da Transparência RS, [Dados abertos – Despesas do Estado]({dados.URL_TRANSPARENCIA}), "
    f"arquivos de despesas baixados em {dados.COLETA_GASTOS}. Foram mantidos apenas os pagamentos das ações "
    "orçamentárias de prevenção e proteção contra cheias (`scripts/config.py` e `scripts/classificar_acoes.py`). "
    "Simulação: INCT SiMAI (`data.json`)."
)
