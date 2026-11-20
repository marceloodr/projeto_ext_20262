"""Dashboard: Análise de Dados de Enchentes do INCT SiMAI.

Uso (na raiz do projeto):
    streamlit run app/app.py
"""

import streamlit as st

st.set_page_config(page_title="Enchentes em Porto Alegre", page_icon="🌊", layout="wide")

# O nível escolhido na Tela 1 é guardado aqui para sobreviver à troca de tela
# (o Streamlit apaga o estado de um controle quando a página dele não está aberta).
st.session_state["nivel"] = st.session_state.get("nivel", 5.3)

paginas = st.navigation([
    st.Page("tela1_simulacao.py", title="Tela 1 · Simulação do INCT", icon="🏘️", default=True),
    st.Page("tela2_guaiba.py", title="Tela 2 · O Guaíba ao longo dos anos", icon="📈"),
])
paginas.run()
