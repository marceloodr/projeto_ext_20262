import pandas as pd
from config import ANO, DADOS_TRATADOS
df = pd.read_csv(DADOS_TRATADOS / f'pagamentos_prevencao_{ANO}.csv', sep=';', encoding='utf-8-sig', dtype=str)
df['ValorNumerico'] = pd.to_numeric(df['Valor'].fillna('').str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce')
print(f'10 MAIORES PAGAMENTOS DE {ANO}:')
for _, r in df.nlargest(10, 'ValorNumerico').iterrows():
    print('-' * 50)
    for c in ['Mes', 'Data', 'Acao', 'Orgao', 'ValorNumerico', 'Historico', 'Informacoes Complementares']:
        print(f'{c}: {r.get(c, "")}')
