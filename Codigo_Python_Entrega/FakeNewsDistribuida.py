"""
Simulação distribuída: um coordenador e N trabalhadores via sockets TCP.

Uso (cada comando em um terminal; os trabalhadores podem estar em outras
máquinas, basta trocar 127.0.0.1 pelo IP delas):
  python FakeNewsDistribuida.py worker --port 5001
  python FakeNewsDistribuida.py worker --port 5002
  python FakeNewsDistribuida.py coordinator --workers 127.0.0.1:5001,127.0.0.1:5002

Divisão: a matriz é dividida em faixas horizontais de linhas
(dividir_linhas), uma por trabalhador.

Dois modos de comunicação (--modo):

  halo (padrão, MELHORIA):
    Cada trabalhador recebe sua faixa UMA vez e a mantém em memória. A cada
    geração, o coordenador envia a cada trabalhador apenas as duas linhas de
    fronteira dos vizinhos (halo) e recebe de volta as suas novas linhas de
    fronteira e a contagem de estados da faixa. É a troca de fronteiras
    (halo exchange) usada em decomposição de domínio (Foster, 1995).
    Tráfego por geração e por trabalhador: ~4 linhas.

  faixa (versão inicial, mantida para comparação):
    Trabalhadores não guardam estado. A cada geração o coordenador envia a
    faixa inteira + halo e recebe a faixa calculada.
    Tráfego por geração e por trabalhador: ~2 x (linhas / N) linhas.

Sincronização: nos dois modos o coordenador só inicia a geração g+1 depois
de receber a resposta de TODOS os trabalhadores para a geração g (barreira).
Como o halo enviado na geração g+1 é exatamente a fronteira calculada na
geração g, todo trabalhador sempre lê a mesma geração.

Protocolo: cada mensagem é um objeto Python serializado com pickle e
precedido por um cabeçalho de 4 bytes (big-endian) com o tamanho. O
cabeçalho é necessário porque TCP é um fluxo de bytes: um recv() pode
devolver só parte da mensagem. As linhas viajam compactadas em bytes
(1 byte por célula).

Segurança: pickle.loads() pode executar código ao desserializar dados
maliciosos. Use apenas em rede confiável (laboratório). Isso é uma
limitação conhecida e documentada.
"""

import argparse
import pickle
import socket
import struct
import time

from FakeNews import (
    ESPALHADOR,
    INATIVO,
    IGNORANTE,
    adicionar_argumentos,
    calcular_linhas,
    como_modelo,
    compactar_linhas,
    contar_estados,
    criar_populacao,
    descompactar_linhas,
    imprimir_geracao,
    imprimir_grade,
    imprimir_resumo,
    modelo_dos_argumentos,
)
from FakeNewsParalela import dividir_linhas, intervalo_com_halo

HOST_PADRAO = "0.0.0.0"
CABECALHO = struct.Struct("!I")  # 4 bytes, inteiro sem sinal, ordem de rede


class Canal:
    """
    Uma conexão TCP com mensagens delimitadas por tamanho.
    Também conta os bytes trafegados (usado na análise de comunicação).
    """

    def __init__(self, conexao):
        self.conexao = conexao
        # Desliga o algoritmo de Nagle: as mensagens de halo são pequenas e
        # não devem ficar esperando para serem agrupadas.
        conexao.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.bytes_enviados = 0
        self.bytes_recebidos = 0

    def enviar(self, valor):
        """Serializa 'valor' e envia [tamanho][dados]."""
        dados = pickle.dumps(valor, protocol=pickle.HIGHEST_PROTOCOL)
        self.conexao.sendall(CABECALHO.pack(len(dados)) + dados)
        self.bytes_enviados += CABECALHO.size + len(dados)

    def receber(self):
        """Lê o cabeçalho, depois exatamente 'tamanho' bytes, e desserializa."""
        tamanho = CABECALHO.unpack(self._receber_exatamente(CABECALHO.size))[0]
        if tamanho == 0:
            raise ConnectionError("Mensagem TCP inválida")
        dados = self._receber_exatamente(tamanho)
        self.bytes_recebidos += CABECALHO.size + tamanho
        return pickle.loads(dados)

    def _receber_exatamente(self, quantidade):
        """recv() pode devolver menos bytes que o pedido: repete até completar."""
        partes = []
        restante = quantidade
        while restante:
            parte = self.conexao.recv(restante)
            if not parte:
                raise ConnectionError("Conexão encerrada durante uma mensagem")
            partes.append(parte)
            restante -= len(parte)
        return b"".join(partes)

    def fechar(self):
        self.conexao.close()


# ----------------------------------------------------------------------
# Trabalhador
# ----------------------------------------------------------------------

def executar_worker(host, port, verboso=True):
    """
    Servidor TCP do trabalhador. Atende um coordenador por vez; ao fim de
    uma sessão volta a aguardar outra (não é preciso reiniciar o worker
    entre execuções). Ctrl+C encerra.
    """
    def log(texto):
        if verboso:
            print(texto, flush=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, port))
        servidor.listen()
        # Timeout no accept() para o Ctrl+C funcionar no Windows.
        servidor.settimeout(1.0)
        log(f"Trabalhador aguardando conexões em {host}:{port}")
        while True:
            try:
                conexao, endereco = servidor.accept()
            except socket.timeout:
                continue
            conexao.settimeout(None)
            with conexao:
                log(f"Coordenador conectado: {endereco}")
                try:
                    atender_coordenador(Canal(conexao))
                except ConnectionError as erro:
                    log(f"Sessão interrompida: {erro}")
                log("Sessão encerrada; aguardando novo coordenador")


def atender_coordenador(canal):
    """
    Laço de comandos de uma sessão.
      calcular -> modo faixa (sem estado)
      iniciar / passo / coletar -> modo halo (faixa guardada no worker)
      encerrar -> fim da sessão
    """
    faixa = None  # estado do modo halo
    while True:
        mensagem = canal.receber()
        comando = mensagem["comando"]

        if comando == "encerrar":
            return

        if comando == "calcular":
            # Modo faixa: recebe faixa + halo, devolve só as linhas da faixa.
            inicio_local = mensagem["inicio"] - mensagem["deslocamento"]
            fim_local = mensagem["fim"] - mensagem["deslocamento"]
            inicio_calculo = time.perf_counter()
            novas = calcular_linhas(
                mensagem["linhas"], inicio_local, fim_local,
                mensagem["modelo"], mensagem["perfis"],
                mensagem["geracao"], mensagem["deslocamento"],
            )
            canal.enviar({
                "inicio": mensagem["inicio"],
                "linhas": compactar_linhas(novas),
                "tempo_calculo": time.perf_counter() - inicio_calculo,
            })

        elif comando == "iniciar":
            # Modo halo: guarda a faixa e os dados fixos da sessão.
            faixa = descompactar_linhas(mensagem["linhas"])
            inicio = mensagem["inicio"]
            tem_cima = inicio > 0
            tem_baixo = mensagem["fim"] < mensagem["total_linhas"]
            perfis = mensagem["perfis"]  # já alinhados com faixa + halo
            modelo = mensagem["modelo"]
            canal.enviar({"ok": True})

        elif comando == "passo":
            # Monta faixa local = [halo de cima] + faixa + [halo de baixo].
            local = faixa
            inicio_local = 0
            if tem_cima:
                local = [mensagem["cima"]] + local
                inicio_local = 1
            if tem_baixo:
                local = local + [mensagem["baixo"]]
            inicio_calculo = time.perf_counter()
            faixa = calcular_linhas(
                local, inicio_local, inicio_local + len(faixa),
                modelo, perfis, mensagem["geracao"], inicio - inicio_local,
            )
            tempo_calculo = time.perf_counter() - inicio_calculo
            canal.enviar({
                "topo": bytes(faixa[0]),     # fronteiras para os vizinhos
                "base": bytes(faixa[-1]),
                "contagem": contar_estados(faixa),
                "tempo_calculo": tempo_calculo,
            })

        elif comando == "coletar":
            canal.enviar({"linhas": compactar_linhas(faixa)})

        else:
            raise ValueError(f"Comando distribuído desconhecido: {comando}")


# ----------------------------------------------------------------------
# Coordenador
# ----------------------------------------------------------------------

def conectar_trabalhadores(enderecos, timeout=30):
    """Abre um Canal para cada (host, porta). Fecha todos se algum falhar."""
    canais = []
    try:
        for host, port in enderecos:
            conexao = socket.create_connection((host, port), timeout=timeout)
            conexao.settimeout(timeout)
            canais.append(Canal(conexao))
    except Exception:
        for canal in canais:
            canal.fechar()
        raise
    return canais


def encerrar_trabalhadores(canais):
    """Avisa cada trabalhador que a sessão acabou e fecha a conexão."""
    for canal in canais:
        try:
            canal.enviar({"comando": "encerrar"})
        except OSError:
            pass
        finally:
            canal.fechar()


# --- modo faixa ---

def proxima_geracao_faixas(canais, grade, modelo, perfis, geracao):
    """
    Modo faixa: envia faixa + halo para cada trabalhador e remonta a grade.
    Retorna (nova_grade, maior tempo de cálculo entre os trabalhadores).
    """
    intervalos = dividir_linhas(len(grade), len(canais))
    # 1) envia para todos (os trabalhadores calculam em paralelo)
    for canal, (inicio, fim) in zip(canais, intervalos):
        halo_inicio, halo_fim = intervalo_com_halo(len(grade), inicio, fim)
        canal.enviar({
            "comando": "calcular",
            "linhas": compactar_linhas(grade[halo_inicio:halo_fim]),
            "perfis": None if perfis is None else perfis[halo_inicio:halo_fim],
            "deslocamento": halo_inicio,
            "inicio": inicio,
            "fim": fim,
            "modelo": modelo,
            "geracao": geracao,
        })
    # 2) recebe de todos (barreira)
    nova_grade = []
    maior_tempo = 0.0
    for canal, (inicio, fim) in zip(canais, intervalos):
        resposta = canal.receber()
        if resposta["inicio"] != inicio or len(resposta["linhas"]) != fim - inicio:
            raise RuntimeError("Resposta de trabalhador não corresponde à partição")
        nova_grade.extend(descompactar_linhas(resposta["linhas"]))
        maior_tempo = max(maior_tempo, resposta["tempo_calculo"])
    return nova_grade, maior_tempo


# --- modo halo ---

def distribuir_faixas(canais, grade, modelo, perfis):
    """
    Modo halo: envia a faixa de cada trabalhador uma única vez.
    Retorna a lista de fronteiras (primeira linha, última linha) de cada faixa.
    """
    total = len(grade)
    intervalos = dividir_linhas(total, len(canais))
    for canal, (inicio, fim) in zip(canais, intervalos):
        halo_inicio, halo_fim = intervalo_com_halo(total, inicio, fim)
        canal.enviar({
            "comando": "iniciar",
            "linhas": compactar_linhas(grade[inicio:fim]),
            "perfis": None if perfis is None else perfis[halo_inicio:halo_fim],
            "inicio": inicio,
            "fim": fim,
            "total_linhas": total,
            "modelo": modelo,
        })
    for canal in canais:
        canal.receber()
    return [(bytes(grade[inicio]), bytes(grade[fim - 1])) for inicio, fim in intervalos]


def passo_halo(canais, fronteiras, geracao):
    """
    Uma geração no modo halo. O trabalhador k recebe a última linha do
    trabalhador k-1 (halo de cima) e a primeira do k+1 (halo de baixo).
    Retorna (novas fronteiras, contagem global, maior tempo de cálculo).
    """
    n = len(canais)
    for k, canal in enumerate(canais):
        canal.enviar({
            "comando": "passo",
            "geracao": geracao,
            "cima": fronteiras[k - 1][1] if k > 0 else None,
            "baixo": fronteiras[k + 1][0] if k < n - 1 else None,
        })
    respostas = [canal.receber() for canal in canais]  # barreira

    contagem = {IGNORANTE: 0, ESPALHADOR: 0, INATIVO: 0}
    for resposta in respostas:
        for estado, quantidade in resposta["contagem"].items():
            contagem[estado] += quantidade
    novas_fronteiras = [(r["topo"], r["base"]) for r in respostas]
    maior_tempo = max(r["tempo_calculo"] for r in respostas)
    return novas_fronteiras, contagem, maior_tempo


def coletar_faixas(canais):
    """Modo halo: busca as faixas de todos os trabalhadores e monta a grade."""
    for canal in canais:
        canal.enviar({"comando": "coletar"})
    grade = []
    for canal in canais:
        grade.extend(descompactar_linhas(canal.receber()["linhas"]))
    return grade


def executar_simulacao(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    modelo=2,
    trabalhadores=(("127.0.0.1", 5001),),
    modo="halo",
    mostrar_grade=False,
    verboso=True,
    parar_sem_espalhadores=True,
):
    """
    Executa a simulação distribuída. Além do retorno da sequencial, informa:
      bytes_trafegados: total enviado + recebido pelo coordenador;
      tempo_calculo: soma, por geração, do tempo do trabalhador mais lento;
      tempo_comunicacao: tempo - tempo_calculo (rede, serialização, espera).
    A conexão com os trabalhadores fica fora do tempo medido.
    """
    if modo not in ("halo", "faixa"):
        raise ValueError("modo deve ser 'halo' ou 'faixa'")
    modelo = como_modelo(modelo)
    grade, perfis = criar_populacao(linhas, colunas, percentual_espalhadores, modelo)
    historico = [contar_estados(grade)]

    canais = conectar_trabalhadores(trabalhadores)
    # Se houver mais trabalhadores que linhas, os excedentes ficam ociosos.
    ativos = canais[:len(dividir_linhas(linhas, len(canais)))]
    if verboso:
        print(f"=== VERSÃO DISTRIBUÍDA: {len(ativos)} trabalhadores | modo {modo} ===")

    tempo_calculo = 0.0
    try:
        inicio_tempo = time.perf_counter()
        if modo == "halo":
            fronteiras = distribuir_faixas(ativos, grade, modelo, perfis)
        for geracao in range(geracoes):
            if modo == "halo":
                fronteiras, contagem, maior = passo_halo(ativos, fronteiras, geracao)
            else:
                grade, maior = proxima_geracao_faixas(ativos, grade, modelo, perfis, geracao)
                contagem = contar_estados(grade)
            tempo_calculo += maior
            historico.append(contagem)
            if verboso:
                imprimir_geracao(geracao + 1, contagem)
                if mostrar_grade:
                    imprimir_grade(coletar_faixas(ativos) if modo == "halo" else grade)
            if parar_sem_espalhadores and contagem[ESPALHADOR] == 0:
                break
        if modo == "halo":
            grade = coletar_faixas(ativos)
        tempo = time.perf_counter() - inicio_tempo
    finally:
        bytes_trafegados = sum(c.bytes_enviados + c.bytes_recebidos for c in canais)
        encerrar_trabalhadores(canais)

    if verboso:
        print(f"Bytes trafegados: {bytes_trafegados:,} | "
              f"cálculo: {tempo_calculo:.4f} s | "
              f"comunicação/sincronização: {tempo - tempo_calculo:.4f} s")
        imprimir_resumo(historico, tempo)
    return {
        "grade": grade,
        "historico": historico,
        "tempo": tempo,
        "bytes_trafegados": bytes_trafegados,
        "tempo_calculo": tempo_calculo,
        "tempo_comunicacao": tempo - tempo_calculo,
    }


def ler_enderecos(valor):
    """'host1:5001,host2:5002' -> [('host1', 5001), ('host2', 5002)]"""
    enderecos = []
    for item in valor.split(","):
        host, porta = item.strip().rsplit(":", 1)
        enderecos.append((host, int(porta)))
    return enderecos


def main():
    parser = argparse.ArgumentParser(description="Versão distribuída com sockets TCP")
    subparsers = parser.add_subparsers(dest="papel", required=True)
    worker = subparsers.add_parser("worker", help="inicia um trabalhador")
    worker.add_argument("--host", default=HOST_PADRAO)
    worker.add_argument("--port", type=int, required=True)
    coordinator = subparsers.add_parser("coordinator", help="inicia o coordenador")
    coordinator.add_argument("--workers", required=True,
                             help="lista host:porta separada por vírgulas")
    coordinator.add_argument("--modo", choices=("halo", "faixa"), default="halo")
    adicionar_argumentos(coordinator)
    args = parser.parse_args()
    if args.papel == "worker":
        executar_worker(args.host, args.port)
    else:
        executar_simulacao(
            args.linhas, args.colunas, args.geracoes, args.percentual,
            modelo_dos_argumentos(args), ler_enderecos(args.workers),
            args.modo, args.mostrar_grade,
        )


if __name__ == "__main__":
    main()
