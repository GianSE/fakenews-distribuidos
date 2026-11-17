# Propagação de Fake News — Sequencial, Paralela e Distribuída

**Grupo 7:** Arthur Henrique Caron, Gian Pedro Rodrigues, João Pedro
Trevisan Borghi e Mario Issamu Barbuglio Morita.

Autômato celular (vizinhança de Moore) com três estados: ignorante (0),
espalhador (1) e inativo (2). A partir do código sequencial fornecido, o grupo
implementou uma versão paralela com threads, uma versão paralela com
`multiprocessing` e uma versão distribuída com sockets TCP. Também foram
implementadas extensões do modelo.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `FakeNews.py` | Versão sequencial (referência) + regra de transição + extensões do modelo |
| `FakeNewsParalela.py` | Versão paralela com `threading.Thread` |
| `FakeNewsMultiprocessing.py` | Versão paralela com `multiprocessing` (paralelismo real) |
| `FakeNewsDistribuida.py` | Versão distribuída: coordenador + trabalhadores TCP |
| `test_implementacoes.py` | Testes: todas as versões produzem exatamente a grade sequencial |
| `benchmark.py` | Experimentos de desempenho → `resultados/benchmark.csv` |
| `gerar_graficos.py` | Gráficos e tabelas a partir do CSV |
| `visualizar.py` | Imagens e GIF da propagação |
| `gerar_demonstracoes.py` | Roda as demonstrações do vídeo e salva as saídas em `resultados/demonstracoes/` |
| `resultados/` | CSV, gráficos, tabelas e descrição do ambiente usados na apresentação |

## Requisitos

- Python 3.8 ou superior (testado com 3.14.6). A simulação não usa
  bibliotecas externas.
- `matplotlib` e `Pillow`, apenas para os gráficos e a animação:
  `pip install matplotlib pillow`.

## Como executar

Todos os comandos devem ser rodados dentro desta pasta. Os parâmetros comuns
a todas as versões são `--linhas --colunas --geracoes --percentual --limiar
--semente --mostrar-grade`, e as extensões são `--beta --influenciadores
--peso-influenciador --bots --ceticos --resistencia`. Use `--help` em qualquer
script para ver a lista.

### Sequencial

```text
python FakeNews.py                      # cenário original: 100x100, 50 gerações, 5%, limiar 3
python FakeNews.py --limiar 2 --linhas 200 --colunas 200
```

### Paralela com threads

```text
python FakeNewsParalela.py --linhas 300 --colunas 300 --geracoes 10 --threads 4
```

### Paralela com multiprocessing

```text
python FakeNewsMultiprocessing.py --linhas 300 --colunas 300 --geracoes 10 --processos 4
```

### Distribuída (sockets TCP)

Abra um terminal para cada trabalhador:

```text
python FakeNewsDistribuida.py worker --port 5001
python FakeNewsDistribuida.py worker --port 5002
```

Em outro terminal, inicie o coordenador:

```text
python FakeNewsDistribuida.py coordinator --workers 127.0.0.1:5001,127.0.0.1:5002 --linhas 300 --colunas 300 --geracoes 10
```

- **Várias máquinas:** rode os workers nas outras máquinas e use os IPs delas
  em `--workers`, por exemplo `192.168.0.10:5001,192.168.0.11:5001`. Libere a
  porta no firewall.
- `--modo halo` (padrão): cada worker guarda a sua faixa e a cada geração
  recebe apenas as linhas de fronteira.
- `--modo faixa`: versão inicial, em que a faixa inteira é reenviada a cada
  geração. Foi mantida para comparar o custo de comunicação.
- O worker continua no ar depois que o coordenador termina. Para encerrá-lo,
  use Ctrl+C.

### Extensões do modelo (exemplo)

```text
python FakeNews.py --limiar 2 --beta 0.6 --influenciadores 0.01 --bots 0.005 --ceticos 0.3
```

Os mesmos parâmetros funcionam em todas as versões e produzem o mesmo
resultado.

### Testes, benchmark, gráficos e visualização

```text
python -m unittest -v test_implementacoes.py
python benchmark.py            # completo, ~15 min (use --rapido para testar)
                               # log da nossa execução: resultados/benchmark_log.txt
python gerar_graficos.py
python visualizar.py
python gerar_demonstracoes.py   # saídas mostradas no vídeo
```

## Decisões de implementação

- **Divisão:** faixas horizontais contíguas, equilibradas por
  `dividir_linhas`. Quando a divisão não é exata, as primeiras faixas recebem
  uma linha a mais.
- **Consistência entre gerações:** a geração atual é só lida, e a próxima é
  escrita em uma matriz nova.
- **Ausência de condição de corrida (threads):** cada thread escreve apenas na
  sua posição da lista de resultados. O `join()` funciona como barreira.
- **Multiprocessing e distribuída:** como os processos não compartilham
  memória, cada um recebe a sua faixa mais uma linha de halo acima e abaixo.
  As linhas viajam como `bytes`, ocupando 1 byte por célula.
- **Sincronização das fronteiras (distribuída, modo halo):** na geração
  *g+1*, o trabalhador *k* recebe a última linha calculada pelo trabalhador
  *k−1* e a primeira do *k+1* na geração *g*. O coordenador só avança depois de
  receber as respostas de todos (barreira).
- **Protocolo TCP:** cada mensagem leva um cabeçalho de 4 bytes com o
  tamanho, porque um `recv()` pode devolver só parte dos dados. O algoritmo de
  Nagle fica desligado (`TCP_NODELAY`), já que as mensagens são pequenas.
- **Limitação:** `pickle` não é seguro com dados de origem desconhecida. Use
  apenas em rede confiável.

## Melhorias implementadas

1. **Convencimento probabilístico (`--beta`).** Cada vizinho espalhador
   convence com probabilidade β, então com *k* vizinhos a chance de conversão
   é 1 − (1 − β)^k. Esse é o modelo de exposição independente dos modelos
   epidêmicos e de rumor.
2. **Influenciadores digitais (`--influenciadores`).** Um influenciador que
   espalha conta como `--peso-influenciador` vizinhos.
3. **Bots (`--bots`).** Começam espalhando e nunca ficam inativos.
4. **Resistência à propagação: céticos (`--ceticos`).** A chance de convencer
   um cético é reduzida pelo fator (1 − resistência).
5. **Sorteio reprodutível em paralelo.** Os números aleatórios saem de um
   gerador baseado em contador (hash SplitMix64 de semente, geração, linha e
   coluna). Assim, a versão probabilística dá exatamente o mesmo resultado em
   qualquer número de threads, processos ou máquinas, sem estado
   compartilhado.
6. **Versão com `multiprocessing`.** Dá paralelismo real, porque contorna o
   GIL.
7. **Redução da comunicação distribuída (modo halo).** Cada worker mantém o
   seu estado e só as fronteiras trafegam, o que reduz muito os bytes por
   geração (ver `resultados/tabelas.tex`). A contagem de estados também passa
   a ser feita em paralelo pelos workers.
8. **Estatísticas adicionais:** pico de espalhadores, geração do pico, alcance
   e geração de extinção.
9. **Visualização gráfica:** `visualizar.py` gera as imagens e o GIF.
10. **Testes automáticos de equivalência e métricas de comunicação.** O
    benchmark mede bytes trafegados e separa o tempo de cálculo do tempo de
    comunicação e sincronização.

Com os parâmetros padrão (`--beta 1` e nenhum perfil especial), o modelo é
exatamente o original. Isso é verificado em
`test_modelo_padrao_igual_ao_fornecido`.

## Uso de IA generativa

O grupo usou o assistente Claude (Anthropic) como apoio na revisão do código,
na implementação das extensões e na organização dos experimentos. O grupo
revisou, testou e é capaz de explicar todo o código entregue.
