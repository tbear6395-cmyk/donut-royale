"""Short-lived, read-only spectator projections for the single-process game server."""
import secrets
import time
from collections import OrderedDict
from threading import Lock

TABLES = OrderedDict()
LOCK = Lock()
GAMES = {"blackjack", "wheel", "casebattle"}


def publish(game, username, view, table=None):
    key = table or secrets.token_hex(8)
    with LOCK:
        TABLES[key] = (time.monotonic(), game, username[:1] + "...........", view)
        TABLES.move_to_end(key)
        while len(TABLES) > 250:
            TABLES.popitem(last=False)
    return key


def tables(game):
    now = time.monotonic()
    result = []
    with LOCK:
        for key, (started, kind, alias, view) in reversed(TABLES.items()):
            if kind != game:
                continue
            age = max(0, now - started)
            state = {"id": key, "player": alias, "stake": view["stake"]}
            if game == "blackjack":
                if age > (1800 if view["outcome"] == "playing" else 90):
                    continue
                state.update(view)
                state["live"] = view["outcome"] == "playing"
            elif game == "wheel":
                if age > 95:
                    continue
                state.update(choice=view["choice"], live=age < 5)
                if not state["live"]:
                    state["result"] = view["result"]
            else:
                shown = min(int(age / 2.77), len(view["drops"]))
                if age > len(view["drops"]) * 2.77 + 90:
                    continue
                state.update(case=view["case"], rounds=len(view["drops"]),
                             drops=view["drops"][:shown], live=shown < len(view["drops"]))
            result.append(state)
            if len(result) == 30:
                break
    return result
