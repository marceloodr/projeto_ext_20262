"""Tela 2: como o nível do Guaíba variou ao longo dos anos e com que frequência passou da cota de inundação?

Usa as séries da ANA coletadas por código (scripts/coleta_ana_hidroweb.py) e limpas
(scripts/limpeza_ana.py). Liga-se à Tela 1 pela cheia de maio de 2024.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
from dados import (AZUL, CAIS_MAUA, CINZA, COTA_ALERTA, COTA_INUNDACAO, ESTACOES, LARANJA, PICO_2024, TEXTO_2,
                   formatar)

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

# ------------------------------------------------------------------ Gastos (em preparação)

# ------------------------------------------------------------------ Gastos do Estado
from pathlib import Path

st.subheader("Gastos do Estado com prevenção de enchentes")
st.caption("Pagamentos selecionados do Governo do RS entre 2020 e 2026.")

raiz = Path(__file__).resolve().parents[1]
arquivo = raiz / "resumo_anual_prevencao_enchentes_2020_2026.csv"

if not arquivo.exists():
    st.warning("Arquivo CSV de despesas não encontrado na raiz do projeto.")
else:
    gastos = pd.read_csv(arquivo, sep=";", encoding="utf-8-sig")

    colunas = ["Obras", "Estudos", "Transferencias", "Total"]

    def converter_valor(coluna):
        texto = coluna.astype(str).str.strip()
        texto = texto.str.replace("R$", "", regex=False)
        texto = texto.str.replace(" ", "", regex=False)
        texto = texto.str.replace(".", "", regex=False)
        texto = texto.str.replace(",", ".", regex=False)
        return pd.to_numeric(texto, errors="raise")

    for coluna in colunas:
        gastos[coluna] = converter_valor(gastos[coluna])

    gastos["Ano"] = gastos["Ano"].astype(int)

    anos = sorted(gastos["Ano"].unique())
    periodo = st.slider(
        "Período dos gastos",
        min_value=min(anos),
        max_value=max(anos),
        value=(min(anos), max(anos))
    )

    filtrado = gastos[
        gastos["Ano"].between(periodo[0], periodo[1])
    ].copy()

    total = filtrado["Total"].sum()
    obras = filtrado["Obras"].sum()
    transferencias = filtrado["Transferencias"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total selecionado", f"R$ {formatar(total / 1e6, 2)} mi")
    c2.metric("Obras de prevenção", f"R$ {formatar(obras / 1e6, 2)} mi")
    c3.metric("Transferências", f"R$ {formatar(transferencias / 1e6, 2)} mi")

    st.subheader("Evolução anual dos pagamentos")

    fig = go.Figure()
    for coluna, nome, cor in [
        ("Obras", "Obras de prevenção", AZUL),
        ("Estudos", "Estudos e projetos", "#1baf7a"),
        ("Transferencias", "Transferências para proteção", LARANJA)
    ]:
        fig.add_trace(go.Bar(
            x=filtrado["Ano"].astype(str),
            y=filtrado[coluna] / 1e6,
            name=nome,
            marker_color=cor
        ))

    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Pagamentos (R$ milhões)")
    fig.update_xaxes(title="Ano", type="category")
    st.plotly_chart(dados.estilo(fig, 400), width="stretch")

    st.subheader("Detalhamento anual")
    tabela = filtrado.rename(columns={
        "Transferencias": "Transferências"
    })
    st.dataframe(
        tabela.style.format({
            "Obras": "R$ {:,.2f}",
            "Estudos": "R$ {:,.2f}",
            "Transferências": "R$ {:,.2f}",
            "Total": "R$ {:,.2f}"
        }),
        hide_index=True,
        width="stretch"
    )

    st.caption(
        "Fonte: Portal da Transparência RS. Valores nominais. "
        "2026 possui dados parciais. Transferências não comprovam "
        "a execução das obras. A seleção depende das regras de classificação "
        "adotadas pelo grupo e das limitações da coleta."
    )

    # ----------------------------------------------------------
    # Comparação entre despesas e frequência de inundações

    st.divider()
    st.subheader("Gastos estaduais x frequência de inundações")
    st.caption(
        "Comparação anual entre os pagamentos selecionados "
        "para prevenção e proteção e os dias com nível do Guaíba "
        "igual ou superior a 3,00 m no Cais Mauá C6."
    )

    # Conta os dias com leitura válida e os dias de inundação
    nivel_ano = cm.groupby(cm.index.year).agg(
        dias_com_leitura="size",
        dias_inundacao=lambda serie: int(
            (serie >= COTA_INUNDACAO).sum()
        )
    )

    nivel_ano.index.name = "Ano"
    nivel_ano = nivel_ano.reset_index()

    # Junta os dados financeiros com os dados do Guaíba
    comparacao = filtrado.merge(
        nivel_ano,
        on="Ano",
        how="left"
    ).sort_values("Ano")

    # Anos sem leitura não devem ser tratados como zero
    comparacao["dias_inundacao"] = comparacao[
        "dias_inundacao"
    ].astype(float)

    # Gráfico superior: pagamentos
    fig_gastos = go.Figure()

    fig_gastos.add_trace(go.Bar(
        x=comparacao["Ano"].astype(str),
        y=comparacao["Total"] / 1_000_000,
        name="Pagamentos",
        marker_color=AZUL,
        hovertemplate=(
            "Ano: %{x}<br>"
            "Pagamentos: R$ %{y:,.2f} milhões"
            "<extra></extra>"
        )
    ))

    fig_gastos.update_layout(
        title="Pagamentos em prevenção e proteção",
        showlegend=False
    )
    fig_gastos.update_yaxes(title="R$ milhões")
    fig_gastos.update_xaxes(type="category")

    st.plotly_chart(
        dados.estilo(fig_gastos, 300),
        width="stretch"
    )

    # Gráfico inferior: dias de inundação
    fig_inundacoes = go.Figure()

    fig_inundacoes.add_trace(go.Bar(
        x=comparacao["Ano"].astype(str),
        y=comparacao["dias_inundacao"],
        name="Dias de inundação",
        marker_color=LARANJA,
        customdata=comparacao[["dias_com_leitura"]],
        hovertemplate=(
            "Ano: %{x}<br>"
            "Dias com inundação: %{y:.0f}<br>"
            "Dias com leitura: %{customdata[0]:.0f}"
            "<extra></extra>"
        )
    ))

    fig_inundacoes.update_layout(
        title="Dias com nível igual ou superior a 3,00 m",
        showlegend=False
    )
    fig_inundacoes.update_yaxes(
        title="Dias",
        rangemode="tozero"
    )
    fig_inundacoes.update_xaxes(type="category")

    st.plotly_chart(
        dados.estilo(fig_inundacoes, 300),
        width="stretch"
    )

    # Tabela conjunta para facilitar a análise
    st.subheader("Resumo comparativo por ano")

    tabela_comparativa = comparacao[[
        "Ano", "Total", "dias_inundacao", "dias_com_leitura"
    ]].copy()

    tabela_comparativa["Total"] = (
        tabela_comparativa["Total"] / 1_000_000
    )

    st.dataframe(
        tabela_comparativa,
        hide_index=True,
        width="stretch",
        column_config={
            "Ano": st.column_config.NumberColumn(
                "Ano", format="%d"
            ),
            "Total": st.column_config.NumberColumn(
                "Pagamentos (R$ milhões)", format="%.2f"
            ),
            "dias_inundacao": st.column_config.NumberColumn(
                "Dias de inundação", format="%.0f"
            ),
            "dias_com_leitura": st.column_config.NumberColumn(
                "Dias com leitura", format="%.0f"
            )
        }
    )

    st.warning(
        "**Limitações da comparação:** a régua do Cais Mauá "
        "ficou sem leituras entre maio de 2024 e junho de 2025. "
        "Portanto, os dias de inundação nesses anos podem estar "
        "subestimados. Os gastos de 2026 também são parciais. "
        "Os pagamentos não comprovam a execução das obras, "
        "e a comparação não estabelece relação de causa e efeito.",
        icon="⚠️"
    )



# ------------------------------------------------------------------ Fontes
st.divider()
st.caption(
    f"Fonte: Agência Nacional de Águas e Saneamento Básico (ANA), [API HidroWebService]({dados.URL_ANA}), "
    f"coletada por código em {coleta:%d/%m/%Y} (`scripts/coleta_ana_hidroweb.py`). Estações 87450004 (Cais Mauá C6), "
    "87444000 e 87450020 (Usina do Gasômetro). Leituras inválidas (sem nível, picos isolados e sensor travado) foram "
    "descartadas na limpeza. Simulação: INCT SiMAI (`data.json`)."
)
