"""Tests for Mines progressive 0.50x, 0.60x, 0.70x payout schedule."""
import unittest
import server

class MinesEconomyTests(unittest.TestCase):
    def test_billion_credit_bet(self):
        expected = (500_000_000, 600_000_000, 700_000_000, 800_000_000,
                    900_000_000, 1_000_000_000, 1_100_000_000, 1_200_000_000)
        for tiles, payout in enumerate(expected, start=1):
            with self.subTest(tiles=tiles):
                self.assertEqual(server.mines_payout(1_000_000_000, 3, tiles), payout)

    def test_every_mine_count_uses_same_increment(self):
        for mines in (1, 3, 5, 10, 20):
            for tiles in range(1, 26 - mines):
                with self.subTest(mines=mines, tiles=tiles):
                    self.assertEqual(server.mines_payout(3_000_000_000, mines, tiles),
                                     3_000_000_000 * (50 + 10 * (tiles - 1)) // 100)

    def test_small_stakes_are_rounded_down(self):
        self.assertEqual(server.mines_payout(1, 3, 1), 0)
        self.assertEqual(server.mines_payout(5, 3, 1), 2)
        self.assertEqual(server.mines_payout(10, 3, 2), 6)

    def test_invalid_reveals_cannot_pay(self):
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 0), 0)
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 23), 0)

    def test_no_one_tile_auto_win_for_new_rounds(self):
        self.assertEqual(server.MINES_MAX_COUNT, 20)
        self.assertGreater(server.MINES_TILES - server.MINES_MAX_COUNT, 1)

if __name__ == "__main__":
    unittest.main()
