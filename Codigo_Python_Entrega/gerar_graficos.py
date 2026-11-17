"""
Gera gráficos e tabelas a partir de resultados/benchmark.csv.

Uso:
  python benchmark.py
  python gerar_graficos.py

Saída em resultados/:
  escalabilidade.png   speedup e eficiência x número de trabalhadores
  cenarios.png         tempo x tamanho / gerações / percentual
  comunicacao.png      bytes por geração e tempo de cálculo x comunicação
  tabelas.tex          tabelas usadas nos slides (LaTeX)

Requer matplotlib (usado só para desenhar; não participa da simulação).
"""

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

PASTA = "resultados"

# Paleta categórica em ordem fixa (cada versão tem sempre a mesma cor).
VERSOES = [
    ("threads", "Threads", "#2a78d6", "o"),
    ("multiprocessing", "Multiprocessing", "#eb6834", "s"),
    ("distribuida-halo", "Distribuída (halo)", "#1baf7a", "^"),
    ("distribuida-faixa", "Distribuída (faixa)", "#eda100", "D"),
]
CINZA = "#8a8984"
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"

plt.rcParams.update({
    "font.size": 11,
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": TEXTO_SECUNDARIO,
    "xtick.color": TEXTO_SECUNDARIO,
    "ytick.color": TEXTO_SECUNDARIO,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": "#e6e5e0",
    "grid.linewidth": 0.8,
    "lines.linewidth": 2,
    "lines.markersize": 7,
    "legend.frameon": False,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})


def virgula(valor, casas=2):
    """Formata número no padrão brasileiro (vírgula decimal)."""
    return f"{valor:.{casas}f}".replace(".", ",")


FORMATO_VIRGULA = FuncFormatter(lambda v, _: virgula(v, 1) if v % 1 else f"{v:.0f}")


def ler_csv():
    with open(os.path.join(PASTA, "benchmark.csv"), encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    for linha in linhas:
        for campo in ("linhas", "colunas", "geracoes", "trabalhadores"):
            linha[campo] = int(linha[campo])
        for campo in ("percentual", "tempo_medio", "tempo_desvio", "speedup", "eficiencia"):
            linha[campo] = float(linha[campo])
        for campo in ("bytes_por_geracao", "tempo_calculo", "tempo_comunicacao"):
            linha[campo] = float(linha[campo]) if linha[campo] else None
    return linhas


def filtrar(registros, **criterios):
    return [r for r in registros if all(r[c] == v for c, v in criterios.items())]


def grafico_escalabilidade(linhas):
    dados = filtrar(linhas, experimento="escalabilidade")
    figura, (eixo_s, eixo_e) = plt.subplots(1, 2, figsize=(12, 4.6))
    quantidades = [1, 2, 4, 8]
    eixo_s.plot(quantidades, quantidades, "--", color=CINZA, linewidth=1.5, label="Ideal")
    eixo_e.axhline(1, linestyle="--", color=CINZA, linewidth=1.5, label="Ideal")
    for chave, nome, cor, marcador in VERSOES:
        serie = sorted(filtrar(dados, versao=chave), key=lambda l: l["trabalhadores"])
        x = [l["trabalhadores"] for l in serie]
        eixo_s.plot(x, [l["speedup"] for l in serie], marker=marcador, color=cor, label=nome)
        eixo_e.plot(x, [l["eficiencia"] for l in serie], marker=marcador, color=cor, label=nome)
    base = dados[0]
    for eixo, titulo in ((eixo_s, "Speedup"), (eixo_e, "Eficiência")):
        eixo.set_xticks(quantidades)
        eixo.set_xlabel("Threads / processos / trabalhadores")
        eixo.set_title(titulo, loc="left", fontsize=12, color=TEXTO)
        eixo.yaxis.set_major_formatter(FORMATO_VIRGULA)
    eixo_s.set_xlim(0.6, 8.6)
    eixo_e.set_ylim(0, 1.15)
    eixo_e.legend(loc="upper right", fontsize=9)
    figura.suptitle(
        f"Escalabilidade — matriz {base['linhas']}x{base['colunas']}, "
        f"{base['geracoes']} gerações, {virgula(base['percentual'] * 100, 0)}% de espalhadores",
        x=0.01, ha="left", fontsize=13, color=TEXTO)
    figura.savefig(os.path.join(PASTA, "escalabilidade.png"))
    plt.close(figura)


def grafico_cenarios(linhas):
    fatores = [
        ("tamanho", "linhas", "Lado da matriz (células)"),
        ("geracoes", "geracoes", "Número de gerações"),
        ("percentual", "percentual", "Espalhadores iniciais (%)"),
    ]
    figura, eixos = plt.subplots(1, 3, figsize=(14, 4.4), sharey=False)
    series = [("sequencial", "Sequencial", CINZA, "x")] + VERSOES
    for eixo, (fator, campo, rotulo) in zip(eixos, fatores):
        dados = filtrar(linhas, experimento=fator)
        for chave, nome, cor, marcador in series:
            serie = sorted(filtrar(dados, versao=chave), key=lambda l: l[campo])
            x = [l[campo] * (100 if campo == "percentual" else 1) for l in serie]
            estilo = "--" if chave == "sequencial" else "-"
            eixo.errorbar(x, [l["tempo_medio"] for l in serie],
                          yerr=[l["tempo_desvio"] for l in serie],
                          marker=marcador, color=cor, linestyle=estilo,
                          capsize=3, label=nome)
        eixo.set_xlabel(rotulo)
        eixo.set_xticks(x)
        eixo.yaxis.set_major_formatter(FORMATO_VIRGULA)
        eixo.xaxis.set_major_formatter(FORMATO_VIRGULA)
    eixos[0].set_ylabel("Tempo médio (s)")
    eixos[0].legend(fontsize=9, loc="upper left")
    figura.suptitle("Tempo de execução por cenário (4 threads / processos / trabalhadores; "
                    "barras = desvio padrão)", x=0.01, ha="left", fontsize=13, color=TEXTO)
    figura.savefig(os.path.join(PASTA, "cenarios.png"))
    plt.close(figura)


def grafico_comunicacao(linhas):
    dados = filtrar(linhas, experimento="escalabilidade")
    quantidades = [1, 2, 4, 8]
    distribuidas = [v for v in VERSOES if v[0].startswith("distribuida")]
    figura, (eixo_b, eixo_t) = plt.subplots(1, 2, figsize=(12, 4.6))

    largura = 0.38
    for deslocamento, (chave, nome, cor, _) in zip((-largura / 2, largura / 2), distribuidas):
        serie = sorted(filtrar(dados, versao=chave), key=lambda l: l["trabalhadores"])
        valores = [l["bytes_por_geracao"] / 1024 for l in serie]
        posicoes = [i + deslocamento for i in range(len(quantidades))]
        eixo_b.bar(posicoes, valores, width=largura - 0.03, color=cor, label=nome)
        for posicao, valor in zip(posicoes, valores):
            eixo_b.annotate(virgula(valor, 1), (posicao, valor), xytext=(0, 3),
                            textcoords="offset points", ha="center", fontsize=8, color=TEXTO)
    eixo_b.set_xticks(range(len(quantidades)), [str(q) for q in quantidades])
    eixo_b.set_xlabel("Trabalhadores")
    eixo_b.set_ylabel("KiB por geração")
    eixo_b.set_title("Dados trafegados por geração\n(média, inclui envio inicial e coleta final)",
                     loc="left", fontsize=12, color=TEXTO, pad=30)
    eixo_b.legend(fontsize=9, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))

    rotulos, calculo, comunicacao = [], [], []
    for chave, nome, _, _ in distribuidas:
        for quantidade in quantidades:
            linha = filtrar(dados, versao=chave, trabalhadores=quantidade)[0]
            rotulos.append(f"{'halo' if 'halo' in chave else 'faixa'}\n{quantidade}")
            calculo.append(linha["tempo_calculo"])
            comunicacao.append(linha["tempo_comunicacao"])
    posicoes = range(len(rotulos))
    eixo_t.bar(posicoes, calculo, color="#2a78d6", width=0.7, label="Cálculo (worker mais lento)")
    eixo_t.bar(posicoes, comunicacao, bottom=calculo, color="#eb6834", width=0.7,
               label="Comunicação + sincronização", edgecolor="white", linewidth=1)
    eixo_t.set_xticks(list(posicoes), rotulos, fontsize=9)
    eixo_t.set_xlabel("Modo / trabalhadores")
    eixo_t.set_ylabel("Tempo (s)")
    eixo_t.yaxis.set_major_formatter(FORMATO_VIRGULA)
    eixo_t.set_title("Onde o tempo é gasto\n ", loc="left", fontsize=12, color=TEXTO, pad=30)
    eixo_t.legend(fontsize=9, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
    figura.savefig(os.path.join(PASTA, "comunicacao.png"))
    plt.close(figura)


NOMES = {"sequencial": "Sequencial", **{v[0]: v[1] for v in VERSOES}}


def tabelas_latex(linhas):
    partes = []

    # Tabela 1: escalabilidade
    dados = filtrar(linhas, experimento="escalabilidade")
    corpo = []
    for chave in ["sequencial"] + [v[0] for v in VERSOES]:
        for linha in sorted(filtrar(dados, versao=chave), key=lambda l: l["trabalhadores"]):
            corpo.append(
                f"{NOMES[chave]} & {linha['trabalhadores']} & "
                f"{virgula(linha['tempo_medio'], 3)} $\\pm$ {virgula(linha['tempo_desvio'], 3)} & "
                f"{virgula(linha['speedup'])} & {virgula(linha['eficiencia'])} \\\\")
    partes.append(
        "% Gerado por gerar_graficos.py\n\\newcommand{\\tabelaEscalabilidade}{%\n"
        "\\begin{tabular}{lrrrr}\\toprule\n"
        "Versão & $p$ & Tempo (s) & Speedup & Eficiência \\\\\\midrule\n"
        + "\n".join(corpo) + "\n\\bottomrule\\end{tabular}}\n")

    # Tabela 2: cenários (tempo médio e speedup com 4 trabalhadores)
    corpo = []
    for fator, campo, nome in (("tamanho", "linhas", "Matriz"),
                               ("geracoes", "geracoes", "Gerações"),
                               ("percentual", "percentual", "Espalhadores")):
        dados = filtrar(linhas, experimento=fator)
        valores = sorted({l[campo] for l in dados})
        for valor in valores:
            texto = (f"{valor}x{valor}" if campo == "linhas" else
                     f"{virgula(valor * 100, 0)}\\%" if campo == "percentual" else str(valor))
            celulas = [f"{nome}: {texto}"]
            for chave in ["sequencial"] + [v[0] for v in VERSOES]:
                linha = filtrar(dados, versao=chave, **{campo: valor})[0]
                if chave == "sequencial":
                    celulas.append(virgula(linha["tempo_medio"], 2))
                else:
                    celulas.append(f"{virgula(linha['tempo_medio'], 2)} ({virgula(linha['speedup'], 1)}x)")
            corpo.append(" & ".join(celulas) + " \\\\")
    partes.append(
        "\\newcommand{\\tabelaCenarios}{%\n"
        "\\begin{tabular}{lrrrrr}\\toprule\n"
        "Cenário & Seq. & Threads & Multiproc. & Dist. halo & Dist. faixa \\\\\\midrule\n"
        + "\n".join(corpo) + "\n\\bottomrule\\end{tabular}}\n")

    # Tabela 3: comunicação
    dados = filtrar(linhas, experimento="escalabilidade")
    corpo = []
    for quantidade in (1, 2, 4, 8):
        halo = filtrar(dados, versao="distribuida-halo", trabalhadores=quantidade)[0]
        faixa = filtrar(dados, versao="distribuida-faixa", trabalhadores=quantidade)[0]
        reducao = faixa["bytes_por_geracao"] / halo["bytes_por_geracao"]
        corpo.append(
            f"{quantidade} & {virgula(faixa['bytes_por_geracao'] / 1024, 1)} & "
            f"{virgula(halo['bytes_por_geracao'] / 1024, 1)} & {virgula(reducao, 1)}x & "
            f"{virgula(faixa['tempo_comunicacao'], 3)} & {virgula(halo['tempo_comunicacao'], 3)} \\\\")
    partes.append(
        "\\newcommand{\\tabelaComunicacao}{%\n"
        "\\begin{tabular}{rrrrrr}\\toprule\n"
        "$p$ & \\multicolumn{2}{c}{KiB/geração} & Redução & \\multicolumn{2}{c}{Comunic. (s)} \\\\\n"
        " & faixa & halo & & faixa & halo \\\\\\midrule\n"
        + "\n".join(corpo) + "\n\\bottomrule\\end{tabular}}\n")

    # Modelo estendido
    dados = filtrar(linhas, experimento="modelo")
    corpo = []
    for chave in ["sequencial"] + [v[0] for v in VERSOES]:
        linha = filtrar(dados, versao=chave)[0]
        corpo.append(f"{NOMES[chave]} & {linha['trabalhadores']} & "
                     f"{virgula(linha['tempo_medio'], 3)} & {virgula(linha['speedup'])} \\\\")
    partes.append(
        "\\newcommand{\\tabelaModelo}{%\n"
        "\\begin{tabular}{lrrr}\\toprule\n"
        "Versão & $p$ & Tempo (s) & Speedup \\\\\\midrule\n"
        + "\n".join(corpo) + "\n\\bottomrule\\end{tabular}}\n")

    with open(os.path.join(PASTA, "tabelas.tex"), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(partes))


def main():
    linhas = ler_csv()
    grafico_escalabilidade(linhas)
    grafico_cenarios(linhas)
    grafico_comunicacao(linhas)
    tabelas_latex(linhas)
    print(f"Gráficos e tabelas salvos em {os.path.abspath(PASTA)}")


if __name__ == "__main__":
    main()
