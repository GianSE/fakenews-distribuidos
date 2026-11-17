"""
Visualização gráfica da propagação (melhoria).

Gera em resultados/:
  evolucao_grade.png   a matriz em algumas gerações
  curvas_modelos.png   espalhadores e alcance ao longo do tempo, comparando
                       o modelo original com cada extensão
  propagacao.gif       animação da matriz (para o vídeo)

Usa a versão sequencial (as outras produzem a mesma grade, ver testes).
matplotlib é usado só para desenhar.

Uso:
  python visualizar.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from FakeNews import (  # noqa: E402
    ESPALHADOR,
    IGNORANTE,
    Modelo,
    contar_estados,
    criar_populacao,
    proxima_geracao,
)

PASTA = "resultados"
LADO = 150
GERACOES = 40
PERCENTUAL = 0.02
TEXTO = "#0b0b0b"

# Ignorante recua (cinza claro), espalhador chama atenção, inativo em azul.
CORES_ESTADOS = ["#e8e7e3", "#eb6834", "#2a78d6"]
MAPA = ListedColormap(CORES_ESTADOS)
LEGENDA_ESTADOS = [Patch(color=c, label=n) for c, n in
                   zip(CORES_ESTADOS, ("Ignorante", "Espalhador", "Inativo"))]

CENARIOS = [
    ("Original (limiar 2)", Modelo(limiar=2), "#2a78d6"),
    ("Probabilístico (β = 0,6)", Modelo(limiar=2, beta=0.6), "#eb6834"),
    ("β = 0,6 + influenciadores (1%)", Modelo(limiar=2, beta=0.6, pct_influenciadores=0.01), "#1baf7a"),
    ("β = 0,6 + bots (0,5%)", Modelo(limiar=2, beta=0.6, pct_bots=0.005), "#eda100"),
    ("β = 0,6 + céticos (30%)", Modelo(limiar=2, beta=0.6, pct_ceticos=0.3), "#e87ba4"),
]


def simular(modelo, geracoes=GERACOES):
    """Devolve a lista de grades (geração 0 até 'geracoes')."""
    grade, perfis = criar_populacao(LADO, LADO, PERCENTUAL, modelo)
    grades = [grade]
    for geracao in range(geracoes):
        grade = proxima_geracao(grade, modelo, perfis, geracao)
        grades.append(grade)
    return grades


def evolucao_grade(grades, titulo, arquivo):
    momentos = [0, 3, 8, 15, 25, len(grades) - 1]
    figura, eixos = plt.subplots(1, len(momentos), figsize=(15, 3.4), layout="constrained")
    for eixo, geracao in zip(eixos, momentos):
        eixo.imshow(grades[geracao], cmap=MAPA, vmin=0, vmax=2, interpolation="nearest")
        eixo.set_title(f"Geração {geracao}", fontsize=11, color=TEXTO)
        eixo.axis("off")
    figura.legend(handles=LEGENDA_ESTADOS, loc="outside lower center", ncol=3, frameon=False)
    figura.suptitle(titulo, fontsize=13, color=TEXTO)
    figura.savefig(os.path.join(PASTA, arquivo), dpi=150, bbox_inches="tight",
                   facecolor="white")
    plt.close(figura)


def curvas_modelos():
    figura, (eixo_e, eixo_a) = plt.subplots(1, 2, figsize=(13, 4.6))
    total = LADO * LADO
    for nome, modelo, cor in CENARIOS:
        contagens = [contar_estados(g) for g in simular(modelo)]
        x = range(len(contagens))
        espalhadores = [c[ESPALHADOR] / total * 100 for c in contagens]
        alcance = [(total - c[IGNORANTE]) / total * 100 for c in contagens]
        eixo_e.plot(x, espalhadores, color=cor, linewidth=2, label=nome)
        eixo_a.plot(x, alcance, color=cor, linewidth=2, label=nome)
        eixo_a.annotate(f"{alcance[-1]:.0f}%".replace(".", ","), (x[-1], alcance[-1]),
                        xytext=(6, 0), textcoords="offset points", va="center",
                        fontsize=9, color=TEXTO)
    for eixo, titulo in ((eixo_e, "Espalhadores ativos (% da população)"),
                         (eixo_a, "Alcance acumulado (% que recebeu a notícia)")):
        eixo.set_title(titulo, loc="left", fontsize=12, color=TEXTO)
        eixo.set_xlabel("Geração")
        eixo.spines[["top", "right"]].set_visible(False)
        eixo.grid(axis="y", color="#e6e5e0")
    eixo_a.set_xlim(0, GERACOES + 4)
    figura.legend(*eixo_e.get_legend_handles_labels(), loc="lower center", ncol=5,
                  fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.06))
    figura.suptitle(f"Efeito das extensões do modelo — matriz {LADO}x{LADO}, "
                    f"{PERCENTUAL * 100:.0f}% de espalhadores iniciais",
                    x=0.01, ha="left", fontsize=13, color=TEXTO)
    figura.savefig(os.path.join(PASTA, "curvas_modelos.png"), dpi=150,
                   bbox_inches="tight", facecolor="white")
    plt.close(figura)


def animacao(grades, arquivo):
    figura, eixo = plt.subplots(figsize=(5, 5.4))
    imagem = eixo.imshow(grades[0], cmap=MAPA, vmin=0, vmax=2, interpolation="nearest")
    eixo.axis("off")
    titulo = eixo.set_title("", fontsize=12)
    eixo.legend(handles=LEGENDA_ESTADOS, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                ncol=3, frameon=False, fontsize=9)

    def quadro(geracao):
        imagem.set_data(grades[geracao])
        titulo.set_text(f"Geração {geracao}")
        return imagem, titulo

    FuncAnimation(figura, quadro, frames=len(grades)).save(
        os.path.join(PASTA, arquivo), writer=PillowWriter(fps=4))
    plt.close(figura)


def main():
    os.makedirs(PASTA, exist_ok=True)
    estendido = Modelo(limiar=2, beta=0.6, pct_influenciadores=0.01,
                       pct_bots=0.005, pct_ceticos=0.3)
    evolucao_grade(simular(Modelo(limiar=2)),
                   "Modelo original (limiar 2) — evolução da matriz", "evolucao_grade.png")
    grades_estendido = simular(estendido)
    evolucao_grade(grades_estendido,
                   "Modelo estendido (β = 0,6, influenciadores, bots e céticos)",
                   "evolucao_grade_estendido.png")
    curvas_modelos()
    animacao(grades_estendido, "propagacao.gif")
    print(f"Visualizações salvas em {os.path.abspath(PASTA)}")


if __name__ == "__main__":
    main()
