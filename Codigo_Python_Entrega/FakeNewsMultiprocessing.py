"""
Simulação paralela usando multiprocessing (paralelismo real no CPython).

Por que existe: na versão com threads o GIL impede que duas threads
executem código Python ao mesmo tempo. Processos têm cada um seu próprio
interpretador e seu próprio GIL, então rodam de fato em núcleos diferentes.
O enunciado permite explicitamente o uso de multiprocessing.

Divisão: a MESMA da versão com threads (dividir_linhas). Cada tarefa é uma
faixa de linhas que nós montamos explicitamente; o Pool apenas mantém os
processos vivos entre as gerações (evita criar processos a cada geração).

Diferença em relação às threads: processos NÃO compartilham memória. Por
isso cada tarefa leva somente a sua faixa mais uma linha de halo em cima e
embaixo (intervalo_com_halo), compactada em bytes. A matriz de perfis não
muda durante a simulação, então é enviada uma única vez, na inicialização
de cada processo.

Barreira: pool.map() só retorna depois que todas as faixas da geração
foram calculadas.

Uso:
  python FakeNewsMultiprocessing.py --linhas 300 --colunas 300 --geracoes 10 --processos 4
"""

import argparse
import time
from multiprocessing import Pool

from FakeNews import (
    ESPALHADOR,
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

# Dados fixos de cada processo trabalhador (preenchidos em _inicializar).
_perfis_processo = None
_modelo_processo = None


def _inicializar(perfis, modelo):
    """Executado uma vez em cada processo do Pool, ao ser criado."""
    global _perfis_processo, _modelo_processo
    _perfis_processo = perfis
    _modelo_processo = modelo


def _pronto(_):
    """Tarefa vazia usada para garantir que todos os processos já subiram."""
    return True


def _calcular_faixa(tarefa):
    """
    Executado dentro de um processo trabalhador.
    tarefa = (linha global da 1ª linha local, linhas locais em bytes,
              inicio global, fim global, geração)
    """
    deslocamento, linhas_locais, inicio, fim, geracao = tarefa
    perfis_locais = None
    if _perfis_processo is not None:
        perfis_locais = _perfis_processo[deslocamento:deslocamento + len(linhas_locais)]
    novas = calcular_linhas(
        linhas_locais,
        inicio - deslocamento,
        fim - deslocamento,
        _modelo_processo,
        perfis_locais,
        geracao,
        deslocamento,
    )
    return compactar_linhas(novas)


def proxima_geracao_multiprocessing(pool, grade, processos, geracao):
    """Monta uma tarefa (faixa + halo) por processo e reúne os resultados."""
    tarefas = []
    for inicio, fim in dividir_linhas(len(grade), processos):
        halo_inicio, halo_fim = intervalo_com_halo(len(grade), inicio, fim)
        tarefas.append((
            halo_inicio,
            compactar_linhas(grade[halo_inicio:halo_fim]),
            inicio,
            fim,
            geracao,
        ))
    # map() devolve as faixas na mesma ordem das tarefas.
    partes = pool.map(_calcular_faixa, tarefas, chunksize=1)
    nova_grade = []
    for parte in partes:
        nova_grade.extend(descompactar_linhas(parte))
    return nova_grade


def executar_simulacao(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    modelo=2,
    processos=4,
    mostrar_grade=False,
    verboso=True,
    parar_sem_espalhadores=True,
):
    """
    Executa a simulação completa com processos. Além do retorno da versão
    sequencial, informa 'tempo_inicializacao' (subir os processos), que
    fica fora do tempo medido da simulação.
    """
    modelo = como_modelo(modelo)
    grade, perfis = criar_populacao(linhas, colunas, percentual_espalhadores, modelo)
    historico = [contar_estados(grade)]
    if verboso:
        print(f"=== VERSÃO MULTIPROCESSING: {processos} processos ===")

    inicio_pool = time.perf_counter()
    with Pool(processos, initializer=_inicializar, initargs=(perfis, modelo)) as pool:
        pool.map(_pronto, range(processos), chunksize=1)
        tempo_inicializacao = time.perf_counter() - inicio_pool

        inicio_tempo = time.perf_counter()
        for geracao in range(geracoes):
            grade = proxima_geracao_multiprocessing(pool, grade, processos, geracao)
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
        print(f"(inicialização dos processos: {tempo_inicializacao:.3f} s, "
              f"fora do tempo medido)")
        imprimir_resumo(historico, tempo)
    return {
        "grade": grade,
        "historico": historico,
        "tempo": tempo,
        "tempo_inicializacao": tempo_inicializacao,
    }


def main():
    parser = argparse.ArgumentParser(description="Versão paralela com multiprocessing")
    adicionar_argumentos(parser)
    parser.add_argument("--processos", type=int, default=4)
    args = parser.parse_args()
    executar_simulacao(
        args.linhas, args.colunas, args.geracoes, args.percentual,
        modelo_dos_argumentos(args), args.processos, args.mostrar_grade,
    )


if __name__ == "__main__":
    # Obrigatório no Windows: os processos filhos importam este módulo.
    main()
