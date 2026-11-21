
import os
import re
import json
import hmac
import secrets
import sqlite3
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
DB = BASE / "data.sqlite3"
LOCK = threading.RLock()

MAX_BET = 3_000_000_000
WIN_CHANCE = 10
PAYOUT = 2
SESSION_DAYS = 30


def db_open():
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=30000")
    return db


def now():
    return datetime.now(timezone.utc)


def hash_pw(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt),
        260000
    ).hex()


def initialize():
    with db_open() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE COLLATE NOCASE,
                salt TEXT NOT NULL,
                pw TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'player',
                balance INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                response TEXT NOT NULL DEFAULT '',
                created TEXT DEFAULT CURRENT_TIMESTAMP,
                handled INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires TEXT NOT NULL
            );
        """)

        columns = {
            r["name"]
            for r in db.execute("PRAGMA table_info(users)")
        }

        if "approval" not in columns:
            db.execute("""
                ALTER TABLE users
                ADD COLUMN approval TEXT DEFAULT 'approved'
            """)

        # Registration no longer requires owner approval.
        db.execute("""
            UPDATE users
            SET approval='approved'
            WHERE approval IS NULL
               OR approval != 'approved'
        """)

        owner = db.execute("""
            SELECT id FROM users WHERE role='owner'
        """).fetchone()

        if not owner:
            username = os.getenv("OWNER_USERNAME", "").strip()
            password = os.getenv("OWNER_PASSWORD", "")

            if (
                re.fullmatch(r"[A-Za-z0-9_]{3,16}", username)
                and len(password) >= 12
            ):
                salt = secrets.token_hex(16)
                existing = db.execute("""
                    SELECT id FROM users
                    WHERE username=? COLLATE NOCASE
                """, (username,)).fetchone()

                if existing:
                    db.execute("""
                        UPDATE users
                        SET role='owner',
                            salt=?,
                            pw=?,
                            approval='approved'
                        WHERE id=?
                    """, (
                        salt,
                        hash_pw(password, salt),
                        existing["id"]
                    ))
                else:
                    db.execute("""
                        INSERT INTO users
                        (username, salt, pw, role, balance, approval)
                        VALUES (?, ?, ?, 'owner', 0, 'approved')
                    """, (
                        username,
                        salt,
                        hash_pw(password, salt)
                    ))
            else:
                print("Owner not created: configure OWNER_USERNAME and OWNER_PASSWORD")

        db.execute("""
            DELETE FROM sessions WHERE expires <= ?
        """, (now().isoformat(),))


def public_user(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "balance": row["balance"]
    }


def create_session(db, user_id):
    token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = (now() + timedelta(days=SESSION_DAYS)).isoformat()

    db.execute("""
        INSERT INTO sessions (token_hash, user_id, expires)
        VALUES (?, ?, ?)
    """, (token_hash, user_id, expires))

    return token


class Handler(BaseHTTPRequestHandler):

    def send_json(self, status, data, cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

        if cookie:
            self.send_header("Set-Cookie", cookie)

        self.end_headers()
        self.wfile.write(body)

    def error(self, status, message):
        self.send_json(status, {"error": message})

    def body(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 0 or size > 20000:
                return {}
            result = json.loads(self.rfile.read(size))
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    def session_token(self):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))
            item = cookies.get("session")
            return item.value if item else None
        except Exception:
            return None

    def current_user(self):
        token = self.session_token()
        if not token:
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        with db_open() as db:
            row = db.execute("""
                SELECT u.*
                FROM sessions s
                JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires>?
            """, (token_hash, now().isoformat())).fetchone()

        return public_user(row)

    def session_cookie(self, token):
        cookie = (
            f"session={token}; Path=/; HttpOnly; "
            f"SameSite=Lax; Max-Age={SESSION_DAYS * 86400}"
        )
        if os.getenv("RENDER") or os.getenv("COOKIE_SECURE") == "1":
            cookie += "; Secure"
        return cookie

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            path = "/index.html"

        static = {
            "/index.html": "text/html; charset=utf-8",
            "/style.css": "text/css; charset=utf-8",
            "/app.js": "application/javascript; charset=utf-8",
            "/coin-heads.png": "image/png",
            "/coin-tails.png": "image/png"
        }

        if path in static:
            filename = BASE / path.lstrip("/")

            if not filename.is_file():
                return self.error(404, "File not found")

            content = filename.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", static[path])
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/me":
            return self.send_json(200, {
                "user": self.current_user()
            })

        if path == "/api/rules":
            return self.send_json(200, {
                "max_bet": MAX_BET,
                "win_chance_percent": WIN_CHANCE,
                "loss_chance_percent": 90,
                "payout_multiplier": PAYOUT,
                "all_in_always_loses": True
            })

        user = self.current_user()

        if not user:
            return self.error(401, "Please log in")

        if path == "/api/tickets":
            with db_open() as db:
                if user["role"] in ("owner", "admin"):
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
                    """, (user["id"],)).fetchall()

            return self.send_json(200, {
                "tickets": [dict(r) for r in rows]
            })

        if path == "/api/users":
            if user["role"] not in ("owner", "admin"):
                return self.error(403, "Not allowed")

            with db_open() as db:
                rows = db.execute("""
                    SELECT id, username, role, balance
                    FROM users
                    ORDER BY id DESC
                """).fetchall()

            return self.send_json(200, {
                "users": [dict(r) for r in rows]
            })

        self.error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.body()

        # REGISTER: immediate account creation and login.
        if path == "/api/register":
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))

            if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", username):
                return self.error(
                    400,
                    "Username must be 3-16 letters, numbers or underscores"
                )

            if not 8 <= len(password) <= 128:
                return self.error(
                    400,
                    "Password must have at least 8 characters"
                )

            with LOCK, db_open() as db:
                salt = secrets.token_hex(16)

                try:
                    cursor = db.execute("""
                        INSERT INTO users
                        (username, salt, pw, role, balance, approval)
                        VALUES (?, ?, ?, 'player', 0, 'approved')
                    """, (
                        username,
                        salt,
                        hash_pw(password, salt)
                    ))
                except sqlite3.IntegrityError:
                    return self.error(409, "Username already exists")

                user_id = cursor.lastrowid
                token = create_session(db, user_id)

            return self.send_json(
                200,
                {"ok": True, "message": "Account created"},
                self.session_cookie(token)
            )

        # LOGIN
        if path == "/api/login":
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))

            with LOCK, db_open() as db:
                row = db.execute("""
                    SELECT * FROM users
                    WHERE username=? COLLATE NOCASE
                """, (username,)).fetchone()

                if (
                    not row
                    or not hmac.compare_digest(
                        hash_pw(password, row["salt"]),
                        row["pw"]
                    )
                ):
                    return self.error(401, "Wrong username or password")

                token = create_session(db, row["id"])

            return self.send_json(
                200,
                {"ok": True},
                self.session_cookie(token)
            )

        # LOGOUT
        if path == "/api/logout":
            token = self.session_token()

            if token:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                with LOCK, db_open() as db:
                    db.execute("""
                        DELETE FROM sessions WHERE token_hash=?
                    """, (token_hash,))

            cookie = (
                "session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
            )
            if os.getenv("RENDER") or os.getenv("COOKIE_SECURE") == "1":
                cookie += "; Secure"

            return self.send_json(200, {"ok": True}, cookie)

        user = self.current_user()

        if not user:
            return self.error(401, "Please log in")

        # CREATE TICKET
        if path == "/api/tickets":
            kind = data.get("kind")
            amount = data.get("amount", 0)
            message = str(data.get("message", "")).strip()

            if kind not in ("deposit", "withdraw", "support"):
                return self.error(400, "Invalid ticket type")

            if (
                type(amount) is not int
                or amount < 0
                or amount > 1_000_000_000_000
                or (kind != "support" and amount == 0)
                or len(message) > 1000
            ):
                return self.error(400, "Invalid ticket details")

            with LOCK, db_open() as db:
                if kind == "withdraw":
                    balance = db.execute("""
                        SELECT balance FROM users WHERE id=?
                    """, (user["id"],)).fetchone()["balance"]

                    if amount > balance:
                        return self.error(
                            400,
                            "Not enough balance for withdrawal"
                        )

                db.execute("""
                    INSERT INTO tickets
                    (user_id, kind, amount, message)
                    VALUES (?, ?, ?, ?)
                """, (user["id"], kind, amount, message))

            return self.send_json(200, {"ok": True})

        # REVIEW TICKET
        if path == "/api/ticket/review":
            if user["role"] not in ("owner", "admin"):
                return self.error(403, "Not allowed")

            ticket_id = data.get("id")
            status = data.get("status")
            response = str(data.get("response", "")).strip()[:1000]

            if (
                type(ticket_id) is not int
                or status not in ("approved", "rejected", "closed")
            ):
                return self.error(400, "Invalid review")

            with LOCK, db_open() as db:
                ticket = db.execute("""
                    SELECT * FROM tickets WHERE id=?
                """, (ticket_id,)).fetchone()

                if not ticket or ticket["status"] != "open":
                    return self.error(409, "Ticket already handled")

                if status == "approved":
                    if ticket["kind"] == "deposit":
                        db.execute("""
                            UPDATE users
                            SET balance=balance+?
                            WHERE id=?
                        """, (ticket["amount"], ticket["user_id"]))

                    elif ticket["kind"] == "withdraw":
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
                            return self.error(
                                409,
                                "Player does not have enough balance"
                            )
                    else:
                        return self.error(
                            400,
                            "Close support tickets instead"
                        )

                db.execute("""
                    UPDATE tickets
                    SET status=?, response=?, handled=?
                    WHERE id=?
                """, (
                    status,
                    response,
                    user["id"],
                    ticket_id
                ))

            # The ticket is retained in the database for records,
            # but disappears from both active ticket lists.
            return self.send_json(200, {"ok": True})

        # CHANGE ROLE
        if path == "/api/role":
            if user["role"] != "owner":
                return self.error(403, "Only owner can change roles")

            target_id = data.get("id")
            role = data.get("role")

            if (
                type(target_id) is not int
                or role not in ("admin", "player")
                or target_id == user["id"]
            ):
                return self.error(400, "Invalid role change")

            with LOCK, db_open() as db:
                target = db.execute("""
                    SELECT role FROM users WHERE id=?
                """, (target_id,)).fetchone()

                if not target or target["role"] == "owner":
                    return self.error(403, "Cannot change owner role")

                db.execute("""
                    UPDATE users SET role=? WHERE id=?
                """, (role, target_id))

            return self.send_json(200, {"ok": True})

        # MINIGAMES
        if path == "/api/game":
            game = data.get("game")
            amount = data.get("amount")
            choice = data.get("choice")

            if game not in ("coinflip", "dice", "slots", "wheel"):
                return self.error(400, "Invalid game")

            if (
                type(amount) is not int
                or amount < 1
                or amount > MAX_BET
            ):
                return self.error(400, "Maximum bet is 3B")

            if game == "coinflip" and choice not in ("heads", "tails"):
                return self.error(400, "Choose Heads or Tails")

            if game == "wheel" and choice not in ("red", "black"):
                return self.error(400, "Choose Red or Black")

            with LOCK, db_open() as db:
                row = db.execute("""
                    SELECT balance FROM users WHERE id=?
                """, (user["id"],)).fetchone()

                if not row:
                    return self.error(404, "Player not found")

                balance = row["balance"]

                if amount > balance:
                    return self.error(400, "Not enough balance")

                all_in = amount == balance

                # These rules are displayed on the website:
                # Regular bets: 10% win chance.
                # All-in bets: automatic loss.
                # Winning bets: 2x total return.
                win = (
                    not all_in
                    and secrets.randbelow(100) < WIN_CHANCE
                )

                if game == "coinflip":
                    result = (
                        choice if win
                        else ("tails" if choice == "heads" else "heads")
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
                        choice if win
                        else ("black" if choice == "red" else "red")
                    )
                    details = {"result": result}

                profit = amount if win else -amount

                db.execute("""
                    UPDATE users
                    SET balance=balance+?
                    WHERE id=?
                """, (profit, user["id"]))

                new_balance = balance + profit

            return self.send_json(200, {
                "win": win,
                "profit": profit,
                "balance": new_balance,
                "all_in": all_in,
                "payout_multiplier": PAYOUT,
                **details
            })

        self.error(404, "Not found")


if __name__ == "__main__":
    initialize()
    port = int(os.getenv("PORT", "8000"))
    print(f"DONUT ROYALE running on port {port}")
    ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    ).serve_forever()
