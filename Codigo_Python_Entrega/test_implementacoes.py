"""
Testes de corretude.

1. O modelo padrão reproduz exatamente a regra do código fornecido.
2. Threads, multiprocessing e distribuída (modos halo e faixa) produzem,
   geração a geração, a mesma grade da versão sequencial, tanto no modelo
   original quanto no modelo com todas as extensões ligadas.

Uso:
  python -m unittest -v test_implementacoes.py
"""

import socket
import threading
import unittest

import FakeNews
import FakeNewsDistribuida
import FakeNewsMultiprocessing
import FakeNewsParalela
from FakeNews import Modelo, criar_populacao, proxima_geracao
from FakeNewsParalela import dividir_linhas, proxima_geracao_paralela

LINHAS, COLUNAS, GERACOES, PERCENTUAL = 18, 23, 6, 0.12

MODELO_ORIGINAL = Modelo(limiar=2)
MODELO_ESTENDIDO = Modelo(
    limiar=2, beta=0.6, pct_influenciadores=0.05, pct_bots=0.02,
    pct_ceticos=0.2, semente=7,
)


def proxima_geracao_fornecida(grade, limiar):
    """Cópia da regra do código sequencial original (referência)."""
    linhas, colunas = len(grade), len(grade[0])
    nova = [linha[:] for linha in grade]
    for i in range(linhas):
        for j in range(colunas):
            if grade[i][j] == 0:
                vizinhos = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if (di or dj) and 0 <= i + di < linhas and 0 <= j + dj < colunas:
                            vizinhos += grade[i + di][j + dj] == 1
                if vizinhos >= limiar:
                    nova[i][j] = 1
            elif grade[i][j] == 1:
                nova[i][j] = 2
    return nova


def porta_livre():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        return servidor.getsockname()[1]


def sequencial(modelo):
    """Lista com a grade de cada geração na versão sequencial."""
    grade, perfis = criar_populacao(LINHAS, COLUNAS, PERCENTUAL, modelo)
    grades = []
    for geracao in range(GERACOES):
        grade = proxima_geracao(grade, modelo, perfis, geracao)
        grades.append(grade)
    return grades


class TestModelo(unittest.TestCase):
    def test_modelo_padrao_igual_ao_fornecido(self):
        grade = FakeNews.criar_grade(LINHAS, COLUNAS, PERCENTUAL, 42)
        esperado = grade
        for _ in range(GERACOES):
            grade = proxima_geracao(grade, 2)
            esperado = proxima_geracao_fornecida(esperado, 2)
            self.assertEqual(grade, esperado)

    def test_extensoes_mudam_o_resultado(self):
        self.assertNotEqual(sequencial(MODELO_ORIGINAL)[-1],
                            sequencial(MODELO_ESTENDIDO)[-1])

    def test_bots_nunca_ficam_inativos(self):
        modelo = Modelo(pct_bots=0.05)
        grade, perfis = criar_populacao(LINHAS, COLUNAS, PERCENTUAL, modelo)
        for geracao in range(GERACOES):
            grade = proxima_geracao(grade, modelo, perfis, geracao)
        for i in range(LINHAS):
            for j in range(COLUNAS):
                if perfis[i][j] == FakeNews.BOT:
                    self.assertEqual(grade[i][j], FakeNews.ESPALHADOR)

    def test_divisao_cobre_todas_as_linhas(self):
        for total in (1, 7, 18, 100):
            for partes in (1, 2, 3, 8, 200):
                intervalos = dividir_linhas(total, partes)
                linhas = [i for a, b in intervalos for i in range(a, b)]
                self.assertEqual(linhas, list(range(total)))


class TestEquivalencia(unittest.TestCase):
    def verificar_threads(self, modelo):
        grade, perfis = criar_populacao(LINHAS, COLUNAS, PERCENTUAL, modelo)
        for geracao, esperado in enumerate(sequencial(modelo)):
            grade = proxima_geracao_paralela(grade, 4, modelo, perfis, geracao)
            self.assertEqual(grade, esperado)

    def verificar_multiprocessing(self, modelo):
        resultado = FakeNewsMultiprocessing.executar_simulacao(
            LINHAS, COLUNAS, GERACOES, PERCENTUAL, modelo, processos=3,
            verboso=False, parar_sem_espalhadores=False,
        )
        self.assertEqual(resultado["grade"], sequencial(modelo)[-1])

    def verificar_distribuida(self, modelo, modo):
        portas = [porta_livre() for _ in range(3)]
        for porta in portas:
            threading.Thread(
                target=FakeNewsDistribuida.executar_worker,
                args=("127.0.0.1", porta, False), daemon=True,
            ).start()
        enderecos = [("127.0.0.1", porta) for porta in portas]
        # Espera os workers abrirem as portas.
        for _ in range(100):
            try:
                FakeNewsDistribuida.encerrar_trabalhadores(
                    FakeNewsDistribuida.conectar_trabalhadores(enderecos, 1))
                break
            except OSError:
                threading.Event().wait(0.05)
        resultado = FakeNewsDistribuida.executar_simulacao(
            LINHAS, COLUNAS, GERACOES, PERCENTUAL, modelo, enderecos, modo,
            verboso=False, parar_sem_espalhadores=False,
        )
        grades = sequencial(modelo)
        self.assertEqual(resultado["grade"], grades[-1])
        contagens = [FakeNews.contar_estados(g) for g in grades]
        self.assertEqual(resultado["historico"][1:], contagens)

    def test_threads_original(self):
        self.verificar_threads(MODELO_ORIGINAL)

    def test_threads_estendido(self):
        self.verificar_threads(MODELO_ESTENDIDO)

    def test_multiprocessing_original(self):
        self.verificar_multiprocessing(MODELO_ORIGINAL)

    def test_multiprocessing_estendido(self):
        self.verificar_multiprocessing(MODELO_ESTENDIDO)

    def test_distribuida_halo_original(self):
        self.verificar_distribuida(MODELO_ORIGINAL, "halo")

    def test_distribuida_halo_estendido(self):
        self.verificar_distribuida(MODELO_ESTENDIDO, "halo")

    def test_distribuida_faixa_original(self):
        self.verificar_distribuida(MODELO_ORIGINAL, "faixa")

    def test_distribuida_faixa_estendido(self):
        self.verificar_distribuida(MODELO_ESTENDIDO, "faixa")


if __name__ == "__main__":
    unittest.main()
