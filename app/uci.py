"""
Ponte UCI com o Stockfish compilado para WebAssembly.

O engine roda num worker (`engine/worker.js`) porque a busca usa uma thread só
e trava até achar o lance, e deixá-la fora da thread principal é o que mantém o
tabuleiro e o Python soltos.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import asyncio

from js import Worker
from pyodide.ffi import create_proxy


@dataclass
class Info:
    "O último `info` recebido durante a busca em andamento."

    depth: int = 0
    score: Optional[int] = None
    mate: Optional[int] = None
    nodes: int = 0
    nps: int = 0
    pv: str = ''


class Engine:
    def __init__(self, worker_url: str = 'engine/worker.js'):
        self.worker = Worker.new(worker_url)
        self.worker.addEventListener('message', create_proxy(self._on_message))

        self.info = Info()

        self.on_info: Optional[Callable[[Info], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        self._ready = asyncio.get_event_loop().create_future()
        self._search: Optional[asyncio.Future] = None

    # Recepção ---------------------------------------------------------------

    def _on_message(self, event):
        kind = event.data.type

        if kind == 'ready':
            if not self._ready.done():
                self._ready.set_result(True)
        elif kind == 'line':
            self._on_line(event.data.line)
        elif kind == 'error':
            if self.on_error:
                self.on_error(event.data.message)

    def _on_line(self, line: str):
        if line.startswith('info '):
            self._parse_info(line)
        elif line.startswith('bestmove '):
            move = line.split()[1]

            if self._search and not self._search.done():
                self._search.set_result(None if move in ('(none)', '0000') else move)

    def _parse_info(self, line: str):
        tokens = line.split()
        info = Info()

        for i, token in enumerate(tokens):
            if token == 'depth':
                info.depth = int(tokens[i + 1])
            elif token == 'nodes':
                info.nodes = int(tokens[i + 1])
            elif token == 'nps':
                info.nps = int(tokens[i + 1])
            elif token == 'score':
                if tokens[i + 1] == 'cp':
                    info.score = int(tokens[i + 2])
                elif tokens[i + 1] == 'mate':
                    info.mate = int(tokens[i + 2])
            elif token == 'pv':
                info.pv = ' '.join(tokens[i + 1:])

        if info.depth == 0:
            return

        self.info = info

        if self.on_info:
            self.on_info(info)

    # Envio ------------------------------------------------------------------

    def send(self, command: str):
        self.worker.postMessage(command)

        return self

    async def ready(self):
        await self._ready
        self.send('uci')
        self.send('isready')

        return self

    def new_game(self):
        self.send('ucinewgame')

        return self

    def set_option(self, name: str, value):
        self.send(f'setoption name {name} value {value}')

        return self

    def set_skill(self, level: int):
        "Força do engine, de 0 a 20, na escala do próprio Stockfish."

        return self.set_option('Skill Level', max(0, min(20, level)))

    async def best_move(self, moves: list[str], movetime: int = 500) -> Optional[str]:
        "Devolve o melhor lance para a posição inicial seguida de `moves`."

        self._search = asyncio.get_event_loop().create_future()

        position = 'position startpos'

        if moves:
            position += ' moves ' + ' '.join(moves)

        self.send(position)
        self.send(f'go movetime {movetime}')

        return await self._search
