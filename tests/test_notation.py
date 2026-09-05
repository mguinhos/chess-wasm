#!/usr/bin/env python3
"""
Testes da aplicação dos lances do engine, sem navegador.

    $ python tests/test_notation.py
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'app'))

from chess.notation import ID_TO_POS, apply_uci_move  # noqa: E402
from chess.piece import King, PieceRole, Queen, Rook, get_piece_full_name  # noqa: E402
from chess.table import Table  # noqa: E402


def at(table, square):
    return table[ID_TO_POS[square]]


def play(table, *moves):
    for move in moves:
        assert apply_uci_move(table, move) is not None, f'lance recusado: {move}'

    return table


class TestNotation(unittest.TestCase):
    def test_lance_simples(self):
        table = Table()
        applied = apply_uci_move(table, 'e2e4')

        self.assertEqual(get_piece_full_name(at(table, 'e4')), 'wp')
        self.assertIsNone(at(table, 'e2'))
        self.assertFalse(applied.captured)

    def test_captura(self):
        table = play(Table(), 'e2e4', 'd7d5')
        applied = apply_uci_move(table, 'e4d5')

        self.assertTrue(applied.captured)
        self.assertEqual(get_piece_full_name(at(table, 'd5')), 'wp')

    def test_roque_curto_move_a_torre(self):
        table = play(Table(), 'e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5')
        applied = apply_uci_move(table, 'e1g1')

        self.assertTrue(applied.castled)
        self.assertIsInstance(at(table, 'g1'), King)
        self.assertIsInstance(at(table, 'f1'), Rook)
        self.assertIsNone(at(table, 'h1'))
        self.assertIsNone(at(table, 'e1'))

    def test_roque_longo_move_a_torre(self):
        table = play(Table(), 'd2d4', 'd7d5', 'b1c3', 'b8c6', 'c1f4', 'c8f5', 'd1d2', 'd8d7')
        applied = apply_uci_move(table, 'e1c1')

        self.assertTrue(applied.castled)
        self.assertIsInstance(at(table, 'c1'), King)
        self.assertIsInstance(at(table, 'd1'), Rook)
        self.assertIsNone(at(table, 'a1'))

    def test_en_passant_remove_o_peao_ao_lado(self):
        table = play(Table(), 'e2e4', 'a7a6', 'e4e5', 'd7d5')
        applied = apply_uci_move(table, 'e5d6')

        self.assertTrue(applied.captured)
        self.assertIsNone(at(table, 'd5'))
        self.assertEqual(get_piece_full_name(at(table, 'd6')), 'wp')

    def test_promocao(self):
        table = Table()
        table[ID_TO_POS['a7']] = None
        table[ID_TO_POS['a8']] = None
        play(table, 'a2a4', 'h7h6', 'a4a5', 'h6h5', 'a5a6', 'h5h4', 'a6b7', 'h4h3')

        applied = apply_uci_move(table, 'b7b8q')

        self.assertTrue(applied.promoted)
        self.assertIsInstance(at(table, 'b8'), Queen)
        self.assertIs(at(table, 'b8').role, PieceRole.White)

    def test_origem_vazia(self):
        self.assertIsNone(apply_uci_move(Table(), 'e4e5'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
