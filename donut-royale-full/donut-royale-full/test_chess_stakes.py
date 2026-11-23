"""Exercise real wallet transactions without a live database or game account."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import chess_matches
import server


class ChessStakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(self.temp.cleanup)
        for attr, value in (("DB", Path(self.temp.name) / "test.db"), ("USE_POSTGRES", False)):
            changes = patch.object(server, attr, value)
            changes.start()
            self.addCleanup(changes.stop)
        server.setup()
        chess_matches.engine_ready.set()
        self.addCleanup(chess_matches.engine_ready.clear)
        with server.db_open() as db:
            self.uid = db.execute("INSERT INTO users(username,salt,pw,balance) VALUES('Tester','00','00',500)").lastrowid

    def post(self, action, **body):
        h = object.__new__(server.Handler)
        h.path = "/api/chess/" + action
        h.me = lambda: {"id": self.uid}
        h.payload = lambda: body
        result = []
        h.send_json = lambda status, data: result.append((status, data))
        h.do_POST()
        return result[0]

    def test_stake_and_resignation(self):
        for stake in (-1, True, 501, 3000000001):
            self.assertEqual(self.post("start", stake=stake)[0], 400)
        status, state = self.post("start", stake=100)
        self.assertEqual((status, state["balance"]), (200, 400))
        self.assertEqual(self.post("start", stake=100)[0], 409)
        match = state["match"]["id"]
        status, state = self.post("resign", id=match, ply=0)
        self.assertEqual((status, state["balance"], state["match"]["outcome"]), (200, 400, "lose"))
        self.assertEqual(self.post("resign", id=match, ply=0)[0], 409)

    def test_settlement_is_atomic(self):
        for outcome, expected in (("win",600), ("draw",500), ("lose",400)):
            with self.subTest(outcome=outcome):
                with server.db_open() as db:
                    db.execute("DELETE FROM chess_matches")
                    db.execute("UPDATE users SET balance=500")
                match = self.post("start", stake=100)[1]["match"]["id"]
                with patch.object(chess_matches, "run_turn", return_value={"outcome":outcome,"moves":["e2e4"]}):
                    status, state = self.post("move", id=match, ply=0, move="e2e4", outcome="win", payout=999999)
                self.assertEqual((status,state["balance"]), (200,expected))
                self.assertEqual(self.post("move", id=match, ply=0, move="e2e4")[0], 409)
