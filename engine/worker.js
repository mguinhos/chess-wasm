/*
 * UCI bridge between the page and the WebAssembly build of Stockfish.
 *
 * The engine is single threaded, so a search blocks until it produces a
 * bestmove. Running it inside this worker keeps the board and the Python
 * runtime on the main thread responsive while it thinks.
 */

importScripts('./stockfish.js');

let send = null;
const pending = [];

Stockfish({
  print: (line) => postMessage({ type: 'line', line }),
  printErr: (line) => postMessage({ type: 'stderr', line }),
}).then((module) => {
  send = module.cwrap('sf_command', null, ['string']);
  module.ccall('sf_init', null, [], []);

  while (pending.length) send(pending.shift());

  postMessage({ type: 'ready' });
}).catch((error) => {
  postMessage({ type: 'error', message: String(error) });
});

onmessage = (event) => {
  const command = event.data;

  if (send) send(command);
  else pending.push(command);
};
