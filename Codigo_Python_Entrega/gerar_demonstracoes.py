"""
Gera as saídas das demonstrações usadas no vídeo, para não precisar rodar
nada ao vivo durante a apresentação.

Cada demonstração é executada de verdade e a saída do terminal é salva em
resultados/demonstracoes/, com o comando usado no topo do arquivo.

Uso:
  python gerar_demonstracoes.py
"""

import datetime
import os
import subprocess
import sys
import time

PASTA = os.path.join("resultados", "demonstracoes")
PORTAS = (5001, 5002, 5003, 5004)
WORKERS = ",".join(f"127.0.0.1:{p}" for p in PORTAS)
# Mesmo cenário em todas as versões, para comparar tempos e contagens.
GRADE = ["--linhas", "400", "--colunas", "400", "--geracoes", "10", "--limiar", "2"]

DEMOS = [
    ("1_sequencial.txt", ["FakeNews.py", *GRADE]),
    ("2_threads.txt", ["FakeNewsParalela.py", *GRADE, "--threads", "4"]),
    ("3_multiprocessing.txt", ["FakeNewsMultiprocessing.py", *GRADE, "--processos", "4"]),
    ("4_distribuida_halo.txt",
     ["FakeNewsDistribuida.py", "coordinator", "--workers", WORKERS, *GRADE]),
    ("5_distribuida_faixa.txt",
     ["FakeNewsDistribuida.py", "coordinator", "--workers", WORKERS, *GRADE,
      "--modo", "faixa"]),
    ("6_testes.txt", ["-m", "unittest", "-v", "test_implementacoes.py"]),
]

AMBIENTE = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def executar(arquivo, argumentos):
    comando = [sys.executable, *argumentos]
    exibido = "python " + " ".join(argumentos)
    print(f"-> {exibido}")
    saida = subprocess.run(comando, capture_output=True, text=True,
                           encoding="utf-8", env=AMBIENTE)
    with open(os.path.join(PASTA, arquivo), "w", encoding="utf-8") as f:
        f.write(f"$ {exibido}\n")
        f.write(f"# gerado em {datetime.datetime.now():%Y-%m-%d %H:%M}\n\n")
        f.write(saida.stdout)
        f.write(saida.stderr)  # o unittest escreve o relatório no stderr
    if saida.returncode != 0:
        raise SystemExit(f"Falhou: {exibido}")


def main():
    os.makedirs(PASTA, exist_ok=True)
    workers = [
        subprocess.Popen(
            [sys.executable, "FakeNewsDistribuida.py", "worker", "--port", str(porta)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=AMBIENTE,
        )
        for porta in PORTAS
    ]
    try:
        time.sleep(2)  # tempo para os workers abrirem as portas
        for arquivo, argumentos in DEMOS:
            executar(arquivo, argumentos)
    finally:
        for worker in workers:
            worker.terminate()
    print(f"Saídas salvas em {os.path.abspath(PASTA)}")


if __name__ == "__main__":
    main()
