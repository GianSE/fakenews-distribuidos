# Roteiro do vídeo (10 a 15 min, 4 integrantes)

Meta: cerca de 13 minutos. Todos com a câmera ligada o tempo inteiro.
Cada integrante apresenta os slides da sua parte e mostra o código e a
execução no terminal. O roteiro é um guia: falem com as próprias palavras.

Antes de gravar:
- deixar 4 terminais abertos na pasta `Codigo_Python_Entrega`;
- deixar o VS Code aberto com os arquivos `.py`;
- abrir `resultados/propagacao.gif`;
- gravar em 1280x720 a 30 fps (no OBS: Configurações → Vídeo/Saída,
  codificador x264 e áudio AAC a 44,1 kHz);
- nome do arquivo: `AAAA-MM-DD - Grupo XX - FakeNews.mp4`.

---

## 1. Gian: problema, modelo e sequencial (0:00–3:00)

**Slides:** capa, descrição do problema, modelo computacional, sequencial.

- Apresentar o grupo (cada um diz o próprio nome rapidamente).
- Explicar o problema: a matriz é a população, cada célula tem 3 estados e
  a vizinhança é a de Moore.
- Explicar a regra e por que a atualização é síncrona, numa matriz nova.
- Mostrar no código `calcular_linhas` em `FakeNews.py`. Explicar que todas as
  versões chamam essa mesma função e que, por isso, a lógica é a mesma.
- **Demo:** `python FakeNews.py --limiar 2`. Mostrar as gerações e as
  estatísticas novas no final (pico, alcance, extinção).
- Contar o que fez no trabalho.

## 2. Mario: divisão, threads e multiprocessing (3:00–6:15)

**Slides:** divisão da matriz, threads, GIL/multiprocessing.

- Explicar `dividir_linhas`: faixas equilibradas, com o resto indo para as
  primeiras faixas.
- Na versão com threads, explicar por que não há condição de corrida: a
  grade atual é só lida e cada thread escreve só em `parciais[k]`. O
  `join()` é a barreira.
- Explicar o GIL: por que as threads não ficam mais rápidas.
- Na versão com multiprocessing, explicar que os processos não compartilham
  memória, por isso cada um recebe a faixa com halo em `bytes`, e que o
  `pool.map` funciona como barreira.
- **Demo:**
  `python FakeNewsParalela.py --linhas 300 --colunas 300 --geracoes 10 --threads 4`
  e depois
  `python FakeNewsMultiprocessing.py --linhas 300 --colunas 300 --geracoes 10 --processos 4`.
  Comparar os tempos e mostrar que as contagens das duas são idênticas.
- Contar o que fez no trabalho.

## 3. Arthur: distribuída e comunicação (6:15–9:30)

**Slides:** distribuída, sincronização de fronteiras e protocolo, corretude.

- Arquitetura: um coordenador e N workers, cada worker é um servidor TCP.
- Explicar o modo halo. O worker guarda a sua faixa e, a cada geração,
  recebe só as linhas vizinhas e devolve as suas fronteiras e a contagem.
  Mostrar `passo_halo` no código.
- Protocolo: cabeçalho de 4 bytes com o tamanho, `_receber_exatamente` e por
  que um único `recv()` não basta. Falar do `TCP_NODELAY` e da limitação do
  `pickle`.
- **Demo:** 3 terminais com
  `python FakeNewsDistribuida.py worker --port 5001` (e as portas 5002 e
  5003). No quarto terminal:
  `python FakeNewsDistribuida.py coordinator --workers 127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003 --linhas 300 --colunas 300 --geracoes 10`.
  Mostrar os bytes trafegados e repetir com `--modo faixa` para comparar.
  Se houver duas máquinas, rodar um worker na outra usando o IP dela.
- **Demo:** `python -m unittest -v test_implementacoes.py`, com os 12
  testes passando.
- Contar o que fez no trabalho.

## 4. Borghi: resultados, melhorias e conclusão (9:30–13:00)

**Slides:** configuração, speedup/eficiência, tabelas, cenários,
comunicação, análise, melhorias, extensões, visualização, dificuldades,
contribuições, referências.

- Configuração da máquina e metodologia: um fator variado por vez e 3
  repetições.
- Ler o gráfico de escalabilidade (cenário base 400x400, 20 gerações):
  - sequencial: 5,43 s;
  - threads: entre 0,81x e 1,00x, por causa do GIL;
  - multiprocessing: 3,12x com 4 processos;
  - distribuída no modo halo: 3,67x com 4 workers e eficiência de 0,92,
    o melhor resultado;
  - com 8 workers o ganho não aumenta, porque a CPU tem 6 núcleos físicos.
- Cenários: matrizes maiores escalam melhor (modo halo com 3,7x em 800x800).
- Comunicação: o modo faixa troca 321 KiB por geração e o modo halo cerca de
  6 KiB em regime, ou seja, 50x menos. Com 4 workers, a comunicação mais a
  sincronização ocupam só 5% do tempo no modo halo.
- Análise: gargalos, sincronização e limitações (slide "Análise").
- Melhorias: passar pela lista e mostrar o gráfico de curvas e o GIF.
- Dificuldades e contribuição de cada integrante.
- Encerrar: "Obrigado".

---

## Perguntas prováveis do professor

1. **Por que não alterar a matriz atual direto?** Uma célula veria
   resultados parciais da mesma geração, e o resultado dependeria da ordem
   de cálculo.
2. **Por que o halo tem 1 linha?** A vizinhança de Moore só alcança uma
   linha acima e uma abaixo.
3. **Existe condição de corrida?** Não. A entrada é só lida e cada
   thread/processo escreve numa posição exclusiva.
4. **Por que as threads não aceleram?** Por causa do GIL do CPython. Em
   Python 3.14 sem GIL (free-threaded, PEP 703) o mesmo código rodaria em
   paralelo.
5. **Qual a diferença entre o modo halo e o modo faixa?** No modo faixa a
   faixa inteira é reenviada a cada geração. No modo halo o estado fica no
   worker e só 2 linhas entram e 2 saem por geração.
6. **Como o modelo probabilístico dá o mesmo resultado em paralelo?** O
   sorteio é um hash de (semente, geração, i, j) e não depende de quem
   calcula a célula.
7. **E se um worker cair?** O coordenador recebe `ConnectionError` e
   encerra. Uma extensão futura seria redistribuir a faixa dele.
8. **Por que a distribuída local ganhou do multiprocessing?** No modo halo o
   estado fica no worker e a contagem é feita em paralelo. No
   multiprocessing a faixa vai e volta a cada geração e a contagem é feita
   pelo processo principal.
9. **Por que medir com número fixo de gerações?** Para que todas as versões
   façam o mesmo trabalho e a comparação seja justa.
