# Roteiro do vídeo: Fake News em Sistemas Paralelos e Distribuídos

**Grupo 7:** Arthur Henrique Caron, Gian Pedro Rodrigues, João Pedro
Trevisan Borghi e Mario Issamu Barbuglio Morita.

## Resumo: divisão do vídeo 🎬

A apresentação tem 15 slides (~1 min cada) e o vídeo deve dar uns 13 a 14
min (o limite é de 10 a 15). Não tem apêndice: tudo o que importa está
dentro dos 15 slides apresentados, incluindo a tabela completa de
speedup/eficiência (slide 10).

**Quem roda as demos:** só o **Gian** fica com o terminal e a tela
compartilhada do início ao fim do vídeo — é quem já testou tudo e está com
o ambiente pronto. Quando chega a vez da demo de alguém, essa pessoa
continua narrando normalmente e o Gian executa o comando na tela (combinem
um sinal, tipo "pode rodar"). Isso evita ficar trocando quem compartilha
tela ou pedir pra todo mundo configurar o próprio ambiente.

**Demonstrações ao vivo (híbrido):** sequencial, threads/multiprocessing,
distribuída e os testes rodam **de verdade, na tela, durante a gravação** —
são rápidas (menos de 2,5 s cada) e de baixo risco. A única coisa feita
**antes** de começar a gravar é o Gian subir os 4 workers da distribuída em
segundo plano, para não gastar tempo de vídeo abrindo 4 terminais. O
**slide 8** é um resumo com os números de uma execução de referência, caso
alguém queira ver os valores de novo com calma ou algo falhe ao vivo (as
saídas completas também ficam salvas em
`Codigo_Python_Entrega/resultados/demonstracoes/` como plano B).

No zip estão os códigos, os slides (PPTX e PDF) e este roteiro. Não precisa
decorar, falem com as próprias palavras. Todo mundo de câmera ligada o
tempo todo, e cada um diz em uma frase o que fez no trabalho.

### 1) Gian: 0:00 a 2:35 (slides 1 a 3)

- Capa: abre e cada um fala o próprio nome
- Problema e modelo: matriz = população, 3 estados (ignorante, espalhador, inativo), vizinhança de Moore, atualização síncrona numa matriz nova
- Sequencial: função `calcular_linhas`, que as 4 versões usam
- **Demo ao vivo (Gian roda):** `python FakeNews.py --limiar 2`

### 2) Mario: 2:35 a 5:10 (slides 4 e 5)

- Divisão em faixas com `dividir_linhas`, halo de 1 linha, threads sem condição de corrida (cada thread escreve só em `parciais[k]`), `join()` como barreira
- GIL: por que as threads não aceleram; multiprocessing com `pool.map` como barreira
- **Demo ao vivo (Gian roda, lado a lado, enquanto o Mario narra):** `FakeNewsParalela.py --threads 4` e `FakeNewsMultiprocessing.py --processos 4`, ambos 400x400, 10 gerações, limiar 2

### 3) Arthur: 5:10 a 8:35 (slides 6 a 8)

- Coordenador + workers TCP, modo halo (só as fronteiras trafegam), barreira por geração
- **Demo ao vivo (Gian roda, enquanto o Arthur narra):** só o coordenador (os 4 workers já estão rodando desde antes de gravar, também preparados pelo Gian)
- Protocolo: cabeçalho de 4 bytes, `_receber_exatamente`, `TCP_NODELAY`
- **Demo ao vivo (Gian roda, enquanto o Arthur narra):** `python -m unittest -v test_implementacoes.py` (12 testes)
- **Slide 8:** resumo com os números de referência das 5 execuções

### 4) Borghi: 8:35 a 12:05 (slides 9 a 12)

- Ambiente: Ryzen 5 5500U, 6 núcleos; 400x400, 20 gerações, 3 repetições
- Speedup: halo 3,67x (eficiência 0,92), multiprocessing 3,12x, threads ~1x (GIL)
- Cenários: matriz maior escala melhor; o halo troca ~50x menos dados que o modo faixa (6 KiB x 321 KiB por geração)
- Gargalos (Amdahl ~9% x ~3%) e limitações

### 5) Gian: 12:05 a 13:05 (slide 13)

- As 10 melhorias + o efeito no alcance (19,9% → 4,4% com β = 0,6, bots 12,3%, céticos 3,5%)
- Opcional: mostrar o GIF `resultados/propagacao.gif`

### 6) Mario: 13:05 a 13:50 (slides 14 e 15)

- Dificuldades e contribuição de cada um
- Referências e encerramento: "Obrigado"

### Antes de gravar

- **Gian deixa o ambiente pronto** no computador que vai compartilhar a
  tela: código testado, os 4 comandos de demo ensaiados ao menos uma vez.
- **Gian sobe os 4 workers da distribuída ANTES de ligar a gravação**, num
  terminal que fica fora da tela (minimizado ou numa outra janela):
  ```text
  python FakeNewsDistribuida.py worker --port 5001
  python FakeNewsDistribuida.py worker --port 5002
  python FakeNewsDistribuida.py worker --port 5003
  python FakeNewsDistribuida.py worker --port 5004
  ```
  Eles continuam no ar entre gravações; não precisa reiniciar a cada take.
- Gian deixa 2 terminais lado a lado prontos para a demo de threads/multiprocessing.
- Gian compartilha a tela o vídeo inteiro; nas demos que acontecem durante
  a fala de outra pessoa (Mario e Arthur), combinem um sinal, tipo "pode
  rodar", pra não atropelar a narração.
- Se algum comando falhar ao vivo, não travem: comentem o resultado
  esperado e sigam — o slide 8 mostra os números de qualquer forma.
- Cada um confere se o texto do slide 14 (o que cada um fez) está certo
- OBS: 1280x720, 30 fps, x264 + AAC 44,1 kHz
- Nome do vídeo: `AAAA-MM-DD - Grupo 07 - FakeNews.mp4`
- No fim do roteiro há perguntas prováveis do professor: todos devem saber responder

<!-- pagebreak -->

## Roteiro detalhado

**Duração prevista:** cerca de 13 a 14 minutos (o enunciado pede de 10 a
15). **Slides:** 15 no total, cerca de 1 minuto cada, todos apresentados —
sem apêndice. A tabela completa de speedup e eficiência está no slide 10,
não separada num material à parte.

**As demonstrações rodam ao vivo**, na tela, durante a gravação: são
rápidas (a mais longa leva pouco mais de 2 segundos) e testadas de
antemão. **O Gian é quem opera o terminal o vídeo inteiro** (tela
compartilhada única), inclusive nas demos que caem durante a fala de
outra pessoa — nesses casos o narrador continua falando e o Gian executa
o comando no momento combinado. A única coisa preparada antes de gravar é
o Gian subir os 4 workers da distribuída em segundo plano. O slide 8
resume os números de uma execução de referência e serve de plano B caso
algo falhe ao vivo; as saídas completas dessa execução de referência
ficam em `resultados/demonstracoes/` (geradas por
`python gerar_demonstracoes.py`).

Todos ficam com a câmera ligada o vídeo inteiro. As falas abaixo são um
guia: digam com as próprias palavras, sem ler.

| Integrante | Tempo | Slides |
|---|---|---|
| Gian Pedro Rodrigues | 0:00 a 2:35 | 1 a 3 |
| Mario Issamu Barbuglio Morita | 2:35 a 5:10 | 4 e 5 |
| Arthur Henrique Caron | 5:10 a 8:35 | 6 a 8 |
| João Pedro Trevisan Borghi | 8:35 a 12:05 | 9 a 12 |
| Gian | 12:05 a 13:05 | 13 |
| Mario | 13:05 a 13:50 | 14 e 15 |

## Antes de gravar

- Conferir a capa (Grupo 7 e nomes completos) e exportar o PDF de novo
  pelo PowerPoint, se mudarem algo no PPTX.
- **Gian deixa o ambiente pronto no computador dele** (é quem compartilha
  a tela o vídeo inteiro): código testado, cada comando de demo ensaiado
  ao menos uma vez.
- **Gian sobe os 4 workers antes de ligar a gravação** (ver comandos no
  resumo acima), numa janela fora de quadro. Eles ficam no ar entre takes.
- Gian deixa o VS Code aberto com os arquivos `.py` e dois terminais lado
  a lado prontos para a demo de threads/multiprocessing.
- Combinar com o Mario e o Arthur um sinal (tipo "pode rodar") para o
  momento exato de cada demo, já que quem fala não é quem digita.
- OBS: 1280x720, 30 fps, codificador x264, áudio AAC estéreo a 44,1 kHz,
  sem marca d'água.
- Nome do arquivo: `AAAA-MM-DD - Grupo 07 - FakeNews.mp4`.
- Fazer um ensaio cronometrado. Se passar de 14 minutos, encurtar as falas
  dos slides 9, 11 e 14.

---

## Gian: problema, modelo e sequencial (0:00 a 2:35)

### Slide 1, capa (0:20)

"Boa tarde, somos o grupo 7." Cada integrante diz o próprio nome. "Vamos
mostrar a simulação da propagação de fake news nas versões sequencial,
paralela e distribuída, e comparar o desempenho."

### Slide 2, problema e modelo (1:00)

"O problema é simular como uma notícia falsa se espalha numa população
representada por uma matriz: cada célula é uma pessoa. Cada pessoa tem três
estados: ignorante, espalhador e inativo. A vizinhança é a de Moore, os
oito vizinhos em volta. Um ignorante vira espalhador quando tem pelo menos
'limiar' vizinhos espalhadores, o espalhador fica inativo na geração
seguinte e o inativo continua inativo. A atualização é síncrona: todas as
células olham a mesma geração anterior. Por isso a próxima geração é
escrita numa matriz nova."

### Slide 3, solução sequencial (1:15, com demo)

"Isolamos a regra na função `calcular_linhas`, que calcula só um intervalo
de linhas e escreve numa matriz nova. As quatro versões chamam essa mesma
função, então a lógica é idêntica. O que muda é só quem calcula cada
pedaço."

**Demo ao vivo (20 s, Gian roda):** `python FakeNews.py --limiar 2`.
Mostrar as gerações passando e as estatísticas novas no final: pico de
espalhadores, alcance e geração de extinção.

**Sua parte:** dizer em uma frase o que você fez.

## Mario: divisão, threads e multiprocessing (2:35 a 5:10)

### Slide 4, divisão e threads (1:00)

"Dividimos a matriz em faixas horizontais, uma por thread, processo ou
worker. A `dividir_linhas` equilibra a carga, e o resto da divisão vai para
as primeiras faixas. Como Moore só alcança uma linha, cada faixa lê uma
linha de halo acima e uma abaixo. Na versão com threads, cada faixa tem uma
`threading.Thread` explícita. Não há condição de corrida: a grade atual só
é lida e a thread k escreve só em `parciais[k]`. O `join` é a barreira: a
nova geração só é montada quando todas terminam."

### Slide 5, GIL e multiprocessing (1:35, com demo)

"Só que as threads não aceleram. No CPython, o GIL deixa uma única thread
executar bytecode por vez. O enunciado permite multiprocessing: cada
processo tem o próprio interpretador e o próprio GIL. A divisão é a mesma,
as tarefas com a faixa e o halo em bytes são montadas por nós, e o
`pool.map` funciona como barreira."

**Demo ao vivo (35 s, Gian roda enquanto o Mario continua falando):**
rodar os dois comandos, um em cada terminal, e comparar os tempos. Mostrar
que a última geração é idêntica nos dois.

```text
python FakeNewsParalela.py --linhas 400 --colunas 400 --geracoes 10 --limiar 2 --threads 4
python FakeNewsMultiprocessing.py --linhas 400 --colunas 400 --geracoes 10 --limiar 2 --processos 4
```

**Sua parte:** dizer em uma frase o que você fez.

## Arthur: distribuída, corretude e demonstração (5:10 a 8:35)

### Slide 6, arquitetura distribuída (1:20, com demo)

"Na distribuída há um coordenador e N workers. Cada worker é um servidor
TCP e pode rodar em outra máquina. A melhoria principal é o modo halo: o
worker guarda a sua faixa e, a cada geração, recebe só as duas linhas
vizinhas e devolve as suas duas fronteiras e a contagem de estados. O
coordenador só começa a geração seguinte quando todos respondem: essa é a
barreira. Mantivemos o modo faixa, em que a faixa inteira vai e volta, para
comparar."

**Demo ao vivo (20 s, Gian roda enquanto o Arthur continua falando):** os
4 workers já estão rodando desde antes de começar a gravação (fora de
câmera, preparados pelo Gian). Rodar só o coordenador:

```text
python FakeNewsDistribuida.py coordinator --workers 127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003,127.0.0.1:5004 --linhas 400 --colunas 400 --geracoes 10 --limiar 2
```

Mostrar os bytes trafegados no final. Se houver duas máquinas, rodar um
worker na outra e usar o IP dela.

### Slide 7, protocolo e corretude (1:15, com demo)

"Cada mensagem leva um cabeçalho de 4 bytes com o tamanho, porque TCP é
fluxo e um `recv` pode trazer só parte da mensagem; por isso existe o
`_receber_exatamente`. O `TCP_NODELAY` desliga o algoritmo de Nagle, já que
as mensagens são pequenas, e o pickle só deve ser usado em rede confiável.
Para garantir a corretude, 12 testes comparam cada versão com a sequencial,
geração a geração, no modelo original e no estendido. O sorteio do modelo
probabilístico é um hash da semente, da geração e da posição, então não
importa quem calcula a célula."

**Demo ao vivo (15 s, Gian roda enquanto o Arthur continua falando):**
`python -m unittest -v test_implementacoes.py`, mostrando os 12 testes
passando.

### Slide 8, resumo das execuções (0:50)

"Este slide resume os números das execuções que acabamos de mostrar: a
sequencial levou 2,16 segundos, as threads 2,20 (iguais, por causa do
GIL), o multiprocessing 0,78, e a distribuída 1,03 no modo halo e 1,11 no
modo faixa, que rodamos antes para comparar. O ponto principal é que a
última geração é idêntica nas cinco execuções, e o modo halo trafegou 389
KB contra 3,29 MB no modo faixa. Os valores de tempo variam um pouco a
cada execução; os números de desempenho que valem para a análise são os
do benchmark, que o Borghi mostra agora."

**Sua parte:** dizer em uma frase o que você fez.

## Borghi: resultados e análise (8:35 a 12:05)

### Slide 9, ambiente e metodologia (0:45)

"Tudo rodou num Ryzen 5 5500U, com 6 núcleos físicos e 12 lógicos, Windows
11 e Python 3.14 com GIL. Os workers TCP rodaram como processos na mesma
máquina. O cenário base é 400 por 400, 20 gerações e 5% de espalhadores.
Variamos um fator por vez, com 1, 2, 4 e 8 trabalhadores, e repetimos cada
medição três vezes."

### Slide 10, speedup e eficiência (1:00)

"Esta é a tabela completa: tempo, speedup e eficiência para 1, 2, 4 e 8
trabalhadores, nas 5 versões. O sequencial leva 5,43 segundos. As threads
ficam entre 0,81 e 1 vez, por causa do GIL. O multiprocessing chega a 3,12
vezes com 4 processos, eficiência de 0,78. A distribuída no modo halo é a
melhor: 3,67 vezes com 4 workers, eficiência de 0,92. Com 8 o ganho não
aumenta, porque a CPU tem só 6 núcleos físicos."

### Slide 11, cenários e comunicação (1:00)

"À esquerda: quanto maior a matriz, maior o speedup. O modo halo vai de
3,32 vezes em 200 por 200 para 3,70 em 800 por 800, porque o cálculo cresce
com o quadrado do lado e a fronteira só com o lado. Variar as gerações e o
percentual de espalhadores quase não muda o speedup. À direita: no modo
faixa a grade vai e volta, cerca de 321 KiB por geração. No modo halo, em
regime, são uns 6 KiB, umas 50 vezes menos. A comunicação e a espera na
barreira ocupam 5% do tempo no halo, contra 15% no modo faixa."

### Slide 12, gargalos e limitações (0:45)

"As threads não ganham por causa do GIL. No multiprocessing, o processo
principal serializa as faixas e conta os estados: pela lei de Amdahl, uns
9% do trabalho ficam sequenciais. No modo halo isso cai para uns 3%, porque
o estado e a contagem ficam nos workers. Há uma barreira por geração, então
todos esperam o mais lento. As limitações: testamos numa máquina só, não há
tolerância a falhas, o pickle não é seguro com dados desconhecidos e as
threads só aceleram em Python sem GIL."

**Sua parte:** dizer em uma frase o que você fez.

## Gian: melhorias (12:05 a 13:05)

### Slide 13, dez melhorias (1:00)

"Implementamos dez melhorias. No modelo, todas desligadas por padrão:
convencimento probabilístico, influenciadores, bots, céticos e estatísticas
extras. Na computação: a versão com multiprocessing, o modo halo, o sorteio
por contador, a visualização e os testes com métricas de comunicação. No
modelo original com limiar 2, 19,9% da população recebe a notícia. Com
convencimento probabilístico, beta 0,6, o alcance cai para 4,4%. Os
influenciadores sobem para 7,6%, os bots mantêm a notícia viva e chegam a
12,3%, e os céticos freiam para 3,5%."

**Opcional (10 s):** mostrar `resultados/propagacao.gif`.

## Mario: encerramento (13:05 a 13:50)

### Slide 14, dificuldades e equipe (0:35)

"As principais dificuldades foram manter a atualização síncrona ao dividir
a matriz, acertar os índices das fronteiras, tratar o TCP como fluxo de
bytes, entender por que as threads eram mais lentas, deixar o sorteio igual
em qualquer divisão e algumas particularidades do Windows. À direita está a
contribuição de cada um, que cada integrante já contou na sua parte."

### Slide 15, referências (0:10)

"As referências estão em ABNT, incluindo o uso de IA generativa, como pede
o enunciado. Obrigado, ficamos à disposição para perguntas."

---

## Perguntas prováveis do professor

Qualquer integrante pode ser chamado a responder, então todos devem saber
estas respostas.

1. **Por que não alterar a matriz atual direto?** Uma célula veria
   resultados parciais da mesma geração, e o resultado dependeria da ordem
   de cálculo.
2. **Por que o halo tem uma linha?** A vizinhança de Moore só alcança uma
   linha acima e uma abaixo.
3. **Existe condição de corrida?** Não. A grade atual só é lida e cada
   thread ou processo escreve numa posição exclusiva.
4. **Por que as threads não aceleram?** Por causa do GIL do CPython. Em
   Python 3.14 sem GIL (free-threaded, PEP 703), o mesmo código rodaria em
   paralelo.
5. **Qual a diferença entre o modo halo e o modo faixa?** No modo faixa a
   faixa inteira é reenviada a cada geração. No modo halo o estado fica no
   worker, e só duas linhas entram e duas saem por geração.
6. **Como o modelo probabilístico dá o mesmo resultado em paralelo?** O
   sorteio é um hash de semente, geração, linha e coluna, e não depende de
   quem calcula a célula.
7. **E se um worker cair?** O coordenador recebe um `ConnectionError` e
   encerra a simulação. Uma extensão futura seria redistribuir a faixa
   desse worker.
8. **Por que a distribuída ganhou do multiprocessing no benchmark?** No
   modo halo o estado fica no worker e a contagem é feita em paralelo. No
   multiprocessing a faixa vai e volta a cada geração e a contagem é feita
   pelo processo principal.
9. **Por que medir com número fixo de gerações?** Para que todas as versões
   façam o mesmo trabalho e a comparação seja justa.
10. **Por que no slide 8 os números podem diferir um pouco do que acabamos
    de mostrar ao vivo?** Tempo de execução varia de uma corrida para
    outra, dependendo do estado da máquina no momento (outros processos,
    cache, agendamento do sistema operacional). O que não varia é a lógica:
    a última geração é sempre idêntica. Os números de desempenho que valem
    para a análise são os do benchmark, com 3 repetições por medição.
11. **Por que os workers da distribuída já estavam rodando antes de
    começar a gravar?** Só para não gastar tempo de vídeo abrindo 4
    terminais; o worker é um servidor TCP que fica esperando conexões, e
    continua no ar entre uma simulação e outra. O coordenador, que é a
    parte que realmente calcula e sincroniza as gerações, roda ao vivo.
12. **Por que só o Gian aparece digitando os comandos?** É só uma escolha
    prática de gravação: uma única tela compartilhada, já testada antes.
    Cada integrante explica a própria parte do código e das decisões de
    implementação, como pede o enunciado — quem roda o comando não muda
    quem entende e explica aquela parte.
