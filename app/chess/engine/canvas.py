"""
Camada de apresentação para o navegador.

Substitui `chess/engine/app.py`, que desenhava com pygame, por um equivalente
sobre o <canvas> 2D. A interface é a mesma da versão desktop: `init`,
`process`, `render`, um `surface` com `fill` e `blit` e um `mouse`. Assim a
lógica do jogo em `chess/piece.py` e `chess/table.py` roda sem alteração.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import asyncio

from js import Image as JsImage, ResizeObserver, document, window
from pyodide.ffi import create_proxy

from .coordinates import Position


async def load_image(source: str):
    "Carrega uma imagem e devolve o elemento <img> já decodificado."

    image = JsImage.new()
    loaded = asyncio.get_event_loop().create_future()

    def on_load(_event):
        if not loaded.done():
            loaded.set_result(image)

    def on_error(_event):
        if not loaded.done():
            loaded.set_exception(IOError(f'não foi possível carregar {source}'))

    image.addEventListener('load', create_proxy(on_load))
    image.addEventListener('error', create_proxy(on_error))
    image.src = source

    return await loaded


@dataclass
class Sprite:
    "Um recorte de uma spritesheet, com o tamanho em que será desenhado."

    image: Any
    sx: float
    sy: float
    sw: float
    sh: float
    w: float
    h: float

    def scale(self, w: float, h: float) -> "Sprite":
        return Sprite(self.image, self.sx, self.sy, self.sw, self.sh, w, h)


@dataclass
class Spritesheet:
    image: Any

    def subsurface(self, placement: tuple[float, float, float, float]) -> Sprite:
        sx, sy, sw, sh = placement

        return Sprite(self.image, sx, sy, sw, sh, sw, sh)


class Surface:
    "O equivalente ao `pg.Surface` da versão desktop."

    def __init__(self, context, width: float, height: float):
        self.context = context
        self.width = width
        self.height = height

    def fill(self, color: str):
        self.context.fillStyle = color
        self.context.fillRect(0, 0, self.width, self.height)

        return self

    def fill_rect(self, color: str, position: tuple[float, float], size: tuple[float, float]):
        x, y = position
        w, h = size

        self.context.fillStyle = color
        self.context.fillRect(x, y, w, h)

        return self

    def blit(self, sprite: Sprite, position: tuple[float, float]):
        x, y = position

        self.context.drawImage(
            sprite.image,
            sprite.sx, sprite.sy, sprite.sw, sprite.sh,
            x, y, sprite.w, sprite.h
        )

        return self


@dataclass
class Mouse:
    # Fora do tabuleiro: sem isso a casa a8 aparece realçada antes de o
    # ponteiro sequer entrar no canvas.
    position: Position = field(default_factory=lambda: Position(-1, -1))
    left_button: bool = False
    middle_button: bool = False
    right_button: bool = False


class App:
    """
    Laço de aplicação sobre requestAnimationFrame.

    `process` e `render` são chamados uma vez por quadro, na mesma ordem da
    versão pygame, e os cliques valem por um único quadro.
    """

    def __init__(self, canvas_id: str, width: int, height: int):
        self.width = width
        self.height = height

        self.canvas = document.getElementById(canvas_id)
        self.context = self.canvas.getContext('2d')
        self.surface = Surface(self.context, width, height)

        self.mouse = Mouse()
        self.running = False

        # Cliques chegam por evento e são consumidos um por quadro, cada um na
        # casa em que aconteceu. Sem a fila, dois cliques dentro dos mesmos
        # 16 ms virariam um só na posição errada.
        self._hover = Position(-1, -1)
        self._clicks = []

        self._frame = create_proxy(self._on_frame)

        self.canvas.addEventListener('pointermove', create_proxy(self._on_pointer_move))
        self.canvas.addEventListener('pointerdown', create_proxy(self._on_pointer_down))
        self.canvas.addEventListener('pointerup', create_proxy(self._on_pointer_up))
        self.canvas.addEventListener('contextmenu', create_proxy(lambda event: event.preventDefault()))

        # Observar o próprio canvas pega tudo que muda o tamanho dele: janela
        # redimensionada, zoom e DevTools abrindo.
        self._observer = ResizeObserver.new(create_proxy(lambda _entries, _observer: self.resize()))
        self._observer.observe(self.canvas)

        self.resize()

    # Redimensionamento -----------------------------------------------------

    def resize(self):
        """
        Mantém o canvas nítido: o buffer segue o devicePixelRatio enquanto o
        desenho continua usando as coordenadas lógicas do tabuleiro.
        """

        # Lido a cada chamada: o devicePixelRatio muda quando o usuário dá
        # zoom, e um valor capturado na importação deixaria o canvas borrado.
        ratio = window.devicePixelRatio or 1
        box = self.canvas.getBoundingClientRect()

        css_width = box.width or self.width
        css_height = box.height or self.height

        self.canvas.width = int(css_width * ratio)
        self.canvas.height = int(css_height * ratio)

        self.context.setTransform(
            self.canvas.width / self.width, 0,
            0, self.canvas.height / self.height,
            0, 0
        )

        self.context.imageSmoothingEnabled = True
        self.context.imageSmoothingQuality = 'high'

        return self

    # Entrada ---------------------------------------------------------------

    def _to_board(self, event) -> Position:
        box = self.canvas.getBoundingClientRect()

        return Position(
            (event.clientX - box.left) * self.width / (box.width or self.width),
            (event.clientY - box.top) * self.height / (box.height or self.height)
        )

    def _on_pointer_move(self, event):
        self._hover = self._to_board(event)

    def _on_pointer_down(self, event):
        event.preventDefault()

        # No toque não há hover: a posição só chega junto com o clique.
        position = self._to_board(event)
        self._hover = position

        if event.button == 0:
            self._clicks.append(position)
        elif event.button == 1:
            self.mouse.middle_button = True
        elif event.button == 2:
            self.mouse.right_button = True

    def _on_pointer_up(self, event):
        event.preventDefault()

    # Laço ------------------------------------------------------------------

    def init(self):
        return self

    def process(self):
        return self

    def render(self):
        return self

    def reset_updates(self):
        self.mouse.left_button = False
        self.mouse.middle_button = False
        self.mouse.right_button = False

    def _on_frame(self, _timestamp):
        if not self.running:
            return

        if self._clicks:
            self.mouse.position = self._clicks.pop(0)
            self.mouse.left_button = True
        else:
            self.mouse.position = self._hover
            self.mouse.left_button = False

        self.surface.fill('#ffffff')

        self.process()
        self.render()
        self.reset_updates()

        window.requestAnimationFrame(self._frame)

    def run(self):
        self.running = True
        window.requestAnimationFrame(self._frame)

        return self

    def stop(self):
        self.running = False

        return self
