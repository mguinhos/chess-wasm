"""
Porte do jogo para a web.

É o mesmo `main.py` da versão desktop. As classes `Boundingbox` e `Chess`, o
laço `process`/`render` e a tabela de recortes da spritesheet continuam iguais.
Só o entorno mudou: o pygame virou <canvas>, o `pg.mixer` virou <audio> e o
processo do Stockfish virou um worker com o engine compilado para WebAssembly.
O servidor TCP saiu porque não faz sentido dentro do navegador.
"""

from dataclasses import dataclass
from math import radians, sin, cos
import asyncio

from chess.engine.canvas import App, Spritesheet, load_image
from chess.engine.coordinates import Size, Position

from chess.notation import POS_TO_ID, apply_uci_move
from chess.table import Table
from chess.piece import *

from audio import Sounds
from uci import Engine
import ui


@dataclass
class Boundingbox:
    position: Position
    size: Size

    def is_position_inside(self, position: Position) -> bool:
        px, py = position

        x, y = self.position
        x1, y1 = self.position + Position(self.size.w, self.size.h)

        return (
            (px >= x and px <= x1) and (py >= y and py <= y1)
        )


shake_animation_frame = 9999
SHAKE_ANIMATION = []

for i in range(3600):
    i /= 10

    SHAKE_ANIMATION.append(
        Position(sin(radians(i)), cos(radians(i)) / 2)
    )

# Os tiles da spritesheet já marcam os lances possíveis. Por isso o último
# lance ganha um tom próprio por cima da casa.
LAST_MOVE_TINT = 'rgba(240, 200, 90, 0.38)'

class Chess(App):
    bboxes: list[Boundingbox]

    def init(self):
        self.pieces_placements = {
            "wk": (0, 150, 150, 150),
            "wq": (150, 150, 150, 150),
            "wr": (150 * 2, 150, 150, 150),
            "wb": (150 * 3, 150, 150, 150),
            "wn": (150 * 4, 150, 150, 150),
            "wp": (150 * 5, 150, 150, 150),
            "wt": (150 * 6, 150, 150, 150),
            "wtl": (150 * 7, 150, 150, 150),
            "wtr": (150 * 8, 150, 150, 150),
            "wtb": (150 * 9, 150, 150, 150),

            "bk": (0, 0, 150, 150),
            "bq": (150, 0, 150, 150),
            "br": (150 * 2, 0, 150, 150),
            "bb": (150 * 3, 0, 150, 150),
            "bn": (150 * 4, 0, 150, 150),
            "bp": (150 * 5, 0, 150, 150),
            "bt": (150 * 6, 0, 150, 150),
            "btl": (150 * 7, 0, 150, 150),
            "btr": (150 * 8, 0, 150, 150),
            "btb": (150 * 9, 0, 150, 150),
        }

        self.turn = PieceRole.White

        self.scale = Size(100, 100)
        self.table = Table()
        self.move_highlights = {}
        self.selected_piece = None
        self.selected_piece_bbox = None

        self.history = []
        self.last_move = ()

        self.thinking = False
        self.finished = False

        self.update_zoom()

        return self

    def update_zoom(self):
        w, h = self.scale

        self.pieces_subsurfaces = {}

        self.bboxes = []

        for name, placement in self.pieces_placements.items():
            self.pieces_subsurfaces[name] = self.pieces.subsurface(placement).scale(w, h)

        for j in range(8):
            for i in range(8):
                self.bboxes.append(Boundingbox(Position(i * w, j * h), self.scale))

        return self

    def verify_check(self):
        for piece in self.table.pieces.values():
            if piece.role == self.turn:
                continue

            for move in piece.get_moves(self.table).values():
                if move.kind is not MoveKind.Capture:
                    continue

                piece_in_position = self.table[move.position]

                if type(piece_in_position) in (BeginKing, King):
                    return True

        return False

    def process_move(self, piece: Piece, move: Move):
        destination = self.table[move.position]

        if piece.role is not self.turn:
            return False
        elif destination and destination.role is self.turn:
            return False

        was_pawn = get_piece_name(piece) == 'p'
        piece = piece.on_move(self.table, move)

        if destination:
            if move.kind is not MoveKind.Capture:
                return False

        previous_piece = self.table[move.position]
        previous_position = piece.position
        next_position = move.position

        self.table[move.position] = piece
        self.table[piece.position] = None
        piece.position = move.position

        if self.verify_check():
            self.table[previous_position] = piece
            self.table[piece.position] = previous_piece
            piece.position = previous_position

            self.sounds.play('game-end')

            return False

        self.record_move(was_pawn, previous_position, next_position)

        if self.turn is PieceRole.White:
            self.turn = PieceRole.Black
        else:
            self.turn = PieceRole.White

        return move.kind

    def record_move(self, was_pawn: bool, origin: Position, destination: Position):
        """
        Registra o lance em notação longa, que é o que o Stockfish lê.

        O sufixo de promoção não existia na versão desktop. Sem ele o engine
        recusa a linha inteira e a partida sai de sincronia. Neste ponto o
        `TopPawn.on_move` já trocou o peão por uma dama. Por isso o sufixo é
        sempre 'q'.
        """

        notation = POS_TO_ID[origin] + POS_TO_ID[destination]

        if was_pawn and destination.y == 0:
            notation += 'q'
            self.sounds.play('promote')

        self.history.append(notation)
        self.last_move = (origin, destination)

        ui.set_history(self.history)

        return self

    def update_highlights(self, piece: Piece):
        self.move_highlights = {}

        for position, move in piece.get_moves(self.table).items():
            self.move_highlights[position] = move

    # Lances do engine ------------------------------------------------------

    def apply_engine_move(self, notation: str):
        "Aplica no tabuleiro o lance escolhido pelo Stockfish."

        applied = apply_uci_move(self.table, notation)

        if applied is None:
            return False

        self.history.append(notation)
        self.last_move = (applied.origin, applied.destination)

        ui.set_history(self.history)

        self.turn = PieceRole.White

        if applied.castled:
            self.sounds.play('castle')
        elif applied.promoted:
            self.sounds.play('promote')
        elif applied.captured:
            self.sounds.play('capture')
        else:
            self.sounds.play('move-opponent')

        return True

    async def play_engine_move(self):
        self.thinking = True
        ui.set_status('Stockfish pensando', busy=True)

        move = await self.engine.best_move(self.history, movetime=ui.movetime())

        self.thinking = False

        if move is None:
            self.finished = True
            ui.set_status('Fim de jogo, o Stockfish não tem lances', busy=False)
            self.sounds.play('game-end')

            return self

        self.apply_engine_move(move)
        ui.set_status('Sua vez', busy=False)

        return self

    # Laço ------------------------------------------------------------------

    def process(self):
        global shake_animation_frame

        w, h = self.scale

        if self.finished:
            return self

        if self.turn is PieceRole.Black:
            if not self.thinking:
                asyncio.ensure_future(self.play_engine_move())

            return self

        # Sem isso os realces do último hover ficam presos quando o ponteiro sai
        # do tabuleiro.
        if not self.selected_piece:
            self.move_highlights = {}

        for bbox in self.bboxes:
            if bbox.is_position_inside(self.mouse.position):
                abs_position = bbox.position / Position(w, h)
                piece = self.table[abs_position]

                if self.selected_piece:
                    self.update_highlights(self.selected_piece)

                    if self.mouse.left_button:
                        if abs_position in self.move_highlights:
                            if not self.process_move(self.selected_piece, self.move_highlights[abs_position]):
                                self.sounds.play('illegal')
                                shake_animation_frame = 0

                                # Quase sempre é o rei ficando em xeque. Sem
                                # aviso isso parece um travamento.
                                ui.set_status('Lance recusado: o rei ficaria em xeque')
                            else:
                                self.sounds.play('move-self')
                                self.move_highlights = {}

                        self.selected_piece = None
                        self.selected_piece_bbox = None
                elif piece:
                    self.update_highlights(piece)

                    if self.mouse.left_button:
                        self.selected_piece = piece
                        self.selected_piece_bbox = bbox
                        self.sounds.play('click')

        return self

    def render(self):
        global shake_animation_frame

        w, h = self.scale

        tiles_subsurfaces = [self.pieces_subsurfaces['wt'], self.pieces_subsurfaces['bt']]
        tiles_subsurfaces_highlighted = [self.pieces_subsurfaces['wtl'], self.pieces_subsurfaces['btl']]
        tiles_subsurface_highlighted_red = [self.pieces_subsurfaces['wtr'], self.pieces_subsurfaces['btr']]
        tiles_subsurface_highlighted_blue = [self.pieces_subsurfaces['wtb'], self.pieces_subsurfaces['btb']]

        for j in range(8):
            for i in range(8):
                self.surface.blit(tiles_subsurfaces[(i + j) % 2], (i * w, j * h))

                if Position(i, j) in self.last_move:
                    self.surface.fill_rect(LAST_MOVE_TINT, (i * w, j * h), (w, h))

                move = self.move_highlights.get(Position(i, j))

                if move:
                    if move.kind is MoveKind.Illegal:
                        self.surface.blit(tiles_subsurface_highlighted_red[(i + j) % 2], (i * w, j * h))
                    elif move.kind is MoveKind.Capture:
                        self.surface.blit(tiles_subsurface_highlighted_blue[(i + j) % 2], (i * w, j * h))
                    else:
                        self.surface.blit(tiles_subsurfaces_highlighted[(i + j) % 2], (i * w, j * h))

                piece = self.table[i, j]

                if piece:
                    self.surface.blit(self.pieces_subsurfaces[get_piece_full_name(piece)], (i * w, j * h))

        if self.selected_piece:
            cx, cy = self.scale / Size.from_constant(2)

            shake_pos = self.mouse.position

            if shake_animation_frame < len(SHAKE_ANIMATION):
                shake_pos += SHAKE_ANIMATION[shake_animation_frame]

            self.surface.blit(
                self.pieces_subsurfaces[get_piece_full_name(self.selected_piece)],
                (shake_pos.x - cx, shake_pos.y - cy)
            )

        if shake_animation_frame < len(SHAKE_ANIMATION):
            shake_animation_frame += 1

        return self

    # Partida ---------------------------------------------------------------

    def restart(self):
        global shake_animation_frame

        shake_animation_frame = 9999

        self.turn = PieceRole.White
        self.table = Table()
        self.move_highlights = {}
        self.selected_piece = None
        self.selected_piece_bbox = None
        self.history = []
        self.last_move = ()
        self.finished = False

        self.engine.new_game()

        ui.set_history(self.history)
        ui.set_status('Sua vez', busy=False)
        ui.set_evaluation(None)

        self.sounds.play('notify')

        return self


async def main():
    app = Chess('board', 800, 800)

    app.pieces = Spritesheet(await load_image('assets/pieces.png'))
    app.sounds = Sounds(names=(
        'capture', 'castle', 'click', 'game-end', 'illegal',
        'move-opponent', 'move-self', 'notify', 'promote'
    ))
    app.engine = Engine()
    app.engine.on_info = lambda info: ui.set_evaluation(info)

    app.init()
    app.run()

    ui.bind(app)
    ui.set_status('Carregando o Stockfish', busy=True)

    await app.engine.ready()
    app.engine.new_game()

    ui.set_status('Sua vez', busy=False)
    ui.set_ready()

    return app


asyncio.ensure_future(main())
