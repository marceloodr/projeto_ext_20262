import csv
import re
import unicodedata
from zipfile import ZipFile
from config import ANO, DADOS_ORIGINAIS, DADOS_TRATADOS, VALIDACAO

COLUNAS = ["Exercicio", "Mes", "FaseGasto", "Pagamento", "Empenho", "Processo", "Data", "Orgao", "Acao", "Projeto", "Programa", "Historico", "Informacoes Complementares", "Valor", "Municipio"]
BUSCA = ["Acao", "Projeto", "Programa", "Historico", "Informacoes Complementares"]
PADRAO = re.compile(r"enchent|inund|alagament|cheia|drenagem|dique|comporta|casa de bomba|casas de bomba|protecao contra cheias|controle de cheias|desassoreamento|contenc")

def normalizar(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s).lower()) if not unicodedata.combining(c))

zips = sorted(DADOS_ORIGINAIS.glob('*.zip'))
if not zips:
    raise SystemExit(f"Nenhum ZIP encontrado em {DADOS_ORIGINAIS}. Nada foi alterado.")
DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
VALIDACAO.mkdir(parents=True, exist_ok=True)
saida = DADOS_TRATADOS / f"despesas_enchentes_{ANO}.csv"
problemas = VALIDACAO / f"linhas_irregulares_{ANO}.csv"
saida_tmp = saida.with_suffix('.tmp')
problemas_tmp = problemas.with_suffix('.tmp')
total = 0
irregulares = 0
meses = set()
try:
    with saida_tmp.open('w', newline='', encoding='utf-8-sig') as fs, problemas_tmp.open('w', newline='', encoding='utf-8-sig') as fp:
        writer = csv.DictWriter(fs, fieldnames=COLUNAS + ['ArquivoOrigem'], delimiter=';')
        writer.writeheader()
        bad = csv.writer(fp, delimiter=';')
        bad.writerow(['ArquivoZIP', 'ArquivoCSV', 'LinhaLogica', 'QuantidadeCampos', 'Esperado', 'Conteudo'])
        for zpath in zips:
            print('Processando:', zpath.name, flush=True)
            with ZipFile(zpath) as z:
                nomes = [n for n in z.namelist() if n.lower().endswith('.csv')]
                if not nomes:
                    raise ValueError(f"ZIP sem CSV: {zpath.name}")
                for nome in nomes:
                    with z.open(nome) as raw:
                        linhas = (b.decode('latin1', errors='replace') for b in raw)
                        leitor = csv.reader(linhas, delimiter=';')
                        cabecalho = next(leitor)
                        if not set(COLUNAS).issubset(cabecalho):
                            raise ValueError(f"Colunas faltando em {zpath.name}/{nome}: {set(COLUNAS)-set(cabecalho)}")
                        for n, campos in enumerate(leitor, 2):
                            if len(campos) != len(cabecalho):
                                irregulares += 1
                                bad.writerow([zpath.name, nome, n, len(campos), len(cabecalho), ';'.join(campos)])
                                continue
                            registro = dict(zip(cabecalho, campos))
                            if registro['Exercicio'].strip() != str(ANO):
                                raise ValueError(f"Ano inesperado em {zpath.name}, registro {n}: {registro['Exercicio']}")
                            meses.add(registro['Mes'].strip())
                            texto = normalizar(' '.join(registro.get(c, '') for c in BUSCA))
                            if PADRAO.search(texto):
                                writer.writerow({**{c: registro[c] for c in COLUNAS}, 'ArquivoOrigem': zpath.name})
                                total += 1
    saida_tmp.replace(saida)
    problemas_tmp.replace(problemas)
except Exception:
    saida_tmp.unlink(missing_ok=True)
    problemas_tmp.unlink(missing_ok=True)
    raise
print('ZIPs:', len(zips), '| Meses nos registros regulares:', ', '.join(sorted(meses, key=lambda x: int(x) if x.isdigit() else 99)))
print('Registros filtrados:', total, '| Linhas irregulares excluídas:', irregulares)
print('Saída:', saida)
print('Validação:', problemas)
if len(meses) < 12:
    print('ATENÇÃO: menos de 12 meses encontrados. Verifique arquivos ZIP e relatório de irregularidades.')
