import os
import sqlite3
import secrets
import hashlib
import hmac
import json
import re
import threading

from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse


BASE = Path(__file__).resolve().parent
DB = BASE / "data.sqlite3"

LOCK = threading.RLock()
SESSIONS = {}

WIN_CHANCE = 10
PAYOUT_MULTIPLIER = 2
MAX_BET = 1_000_000


def database():
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    return db


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        260000
    ).hex()


def initialize_database():
    with database() as db:
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
            SET approval = 'approved'
            WHERE role IN ('owner', 'admin')
        """)

        owner = db.execute("""
            SELECT id FROM users WHERE role = 'owner'
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
                    password_hash(password, salt)
                ))
            else:
                print(
                    "Set OWNER_USERNAME and OWNER_PASSWORD "
                    "in Render environment variables."
                )


def get_user(user_id):
    if user_id is None:
        return None

    with database() as db:
        row = db.execute("""
            SELECT id, username, role, balance, approval
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

    return dict(row) if row else None


class Handler(BaseHTTPRequestHandler):

    def send_json(self, status, data, cookie=None):
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

    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))

            if length < 0 or length > 10000:
                return {}

            data = json.loads(self.rfile.read(length))

            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def current_user(self):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))

            session = cookies.get("session")

            if not session:
                return None

            user_id = SESSIONS.get(session.value)
            return get_user(user_id)
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
                return self.send_json(404, {
                    "error": "File not found"
                })

            content = filename.read_bytes()

            self.send_response(200)
            self.send_header("Content-Type", static_files[path])
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        current = self.current_user()

        if path == "/api/me":
            return self.send_json(200, {
                "user": current
            })

        if path == "/api/rules":
            return self.send_json(200, {
                "win_chance_percent": WIN_CHANCE,
                "loss_chance_percent": 100 - WIN_CHANCE,
                "payout_multiplier": PAYOUT_MULTIPLIER,
                "all_in_always_loses": True
            })

        if current is None:
            return self.send_json(401, {
                "error": "Please log in"
            })

        if path == "/api/tickets":
            with database() as db:
                if current["role"] in ("owner", "admin"):
                    rows = db.execute("""
                        SELECT t.*, u.username
                        FROM tickets t
                        JOIN users u ON u.id = t.user_id
                        ORDER BY t.id DESC
                    """).fetchall()
                else:
                    rows = db.execute("""
                        SELECT t.*, u.username
                        FROM tickets t
                        JOIN users u ON u.id = t.user_id
                        WHERE t.user_id = ?
                        ORDER BY t.id DESC
                    """, (current["id"],)).fetchall()

            return self.send_json(200, {
                "tickets": [dict(row) for row in rows]
            })

        if path == "/api/users":
            if current["role"] not in ("owner", "admin"):
                return self.send_json(403, {
                    "error": "Not allowed"
                })

            with database() as db:
                rows = db.execute("""
                    SELECT id, username, role, balance, approval
                    FROM users
                    ORDER BY
                        CASE WHEN approval = 'pending' THEN 0 ELSE 1 END,
                        id DESC
                """).fetchall()

            return self.send_json(200, {
                "users": [dict(row) for row in rows]
            })

        return self.send_json(404, {
            "error": "Not found"
        })

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_body()
        current = self.current_user()

        # REGISTER / LOGIN

        if path in ("/api/register", "/api/login"):
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))

            if (
                not re.fullmatch(r"[A-Za-z0-9_]{3,16}", username)
                or not 8 <= len(password) <= 128
            ):
                return self.send_json(400, {
                    "error": "Invalid username or password"
                })

            if path == "/api/register":
                salt = secrets.token_hex(16)

                with LOCK, database() as db:
                    try:
                        db.execute("""
                            INSERT INTO users
                            (username, salt, pw, role, balance, approval)
                            VALUES (?, ?, ?, 'player', 0, 'pending')
                        """, (
                            username,
                            salt,
                            password_hash(password, salt)
                        ))
                    except sqlite3.IntegrityError:
                        return self.send_json(409, {
                            "error": "Username already registered"
                        })

                return self.send_json(200, {
                    "ok": True,
                    "pending": True,
                    "message": "Wait for owner approval"
                })

            with database() as db:
                row = db.execute("""
                    SELECT *
                    FROM users
                    WHERE username = ? COLLATE NOCASE
                """, (username,)).fetchone()

            if (
                row is None
                or not hmac.compare_digest(
                    password_hash(password, row["salt"]),
                    row["pw"]
                )
            ):
                return self.send_json(401, {
                    "error": "Invalid login"
                })

            if row["approval"] == "pending":
                return self.send_json(403, {
                    "error": "Wait for owner approval"
                })

            if row["approval"] == "rejected":
                return self.send_json(403, {
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

            return self.send_json(200, {
                "ok": True
            }, cookie)

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

            return self.send_json(
                200,
                {"ok": True},
                "session=; HttpOnly; SameSite=Strict; "
                "Path=/; Max-Age=0"
            )

        if current is None:
            return self.send_json(401, {
                "error": "Please log in"
            })

        # OWNER APPROVAL

        if path == "/api/user/approval":
            if current["role"] != "owner":
                return self.send_json(403, {
                    "error": "Only owner can approve players"
                })

            target_id = data.get("id")
            approval = data.get("approval")

            if (
                type(target_id) is not int
                or approval not in ("approved", "rejected")
                or target_id == current["id"]
            ):
                return self.send_json(400, {
                    "error": "Invalid approval request"
                })

            with LOCK, database() as db:
                target = db.execute("""
                    SELECT role
                    FROM users
                    WHERE id = ?
                """, (target_id,)).fetchone()

                if target is None or target["role"] != "player":
                    return self.send_json(403, {
                        "error": "Only players can be reviewed"
                    })

                db.execute("""
                    UPDATE users
                    SET approval = ?
                    WHERE id = ?
                """, (approval, target_id))

            if approval == "rejected":
                for token, uid in list(SESSIONS.items()):
                    if uid == target_id:
                        SESSIONS.pop(token, None)

            return self.send_json(200, {"ok": True})

        if current["approval"] != "approved":
            return self.send_json(403, {
                "error": "Account not approved"
            })

        # CREATE TICKET

        if path == "/api/tickets":
            kind = data.get("kind")
            amount = data.get("amount")
            message = str(data.get("message", "")).strip()

            if kind not in ("deposit", "withdraw", "support"):
                return self.send_json(400, {
                    "error": "Invalid ticket type"
                })

            if (
                type(amount) is not int
                or amount < 0
                or amount > 1_000_000_000
                or (kind != "support" and amount == 0)
                or len(message) > 1000
            ):
                return self.send_json(400, {
                    "error": "Invalid amount or message"
                })

            with LOCK, database() as db:
                if kind == "withdraw":
                    row = db.execute("""
                        SELECT balance
                        FROM users
                        WHERE id = ?
                    """, (current["id"],)).fetchone()

                    if row is None or row["balance"] < amount:
                        return self.send_json(400, {
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

            return self.send_json(200, {"ok": True})

        # REVIEW TICKET

        if path == "/api/ticket/review":
            if current["role"] not in ("owner", "admin"):
                return self.send_json(403, {
                    "error": "Not allowed"
                })

            ticket_id = data.get("id")
            status = data.get("status")
            response = str(data.get("response", ""))[:1000]

            if (
                type(ticket_id) is not int
                or status not in ("approved", "rejected", "closed")
            ):
                return self.send_json(400, {
                    "error": "Invalid request"
                })

            with LOCK, database() as db:
                ticket = db.execute("""
                    SELECT *
                    FROM tickets
                    WHERE id = ?
                """, (ticket_id,)).fetchone()

                if ticket is None or ticket["status"] != "open":
                    return self.send_json(409, {
                        "error": "Ticket already handled"
                    })

                if (
                    status == "approved"
                    and ticket["kind"] == "support"
                ):
                    return self.send_json(400, {
                        "error": "Cannot approve support ticket"
                    })

                if (
                    status == "approved"
                    and ticket["kind"] == "withdraw"
                ):
                    result = db.execute("""
                        UPDATE users
                        SET balance = balance - ?
                        WHERE id = ? AND balance >= ?
                    """, (
                        ticket["amount"],
                        ticket["user_id"],
                        ticket["amount"]
                    ))

                    if result.rowcount != 1:
                        return self.send_json(409, {
                            "error": "Not enough balance for withdrawal"
                        })

                if (
                    status == "approved"
                    and ticket["kind"] == "deposit"
                ):
                    db.execute("""
                        UPDATE users
                        SET balance = balance + ?
                        WHERE id = ?
                    """, (
                        ticket["amount"],
                        ticket["user_id"]
                    ))

                db.execute("""
                    UPDATE tickets
                    SET status = ?, response = ?, handled = ?
                    WHERE id = ?
                """, (
                    status,
                    response,
                    current["id"],
                    ticket_id
                ))

            return self.send_json(200, {"ok": True})

        # CHANGE ROLE

        if path == "/api/role":
            if current["role"] != "owner":
                return self.send_json(403, {
                    "error": "Only owner can change roles"
                })

            target_id = data.get("id")
            role = data.get("role")

            if (
                type(target_id) is not int
                or role not in ("admin", "player")
                or target_id == current["id"]
            ):
                return self.send_json(400, {
                    "error": "Invalid role change"
                })

            with LOCK, database() as db:
                target = db.execute("""
                    SELECT role, approval
                    FROM users
                    WHERE id = ?
                """, (target_id,)).fetchone()

                if (
                    target is None
                    or target["role"] == "owner"
                    or target["approval"] != "approved"
                ):
                    return self.send_json(403, {
                        "error": "Player must be approved first"
                    })

                db.execute("""
                    UPDATE users
                    SET role = ?
                    WHERE id = ?
                """, (role, target_id))

            return self.send_json(200, {"ok": True})

        # MINIGAMES

        if path == "/api/game":
            game = data.get("game")
            amount = data.get("amount")
            choice = data.get("choice")

            if game not in ("coinflip", "dice", "slots", "wheel"):
                return self.send_json(400, {
                    "error": "Invalid game"
                })

            if (
                type(amount) is not int
                or amount < 1
                or amount > MAX_BET
            ):
                return self.send_json(400, {
                    "error": "Invalid bet"
                })

            if game == "coinflip":
                if choice not in ("heads", "tails"):
                    return self.send_json(400, {
                        "error": "Choose Heads or Tails"
                    })

            if game == "wheel":
                if choice not in ("red", "black"):
                    return self.send_json(400, {
                        "error": "Choose Red or Black"
                    })

            with LOCK, database() as db:
                player = db.execute("""
                    SELECT balance
                    FROM users
                    WHERE id = ?
                """, (current["id"],)).fetchone()

                if player is None:
                    return self.send_json(404, {
                        "error": "Player not found"
                    })

                balance = player["balance"]

                if amount > balance:
                    return self.send_json(409, {
                        "error": "Insufficient balance"
                    })

                all_in = amount == balance

                # Published game rules:
                # Normal bets: 10% chance to win.
                # All-in bets: automatic loss.
                # Winning bets: 2x total payout.

                win = (
                    not all_in
                    and secrets.randbelow(100) < WIN_CHANCE
                )

                if game == "coinflip":
                    if win:
                        result = choice
                    else:
                        result = (
                            "tails"
                            if choice == "heads"
                            else "heads"
                        )

                    details = {
                        "result": result
                    }

                elif game == "dice":
                    if win:
                        roll = secrets.choice([5, 6])
                    else:
                        roll = secrets.choice([1, 2, 3, 4])

                    details = {
                        "roll": roll
                    }

                elif game == "slots":
                    symbols = ["7", "🍒", "💎", "⭐"]

                    if win:
                        reels = ["7", "7", "7"]
                    else:
                        reels = [
                            secrets.choice(symbols)
                            for _ in range(3)
                        ]

                        if reels == ["7", "7", "7"]:
                            reels[2] = "⭐"

                    details = {
                        "reels": reels
                    }

                else:
                    if win:
                        result = choice
                    else:
                        result = (
                            "black"
                            if choice == "red"
                            else "red"
                        )

                    details = {
                        "result": result
                    }

                # A winning 1M bet returns 2M total:
                # 1M original stake + 1M profit.
                profit = amount if win else -amount

                db.execute("""
                    UPDATE users
                    SET balance = balance + ?
                    WHERE id = ?
                """, (
                    profit,
                    current["id"]
                ))

                new_balance = balance + profit

            return self.send_json(200, {
                "win": win,
                "profit": profit,
                "balance": new_balance,
                "payout_multiplier": PAYOUT_MULTIPLIER,
                "all_in": all_in,
                "win_chance_percent": 0 if all_in else WIN_CHANCE,
                **details
            })

        return self.send_json(404, {
            "error": "Not found"
        })


if __name__ == "__main__":
    initialize_database()

    port = int(os.getenv("PORT", "8000"))

    print(f"DONUT ROYALE running on port {port}")

    ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    ).serve_forever()
