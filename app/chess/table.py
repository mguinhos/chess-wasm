from typing import Optional
from dataclasses import dataclass

from .engine.coordinates import Position
from .piece import Piece, PieceRole, BeginRook, BeginKing, BeginTopPawn, BeginBottomPawn, Bishop, Knight, Queen


def clamp(value: float, min_value: float, max_value: float):
    if value <= min_value:
        return min_value
    elif value >= max_value:
        return max_value
    
    return value

@dataclass
class Table:
    state: list[list[Optional[Piece]]]
    
    def __init__(self, state: Optional[list[list[int]]]=None,):
        self.state = [[None for _ in range(8)] for _ in range(8)] if state is None else state
        self.pieces = {}

        self.reset()

    def __getitem__(self, position: tuple[int, int]):
        i, j = position

        try:
            return self.state[clamp(round(j), 0, 7)][clamp(round(i), 0, 7)]
        except IndexError:
            return None
    
    def __setitem__(self, position: tuple[int, int], value: str):
        i, j = position

        self.state[clamp(round(j), 0, 7)][clamp(round(i), 0, 7)] = value

        if value is None:
            del self.pieces[Position(i, j)]
        else:
            self.pieces[Position(i, j)] = value

    def reset(self):
        for i, piece_type in enumerate([BeginRook, Knight, Bishop, Queen, BeginKing, Bishop, Knight, BeginRook]):
            self[i, 0] = piece_type(PieceRole.Black, Position(i, 0))
            self[i, 7] = piece_type(PieceRole.White, Position(i, 7))

        for i in range(8):
            self[i, 1] = BeginBottomPawn(PieceRole.Black, Position(i, 1))
            self[i, 6] = BeginTopPawn(PieceRole.White, Position(i, 6))
        
        return self
    