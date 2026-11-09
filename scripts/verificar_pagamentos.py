import pandas as pd
from config import ANO, DADOS_TRATADOS
df = pd.read_csv(DADOS_TRATADOS / f'pagamentos_prevencao_{ANO}.csv', sep=';', encoding='utf-8-sig', dtype=str)
for c in ['Acao', 'Orgao', 'Municipio', 'Projeto', 'FaseGasto']:
    if c in df.columns:
        print(f'\n{c.upper()}\n{df[c].value_counts().head(20).to_string()}')
ids = ['Pagamento', 'Empenho', 'Processo', 'Data', 'Valor']
if all(c in df.columns for c in ids):
    print('\nPOSSÍVEIS REPETIÇÕES:', df.duplicated(subset=ids, keep=False).sum())
else:
    print('Identificadores incompletos; não é possível conferir duplicidades.')
