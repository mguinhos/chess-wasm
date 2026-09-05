"""
Notação longa (`e2e4`, `e7e8q`, `e1g1`) e aplicação dos lances do engine.

O Stockfish manda nos próprios lances. Eles entram no tabuleiro sem passar
pela validação de `Piece.get_moves`, inclusive os recursos que a lógica caseira
não modela: roque, en passant e promoção.

Fica em Python puro, sem nada do navegador, para poder ser testado direto.
"""

from typing import NamedTuple, Optional

from .engine.coordinates import Position
from .piece import (
    Bishop, Knight, MoveKind, Move, Piece, Queen, Rook,
    get_piece_name,
)

POS_TO_ID: dict[Position, str] = {}
ID_TO_POS: dict[str, Position] = {}

for _i, _file in enumerate('abcdefgh'):
    for _j, _rank in enumerate('87654321'):
        POS_TO_ID[Position(_i, _j)] = _file + _rank
        ID_TO_POS[_file + _rank] = Position(_i, _j)

PROMOTIONS = {'q': Queen, 'r': Rook, 'b': Bishop, 'n': Knight}


class AppliedMove(NamedTuple):
    origin: Position
    destination: Position
    captured: bool
    castled: bool
    promoted: bool


def apply_uci_move(table, notation: str) -> Optional[AppliedMove]:
    "Aplica `notation` em `table`. Devolve None se não houver peça na origem."

    origin = ID_TO_POS[notation[0:2]]
    destination = ID_TO_POS[notation[2:4]]
    promotion = notation[4:5]

    piece = table[origin]

    if piece is None:
        return None

    captured = table[destination] is not None
    castled = False

    # En passant: o peão vai para uma casa vazia andando na diagonal, e quem
    # sai do tabuleiro é o peão que está ao lado dele.
    if get_piece_name(piece) == 'p' and not captured and origin.x != destination.x:
        passed = Position(destination.x, origin.y)

        if table[passed]:
            table[passed] = None
            captured = True

    # Roque: o rei anda duas casas e a torre pula para o outro lado dele.
    if get_piece_name(piece) == 'k' and abs(destination.x - origin.x) == 2:
        to_kingside = destination.x > origin.x

        rook_origin = Position(7 if to_kingside else 0, origin.y)
        rook_destination = Position(destination.x - 1 if to_kingside else destination.x + 1, origin.y)

        rook = table[rook_origin]

        if rook:
            table[rook_origin] = None

            moved_rook = Rook(rook.role, rook_destination)
            table[rook_destination] = moved_rook
            moved_rook.position = rook_destination

            castled = True

    piece = piece.on_move(table, Move(MoveKind.Place, destination))

    if promotion:
        piece = PROMOTIONS[promotion](piece.role, destination)

    table[origin] = None
    table[destination] = piece
    piece.position = destination

    return AppliedMove(origin, destination, captured, castled, bool(promotion))
