"""Mines credit-economy regression tests. Run: python -m unittest test_mines_economy.py"""
import unittest
from fractions import Fraction
import server

class MinesEconomyTests(unittest.TestCase):
    def test_first_pick_pays_half_even_for_billion_bet(self):
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 1), 500_000_000)
        self.assertEqual(server.mines_payout(1_000_000_000, 20, 1), 500_000_000)

    def test_second_pick_pays_80_percent(self):
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 2), 800_000_000)
        self.assertEqual(server.mines_payout(1_000_000_000, 20, 2), 800_000_000)

    def test_third_pick_returns_to_probability_based_multipliers(self):
        for mines in (1, 3, 5, 10, 20):
            with self.subTest(mines=mines):
                bet = 1_000_000_000
                chance = Fraction(1)
                for opened in range(3):
                    chance *= Fraction(25 - mines - opened, 25 - opened)
                payout = server.mines_payout(bet, mines, 3)
                self.assertGreaterEqual(payout, bet)
                self.assertLessEqual(chance * payout, Fraction(94 * bet, 100))

    def test_new_rounds_leave_at_least_five_safe_tiles(self):
        self.assertEqual(server.MINES_MAX_COUNT, 20)
        self.assertGreaterEqual(server.MINES_TILES - server.MINES_MAX_COUNT, 5)

    def test_invalid_pick_count_has_no_payout(self):
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 0), 0)
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 23), 0)

if __name__ == "__main__":
    unittest.main()
