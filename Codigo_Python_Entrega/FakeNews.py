"""
Simulação sequencial de Propagação de Fake News

Estados:
0 = Ignorante: ainda não recebeu/acredita na informação
1 = Espalhador: acredita e compartilha a informação
2 = Inativo: recebeu a informação, mas não compartilha mais

Fluxograma básico:
Início
  ↓
Criar grade inicial
  ↓
Para cada geração
  ↓
Calcular próxima geração usando a grade atual
  ↓
Contar estados
  ↓
Imprimir estatísticas
  ↓
Ainda existem espalhadores e ainda há gerações?
  ↓ sim
Próxima geração
  ↓
Calcular próxima geração usando a grade atual
  ↓ não
Resultado final

------------------------------------------------------------------------
Modificações feitas pelo grupo
------------------------------------------------------------------------
1. A regra de transição foi isolada em calcular_linhas(), que calcula só
   um intervalo [inicio, fim) de linhas. As versões paralela, multiprocessing
   e distribuída chamam exatamente esta função, então a lógica é a mesma
   nas quatro versões.

2. Extensões do modelo (todas DESLIGADAS por padrão; com os valores padrão
   o resultado é idêntico ao código sequencial fornecido):
   - Convencimento probabilístico (beta): cada vizinho espalhador convence
     com probabilidade beta, de forma independente. Com k vizinhos, a
     chance de conversão é 1 - (1 - beta)^k (modelo de exposição
     independente, como no SIR/Daley-Kendall).
   - Influenciadores digitais: um influenciador espalhando conta como
     'peso_influenciador' vizinhos (alcance maior que uma pessoa comum).
   - Bots: começam espalhando e nunca ficam inativos.
   - Céticos (resistência): a probabilidade de serem convencidos é
     multiplicada por (1 - resistencia_cetico).
   - Estatísticas adicionais: pico de espalhadores, geração do pico,
     alcance final e geração de extinção.

3. Os números aleatórios da regra probabilística vêm de um gerador baseado
   em contador (numero_aleatorio): o valor depende apenas de
   (semente, geração, linha, coluna). Assim, não importa qual thread,
   processo ou máquina calcula a célula, o sorteio é sempre o mesmo e as
   versões paralelas continuam produzindo exatamente o resultado sequencial.
"""

import argparse
import random
import time
from dataclasses import dataclass

IGNORANTE = 0
ESPALHADOR = 1
INATIVO = 2

# Perfis de indivíduo (extensões). Ficam numa matriz separada, que não muda
# durante a simulação.
NORMAL = 0
INFLUENCIADOR = 1
BOT = 2
CETICO = 3

MASCARA_64 = (1 << 64) - 1


@dataclass(frozen=True)
class Modelo:
    """
    Parâmetros do modelo. Os valores padrão reproduzem o modelo original.

    limiar: vizinhos espalhadores (ponderados) necessários para convencer.
    beta: probabilidade de um vizinho espalhador convencer (1.0 = sempre).
    pct_influenciadores, pct_bots, pct_ceticos: fração da população com
        cada perfil (0.0 = perfil desligado).
    peso_influenciador: quantos vizinhos um influenciador "vale".
    resistencia_cetico: redução da probabilidade de convencer um cético.
    semente: semente da população e dos sorteios.
    """
    limiar: int = 2
    beta: float = 1.0
    pct_influenciadores: float = 0.0
    peso_influenciador: int = 3
    pct_bots: float = 0.0
    pct_ceticos: float = 0.0
    resistencia_cetico: float = 0.7
    semente: int = 42


def como_modelo(modelo):
    """Aceita um Modelo ou apenas o limiar (int), como no código original."""
    if isinstance(modelo, int):
        return Modelo(limiar=modelo)
    return modelo


def criar_grade(linhas, colunas, percentual_espalhadores=0.02, semente=42):
    """
    Cria uma matriz inicial.
    A maior parte da população começa ignorante.
    Uma pequena parte começa como espalhadora da fake news.
    """
    random.seed(semente)

    grade = [[IGNORANTE for _ in range(colunas)] for _ in range(linhas)]

    total_celulas = linhas * colunas
    total_espalhadores = int(total_celulas * percentual_espalhadores)

    for _ in range(total_espalhadores):
        i = random.randint(0, linhas - 1)
        j = random.randint(0, colunas - 1)
        grade[i][j] = ESPALHADOR

    return grade


def criar_populacao(linhas, colunas, percentual_espalhadores, modelo):
    """
    Cria a grade de estados e, se alguma extensão de perfil estiver ligada,
    a matriz de perfis.

    Retorna (grade, perfis). 'perfis' é None quando não há influenciadores,
    bots nem céticos: nesse caso a grade é exatamente a do código original.
    """
    modelo = como_modelo(modelo)
    grade = criar_grade(linhas, colunas, percentual_espalhadores, modelo.semente)

    fracoes = (modelo.pct_influenciadores, modelo.pct_bots, modelo.pct_ceticos)
    if sum(fracoes) == 0:
        return grade, None

    # Gerador separado para não alterar a sequência usada em criar_grade().
    gerador = random.Random(modelo.semente + 1)
    limite_influenciador = modelo.pct_influenciadores
    limite_bot = limite_influenciador + modelo.pct_bots
    limite_cetico = limite_bot + modelo.pct_ceticos

    perfis = [[NORMAL] * colunas for _ in range(linhas)]
    for i in range(linhas):
        for j in range(colunas):
            sorteio = gerador.random()
            if sorteio < limite_influenciador:
                perfis[i][j] = INFLUENCIADOR
            elif sorteio < limite_bot:
                perfis[i][j] = BOT
                grade[i][j] = ESPALHADOR  # bots já começam espalhando
            elif sorteio < limite_cetico:
                perfis[i][j] = CETICO

    return grade, perfis


def numero_aleatorio(semente, geracao, i, j):
    """
    Número pseudoaleatório em [0, 1) que depende só de (semente, geração, i, j).

    É um gerador "baseado em contador" (Salmon et al., 2011): em vez de um
    estado que avança a cada chamada, o número é um hash das coordenadas.
    Usa o finalizador do SplitMix64 (Steele; Lea; Flood, 2014). Por não ter
    estado compartilhado, threads e processos diferentes obtêm o mesmo
    sorteio para a mesma célula, sem sincronização nenhuma.
    """
    x = (
        semente * 0x9E3779B97F4A7C15
        + geracao * 0xBF58476D1CE4E5B9
        + i * 0x94D049BB133111EB
        + j * 0x2545F4914F6CDD1D
    ) & MASCARA_64
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & MASCARA_64
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & MASCARA_64
    x ^= x >> 31
    return (x >> 11) / 9007199254740992.0  # divide por 2^53


def contar_vizinhos_espalhadores(grade, i, j):
    """
    Conta quantos vizinhos ao redor da célula estão espalhando a fake news.
    Usa vizinhança de Moore: até 8 vizinhos.
    A vizinhança de Moore é o conjunto das 8 células ao redor de uma célula
    central em uma matriz 2D.
    Por exemplo considere X em:
    A B C
    D X E
    F G H
    a vizinhança de Moore seria:
    A B C
    D   E
    F G H
    """
    linhas = len(grade)
    colunas = len(grade[0])

    total = 0

    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            # Quando di == 0 e dj == 0, temos a própria célula central, que deve ser ignorada.
            if di == 0 and dj == 0:
                continue

            ni = i + di
            nj = j + dj

            if 0 <= ni < linhas and 0 <= nj < colunas:
                if grade[ni][nj] == ESPALHADOR:
                    total += 1

    return total


def peso_vizinhos_espalhadores(grade, perfis, i, j, peso_influenciador):
    """
    Igual a contar_vizinhos_espalhadores(), mas um influenciador espalhando
    conta como 'peso_influenciador' vizinhos.
    """
    linhas = len(grade)
    colunas = len(grade[0])
    total = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            ni = i + di
            nj = j + dj
            if 0 <= ni < linhas and 0 <= nj < colunas and grade[ni][nj] == ESPALHADOR:
                if perfis is not None and perfis[ni][nj] == INFLUENCIADOR:
                    total += peso_influenciador
                else:
                    total += 1
    return total


def foi_convencido(peso, perfil, modelo, geracao, i, j):
    """
    Decide se um ignorante com 'peso' vizinhos espalhadores é convencido.
    i e j são coordenadas GLOBAIS (importante para o sorteio ser o mesmo
    em qualquer versão).
    """
    probabilidade_vizinho = modelo.beta
    if perfil == CETICO:
        probabilidade_vizinho *= 1.0 - modelo.resistencia_cetico
    if probabilidade_vizinho >= 1.0:
        return True  # caso determinístico (modelo original)
    probabilidade = 1.0 - (1.0 - probabilidade_vizinho) ** peso
    return numero_aleatorio(modelo.semente, geracao, i, j) < probabilidade


def proxima_geracao(grade, limiar_convencimento=2, perfis=None, geracao=0):
    """
    Calcula a próxima geração da simulação.

    Regra simplificada:
    - Ignorante vira espalhador se tiver pelo menos 'limiar_convencimento'
      vizinhos espalhadores.
    - Espalhador vira inativo na próxima geração.
    - Inativo permanece inativo.

    'limiar_convencimento' também pode ser um Modelo completo (extensões).

    Importante:
    Usa uma nova matriz para evitar atualização "ao vivo".
    """
    return calcular_linhas(
        grade, 0, len(grade), limiar_convencimento, perfis, geracao
    )


def calcular_linhas(grade, inicio, fim, modelo=2, perfis=None, geracao=0,
                    deslocamento=0):
    """
    Calcula um intervalo [inicio, fim) da próxima geração.

    A grade recebida é somente leitura. Isso permite que diferentes
    trabalhadores calculem intervalos independentes da mesma geração.

    grade: pode ser a grade inteira ou só uma faixa com linhas de halo
        (versões multiprocessing e distribuída).
    perfis: matriz de perfis alinhada com 'grade' (ou None).
    geracao: número da geração sendo calculada (usado nos sorteios).
    deslocamento: índice global da linha 0 de 'grade'. Linha local i é a
        linha global i + deslocamento.
    """
    modelo = como_modelo(modelo)
    linhas = len(grade)
    colunas = len(grade[0])

    if not 0 <= inicio <= fim <= linhas:
        raise ValueError("Intervalo de linhas inválido")

    novas_linhas = [list(grade[i]) for i in range(inicio, fim)]
    limiar = modelo.limiar

    if perfis is None and modelo.beta >= 1.0:
        # Modelo original: mesmo laço do código fornecido.
        for indice, i in enumerate(range(inicio, fim)):
            for j in range(colunas):
                if grade[i][j] == IGNORANTE:
                    vizinhos = contar_vizinhos_espalhadores(grade, i, j)
                    if vizinhos >= limiar:
                        novas_linhas[indice][j] = ESPALHADOR
                elif grade[i][j] == ESPALHADOR:
                    novas_linhas[indice][j] = INATIVO
        return novas_linhas

    # Modelo estendido.
    for indice, i in enumerate(range(inicio, fim)):
        for j in range(colunas):
            estado = grade[i][j]
            perfil = perfis[i][j] if perfis is not None else NORMAL
            if estado == IGNORANTE:
                peso = peso_vizinhos_espalhadores(
                    grade, perfis, i, j, modelo.peso_influenciador
                )
                if peso >= limiar and foi_convencido(
                    peso, perfil, modelo, geracao, i + deslocamento, j
                ):
                    novas_linhas[indice][j] = ESPALHADOR
            elif estado == ESPALHADOR and perfil != BOT:
                novas_linhas[indice][j] = INATIVO

    return novas_linhas


def contar_estados(grade):
    """
    Conta quantas células existem em cada estado.
    """
    contagem = {
        IGNORANTE: 0,
        ESPALHADOR: 0,
        INATIVO: 0
    }

    for linha in grade:
        for celula in linha:
            contagem[celula] += 1

    return contagem


def compactar_linhas(linhas):
    """
    Converte linhas (listas de 0/1/2) em bytes: 1 byte por célula.
    Usado para enviar faixas entre processos/máquinas. Uma lista Python
    serializada com pickle ocupa ~2 bytes por célula; bytes ocupa 1.
    'bytes' também pode ser lido diretamente por calcular_linhas().
    """
    return [bytes(linha) for linha in linhas]


def descompactar_linhas(linhas):
    """Converte linhas em bytes de volta para listas."""
    return [list(linha) for linha in linhas]


def imprimir_grade(grade, limite=30):
    """
    Mostra parte da grade no terminal.
    Use apenas para grades pequenas ou para demonstração.
    """
    simbolos = {
        IGNORANTE: ".",
        ESPALHADOR: "E",
        INATIVO: "N"
    }

    linhas = min(len(grade), limite)
    colunas = min(len(grade[0]), limite)

    for i in range(linhas):
        linha = ""
        for j in range(colunas):
            linha += simbolos[grade[i][j]] + " "
        print(linha)
    print()


def imprimir_geracao(geracao, contagem):
    """Linha de estatísticas de uma geração (igual em todas as versões)."""
    print(
        f"Geração {geracao:03d} | "
        f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
        f"Espalhadores: {contagem[ESPALHADOR]:>10,} | "
        f"Inativos: {contagem[INATIVO]:>10,}"
    )


def resumir_historico(historico):
    """
    Estatísticas adicionais a partir das contagens de cada geração.
    historico[0] é o estado inicial; historico[g] é a geração g.
    """
    total = sum(historico[0].values())
    geracao_pico = max(
        range(len(historico)), key=lambda g: historico[g][ESPALHADOR]
    )
    geracao_extincao = next(
        (g for g, c in enumerate(historico) if c[ESPALHADOR] == 0), None
    )
    final = historico[-1]
    return {
        "geracoes_executadas": len(historico) - 1,
        "pico_espalhadores": historico[geracao_pico][ESPALHADOR],
        "geracao_pico": geracao_pico,
        # alcance: fração da população que recebeu a fake news
        "alcance": (total - final[IGNORANTE]) / total,
        "geracao_extincao": geracao_extincao,
    }


def imprimir_resumo(historico, tempo_total):
    """Resultado final + estatísticas adicionais."""
    final = historico[-1]
    total = sum(final.values())
    resumo = resumir_historico(historico)

    print()
    print("=== RESULTADO FINAL ===")
    print(f"Tempo total de execução: {tempo_total:.4f} segundos")
    print(f"Ignorantes finais: {final[IGNORANTE]:,} ({final[IGNORANTE] / total * 100:,.2f}%)")
    print(f"Espalhadores finais: {final[ESPALHADOR]:,} ({final[ESPALHADOR] / total * 100:,.2f}%)")
    print(f"Inativos finais: {final[INATIVO]:,} ({final[INATIVO] / total * 100:,.2f}%)")
    print("--- Estatísticas adicionais ---")
    print(f"Pico de espalhadores: {resumo['pico_espalhadores']:,} "
          f"(geração {resumo['geracao_pico']})")
    print(f"Alcance da fake news: {resumo['alcance'] * 100:.2f}% da população")
    if resumo["geracao_extincao"] is None:
        print("A propagação não se extinguiu dentro das gerações simuladas.")
    else:
        print(f"Propagação extinta na geração {resumo['geracao_extincao']}")


def executar_simulacao(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    limiar_convencimento=2,
    mostrar_grade=False,
    verboso=True,
    parar_sem_espalhadores=True,
):
    """
    Executa a simulação sequencial completa.

    limiar_convencimento: int (modelo original) ou Modelo (extensões).
    verboso / parar_sem_espalhadores: o benchmark desliga ambos para medir
        sempre o mesmo número de gerações sem custo de impressão.

    Retorna um dicionário com a grade final, o histórico de contagens e o
    tempo de execução.
    """
    modelo = como_modelo(limiar_convencimento)
    grade, perfis = criar_populacao(
        linhas, colunas, percentual_espalhadores, modelo
    )
    historico = [contar_estados(grade)]

    if verboso:
        print("=== SIMULAÇÃO SEQUENCIAL DE PROPAGAÇÃO DE FAKE NEWS ===")
        print(f"Tamanho da grade: {linhas} x {colunas} ({linhas*colunas:,} pessoas)")
        print(f"Gerações: {geracoes}")
        print(
            f"Percentual inicial de espalhadores: "
            f"{percentual_espalhadores * 100:.2f}% "
            f"({historico[0][ESPALHADOR]:,} espalhadores reais)"
        )
        print(f"Limiar de convencimento: {modelo.limiar} vizinhos")
        if modelo != Modelo(limiar=modelo.limiar, semente=modelo.semente):
            print(f"Extensões: {modelo}")
        print()

    inicio = time.perf_counter()

    for geracao in range(geracoes):
        grade = proxima_geracao(grade, modelo, perfis, geracao)

        contagem = contar_estados(grade)
        historico.append(contagem)

        if verboso:
            imprimir_geracao(geracao + 1, contagem)
            if mostrar_grade:
                imprimir_grade(grade)

        if parar_sem_espalhadores and contagem[ESPALHADOR] == 0:
            if verboso:
                print("\nA propagação terminou: não há mais espalhadores.")
            break

    tempo_total = time.perf_counter() - inicio

    if verboso:
        imprimir_resumo(historico, tempo_total)

    return {"grade": grade, "historico": historico, "tempo": tempo_total}


def adicionar_argumentos(parser):
    """Argumentos de linha de comando comuns a todas as versões."""
    parser.add_argument("--linhas", type=int, default=100)
    parser.add_argument("--colunas", type=int, default=100)
    parser.add_argument("--geracoes", type=int, default=50)
    parser.add_argument("--percentual", type=float, default=0.05,
                        help="fração inicial de espalhadores (0.05 = 5%%)")
    parser.add_argument("--limiar", type=int, default=3)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--mostrar-grade", action="store_true")
    extensoes = parser.add_argument_group("extensões do modelo (padrão: desligadas)")
    extensoes.add_argument("--beta", type=float, default=1.0,
                           help="probabilidade de cada vizinho convencer")
    extensoes.add_argument("--influenciadores", type=float, default=0.0,
                           help="fração de influenciadores")
    extensoes.add_argument("--peso-influenciador", type=int, default=3)
    extensoes.add_argument("--bots", type=float, default=0.0,
                           help="fração de bots")
    extensoes.add_argument("--ceticos", type=float, default=0.0,
                           help="fração de céticos")
    extensoes.add_argument("--resistencia", type=float, default=0.7,
                           help="resistência dos céticos (0 a 1)")


def modelo_dos_argumentos(args):
    """Monta o Modelo a partir dos argumentos de linha de comando."""
    return Modelo(
        limiar=args.limiar,
        beta=args.beta,
        pct_influenciadores=args.influenciadores,
        peso_influenciador=args.peso_influenciador,
        pct_bots=args.bots,
        pct_ceticos=args.ceticos,
        resistencia_cetico=args.resistencia,
        semente=args.semente,
    )


def main():
    parser = argparse.ArgumentParser(description="Versão sequencial")
    adicionar_argumentos(parser)
    args = parser.parse_args()
    executar_simulacao(
        args.linhas, args.colunas, args.geracoes, args.percentual,
        modelo_dos_argumentos(args), args.mostrar_grade,
    )


if __name__ == "__main__":
    # Sem argumentos, roda o mesmo cenário do código original:
    # 100x100, 50 gerações, 5% de espalhadores, limiar 3.
    main()
