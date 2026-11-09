from pathlib import Path

# ÚNICO lugar onde você muda o ano
ANO = 2024
PASTA_PROJETO = Path(__file__).resolve().parent.parent
DADOS_ORIGINAIS = PASTA_PROJETO / f"dados_{ANO}"
DADOS_TRATADOS = PASTA_PROJETO / "dados_tratados"
RESULTADOS = PASTA_PROJETO / "resultados"
VALIDACAO = PASTA_PROJETO / "validacao"

# As ações orçamentárias precisam ser revisadas em cada ano.
ACOES_APROVADAS = {
    2024: [
        "DESASSOREAMENTO E OBRAS DE MACRO-DRENAGEM"
    ]
}
INCLUIR_SPCC_FUNDO_A_FUNDO = {2025: True, 2026: False}
