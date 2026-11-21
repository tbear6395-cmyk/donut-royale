
import os
import re
import json
import hmac
import secrets
import sqlite3
import hashlib
import threading

from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse


BASE = Path(__file__).resolve().parent
DB = BASE / "data.sqlite3"

LOCK = threading.RLock()
SESSIONS = {}

MAX_BET = 3_000_000_000
WIN_CHANCE = 10
PAYOUT = 2


def connect():
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    return db


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        260000
    ).hex()


def initialize():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE COLLATE NOCASE,
                salt TEXT,
                pw TEXT,
                role TEXT DEFAULT 'player',
                balance INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                kind TEXT,
                amount INTEGER,
                message TEXT,
                status TEXT DEFAULT 'open',
                response TEXT DEFAULT '',
                created TEXT DEFAULT CURRENT_TIMESTAMP,
                handled INTEGER DEFAULT 0
            );
        """)

        columns = [
            row["name"]
            for row in db.execute("PRAGMA table_info(users)")
        ]

        if "approval" not in columns:
            db.execute("""
                ALTER TABLE users
                ADD COLUMN approval TEXT NOT NULL DEFAULT 'approved'
            """)

        db.execute("""
            UPDATE users
            SET approval='approved'
            WHERE role IN ('owner', 'admin')
        """)

        owner = db.execute("""
            SELECT id FROM users WHERE role='owner'
        """).fetchone()

        if owner is None:
            username = os.getenv("OWNER_USERNAME", "")
            password = os.getenv("OWNER_PASSWORD", "")

            if (
                re.fullmatch(r"[A-Za-z0-9_]{3,16}", username)
                and len(password) >= 12
            ):
                salt = secrets.token_hex(16)

                db.execute("""
                    INSERT INTO users
                    (username, salt, pw, role, balance, approval)
                    VALUES (?, ?, ?, 'owner', 0, 'approved')
                """, (
                    username,
                    salt,
                    hash_password(password, salt)
                ))
            else:
                print("Configure OWNER_USERNAME and OWNER_PASSWORD")


def get_user(uid):
    if uid is None:
        return None

    with connect() as db:
        row = db.execute("""
            SELECT id, username, role, balance, approval
            FROM users
            WHERE id=?
        """, (uid,)).fetchone()

    return dict(row) if row else None


class Handler(BaseHTTPRequestHandler):

    def send(self, status, data, cookie=None):
        payload = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

        if cookie:
            self.send_header("Set-Cookie", cookie)

        self.end_headers()
        self.wfile.write(payload)

    def body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))

            if length < 0 or length > 10000:
                return {}

            data = json.loads(self.rfile.read(length))

            return data if isinstance(data, dict) else {}

        except Exception:
            return {}

    def auth(self):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))

            session = cookies.get("session")

            if not session:
                return None

            return get_user(SESSIONS.get(session.value))

        except Exception:
            return None

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            path = "/index.html"

        static_files = {
            "/index.html": "text/html; charset=utf-8",
            "/style.css": "text/css; charset=utf-8",
            "/app.js": "application/javascript; charset=utf-8",
            "/coin-heads.png": "image/png",
            "/coin-tails.png": "image/png"
        }

        if path in static_files:
            filename = BASE / path.lstrip("/")

            if not filename.is_file():
                return self.send(404, {
                    "error": "File not found"
                })

            payload = filename.read_bytes()

            self.send_response(200)
            self.send_header("Content-Type", static_files[path])
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        current = self.auth()

        if path == "/api/me":
            return self.send(200, {"user": current})

        if path == "/api/rules":
            return self.send(200, {
                "win_chance_percent": WIN_CHANCE,
                "loss_chance_percent": 100 - WIN_CHANCE,
                "payout_multiplier": PAYOUT,
                "all_in_always_loses": True,
                "max_bet": MAX_BET
            })

        if current is None:
            return self.send(401, {
                "error": "Please log in"
            })

        if path == "/api/tickets":
            with connect() as db:
                if current["role"] in ("owner", "admin"):
                    rows = db.execute("""
                        SELECT t.*, u.username
                        FROM tickets t
                        JOIN users u ON u.id=t.user_id
                        WHERE t.status='open'
                        ORDER BY t.id DESC
                    """).fetchall()
                else:
                    rows = db.execute("""
                        SELECT t.*, u.username
                        FROM tickets t
                        JOIN users u ON u.id=t.user_id
                        WHERE t.user_id=? AND t.status='open'
                        ORDER BY t.id DESC
                    """, (current["id"],)).fetchall()

            return self.send(200, {
                "tickets": [dict(row) for row in rows]
            })

        if path == "/api/users":
            if current["role"] not in ("owner", "admin"):
                return self.send(403, {
                    "error": "Not allowed"
                })

            with connect() as db:
                rows = db.execute("""
                    SELECT id, username, role, balance, approval
                    FROM users
                    ORDER BY
                        CASE WHEN approval='pending' THEN 0 ELSE 1 END,
                        id DESC
                """).fetchall()

            return self.send(200, {
                "users": [dict(row) for row in rows]
            })

        return self.send(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.body()
        current = self.auth()

        # REGISTER AND LOGIN

        if path in ("/api/register", "/api/login"):
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))

            if (
                not re.fullmatch(r"[A-Za-z0-9_]{3,16}", username)
                or not 8 <= len(password) <= 128
            ):
                return self.send(400, {
                    "error": "Invalid username or password"
                })

            if path == "/api/register":
                salt = secrets.token_hex(16)

                with LOCK, connect() as db:
                    try:
                        db.execute("""
                            INSERT INTO users
                            (username, salt, pw, role, balance, approval)
                            VALUES (?, ?, ?, 'player', 0, 'pending')
                        """, (
                            username,
                            salt,
                            hash_password(password, salt)
                        ))

                    except sqlite3.IntegrityError:
                        return self.send(409, {
                            "error": "Username already registered"
                        })

                return self.send(200, {
                    "ok": True,
                    "pending": True,
                    "message": "Wait for owner approval"
                })

            with connect() as db:
                row = db.execute("""
                    SELECT *
                    FROM users
                    WHERE username=? COLLATE NOCASE
                """, (username,)).fetchone()

            if (
                row is None
                or not hmac.compare_digest(
                    hash_password(password, row["salt"]),
                    row["pw"]
                )
            ):
                return self.send(401, {
                    "error": "Invalid login"
                })

            if row["approval"] == "pending":
                return self.send(403, {
                    "error": "Wait for owner approval"
                })

            if row["approval"] == "rejected":
                return self.send(403, {
                    "error": "Your account was rejected"
                })

            token = secrets.token_urlsafe(32)
            SESSIONS[token] = row["id"]

            cookie = (
                f"session={token}; "
                "HttpOnly; SameSite=Strict; Path=/"
            )

            if os.getenv("COOKIE_SECURE") == "1":
                cookie += "; Secure"

            return self.send(200, {"ok": True}, cookie)

        # LOGOUT

        if path == "/api/logout":
            try:
                cookies = SimpleCookie()
                cookies.load(self.headers.get("Cookie", ""))

                session = cookies.get("session")

                if session:
                    SESSIONS.pop(session.value, None)

            except Exception:
                pass

            return self.send(
                200,
                {"ok": True},
                "session=; HttpOnly; SameSite=Strict; "
                "Path=/; Max-Age=0"
            )

        if current is None:
            return self.send(401, {
                "error": "Please log in"
            })

        # OWNER APPROVES OR REJECTS USERS

        if path == "/api/user/approval":
            if current["role"] != "owner":
                return self.send(403, {
                    "error": "Only owner can approve players"
                })

            target_id = data.get("id")
            approval = data.get("approval")

            if (
                type(target_id) is not int
                or approval not in ("approved", "rejected")
                or target_id == current["id"]
            ):
                return self.send(400, {
                    "error": "Invalid approval request"
                })

            with LOCK, connect() as db:
                target = db.execute("""
                    SELECT role FROM users WHERE id=?
                """, (target_id,)).fetchone()

                if target is None or target["role"] != "player":
                    return self.send(403, {
                        "error": "Only players can be reviewed"
                    })

                db.execute("""
                    UPDATE users
                    SET approval=?
                    WHERE id=?
                """, (approval, target_id))

            if approval == "rejected":
                for token, uid in list(SESSIONS.items()):
                    if uid == target_id:
                        SESSIONS.pop(token, None)

            return self.send(200, {"ok": True})

        if current["approval"] != "approved":
            return self.send(403, {
                "error": "Account not approved"
            })

        # CREATE TICKET

        if path == "/api/tickets":
            kind = data.get("kind")
            amount = data.get("amount")
            message = str(data.get("message", "")).strip()

            if kind not in ("deposit", "withdraw", "support"):
                return self.send(400, {
                    "error": "Invalid ticket type"
                })

            if (
                type(amount) is not int
                or amount < 0
                or amount > 1_000_000_000_000
                or (kind != "support" and amount == 0)
                or len(message) > 1000
            ):
                return self.send(400, {
                    "error": "Invalid amount or message"
                })

            with LOCK, connect() as db:
                if kind == "withdraw":
                    row = db.execute("""
                        SELECT balance FROM users WHERE id=?
                    """, (current["id"],)).fetchone()

                    if row is None or row["balance"] < amount:
                        return self.send(400, {
                            "error": "Not enough balance for withdrawal"
                        })

                db.execute("""
                    INSERT INTO tickets
                    (user_id, kind, amount, message)
                    VALUES (?, ?, ?, ?)
                """, (
                    current["id"],
                    kind,
                    amount,
                    message
                ))

            return self.send(200, {"ok": True})

        # REVIEW TICKET
        # Handled tickets are deleted from the active list.

        if path == "/api/ticket/review":
            if current["role"] not in ("owner", "admin"):
                return self.send(403, {
                    "error": "Not allowed"
                })

            ticket_id = data.get("id")
            status = data.get("status")
            response = str(data.get("response", ""))[:1000]

            if (
                type(ticket_id) is not int
                or status not in ("approved", "rejected", "closed")
            ):
                return self.send(400, {
                    "error": "Invalid request"
                })

            with LOCK, connect() as db:
                ticket = db.execute("""
                    SELECT * FROM tickets WHERE id=?
                """, (ticket_id,)).fetchone()

                if ticket is None or ticket["status"] != "open":
                    return self.send(409, {
                        "error": "Ticket already handled"
                    })

                if (
                    status == "approved"
                    and ticket["kind"] == "support"
                ):
                    return self.send(400, {
                        "error": "Close support tickets instead"
                    })

                if (
                    status == "approved"
                    and ticket["kind"] == "withdraw"
                ):
                    result = db.execute("""
                        UPDATE users
                        SET balance=balance-?
                        WHERE id=? AND balance>=?
                    """, (
                        ticket["amount"],
                        ticket["user_id"],
                        ticket["amount"]
                    ))

                    if result.rowcount != 1:
                        return self.send(409, {
                            "error": "Not enough balance for withdrawal"
                        })

                if (
                    status == "approved"
                    and ticket["kind"] == "deposit"
                ):
                    db.execute("""
                        UPDATE users
                        SET balance=balance+?
                        WHERE id=?
                    """, (
                        ticket["amount"],
                        ticket["user_id"]
                    ))

                # Ticket disappears after approval,
                # rejection, or closing.
                db.execute("""
                    DELETE FROM tickets WHERE id=?
                """, (ticket_id,))

            return self.send(200, {
                "ok": True,
                "message": "Ticket handled and removed"
            })

        # OWNER CHANGES ROLES

        if path == "/api/role":
            if current["role"] != "owner":
                return self.send(403, {
                    "error": "Only owner can change roles"
                })

            target_id = data.get("id")
            role = data.get("role")

            if (
                type(target_id) is not int
                or role not in ("admin", "player")
                or target_id == current["id"]
            ):
                return self.send(400, {
                    "error": "Invalid role change"
                })

            with LOCK, connect() as db:
                target = db.execute("""
                    SELECT role, approval
                    FROM users
                    WHERE id=?
                """, (target_id,)).fetchone()

                if (
                    target is None
                    or target["role"] == "owner"
                    or target["approval"] != "approved"
                ):
                    return self.send(403, {
                        "error": "Player must be approved first"
                    })

                db.execute("""
                    UPDATE users SET role=? WHERE id=?
                """, (role, target_id))

            return self.send(200, {"ok": True})

        # ALL FOUR MINIGAMES

        if path == "/api/game":
            game = data.get("game")
            amount = data.get("amount")
            choice = data.get("choice")

            if game not in ("coinflip", "dice", "slots", "wheel"):
                return self.send(400, {
                    "error": "Invalid game"
                })

            if (
                type(amount) is not int
                or amount < 1
                or amount > MAX_BET
            ):
                return self.send(400, {
                    "error": "Maximum bet is 3B"
                })

            if (
                game == "coinflip"
                and choice not in ("heads", "tails")
            ):
                return self.send(400, {
                    "error": "Choose Heads or Tails"
                })

            if (
                game == "wheel"
                and choice not in ("red", "black")
            ):
                return self.send(400, {
                    "error": "Choose Red or Black"
                })

            with LOCK, connect() as db:
                row = db.execute("""
                    SELECT balance FROM users WHERE id=?
                """, (current["id"],)).fetchone()

                if row is None:
                    return self.send(404, {
                        "error": "Player not found"
                    })

                balance = row["balance"]

                if amount > balance:
                    return self.send(409, {
                        "error": "Insufficient balance"
                    })

                all_in = amount == balance

                # Rules must be visible before betting.
                # Regular bet: 10% chance to win.
                # All-in: automatic loss.
                # Winning bet: 2x total payout.

                win = (
                    not all_in
                    and secrets.randbelow(100) < WIN_CHANCE
                )

                if game == "coinflip":
                    result = (
                        choice
                        if win
                        else (
                            "tails"
                            if choice == "heads"
                            else "heads"
                        )
                    )

                    details = {"result": result}

                elif game == "dice":
                    roll = secrets.choice(
                        [5, 6] if win else [1, 2, 3, 4]
                    )

                    details = {"roll": roll}

                elif game == "slots":
                    if win:
                        reels = ["7", "7", "7"]
                    else:
                        symbols = ["7", "🍒", "💎", "⭐"]
                        reels = [
                            secrets.choice(symbols)
                            for _ in range(3)
                        ]

                        if reels == ["7", "7", "7"]:
                            reels[2] = "⭐"

                    details = {"reels": reels}

                else:
                    result = (
                        choice
                        if win
                        else (
                            "black"
                            if choice == "red"
                            else "red"
                        )
                    )

                    details = {"result": result}

                profit = amount if win else -amount

                db.execute("""
                    UPDATE users
                    SET balance=balance+?
                    WHERE id=?
                """, (
                    profit,
                    current["id"]
                ))

                new_balance = balance + profit

            return self.send(200, {
                "win": win,
                "profit": profit,
                "balance": new_balance,
                "payout_multiplier": PAYOUT,
                "all_in": all_in,
                "win_chance_percent": 0 if all_in else WIN_CHANCE,
                **details
            })

        return self.send(404, {
            "error": "Not found"
        })


if __name__ == "__main__":
    initialize()

    port = int(os.getenv("PORT", "8000"))

    print(f"DONUT ROYALE running on port {port}")

    ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    ).serve_forever()
