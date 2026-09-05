#!/usr/bin/env bash
#
# Compila o Stockfish 17 para WebAssembly e escreve o resultado em engine/.
#
# Requer o Emscripten no PATH (source ~/emsdk/emsdk_env.sh). Baixa o código do
# Stockfish e a rede NNUE em build/, aplica tools/stockfish-wasm.patch e chama
# o emcc. Nada além dos artefatos entra no repositório.
#
# Três decisões moldam esse build:
#
#   single thread  A busca do Stockfish usa std::thread. Threads em WASM exigem
#                  SharedArrayBuffer, que exige os cabeçalhos COOP/COEP. O
#                  GitHub Pages não manda esses cabeçalhos. O patch troca a
#                  thread de busca por execução inline. O comando `go` trava até
#                  sair o bestmove, o que não incomoda porque o engine roda num
#                  Web Worker. Ainda dá mais de 1 milhão de nós por segundo.
#
#   só a rede small  O Stockfish 17 traz duas redes NNUE, uma de 62 MB e outra
#                  de 3 MB. Baixar 62 MB para abrir uma página é inviável, então
#                  o patch avalia tudo com a pequena.
#
#   SIMD128        O Emscripten mapeia os intrínsecos SSE do código NNUE para as
#                  instruções SIMD do WebAssembly, o que multiplica a velocidade
#                  da avaliação.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build"
OUT="$ROOT/engine"

VERSION="sf_17"
NET="nn-37f18f62d772.nnue"
SOURCE_URL="https://github.com/official-stockfish/Stockfish/archive/refs/tags/$VERSION.tar.gz"
NET_URL="https://tests.stockfishchess.org/api/nn/$NET"

command -v emcc >/dev/null || {
  echo 'emcc não encontrado. Rode `source ~/emsdk/emsdk_env.sh` antes.' >&2
  exit 1
}

mkdir -p "$BUILD" "$OUT"

if [ ! -d "$BUILD/Stockfish-$VERSION" ]; then
  echo "==> baixando o Stockfish $VERSION"
  curl -sL "$SOURCE_URL" | tar xz -C "$BUILD"

  echo "==> aplicando tools/stockfish-wasm.patch"
  (cd "$BUILD/Stockfish-$VERSION/src" && patch -p1 -i "$ROOT/tools/stockfish-wasm.patch")
fi

SRC="$BUILD/Stockfish-$VERSION/src"

if [ ! -f "$SRC/$NET" ]; then
  echo "==> baixando a rede $NET"
  curl -sL "$NET_URL" -o "$SRC/$NET"
fi

SOURCES=(
  "$ROOT/tools/main_wasm.cpp"
  benchmark.cpp bitboard.cpp evaluate.cpp misc.cpp movegen.cpp movepick.cpp
  position.cpp score.cpp search.cpp thread.cpp timeman.cpp tt.cpp uci.cpp
  ucioption.cpp tune.cpp memory.cpp engine.cpp
  syzygy/tbprobe.cpp
  nnue/nnue_misc.cpp nnue/features/half_ka_v2_hm.cpp nnue/network.cpp
)

echo "==> compilando"

cd "$SRC"
em++ -O3 -flto -std=c++17 \
  -DNDEBUG \
  -DSF_SINGLE_THREADED -DSF_SMALL_NET_ONLY -DNNUE_EMBEDDING_OFF \
  -DUSE_POPCNT -DUSE_SSE2 -DUSE_SSE41 -DUSE_SSSE3 \
  -msimd128 -msse -msse2 -msse3 -mssse3 -msse4.1 \
  -fno-exceptions -fno-rtti \
  -I"$SRC" \
  "${SOURCES[@]}" \
  -o "$OUT/stockfish.js" \
  --preload-file "$SRC/$NET@/$NET" \
  -sMODULARIZE=1 \
  -sEXPORT_NAME=Stockfish \
  -sEXPORT_ES6=0 \
  -sENVIRONMENT=web,worker,node \
  -sINVOKE_RUN=0 \
  -sEXIT_RUNTIME=0 \
  -sALLOW_MEMORY_GROWTH=1 \
  -sINITIAL_MEMORY=134217728 \
  -sMAXIMUM_MEMORY=1073741824 \
  -sSTACK_SIZE=8388608 \
  -sFILESYSTEM=1 \
  -sEXPORTED_FUNCTIONS='["_sf_init","_sf_command","_main","_malloc","_free"]' \
  -sEXPORTED_RUNTIME_METHODS='["ccall","cwrap","callMain","stringToNewUTF8"]'

echo "==> pronto"
ls -la "$OUT"
