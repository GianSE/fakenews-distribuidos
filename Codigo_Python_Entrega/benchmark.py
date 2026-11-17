"""
Benchmark das versões sequencial, threads, multiprocessing e distribuída.

Experimentos (cada medição é repetida N vezes; usamos média e desvio):
  1. Escalabilidade: cenário base com 1, 2, 4 e 8 threads/processos/workers.
  2. Cenários ("tamanho", "geracoes", "percentual"): varia um fator por vez em relação ao cenário base
     (tamanho da matriz, número de gerações, percentual de espalhadores),
     sempre com 4 threads/processos/workers.
  3. Modelo estendido: cenário base com todas as extensões ligadas.

Todas as execuções rodam o número fixo de gerações (não param quando os
espalhadores acabam), para que o trabalho seja o mesmo em todas as versões.
A grade final de cada versão é comparada com a sequencial.

Os trabalhadores distribuídos são processos separados (python
FakeNewsDistribuida.py worker) na mesma máquina, conectados por TCP
via 127.0.0.1.

Uso:
  python benchmark.py                  # completo (~12 min)
  python benchmark.py --rapido         # versão curta para testar (~1 min)
  python benchmark.py --repeticoes 5

Saída: resultados/benchmark.csv e resultados/ambiente.txt
Depois rode: python gerar_graficos.py
"""

import argparse
import csv
import os
import platform
import socket
import statistics
import subprocess
import sys
import time

import FakeNews
import FakeNewsDistribuida
import FakeNewsMultiprocessing
import FakeNewsParalela
from FakeNews import Modelo

PASTA_RESULTADOS = "resultados"
LIMIAR = 3
MODELO_ESTENDIDO = Modelo(
    limiar=2, beta=0.5, pct_influenciadores=0.02, pct_bots=0.005,
    pct_ceticos=0.2, semente=42,
)


def porta_livre():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        return servidor.getsockname()[1]


def iniciar_workers(quantidade):
    """Sobe 'quantidade' processos trabalhadores e espera as portas abrirem."""
    portas = [porta_livre() for _ in range(quantidade)]
    processos = [
        subprocess.Popen(
            [sys.executable, "FakeNewsDistribuida.py", "worker",
             "--host", "127.0.0.1", "--port", str(porta)],
            stdout=subprocess.DEVNULL,
        )
        for porta in portas
    ]
    enderecos = [("127.0.0.1", porta) for porta in portas]
    limite = time.time() + 20
    while True:
        try:
            FakeNewsDistribuida.encerrar_trabalhadores(
                FakeNewsDistribuida.conectar_trabalhadores(enderecos, 1))
            return processos, enderecos
        except OSError:
            if time.time() > limite:
                raise RuntimeError("Os trabalhadores não ficaram disponíveis")
            time.sleep(0.1)


def executar(versao, trabalhadores, cenario, modelo, enderecos):
    """Executa uma versão uma vez e devolve o dicionário de resultado."""
    argumentos = dict(
        linhas=cenario["linhas"], colunas=cenario["colunas"],
        geracoes=cenario["geracoes"],
        percentual_espalhadores=cenario["percentual"],
        verboso=False, parar_sem_espalhadores=False,
    )
    if versao == "sequencial":
        return FakeNews.executar_simulacao(limiar_convencimento=modelo, **argumentos)
    if versao == "threads":
        return FakeNewsParalela.executar_simulacao(
            modelo=modelo, threads=trabalhadores, **argumentos)
    if versao == "multiprocessing":
        return FakeNewsMultiprocessing.executar_simulacao(
            modelo=modelo, processos=trabalhadores, **argumentos)
    modo = versao.split("-")[1]  # distribuida-halo / distribuida-faixa
    return FakeNewsDistribuida.executar_simulacao(
        modelo=modelo, trabalhadores=enderecos[:trabalhadores], modo=modo,
        **argumentos)


def medir(versao, trabalhadores, cenario, modelo, enderecos, repeticoes):
    """Repete a execução e resume tempos e métricas de comunicação."""
    execucoes = [
        executar(versao, trabalhadores, cenario, modelo, enderecos)
        for _ in range(repeticoes)
    ]
    tempos = [e["tempo"] for e in execucoes]
    medida = {
        "tempo_medio": statistics.mean(tempos),
        "tempo_desvio": statistics.stdev(tempos) if len(tempos) > 1 else 0.0,
        "grade": execucoes[0]["grade"],
        "bytes_por_geracao": "",
        "tempo_calculo": "",
        "tempo_comunicacao": "",
    }
    if versao.startswith("distribuida"):
        medida["bytes_por_geracao"] = round(
            statistics.mean(e["bytes_trafegados"] for e in execucoes)
            / cenario["geracoes"])
        medida["tempo_calculo"] = statistics.mean(e["tempo_calculo"] for e in execucoes)
        medida["tempo_comunicacao"] = statistics.mean(
            e["tempo_comunicacao"] for e in execucoes)
    return medida


def nome_cpu():
    """Nome do processador (Windows ou Linux)."""
    try:
        if sys.platform == "win32":
            import winreg
            chave = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(chave, "ProcessorNameString")[0].strip()
        with open("/proc/cpuinfo", encoding="utf-8") as arquivo:
            for linha in arquivo:
                if linha.startswith("model name"):
                    return linha.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def memoria_gb():
    """Memória RAM total em GB (Windows ou Linux)."""
    try:
        if sys.platform == "win32":
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = Status()
            status.dwLength = ctypes.sizeof(Status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 1024 ** 3
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except (OSError, AttributeError, ValueError):
        return float("nan")


def salvar_ambiente(repeticoes):
    texto = [
        f"Processador: {nome_cpu()}",
        f"Núcleos lógicos: {os.cpu_count()}",
        f"Memória RAM (visível ao SO): {memoria_gb():.1f} GB",
        f"Sistema operacional: {platform.platform()}",
        f"Python: {platform.python_implementation()} {platform.python_version()}",
        f"GIL ativo: {FakeNewsParalela.gil_ativo()}",
        f"Repetições por medição: {repeticoes}",
        f"Data: {time.strftime('%Y-%m-%d %H:%M')}",
    ]
    with open(os.path.join(PASTA_RESULTADOS, "ambiente.txt"), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(texto) + "\n")
    print("\n".join(texto))


def montar_plano(rapido):
    """Lista de (experimento, cenário, nome do modelo, versão, trabalhadores)."""
    if rapido:
        base = dict(linhas=120, colunas=120, geracoes=5, percentual=0.05)
        tamanhos, geracoes, percentuais = (80, 120), (5, 10), (0.01, 0.05)
    else:
        base = dict(linhas=400, colunas=400, geracoes=20, percentual=0.05)
        tamanhos, geracoes, percentuais = (200, 400, 800), (10, 20, 40), (0.01, 0.05, 0.10)

    paralelas = ("threads", "multiprocessing", "distribuida-halo", "distribuida-faixa")
    plano = [("escalabilidade", base, "original", "sequencial", 1)]
    for versao in paralelas:
        for quantidade in (1, 2, 4, 8):
            plano.append(("escalabilidade", base, "original", versao, quantidade))

    # O nome do experimento é o fator variado (o resto fica igual à base).
    cenarios = [("tamanho", dict(base, linhas=t, colunas=t)) for t in tamanhos]
    cenarios += [("geracoes", dict(base, geracoes=g)) for g in geracoes]
    cenarios += [("percentual", dict(base, percentual=p)) for p in percentuais]
    for fator, cenario in cenarios:
        plano.append((fator, cenario, "original", "sequencial", 1))
        for versao in paralelas:
            plano.append((fator, cenario, "original", versao, 4))

    plano.append(("modelo", base, "estendido", "sequencial", 1))
    for versao in paralelas:
        plano.append(("modelo", base, "estendido", versao, 4))
    return plano


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeticoes", type=int, default=3)
    parser.add_argument("--rapido", action="store_true")
    args = parser.parse_args()

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    salvar_ambiente(args.repeticoes)
    plano = montar_plano(args.rapido)
    modelos = {"original": Modelo(limiar=LIMIAR), "estendido": MODELO_ESTENDIDO}

    processos, enderecos = iniciar_workers(8)
    cache = {}       # evita medir duas vezes o mesmo caso (cenário base)
    linhas_csv = []
    try:
        for numero, (experimento, cenario, nome_modelo, versao, quantidade) in enumerate(plano, 1):
            chave_cenario = (tuple(sorted(cenario.items())), nome_modelo)
            chave = chave_cenario + (versao, quantidade)
            if chave not in cache:
                cache[chave] = medir(versao, quantidade, cenario, modelos[nome_modelo],
                                     enderecos, args.repeticoes)
            medida = cache[chave]
            referencia = cache[chave_cenario + ("sequencial", 1)]
            speedup = referencia["tempo_medio"] / medida["tempo_medio"]
            igual = medida["grade"] == referencia["grade"]
            linhas_csv.append({
                "experimento": experimento,
                **cenario,
                "modelo": nome_modelo,
                "versao": versao,
                "trabalhadores": quantidade,
                "tempo_medio": f"{medida['tempo_medio']:.4f}",
                "tempo_desvio": f"{medida['tempo_desvio']:.4f}",
                "speedup": f"{speedup:.3f}",
                "eficiencia": f"{speedup / quantidade:.3f}",
                "bytes_por_geracao": medida["bytes_por_geracao"],
                "tempo_calculo": (f"{medida['tempo_calculo']:.4f}"
                                  if medida["tempo_calculo"] != "" else ""),
                "tempo_comunicacao": (f"{medida['tempo_comunicacao']:.4f}"
                                      if medida["tempo_comunicacao"] != "" else ""),
                "igual_sequencial": igual,
            })
            print(f"[{numero:02d}/{len(plano)}] {experimento:<14} "
                  f"{cenario['linhas']}x{cenario['colunas']} g={cenario['geracoes']} "
                  f"p={cenario['percentual']:.2f} {nome_modelo:<9} {versao:<17} "
                  f"n={quantidade} | {medida['tempo_medio']:.3f} s "
                  f"| speedup {speedup:.2f} | {'OK' if igual else 'DIFERENTE!'}",
                  flush=True)
    finally:
        for processo in processos:
            processo.terminate()

    caminho = os.path.join(PASTA_RESULTADOS, "benchmark.csv")
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas_csv[0]))
        escritor.writeheader()
        escritor.writerows(linhas_csv)
    print(f"\nResultados salvos em: {os.path.abspath(caminho)}")
    if not all(linha["igual_sequencial"] for linha in linhas_csv):
        print("ATENÇÃO: alguma versão divergiu da sequencial!")


if __name__ == "__main__":
    main()
