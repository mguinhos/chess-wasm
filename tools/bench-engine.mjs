// Confere o engine compilado fora do navegador:
//
//     node tools/bench-engine.mjs
//
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const Stockfish = require('../engine/stockfish.js');

const lines = [];

// No Node o runtime procura o .data no diretório atual; aponta para engine/.
const engineDir = new URL('../engine/', import.meta.url);

const module = await Stockfish({
  print: (line) => lines.push(line),
  locateFile: (path) => new URL(path, engineDir).pathname,
});
const command = module.cwrap('sf_command', null, ['string']);

module.ccall('sf_init', null, [], []);
command('setoption name Hash value 16');
command('position startpos');

const started = Date.now();
command('go depth 16');
const elapsed = Date.now() - started;

const info = lines.filter((line) => line.startsWith('info depth')).pop();
const best = lines.find((line) => line.startsWith('bestmove'));

console.log(info);
console.log(`${best} em ${elapsed} ms na profundidade 16`);
