# chess-wasm

Xadrez em Python rodando no navegador com PyScript, contra o Stockfish 17 compilado para
WebAssembly.

Veja em [https://mguinhos.github.io/chess-wasm/](https://mguinhos.github.io/chess-wasm/)

É o porte de um jogo que era desktop. A lógica de xadrez é a mesma de antes, o que mudou
foi o entorno: o pygame virou `<canvas>`, o `pg.mixer` virou `<audio>` e o processo do
Stockfish virou um worker com o engine em WebAssembly. Não tem servidor, a página é
estática.

## Utiliza
- PyScript e Pyodide
- Stockfish 17 em WebAssembly
- Canvas 2D
- Bulma
- Playwright, nos testes

## Como está organizado

```
app/            o jogo em Python
  main.py       tabuleiro, seleção de peça e o laço de quadros
  ui.py         painel lateral com status, avaliação e histórico
  uci.py        conversa UCI com o worker do engine
  chess/        a lógica de xadrez, a mesma da versão desktop
engine/         o Stockfish compilado, mais o worker que fala com ele
tools/          build do engine e servidor de desenvolvimento
tests/          testes da lógica e do jogo dentro do navegador
```

## Servindo localmente

```bash
$ python tools/serve.py
```

Abrir o `index.html` direto do disco não funciona, o navegador precisa de HTTP para
carregar o worker e o `.wasm`.

## Testes

```bash
$ python tests/test_notation.py                      # lógica, sem navegador

$ pip install playwright && playwright install chromium
$ python tests/test_browser.py                       # joga uma partida de verdade
```

## Recompilando o engine

O Stockfish já vem compilado em `engine/`, isso aqui só é preciso para mexer no build. Com
o [Emscripten](https://emscripten.org/) instalado:

```bash
$ source ~/emsdk/emsdk_env.sh
$ ./tools/build-engine.sh
```

O script baixa o código do Stockfish 17, aplica `tools/stockfish-wasm.patch` e chama o
`emcc`. O patch faz três coisas.

**Tira as threads.** A busca do Stockfish usa `std::thread`, e thread em WebAssembly
depende de `SharedArrayBuffer`, que exige os cabeçalhos COOP e COEP. O GitHub Pages não
manda esses cabeçalhos. Sem as threads o `go` trava até sair o lance, o que não incomoda
porque o engine vive num worker. Ainda passa de 1 milhão de nós por segundo.

**Deixa só a rede pequena.** O Stockfish 17 traz duas redes NNUE, uma de 62 MB e outra de
3 MB. Baixar 62 MB para abrir uma página não se justifica, então a avaliação usa a pequena.

**Expõe um comando por vez.** O `UCIEngine::loop()` original fica preso em `std::cin`, e um
worker não tem stdin que trava. O laço virou um `execute()` que o worker chama a cada
mensagem.

## O que ficou de fora

A lógica de xadrez é a original, caseira, com os buracos que sempre teve: não tem roque nem
en passant do seu lado, e xeque-mate não é anunciado. Os lances do Stockfish entram
completos, com roque, en passant e promoção, porque quem valida os lances dele é ele mesmo.

## Licença

GPLv3, por causa do Stockfish, que vai distribuído junto e é GPLv3. O código do Stockfish
está em [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish),
aqui vão só o binário WebAssembly e o patch usado para gerá-lo.

2026 - Marcel Guinhos - GPLv3
