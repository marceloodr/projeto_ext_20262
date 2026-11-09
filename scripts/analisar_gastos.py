import pandas as pd
from config import ANO, DADOS_TRATADOS
arquivo = DADOS_TRATADOS / f"despesas_enchentes_{ANO}.csv"
if ANO == 2025 and (DADOS_TRATADOS / 'despesas_enchentes_2025_completo.csv').exists():
    arquivo = DADOS_TRATADOS / 'despesas_enchentes_2025_completo.csv'
df = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', dtype=str)
pag = df[df['FaseGasto'].fillna('').str.strip() == 'Pagamento']
print('ANO:', ANO, '| Registros:', len(df), '| Pagamentos:', len(pag))
print('\nFASES:\n', df['FaseGasto'].value_counts().to_string())
print('\nAÇÕES COM PAGAMENTOS:\n', pag['Acao'].value_counts().to_string())
print('\nÓRGÃOS:\n', pag['Orgao'].value_counts().head(20).to_string())
print('\nMESES:\n', df['Mes'].value_counts().sort_index(key=lambda x: x.astype(int)).to_string())
if 'ArquivoOrigem' in df.columns:
    print('\nORIGENS:\n', df['ArquivoOrigem'].value_counts().to_string())
