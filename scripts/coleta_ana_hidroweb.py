"""Coleta do nível do Guaíba em Porto Alegre na API HidroWebService da ANA.

Fonte: Agência Nacional de Águas e Saneamento Básico (ANA)
API:   https://www.ana.gov.br/hidrowebservice (documentação em /swagger-ui/index.html)

É a fonte principal do projeto. O serviço antigo (scripts/coleta_ana_guaiba.py,
dados em dados/originais/ana/) fica guardado para conferência.

Baixa e guarda as respostas JSON como vieram, sem nenhum tratamento, em
dados/originais/ana_hidroweb/. Arquivos já baixados não são requisitados de
novo (exceto os períodos recentes, que ainda recebem dados). Cada requisição
fica registrada em dados/originais/ana_hidroweb/coleta_log.csv com a URL e a
data de coleta.

Credenciais: a API exige usuário e senha fornecidos pela ANA. Eles NÃO vão para
o código nem para o repositório. Crie um arquivo .env na raiz do projeto (já
está no .gitignore) com:

    ANA_IDENTIFICADOR=seu_usuario
    ANA_SENHA=sua_senha

Uso:
    python scripts/coleta_ana_hidroweb.py            # baixa só o que falta
    python scripts/coleta_ana_hidroweb.py --forcar   # baixa tudo de novo
    python scripts/coleta_ana_hidroweb.py --testar   # uma requisição de teste, sem salvar

Limites da API (documentação oficial):
- Telemetria: no máximo 30 dias por requisição.
- Cotas das estações convencionais: no máximo 366 dias por requisição.
- O token de acesso vale 60 minutos. Ele é reaproveitado e só renovado quando
  perto de vencer, porque autenticações seguidas podem bloquear o IP.
"""

import argparse
import csv
import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

URL_BASE = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"

RAIZ = Path(__file__).resolve().parents[1]
PASTA_SAIDA = RAIZ / "dados" / "originais" / "ana_hidroweb"
ARQUIVO_LOG = PASTA_SAIDA / "coleta_log.csv"

# Estações telemétricas (leituras a cada 15 min): código -> (nome, primeiro dia com dados)
ESTACOES_TELEMETRICAS = {
    87450004: ("Cais Mauá C6", date(2014, 7, 1)),
    87444000: ("Usina do Gasômetro (cheia 2024)", date(2024, 5, 1)),
    87450020: ("Usina do Gasômetro", date(2024, 5, 1)),
}

# Estações convencionais (cotas diárias, leitura manual): código -> (nome, primeiro ano, último ano)
ESTACOES_CONVENCIONAIS = {
    87450000: ("Porto Alegre", 1929, 1980),  # inclui a cheia de 1941
    87450003: ("Praça da Harmonia", 1941, 2008),
}

DIAS_POR_JANELA = 30  # limite da telemetria
PAUSA_SEGUNDOS = 1.0
TIMEOUT_SEGUNDOS = 120
TENTATIVAS = 3
VALIDADE_TOKEN = timedelta(minutes=50)  # o token vale 60 min; renova com folga

falhas = []  # arquivos que não puderam ser baixados nesta execução


def carregar_credenciais():
    """Lê ANA_IDENTIFICADOR e ANA_SENHA do ambiente ou do arquivo .env."""
    arquivo = RAIZ / ".env"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
    identificador, senha = os.environ.get("ANA_IDENTIFICADOR"), os.environ.get("ANA_SENHA")
    if not identificador or not senha:
        raise SystemExit("Credenciais não encontradas: defina ANA_IDENTIFICADOR e ANA_SENHA no arquivo .env")
    return identificador, senha


class ClienteANA:
    """Faz as requisições à API, reaproveitando o token enquanto ele vale."""

    def __init__(self, identificador, senha):
        self.identificador = identificador
        self.senha = senha
        self.token = None
        self.obtido_em = None

    def autenticar(self):
        resposta = requests.get(f"{URL_BASE}/OAUth/v1", timeout=TIMEOUT_SEGUNDOS,
                                headers={"Identificador": self.identificador, "Senha": self.senha})
        resposta.raise_for_status()
        itens = resposta.json().get("items") or {}
        self.token = itens.get("tokenautenticacao")
        if not self.token:
            raise SystemExit(f"Autenticação falhou: {resposta.json().get('message')}")
        self.obtido_em = datetime.now()
        print("  token obtido")

    def get(self, rota, parametros):
        if self.token is None or datetime.now() - self.obtido_em > VALIDADE_TOKEN:
            self.autenticar()
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                resposta = requests.get(f"{URL_BASE}/{rota}", params=parametros, timeout=TIMEOUT_SEGUNDOS,
                                        headers={"Authorization": f"Bearer {self.token}"})
                if resposta.status_code == 401 and tentativa == 1:
                    self.autenticar()  # token recusado: renova uma vez
                    continue
                resposta.raise_for_status()
                return resposta
            except requests.RequestException as erro:
                print(f"  tentativa {tentativa} falhou: {erro}")
                if tentativa == TENTATIVAS:
                    raise
                time.sleep(PAUSA_SEGUNDOS * 5 * tentativa)


def baixar(cliente, rota, parametros, destino, forcar=False):
    """Baixa uma rota da API e salva a resposta bruta em `destino`."""
    if destino.exists() and not forcar:
        return
    try:
        resposta = cliente.get(rota, parametros)
    except requests.RequestException:
        # Falha do servidor depois de todas as tentativas: segue para o próximo arquivo.
        # Nada é salvo, então ele é baixado na próxima execução.
        falhas.append(destino)
        print(f"  falhou: {destino.relative_to(RAIZ)}")
        time.sleep(PAUSA_SEGUNDOS * 10)
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resposta.content)

    status = "ok" if resposta.json().get("items") else "sem_dados"
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


def parametros_telemetria(codigo, data_busca):
    return {
        "Código da Estação": codigo,
        "Tipo Filtro Data": "DATA_LEITURA",
        "Data de Busca (yyyy-MM-dd)": data_busca.isoformat(),
        "Range Intervalo de busca": f"DIAS_{DIAS_POR_JANELA}",
    }


def coletar_inventario(cliente, forcar):
    """Metadados das estações (nome, rio, coordenadas, responsável)."""
    print("Inventário das estações")
    for codigo in [*ESTACOES_TELEMETRICAS, *ESTACOES_CONVENCIONAIS]:
        baixar(cliente, "HidroInventarioEstacoes/v1", {"Código da Estação": codigo},
               PASTA_SAIDA / "inventario" / f"{codigo}.json", forcar)


def coletar_telemetria(cliente, forcar):
    """Séries telemétricas em janelas de 30 dias, um arquivo por janela.

    Cada janela é identificada pela data de busca, o último dia do período.
    """
    hoje = date.today()
    for codigo, (nome, inicio) in ESTACOES_TELEMETRICAS.items():
        print(f"Telemetria {codigo} - {nome}")
        fim_janela = inicio + timedelta(days=DIAS_POR_JANELA - 1)
        while fim_janela - timedelta(days=DIAS_POR_JANELA - 1) <= hoje:
            # Janelas recentes ainda recebem dados, então são sempre baixadas de novo
            recente = fim_janela >= hoje - timedelta(days=DIAS_POR_JANELA)
            baixar(cliente, "HidroinfoanaSerieTelemetricaAdotada/v1", parametros_telemetria(codigo, fim_janela),
                   PASTA_SAIDA / "telemetria" / str(codigo) / f"{codigo}_{fim_janela:%Y-%m-%d}.json",
                   forcar or recente)
            fim_janela += timedelta(days=DIAS_POR_JANELA)


def coletar_cotas(cliente, forcar):
    """Cotas diárias das estações convencionais, um arquivo por ano."""
    for codigo, (nome, primeiro_ano, ultimo_ano) in ESTACOES_CONVENCIONAIS.items():
        print(f"Cotas {codigo} - {nome}")
        for ano in range(primeiro_ano, ultimo_ano + 1):
            parametros = {
                "Código da Estação": codigo,
                "Tipo Filtro Data": "DATA_LEITURA",
                "Data Inicial (yyyy-MM-dd)": f"{ano}-01-01",
                "Data Final (yyyy-MM-dd)": f"{ano}-12-31",
            }
            baixar(cliente, "HidroSerieCotas/v1", parametros,
                   PASTA_SAIDA / "cotas" / str(codigo) / f"{codigo}_{ano}.json", forcar)


def testar(cliente):
    """Faz uma requisição pequena e mostra a estrutura da resposta, sem salvar nada."""
    resposta = cliente.get("HidroinfoanaSerieTelemetricaAdotada/v1", parametros_telemetria(87450004, date(2024, 4, 30)))
    corpo = resposta.json()
    itens = corpo.get("items") or []
    print(f"status: {corpo.get('status')} | mensagem: {corpo.get('message')} | itens: {len(itens)}")
    if itens:
        print("campos:", list(itens[0]))
        print("primeiro:", json.dumps(itens[0], ensure_ascii=False))
        print("último:  ", json.dumps(itens[-1], ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--forcar", action="store_true", help="baixa de novo arquivos que já existem")
    parser.add_argument("--testar", action="store_true", help="faz uma requisição de teste, sem salvar")
    args = parser.parse_args()

    cliente = ClienteANA(*carregar_credenciais())
    if args.testar:
        testar(cliente)
        return

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    coletar_inventario(cliente, args.forcar)
    coletar_telemetria(cliente, args.forcar)
    coletar_cotas(cliente, args.forcar)
    print(f"Concluído. Log em {ARQUIVO_LOG.relative_to(RAIZ)}")
    if falhas:
        print(f"\n{len(falhas)} arquivo(s) não baixado(s) por falha do servidor. Rode o script de novo para "
              "tentar só esses:")
        for destino in falhas:
            print(f"  {destino.relative_to(RAIZ)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
