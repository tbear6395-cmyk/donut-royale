"""Authoritative chess turns and persistent single-stake matches."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import urllib.request

BASE = Path(__file__).resolve().parent
ENGINE_HASH = "7ca31bedd166148931a1cc84dbd8dd9cf001744e9994caf23a3c6ff4988d7086"
ENGINE_URL = "https://unpkg.com/stockfish@17.1.0/src/stockfish-17.1-lite-single-03e3232.wasm"
ENGINE_DIR = tempfile.TemporaryDirectory(prefix="royale-chess-")
WASM = Path(ENGINE_DIR.name) / "stockfish.wasm"
engine_ready = threading.Event()
warm_lock = threading.Lock()
engine_slot = threading.BoundedSemaphore(1)


def run_turn(moves, move):
    job = subprocess.run(["node", str(BASE / "chess-turn.cjs"), str(WASM)],
                         input=json.dumps({"moves": moves, "move": move}), text=True,
                         capture_output=True, check=True, timeout=15)
    return json.loads(job.stdout)


def warm():
    if engine_ready.is_set() or not warm_lock.acquire(False):
        return
    def prepare():
        try:
            if not shutil.which("node"):
                raise RuntimeError("Node runtime unavailable")
            with urllib.request.urlopen(ENGINE_URL, timeout=25) as response:
                data = response.read(8 * 1024 * 1024)
            if hashlib.sha256(data).hexdigest() != ENGINE_HASH:
                raise ValueError("Invalid engine checksum")
            WASM.write_bytes(data)
            if run_turn([], "e2e4")["outcome"] == "active":
                engine_ready.set()
        except Exception as err:
            print("Chess engine initialization failed:", type(err).__name__, flush=True)
        finally:
            warm_lock.release()
    threading.Thread(target=prepare, daemon=True).start()


def setup(db):
    db.execute("""CREATE TABLE IF NOT EXISTS chess_matches(
        user_id BIGINT PRIMARY KEY REFERENCES users(id), game_id TEXT NOT NULL,
        stake BIGINT NOT NULL, moves TEXT NOT NULL, outcome TEXT NOT NULL)""")


def current(db, uid):
    row = db.execute("SELECT game_id,stake,moves,outcome FROM chess_matches WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None
    return dict(id=row["game_id"], stake=row["stake"], moves=json.loads(row["moves"]), outcome=row["outcome"])


def state(db, uid):
    balance = db.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()["balance"]
    return {"match": current(db, uid), "balance": balance, "engine_ready": engine_ready.is_set()}


def handle(h, action, uid, body, srv):
    if action not in ("start", "move", "resign"):
        return h.fail(404, "Unknown chess action")
    def lock_user(db):
        if srv.USE_POSTGRES:
            db.execute("SELECT pg_advisory_xact_lock(?)", (64000000000 + uid,))
    if action == "start":
        stake = body.get("stake")
        if type(stake) is not int or not 1 <= stake <= srv.MAX_BET:
            return h.fail(400, "Stake must be 1 to 3B credits")
        if not engine_ready.is_set():
            warm()
            return h.fail(503, "Engine warming up. Try again shortly.")
        with srv.LOCK, srv.db_open() as db:
            lock_user(db)
            old = current(db, uid)
            if old and (old["outcome"] == "active" or old["id"] != body.get("previous")):
                return h.fail(409, "Reload your current match before starting another.")
            if srv.staff_setting(db, "games_paused") == "1":
                return h.fail(409, "Games are paused")
            if not db.execute("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?",
                              (stake, uid, stake)).rowcount:
                return h.fail(400, "Insufficient credits")
            db.execute("""INSERT INTO chess_matches(user_id,game_id,stake,moves,outcome)
                VALUES(?,?,?,'[]','active') ON CONFLICT(user_id) DO UPDATE SET
                game_id=excluded.game_id,stake=excluded.stake,moves='[]',outcome='active'""",
                       (uid, secrets.token_hex(16), stake))
            result = state(db, uid)
        return h.send_json(200, result)

    with srv.db_open() as db:
        match = current(db, uid)
    if not match or match["outcome"] != "active" or match["id"] != body.get("id") or len(match["moves"]) != body.get("ply"):
        return h.fail(409, "Match changed. Reloading the board.")
    moves, outcome = match["moves"], "lose"
    if action == "move":
        move = body.get("move")
        if not isinstance(move, str) or not re.fullmatch("[a-h][1-8][a-h][1-8][qrbn]?", move):
            return h.fail(400, "Invalid move")
        if not engine_ready.is_set():
            warm()
            return h.fail(503, "Engine warming up. Your match is saved.")
        if not engine_slot.acquire(timeout=3):
            return h.fail(503, "Engine is busy. Try the move again.")
        try:
            turn = run_turn(moves, move)
        except (OSError, subprocess.SubprocessError, ValueError):
            return h.fail(503, "Engine unavailable. Your position is saved.")
        finally:
            engine_slot.release()
        if turn.get("invalid"):
            return h.fail(400, "Illegal move")
        moves, outcome = turn["moves"], turn["outcome"]
    with srv.LOCK, srv.db_open() as db:
        lock_user(db)
        if current(db, uid) != match:
            return h.fail(409, "Match changed. Reloading the board.")
        db.execute("UPDATE chess_matches SET moves=?,outcome=? WHERE user_id=?",
                   (json.dumps(moves), outcome, uid))
        if outcome != "active":
            payout = match["stake"] * {"win": 2, "draw": 1, "lose": 0}[outcome]
            db.execute("UPDATE users SET balance=balance+? WHERE id=?", (payout, uid))
            srv.log_game(db, uid, "chess", match["stake"], payout, outcome)
        result = state(db, uid)
    return h.send_json(200, result)
