import pandas as pd
from config import ANO, DADOS_TRATADOS, RESULTADOS, VALIDACAO
RESULTADOS.mkdir(parents=True, exist_ok=True)
VALIDACAO.mkdir(parents=True, exist_ok=True)
arquivo = DADOS_TRATADOS / f"pagamentos_prevencao_{ANO}.csv"
df = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', dtype=str)
ids = ['Pagamento', 'Empenho', 'Processo', 'Data', 'Valor']
faltam = [c for c in ids if c not in df.columns]
if faltam:
    raise SystemExit(f'Faltam colunas para validação: {faltam}')
repetidos = df[df.duplicated(subset=ids, keep=False)].copy()
print('ANO:', ANO, '| Pagamentos:', len(df), '| Possíveis repetições:', len(repetidos))
if not repetidos.empty:
    repetidos.to_csv(VALIDACAO / f'possiveis_duplicidades_{ANO}.csv', sep=';', index=False, encoding='utf-8-sig')
valores = df['Valor'].fillna('').str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
df['ValorNumerico'] = pd.to_numeric(valores, errors='coerce')
invalidos = df['ValorNumerico'].isna().sum()
print('Valores inválidos:', invalidos)
if invalidos:
    raise SystemExit('Há valores inválidos: revise antes de gerar totais.')
resumo = df.groupby('Acao').agg(Quantidade=('ValorNumerico', 'size'), Total=('ValorNumerico', 'sum')).sort_values('Total', ascending=False)
mensal = df.groupby('Mes')['ValorNumerico'].sum()
mensal.index = mensal.index.astype(int)
mensal = mensal.sort_index()
print('TOTAL R$:', f"{df['ValorNumerico'].sum():,.2f}")
print('\nPOR AÇÃO:\n', resumo.to_string())
print('\nPOR MÊS:\n', mensal.to_string())
resumo.to_csv(RESULTADOS / f'resumo_pagamentos_{ANO}.csv', sep=';', encoding='utf-8-sig')
mensal.to_csv(RESULTADOS / f'pagamentos_mensais_{ANO}.csv', sep=';', encoding='utf-8-sig')
