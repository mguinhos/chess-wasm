/*
  WebAssembly entry point for Stockfish.

  The native binary blocks on std::cin inside UCIEngine::loop(). A Web Worker
  has no blocking stdin, so instead of a loop we expose a single entry point
  that runs one UCI command and returns. Engine output goes to stdout, which
  Emscripten forwards to the JS `print` handler installed by the worker.
*/

#include <emscripten.h>

#include <iostream>
#include <memory>
#include <string>

#include "bitboard.h"
#include "misc.h"
#include "position.h"
#include "tune.h"
#include "uci.h"

using namespace Stockfish;

namespace {
std::unique_ptr<UCIEngine> engine;
}

extern "C" {

EMSCRIPTEN_KEEPALIVE void sf_init() {
    if (engine)
        return;

    Bitboards::init();
    Position::init();

    static char  arg0[] = "stockfish";
    static char* argv[] = {arg0, nullptr};

    engine = std::make_unique<UCIEngine>(1, argv);
    Tune::init(engine->engine_options());

    std::cout << engine_info() << std::endl;
}

EMSCRIPTEN_KEEPALIVE void sf_command(const char* cmd) {
    if (!engine || !cmd)
        return;

    engine->execute(std::string(cmd));
}
}

int main() {
    // Nothing to do: the worker drives the engine through sf_init/sf_command.
    return 0;
}
