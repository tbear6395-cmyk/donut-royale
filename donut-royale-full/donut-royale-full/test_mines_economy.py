"""Regressions for Mines payouts that scale with how many mines are selected."""
import unittest
import server


class MinesEconomyTests(unittest.TestCase):
    def test_approved_presets_for_one_billion_bet(self):
        presets = {
            1: [300_000_000, 350_000_000, 400_000_000, 450_000_000,
                500_000_000, 550_000_000, 600_000_000, 650_000_000],
            3: [500_000_000, 600_000_000, 700_000_000, 800_000_000,
                900_000_000, 1_000_000_000, 1_100_000_000, 1_200_000_000],
            5: [700_000_000, 850_000_000, 1_000_000_000, 1_150_000_000,
                1_300_000_000, 1_450_000_000, 1_600_000_000, 1_750_000_000],
        }
        for mines, values in presets.items():
            for opened, payout in enumerate(values, start=1):
                with self.subTest(mines=mines, opened=opened):
                    self.assertEqual(server.mines_payout(1_000_000_000, mines, opened), payout)

    def test_more_mines_pay_more_at_same_reveal_count(self):
        for opened in range(1, 6):
            payouts = [server.mines_payout(1_000_000_000, mines, opened)
                       for mines in range(1, server.MINES_MAX_COUNT + 1)]
            self.assertEqual(payouts, sorted(payouts))
            self.assertEqual(len(payouts), len(set(payouts)))

    def test_each_safe_diamond_increases_payout(self):
        for mines in range(1, server.MINES_MAX_COUNT + 1):
            previous = 0
            for opened in range(1, server.MINES_TILES - mines + 1):
                payout = server.mines_payout(3_000_000_000, mines, opened)
                self.assertGreater(payout, previous)
                previous = payout

    def test_exact_integer_rounding_and_reveal_boundaries(self):
        self.assertEqual(server.mines_payout(1, 1, 1), 0)
        self.assertEqual(server.mines_payout(5, 1, 1), 1)
        self.assertEqual(server.mines_payout(10, 3, 2), 6)
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 0), 0)
        self.assertEqual(server.mines_payout(1_000_000_000, 3, 23), 0)

    def test_new_rounds_reject_one_safe_tile_auto_win_setup(self):
        self.assertEqual(server.MINES_MAX_COUNT, 20)
        self.assertGreater(server.MINES_TILES-server.MINES_MAX_COUNT, 1)


if __name__ == "__main__":
    unittest.main()
