"""Coleta do nível do Guaíba em Porto Alegre no serviço público de telemetria da ANA.

Fonte: Agência Nacional de Águas e Saneamento Básico (ANA)
Serviço: https://telemetriaws1.ana.gov.br/ServiceANA.asmx (não exige cadastro)

Baixa e guarda as respostas XML como vieram, sem nenhum tratamento, em
dados/originais/ana/. Arquivos já baixados não são requisitados de novo
(exceto o ano corrente das séries telemétricas), para não sobrecarregar o
servidor. Cada requisição fica registrada em dados/originais/ana/coleta_log.csv
com a URL e a data de coleta.

Uso:
    python scripts/coleta_ana_guaiba.py            # baixa só o que falta
    python scripts/coleta_ana_guaiba.py --forcar   # baixa tudo de novo

Observações sobre os dados:
- O nível (cota) vem em centímetros, relativo ao zero da régua de cada estação.
  Réguas diferentes têm zeros diferentes e não podem ser comparadas direto.
- A régua do Cais Mauá C6 foi perdida durante a cheia de maio de 2024; o pico
  dessa cheia aparece na estação de emergência da Usina do Gasômetro.
"""

import argparse
import csv
import time
from datetime import date, datetime
from pathlib import Path

import requests

URL_BASE = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx"

RAIZ = Path(__file__).resolve().parents[1]
PASTA_SAIDA = RAIZ / "dados" / "originais" / "ana"
ARQUIVO_LOG = PASTA_SAIDA / "coleta_log.csv"

# Estações telemétricas (leituras a cada 15 min): código -> (nome, primeiro ano)
ESTACOES_TELEMETRICAS = {
    87450004: ("Cais Mauá C6", 2014),
    87444000: ("Usina do Gasômetro (cheia 2024)", 2024),
    87450020: ("Usina do Gasômetro", 2024),
}

# Estações convencionais (cotas diárias, leitura manual): código -> nome
ESTACOES_CONVENCIONAIS = {
    87450000: "Porto Alegre",  # 1929-1952, inclui a cheia de 1941
    87450003: "Praça da Harmonia",  # 1941-2008
}

PAUSA_SEGUNDOS = 1.0  # intervalo entre requisições
TIMEOUT_SEGUNDOS = 120
TENTATIVAS = 3


def baixar(rota, parametros, destino, forcar=False):
    """Baixa uma rota do serviço e salva a resposta bruta em `destino`."""
    if destino.exists() and not forcar:
        print(f"  já existe, pulando: {destino.relative_to(RAIZ)}")
        return

    url = f"{URL_BASE}/{rota}"
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(url, params=parametros, timeout=TIMEOUT_SEGUNDOS)
            resposta.raise_for_status()
            break
        except requests.RequestException as erro:
            print(f"  tentativa {tentativa} falhou: {erro}")
            if tentativa == TENTATIVAS:
                raise
            time.sleep(PAUSA_SEGUNDOS * 5 * tentativa)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resposta.content)

    # O serviço responde 200 mesmo sem dados, com uma tabela <Error>
    status = "sem_dados" if b"<Error>" in resposta.content else "ok"
    registrar_log(resposta.url, destino, status)
    print(f"  {status}: {destino.relative_to(RAIZ)} ({len(resposta.content):,} bytes)")
    time.sleep(PAUSA_SEGUNDOS)


def registrar_log(url, destino, status):
    novo = not ARQUIVO_LOG.exists()
    with ARQUIVO_LOG.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if novo:
            escritor.writerow(["data_coleta", "arquivo", "status", "url"])
        escritor.writerow([
            datetime.now().isoformat(timespec="seconds"),
            destino.relative_to(RAIZ).as_posix(),
            status,
            url,
        ])


def coletar_inventario(forcar):
    """Metadados das estações (nome, rio, coordenadas, responsável)."""
    print("Inventário das estações")
    for codigo in [*ESTACOES_TELEMETRICAS, *ESTACOES_CONVENCIONAIS]:
        parametros = {
            "codEstDE": codigo, "codEstATE": codigo, "tpEst": "", "nmEst": "",
            "nmRio": "", "codSubBacia": "", "codBacia": "", "nmMunicipio": "",
            "nmEstado": "", "sgResp": "", "sgOper": "", "telemetrica": "",
        }
        baixar("HidroInventario", parametros,
               PASTA_SAIDA / "inventario" / f"{codigo}.xml", forcar)


def coletar_telemetria(forcar):
    """Séries telemétricas, um arquivo por estação e por ano."""
    ano_atual = date.today().year
    for codigo, (nome, primeiro_ano) in ESTACOES_TELEMETRICAS.items():
        print(f"Telemetria {codigo} - {nome}")
        for ano in range(primeiro_ano, ano_atual + 1):
            parametros = {
                "codEstacao": codigo,
                "dataInicio": f"01/01/{ano}",
                "dataFim": f"31/12/{ano}",
            }
            # O ano corrente ainda recebe dados, então é sempre baixado de novo
            baixar("DadosHidrometeorologicos", parametros,
                   PASTA_SAIDA / "telemetria" / f"{codigo}_{ano}.xml",
                   forcar or ano == ano_atual)


def coletar_series_historicas(forcar):
    """Cotas diárias das estações convencionais, período completo."""
    for codigo, nome in ESTACOES_CONVENCIONAIS.items():
        print(f"Série histórica {codigo} - {nome}")
        parametros = {
            "codEstacao": codigo,
            "dataInicio": "01/01/1900",
            "dataFim": date.today().strftime("%d/%m/%Y"),
            "tipoDados": 1,  # 1 = cotas
            "nivelConsistencia": "",  # bruto e consistido
        }
        baixar("HidroSerieHistorica", parametros,
               PASTA_SAIDA / "serie_historica" / f"{codigo}_cotas.xml", forcar)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--forcar", action="store_true",
                        help="baixa de novo arquivos que já existem")
    args = parser.parse_args()

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    coletar_inventario(args.forcar)
    coletar_telemetria(args.forcar)
    coletar_series_historicas(args.forcar)
    print(f"Concluído. Log em {ARQUIVO_LOG.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
