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

"Oi, boa tarde! A gente é o grupo 7." Cada integrante diz o próprio nome.
"Nosso trabalho simula como uma fake news se espalha numa população, e a
gente fez isso de quatro jeitos: sequencial, com threads, com processos e
distribuído em rede. No fim, a gente compara o desempenho de cada um."

### Slide 2, problema e modelo (1:00)

"A ideia é simples: a população é uma matriz e cada célula é uma pessoa.
Cada pessoa pode estar em três estados: ignorante, que ainda não viu a
notícia; espalhador, que acreditou e tá repassando; e inativo, que já
repassou e cansou do assunto. Cada pessoa olha pros oito vizinhos em volta.
Se pelo menos 'limiar' vizinhos estão espalhando, ela começa a espalhar
também; na geração seguinte ela fica inativa e fica assim até o fim. Um
detalhe importante: todo mundo olha a geração anterior ao mesmo tempo,
então a geração nova é escrita numa matriz separada."

### Slide 3, solução sequencial (1:15, com demo)

"A regra toda fica numa função só, a `calcular_linhas`. Ela recebe um
pedaço das linhas, passa por cada célula, conta os vizinhos espalhando e
escreve o resultado numa matriz nova. O legal é que as quatro versões usam
essa mesma função, então a lógica é igualzinha em todas; o que muda é só
quem calcula cada pedaço."

**Demo ao vivo (20 s, Gian roda):** `python FakeNews.py --limiar 2`.
Mostrar as gerações passando e as estatísticas novas no final: pico de
espalhadores, alcance e geração de extinção.

**Sua parte:** dizer em uma frase o que você fez.

## Mario: divisão, threads e multiprocessing (2:35 a 5:10)

### Slide 4, divisão e threads (1:00)

"Pra paralelizar, a gente corta a matriz em faixas horizontais, uma pra
cada thread, processo ou worker. A `dividir_linhas` deixa as faixas do
mesmo tamanho, e se sobrar linha ela vai pras primeiras. Só que a célula da
borda precisa ver o vizinho da faixa do lado, então cada faixa lê uma linha
extra em cima e uma embaixo: isso é o halo. Na versão com threads, cada
faixa ganha uma `threading.Thread`. E não tem condição de corrida, porque
ninguém escreve na grade atual e cada thread só mexe no seu `parciais[k]`.
O `join` funciona como barreira: só monta a próxima geração quando todas
terminaram."

### Slide 5, GIL e multiprocessing (1:35, com demo)

"Só que aí veio a surpresa: as threads não deixaram nada mais rápido. A
culpa é do GIL: no Python padrão só uma thread roda por vez, e como nosso
cálculo é só CPU, colocar mais threads não ajuda. A saída foi usar
multiprocessing, que o enunciado permite: cada processo tem seu próprio
Python e seu próprio GIL, então aí sim roda em paralelo de verdade. A
divisão em faixas é a mesma, e o `pool.map` faz o papel de barreira."

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

"Na versão distribuída tem um coordenador e vários workers. Cada worker é
um servidor TCP e pode rodar em outra máquina. A sacada principal foi o
modo halo: cada worker fica com a sua faixa guardada e, a cada geração, só
recebe as duas linhas vizinhas e devolve as duas linhas de borda e a
contagem. O coordenador só começa a próxima geração quando todo mundo
respondeu, essa é a barreira. A gente deixou também o modo faixa, que foi
nossa primeira versão e manda a faixa inteira toda vez, só pra comparar."

**Demo ao vivo (20 s, Gian roda enquanto o Arthur continua falando):** os
4 workers já estão rodando desde antes de começar a gravação (fora de
câmera, preparados pelo Gian). Rodar só o coordenador:

```text
python FakeNewsDistribuida.py coordinator --workers 127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003,127.0.0.1:5004 --linhas 400 --colunas 400 --geracoes 10 --limiar 2
```

Mostrar os bytes trafegados no final. Se houver duas máquinas, rodar um
worker na outra e usar o IP dela.

### Slide 7, protocolo e corretude (1:15, com demo)

"Sobre o protocolo: o TCP não separa as mensagens, um `recv` pode vir pela
metade. Então toda mensagem começa com 4 bytes dizendo o tamanho, e o
`_receber_exatamente` fica lendo até completar. Também ligamos o
`TCP_NODELAY`, pra ele mandar as mensagens pequenas na hora em vez de ficar
segurando. E pra ter certeza de que tá tudo certo, temos 12 testes que
comparam cada versão com a sequencial, geração por geração, no modelo
original e no estendido. Até o sorteio do modelo probabilístico dá igual,
porque ele vem de um hash da posição da célula, então não importa quem
calcula."

**Demo ao vivo (15 s, Gian roda enquanto o Arthur continua falando):**
`python -m unittest -v test_implementacoes.py`, mostrando os 12 testes
passando.

### Slide 8, resumo das execuções (0:50)

"Aqui tá o resumo do que a gente acabou de rodar: o sequencial levou 2,16
segundos, as threads 2,20, praticamente igual por causa do GIL, o
multiprocessing 0,78 e a distribuída 1,03 no modo halo e 1,11 no modo
faixa, que rodamos antes pra comparar. O mais importante: a última geração
deu exatamente igual nas cinco. E o halo mandou 389 KB pela rede, contra
3,29 MB do modo faixa. O tempo varia um pouco a cada execução, então os
números pra valer são os do benchmark, que o Borghi mostra agora."

**Sua parte:** dizer em uma frase o que você fez.

## Borghi: resultados e análise (8:35 a 12:05)

### Slide 9, ambiente e metodologia (0:45)

"Pra medir direito, rodamos tudo num Ryzen 5 5500U, que tem 6 núcleos,
com Windows 11 e Python 3.14. Os workers rodaram na mesma máquina. O
cenário base é uma matriz 400 por 400, com 20 gerações e 5% de
espalhadores. A gente mudou um fator por vez, testou com 1, 2, 4 e 8
trabalhadores e repetiu cada medição três vezes."

### Slide 10, speedup e eficiência (1:00)

"Essa é a tabela completa. O sequencial leva 5,43 segundos. As threads
ficam ali em 1 vez, ou seja, nenhum ganho, por causa do GIL. O
multiprocessing chega a 3,12 vezes mais rápido com 4 processos. E a
distribuída no modo halo foi a melhor: 3,67 vezes com 4 workers, com
eficiência de 0,92. Com 8 não melhora, porque a CPU só tem 6 núcleos."

### Slide 11, cenários e comunicação (1:00)

"No gráfico da esquerda dá pra ver que quanto maior a matriz, melhor o
ganho: o halo vai de 3,32 vezes no 200 por 200 pra 3,70 no 800 por 800.
Isso porque o cálculo cresce bem mais rápido que a borda que precisa ser
trocada. Mudar gerações ou espalhadores quase não muda nada. No da direita,
a comunicação: o modo faixa manda uns 321 KiB por geração, e o halo uns 6,
umas 50 vezes menos. No halo, comunicação e espera comem só 5% do tempo,
contra 15% no modo faixa."

### Slide 12, gargalos e limitações (0:45)

"Resumindo onde perde tempo: as threads travam no GIL. No
multiprocessing, o processo principal ainda empacota as faixas e conta os
estados sozinho, então pela lei de Amdahl uns 9% fica sequencial. No halo
isso cai pra uns 3%, porque os workers guardam o estado e contam sozinhos.
E como tem barreira a cada geração, todo mundo espera o mais lento. O que
ainda dá pra melhorar: só testamos numa máquina, se um worker cair a
simulação para, o pickle só é seguro numa rede confiável, e as threads só
ganhariam num Python sem GIL."

**Sua parte:** dizer em uma frase o que você fez.

## Gian: melhorias (12:05 a 13:05)

### Slide 13, dez melhorias (1:00)

"Além do básico, a gente fez dez melhorias. No modelo, todas desligadas
por padrão: convencimento probabilístico, influenciadores, bots, céticos e
umas estatísticas a mais. Na parte de computação: o multiprocessing, o modo
halo, o sorteio por contador, a visualização e os testes com métricas de
comunicação. E dá pra ver o efeito: no modelo original a notícia chega em
19,9% da população. Com o convencimento probabilístico cai pra 4,4%. Os
influenciadores sobem pra 7,6%, os bots mantêm a notícia viva e chegam em
12,3%, e os céticos seguram em 3,5%."

**Opcional (10 s):** mostrar `resultados/propagacao.gif`.

## Mario: encerramento (13:05 a 13:50)

### Slide 14, dificuldades e equipe (0:35)

"O que mais deu trabalho: manter todo mundo olhando a mesma geração
depois de dividir a matriz, acertar os índices das bordas, lidar com o TCP
mandando mensagem pela metade, entender por que as threads eram mais
lentas, fazer o sorteio dar igual em qualquer divisão e umas manias do
Windows. Do lado direito tá o que cada um fez, que cada um já contou na sua
parte."

### Slide 15, referências (0:10)

"Aqui estão as referências que a gente usou, incluindo o uso de IA, como o
enunciado pede. É isso, obrigado! Ficamos à disposição pra perguntas."

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
