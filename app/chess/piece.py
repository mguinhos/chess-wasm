from typing import TYPE_CHECKING
from dataclasses import dataclass


from enum import Enum

from .engine.coordinates import Position


if TYPE_CHECKING:
    from .table import Table

class MoveKind(Enum):
    Illegal= 0
    Place= 1
    Capture= 2
    Castle= 3
    Promote= 4

@dataclass
class Move:
    kind: MoveKind
    position: Position


class PieceRole(Enum):
    Black= 0
    White= 1

@dataclass
class Piece:
    role: PieceRole
    position: Position

    def get_moves(self, table: "Table") -> dict[Position, Move]:
        position = self.position
        trails = self.trails
        capture_trails = self.capture_trails

        moves = {}

        for trail in trails:
            trail_blocked = False

            for x, y in trail:
                abs_position = position - Position(x, y)

                if trail_blocked:
                    moves[abs_position] = Move(MoveKind.Illegal, abs_position)
                    continue

                if piece := table[abs_position]:
                    if self.role == piece.role:
                        moves[abs_position] = Move(MoveKind.Illegal, abs_position)
                        trail_blocked = True
                else:
                    moves[abs_position] = Move(MoveKind.Place, abs_position)
        
        for capture_trail in capture_trails:
            for x, y in capture_trail:
                abs_position = position - Position(x, y)

                current = moves.get(abs_position)

                if current and current.kind is MoveKind.Illegal:
                    continue

                if piece := table[abs_position]:
                    if self.role != piece.role:
                        moves[abs_position] = Move(MoveKind.Capture, abs_position)
                        break

        return moves
    
    def on_move(self, table: "Table", move: Move):
        return self
    
    @property
    def trails(self) -> list[list[Position]]:
        return []
    
    @property
    def capture_trails(self) -> list[list[Position]]:
        return self.trails

class TopPawn(Piece):
    def on_move(self, table: "Table", move: Move):
        if move.position.y == 0:
            return Queen(self.role, self.position)

        return self

    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(0, 1)],
        ]
    
    @property
    def capture_trails(self) -> list[list[Position]]:
        return [
            [Position(-1, 1)],
            [Position(1, 1)],
        ]

class BeginTopPawn(TopPawn):
    def on_move(self, table: "Table", move: Move):
        return TopPawn(self.role, self.position)

    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(0, 1)],
            [Position(0, 2)]
        ]
    
class BottomPawn(Piece):
    def on_move(self, table: "Table", move: Move):
        if move.position.y == 0:
            return Queen(self.role, self.position)

        return self
    
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(0, -1)],
        ]
    
    @property
    def capture_trails(self) -> list[list[Position]]:
        return [
            [Position(-1, -1)],
            [Position(1, -1)],
        ]
    
class BeginBottomPawn(BottomPawn):
    def on_move(self, table: "Table", move: Move):
        return BottomPawn(self.role, self.position)
    
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(0, -1)],
            [Position(0, -2)]
        ]


class King(Piece):
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(-1, 1)],
            [Position(-1, 0)],
            [Position(-1, -1)],
            [Position(0, 1)],
            [Position(0, -1)],
            [Position(1, 1)],
            [Position(1, 0)],
            [Position(1, -1)],
        ]

class BeginKing(King):
    def on_move(self, table: "Table", move: Move):
        return King(self.role, self.position)

class Knight(Piece):
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(-1, 2)],
            [Position(1, 2)],
            [Position(-1, -2)],
            [Position(1, -2)],
            [Position(-2, -1)],
            [Position(-2, 1)],
            [Position(2, -1)],
            [Position(2, 1)],
        ]

class Bishop(Piece):
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(i, i) for i in range(1, 8)],
            [Position(-i, i) for i in range(1, 8)],
            [Position(-i, -i) for i in range(1, 8)],
            [Position(i, -i) for i in range(1, 8)],
        ]
    
class Rook(Piece):
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(0, y) for y in range(1, 8)],
            [Position(0, -y) for y in range(1, 8)],
            [Position(x, 0) for x in range(1, 8)],
            [Position(-x, 0) for x in range(1, 8)],
        ]

class BeginRook(Rook):
    pass
    
class Queen(Piece):
    @property
    def trails(self) -> list[list[Position]]:
        return [
            [Position(i, i) for i in range(1, 8)],
            [Position(-i, i) for i in range(1, 8)],
            [Position(-i, -i) for i in range(1, 8)],
            [Position(i, -i) for i in range(1, 8)],
            
            [Position(0, y) for y in range(1, 8)],
            [Position(0, -y) for y in range(1, 8)],
            [Position(x, 0) for x in range(1, 8)],
            [Position(-x, 0) for x in range(1, 8)],
            
            [Position(-1, 1)],
            [Position(-1, 0)],
            [Position(-1, -1)],
            [Position(1, 1)],
            [Position(1, 0)],
            [Position(1, -1)],
            [Position(0, 1)],
            [Position(1, -1)],
        ]

def get_piece_name(piece: Piece):
    type_piece = type(piece)

    if type_piece in (BeginKing, King):
        return 'k'
    elif type_piece in (BeginRook, Rook):
        return 'r'
    elif type_piece is Knight:
        return 'n'
    elif type_piece is Bishop:
        return 'b'
    elif type_piece is Queen:
        return 'q'
    
    return 'p'

def get_piece_full_name(piece: Piece):
    if piece is None:
        return
    
    return ('w' if piece.role is PieceRole.White else 'b') + get_piece_name(piece)
