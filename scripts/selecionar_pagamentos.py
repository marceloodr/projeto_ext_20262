import pandas as pd
from config import ANO, DADOS_TRATADOS, ACOES_APROVADAS, INCLUIR_SPCC_FUNDO_A_FUNDO
acoes = ACOES_APROVADAS.get(ANO)
if not acoes:
    raise SystemExit(f"Ações de {ANO} ainda não revisadas. Execute analisar_gastos.py e revise a lista ACOES_APROVADAS em config.py antes de selecionar pagamentos.")
arquivo = DADOS_TRATADOS / f"despesas_enchentes_{ANO}.csv"
if ANO == 2025 and (DADOS_TRATADOS / 'despesas_enchentes_2025_completo.csv').exists():
    arquivo = DADOS_TRATADOS / 'despesas_enchentes_2025_completo.csv'
df = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', dtype=str)
pag = df[df['FaseGasto'].fillna('').str.strip() == 'Pagamento'].copy()
filtro = pag['Acao'].fillna('').str.strip().isin(acoes)
if INCLUIR_SPCC_FUNDO_A_FUNDO.get(ANO, False):
    filtro |= pag['Acao'].fillna('').str.contains('sistema de protecao contra cheias', case=False, regex=False)
selecionados = pag[filtro].copy()
if selecionados.empty:
    raise SystemExit('Nenhum pagamento selecionado. Confira a lista de ações; nenhum arquivo foi substituído.')
saida = DADOS_TRATADOS / f"pagamentos_prevencao_{ANO}.csv"
selecionados.to_csv(saida, sep=';', index=False, encoding='utf-8-sig')
print('ANO:', ANO, '| Pagamentos selecionados:', len(selecionados))
print(selecionados['Acao'].value_counts().to_string())
print('Arquivo:', saida)
print('ATENÇÃO: seleção provisória; não equivale necessariamente a obras executadas.')
