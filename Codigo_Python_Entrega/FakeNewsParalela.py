"""
Simulação paralela usando threading.Thread.

Divisão: as linhas da matriz são divididas em faixas contíguas e
equilibradas (dividir_linhas). Cada thread calcula uma faixa.

Consistência e ausência de condição de corrida:
- a geração atual é SOMENTE LIDA por todas as threads;
- cada thread grava apenas na sua posição de 'parciais' (nenhuma posição é
  compartilhada entre threads), então não há escrita concorrente;
- o join() de todas as threads funciona como barreira: a nova geração só é
  montada depois que todas terminaram.

Limitação: no CPython com GIL, só uma thread executa bytecode Python por
vez, então esta versão não ganha desempenho em código CPU-bound. Em um
interpretador sem GIL (Python 3.14 "free-threaded", PEP 703/779) o mesmo
código roda em paralelo de verdade. Para paralelismo real com o Python
comum, veja FakeNewsMultiprocessing.py.

Uso:
  python FakeNewsParalela.py --linhas 300 --colunas 300 --geracoes 10 --threads 4
"""

import argparse
import sys
import threading
import time

from FakeNews import (
    ESPALHADOR,
    adicionar_argumentos,
    calcular_linhas,
    como_modelo,
    contar_estados,
    criar_populacao,
    imprimir_geracao,
    imprimir_grade,
    imprimir_resumo,
    modelo_dos_argumentos,
)


def dividir_linhas(total, partes):
    """
    Divide 'total' linhas em 'partes' intervalos [inicio, fim) equilibrados.
    As primeiras 'resto' partes recebem uma linha a mais. Nunca gera
    intervalos vazios (se houver mais partes que linhas, usa menos partes).

    Exemplo: dividir_linhas(10, 3) -> [(0, 4), (4, 7), (7, 10)]
    """
    partes = max(1, min(partes, total))
    base, resto = divmod(total, partes)
    intervalos = []
    inicio = 0
    for indice in range(partes):
        tamanho = base + (1 if indice < resto else 0)
        intervalos.append((inicio, inicio + tamanho))
        inicio += tamanho
    return intervalos


def intervalo_com_halo(total, inicio, fim):
    """
    Intervalo [inicio, fim) ampliado com uma linha de halo em cima e embaixo
    (quando existem). A vizinhança de Moore só alcança 1 linha de distância,
    então uma linha de halo de cada lado basta para calcular a faixa.
    Usado nas versões multiprocessing e distribuída, que não compartilham
    memória com o processo principal.
    """
    return max(0, inicio - 1), min(total, fim + 1)


def proxima_geracao_paralela(grade, threads=4, modelo=2, perfis=None, geracao=0):
    """Calcula a próxima geração dividindo as linhas entre threads explícitas."""
    if not grade or not grade[0]:
        raise ValueError("A grade não pode ser vazia")
    if threads < 1:
        raise ValueError("O número de threads deve ser positivo")
    modelo = como_modelo(modelo)

    intervalos = dividir_linhas(len(grade), threads)
    parciais = [None] * len(intervalos)  # posição k é escrita só pela thread k
    erros = []

    def trabalhador(indice, inicio, fim):
        try:
            parciais[indice] = calcular_linhas(
                grade, inicio, fim, modelo, perfis, geracao
            )
        except Exception as erro:  # repassa o erro para a thread principal
            erros.append(erro)

    execucoes = []
    for indice, (inicio, fim) in enumerate(intervalos):
        thread = threading.Thread(
            target=trabalhador,
            args=(indice, inicio, fim),
            name=f"fake-news-linhas-{inicio}-{fim}",
        )
        execucoes.append(thread)
        thread.start()

    # Barreira: espera todas as threads antes de publicar a nova geração.
    for thread in execucoes:
        thread.join()

    if erros:
        raise RuntimeError("Falha ao calcular uma partição da grade") from erros[0]

    nova_grade = []
    for parte in parciais:
        nova_grade.extend(parte)
    return nova_grade


def gil_ativo():
    """True se o interpretador atual usa GIL (Python comum)."""
    verificar = getattr(sys, "_is_gil_enabled", None)
    return True if verificar is None else verificar()


def executar_simulacao(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    modelo=2,
    threads=4,
    mostrar_grade=False,
    verboso=True,
    parar_sem_espalhadores=True,
):
    """Executa a simulação completa com threads. Mesmo retorno da sequencial."""
    modelo = como_modelo(modelo)
    grade, perfis = criar_populacao(linhas, colunas, percentual_espalhadores, modelo)
    historico = [contar_estados(grade)]
    if verboso:
        print(f"=== VERSÃO PARALELA: {threads} threads | "
              f"GIL {'ativo' if gil_ativo() else 'desativado'} ===")

    inicio_tempo = time.perf_counter()
    for geracao in range(geracoes):
        grade = proxima_geracao_paralela(grade, threads, modelo, perfis, geracao)
        contagem = contar_estados(grade)
        historico.append(contagem)
        if verboso:
            imprimir_geracao(geracao + 1, contagem)
            if mostrar_grade:
                imprimir_grade(grade)
        if parar_sem_espalhadores and contagem[ESPALHADOR] == 0:
            break
    tempo = time.perf_counter() - inicio_tempo

    if verboso:
        imprimir_resumo(historico, tempo)
    return {"grade": grade, "historico": historico, "tempo": tempo}


def main():
    parser = argparse.ArgumentParser(description="Versão paralela com threads")
    adicionar_argumentos(parser)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    executar_simulacao(
        args.linhas, args.colunas, args.geracoes, args.percentual,
        modelo_dos_argumentos(args), args.threads, args.mostrar_grade,
    )


if __name__ == "__main__":
    main()
