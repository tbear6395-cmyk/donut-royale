"""Integration tests for private support conversations and the read-only bot log.

Run from this directory with: python -m unittest test_support_console.py
No external services or packages are required.
"""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server


class SupportConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.original_db, cls.original_pg = server.DB, server.USE_POSTGRES
        cls.original_key = os.environ.get("BOT_API_KEY")
        cls.original_owner_name = os.environ.get("OWNER_USERNAME")
        cls.original_owner_password = os.environ.get("OWNER_PASSWORD")
        server.DB = Path(cls.temp.name) / "test.sqlite3"
        server.USE_POSTGRES = False
        os.environ["BOT_API_KEY"] = "integration-test-bot-key"
        os.environ.pop("OWNER_USERNAME", None)
        os.environ.pop("OWNER_PASSWORD", None)
        server.setup()
        cls.cookies = {}
        with server.db_open() as db:
            for name, role in (("TicketPlayer", "player"), ("AnotherPlayer", "player"),
                               ("TicketAdmin", "admin"), ("TicketOwner", "owner")):
                salt = "00" * 16
                db.execute("INSERT INTO users(username,salt,pw,role,balance) VALUES(?,?,?,?,0)",
                           (name, salt, server.pw_hash("test-password", salt), role))
                uid = db.execute("SELECT id FROM users WHERE username=?", (name,)).fetchone()["id"]
                cls.cookies[name] = server.create_session(db, uid)
        cls.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.http.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=5)
        server.DB, server.USE_POSTGRES = cls.original_db, cls.original_pg
        for name, previous in (("BOT_API_KEY",cls.original_key),
                               ("OWNER_USERNAME",cls.original_owner_name),
                               ("OWNER_PASSWORD",cls.original_owner_password)):
            if previous is None: os.environ.pop(name, None)
            else: os.environ[name] = previous
        cls.temp.cleanup()

    @classmethod
    def request(cls, method, path, person=None, body=None, bot_key=None):
        headers = {}
        if person:
            headers["Cookie"] = "session=" + cls.cookies[person]
        if bot_key:
            headers["X-Bot-Api-Key"] = bot_key
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(cls.url + path, data=payload, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read().decode())

    def test_private_thread_and_anonymous_staff_replies(self):
        code, created = self.request("POST", "/api/tickets", "TicketPlayer",
                                     {"kind":"support","amount":0,
                                      "message":"[COMPLAINT] My game did not load correctly"})
        self.assertEqual(code, 200)
        ticket_id = created["ticket_id"]
        path = "/api/ticket/messages?id=" + str(ticket_id)
        self.assertEqual(self.request("GET", path, "AnotherPlayer")[0], 403)
        self.assertEqual(self.request("POST", "/api/ticket/message", "AnotherPlayer",
                                      {"id":ticket_id,"message":"Intrusion"})[0],403)
        self.assertEqual(self.request("POST", "/api/ticket/message", "TicketAdmin",
                                      {"id":ticket_id,"message":"We are checking"})[0],200)
        self.assertEqual(self.request("POST", "/api/ticket/message", "TicketOwner",
                                      {"id":ticket_id,"message":"Please send the round number"})[0],200)
        self.assertEqual(self.request("POST", "/api/ticket/message", "TicketPlayer",
                                      {"id":ticket_id,"message":"Round 123"})[0],200)
        status, received = self.request("GET", path, "TicketPlayer")
        self.assertEqual(status,200)
        self.assertEqual([m["author"] for m in received["messages"]],
                         ["Admin","Admin","Player"])
        serialized=json.dumps(received)
        self.assertNotIn("TicketAdmin",serialized)
        self.assertNotIn("TicketOwner",serialized)
        self.assertNotIn("sender_id",serialized)
        self.assertNotIn("owner",serialized.lower())
        status,list_response=self.request("GET","/api/tickets","TicketPlayer")
        self.assertEqual(status,200)
        self.assertNotIn("handled",list_response["tickets"][0])

    def test_cmd_is_read_only_and_role_restricted(self):
        path="/api/staff/console"
        self.assertEqual(self.request("GET",path,"TicketPlayer")[0],403)
        self.assertEqual(self.request("GET",path,"TicketAdmin")[0],200)
        self.assertEqual(self.request("GET",path,"TicketOwner")[0],200)
        self.assertEqual(self.request("POST","/api/bot/console","TicketPlayer",
                                      {"lines":[{"text":"should not work"}]})[0],401)
        status,response=self.request("POST","/api/bot/console",None,
            {"lines":[{"level":"info","text":"DONUT ROYALE BOT ONLINE"},
                      {"level":"warn","text":"BOT_API_KEY=do-not-expose"}]},
            bot_key="integration-test-bot-key")
        self.assertEqual(status,200)
        self.assertEqual(response["stored"],1)
        _,logs=self.request("GET",path,"TicketAdmin")
        self.assertTrue(any("BOT ONLINE" in row["line"] for row in logs["lines"]))
        self.assertFalse(any("do-not-expose" in row["line"] for row in logs["lines"]))


if __name__ == "__main__":
    unittest.main()
