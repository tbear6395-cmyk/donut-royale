
import os, sqlite3, secrets, hashlib, hmac, json, re, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse
from pathlib import Path

DB = Path(__file__).with_name('data.sqlite3')
LOCK = threading.RLock()
SESS = {}

def conn():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    return c

def hashpw(p, s):
    return hashlib.pbkdf2_hmac(
        'sha256', p.encode(), bytes.fromhex(s), 260000
    ).hex()

def init():
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE COLLATE NOCASE,
            salt TEXT,
            pw TEXT,
            role TEXT DEFAULT 'player',
            balance INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tickets(
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
        ''')
        if not c.execute(
            "SELECT 1 FROM users WHERE role='owner'"
        ).fetchone():
            u = os.getenv('OWNER_USERNAME')
            p = os.getenv('OWNER_PASSWORD')
            if u and p and re.fullmatch('[A-Za-z0-9_]{3,16}', u) and len(p) >= 12:
                salt = secrets.token_hex(16)
                c.execute(
                    'INSERT INTO users(username,salt,pw,role) VALUES(?,?,?,?)',
                    (u, salt, hashpw(p, salt), 'owner')
                )
            else:
                print('OWNER NOT CONFIGURED: set OWNER_USERNAME and OWNER_PASSWORD (12+ chars)')

def user(uid):
    with conn() as c:
        r = c.execute(
            'SELECT id,username,role,balance FROM users WHERE id=?',
            (uid,)
        ).fetchone()
        return dict(r) if r else None

class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, cookie=None):
        b = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header(
            'Content-Security-Policy',
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"
        )
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(b)

    def auth(self):
        co = SimpleCookie()
        try:
            co.load(self.headers.get('Cookie', ''))
        except Exception:
            pass
        token = co.get('session')
        return user(SESS.get(token.value)) if token and token.value in SESS else None

    def body(self):
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if n > 10000:
                raise ValueError()
            return json.loads(self.rfile.read(n))
        except Exception:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            path = '/index.html'

        if path in ('/index.html', '/app.js', '/style.css'):
            try:
                b = (Path(__file__).parent / path.lstrip('/')).read_bytes()
            except FileNotFoundError:
                return self.send(404, {'error': 'File not found'})
            self.send_response(200)
            self.send_header('Content-Type', {
                '/index.html': 'text/html; charset=utf-8',
                '/app.js': 'application/javascript',
                '/style.css': 'text/css'
            }[path])
            self.send_header('Content-Length', str(len(b)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(b)
            return

        u = self.auth()
        if path == '/api/me':
            return self.send(200, {'user': u})
        if not u:
            return self.send(401, {'error': 'Please log in'})

        if path == '/api/tickets':
            with conn() as c:
                q = 'SELECT t.*,u.username FROM tickets t JOIN users u ON u.id=t.user_id '
                q += 'ORDER BY t.id DESC' if u['role'] in ('admin', 'owner') else 'WHERE t.user_id=? ORDER BY t.id DESC'
                rows = c.execute(
                    q, () if u['role'] in ('admin', 'owner') else (u['id'],)
                ).fetchall()
            return self.send(200, {'tickets': [dict(x) for x in rows]})

        if path == '/api/users' and u['role'] in ('admin', 'owner'):
            with conn() as c:
                rows = c.execute(
                    'SELECT id,username,role,balance FROM users ORDER BY id DESC'
                ).fetchall()
            return self.send(200, {'users': [dict(x) for x in rows]})

        return self.send(404, {'error': 'Not found'})

    def do_POST(self):
        path = urlparse(self.path).path
        d = self.body()
        u = self.auth()

        if path in ('/api/register', '/api/login'):
            name = str(d.get('username', '')).strip()
            pw = str(d.get('password', ''))
            if not re.fullmatch('[A-Za-z0-9_]{3,16}', name) or not (8 <= len(pw) <= 128):
                return self.send(400, {'error': 'Minecraft username 3-16 characters; password 8+ characters'})

            with LOCK, conn() as c:
                if path.endswith('register'):
                    salt = secrets.token_hex(16)
                    try:
                        c.execute(
                            'INSERT INTO users(username,salt,pw) VALUES(?,?,?)',
                            (name, salt, hashpw(pw, salt))
                        )
                    except sqlite3.IntegrityError:
                        return self.send(409, {'error': 'Username already registered'})

                r = c.execute(
                    'SELECT * FROM users WHERE username=? COLLATE NOCASE',
                    (name,)
                ).fetchone()
                if not r or not hmac.compare_digest(hashpw(pw, r['salt']), r['pw']):
                    return self.send(401, {'error': 'Invalid login'})

            token = secrets.token_urlsafe(32)
            SESS[token] = r['id']
            cookie = f'session={token}; HttpOnly; SameSite=Strict; Path=/'
            if os.getenv('COOKIE_SECURE') == '1':
                cookie += '; Secure'
            return self.send(200, {'ok': True}, cookie)

        if path == '/api/logout':
            co = SimpleCookie()
            try:
                co.load(self.headers.get('Cookie', ''))
                t = co.get('session')
                if t:
                    SESS.pop(t.value, None)
            except Exception:
                pass
            return self.send(
                200, {'ok': True},
                'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
            )

        if not u:
            return self.send(401, {'error': 'Please log in'})

        if path == '/api/tickets':
            kind = d.get('kind')
            amount = d.get('amount')
            message = str(d.get('message', '')).strip()
            if kind not in ('deposit', 'withdraw', 'support') or len(message) > 1000:
                return self.send(400, {'error': 'Invalid ticket'})
            if type(amount) is not int or amount < 0 or amount > 1000000000 or (kind != 'support' and amount == 0):
                return self.send(400, {'error': 'Invalid amount'})
            with LOCK, conn() as c:
                c.execute(
                    'INSERT INTO tickets(user_id,kind,amount,message) VALUES(?,?,?,?)',
                    (u['id'], kind, amount, message)
                )
            return self.send(200, {'ok': True})

        if path == '/api/ticket/review' and u['role'] in ('admin', 'owner'):
            tid = d.get('id')
            status = d.get('status')
            response = str(d.get('response', ''))[:1000]
            if type(tid) is not int or status not in ('approved', 'rejected', 'closed'):
                return self.send(400, {'error': 'Invalid request'})

            with LOCK, conn() as c:
                t = c.execute(
                    'SELECT * FROM tickets WHERE id=?', (tid,)
                ).fetchone()
                if not t or t['status'] != 'open':
                    return self.send(409, {'error': 'Ticket already handled'})
                if status == 'approved' and t['kind'] == 'support':
                    return self.send(400, {'error': 'Cannot approve support ticket'})
                if status == 'approved' and t['kind'] == 'withdraw':
                    balance = c.execute(
                        'SELECT balance FROM users WHERE id=?',
                        (t['user_id'],)
                    ).fetchone()['balance']
                    if balance < t['amount']:
                        return self.send(409, {'error': 'Insufficient balance'})
                    c.execute(
                        'UPDATE users SET balance=balance-? WHERE id=?',
                        (t['amount'], t['user_id'])
                    )
                if status == 'approved' and t['kind'] == 'deposit':
                    c.execute(
                        'UPDATE users SET balance=balance+? WHERE id=?',
                        (t['amount'], t['user_id'])
                    )
                c.execute(
                    'UPDATE tickets SET status=?,response=?,handled=? WHERE id=?',
                    (status, response, u['id'], tid)
                )
            return self.send(200, {'ok': True})

        if path == '/api/role' and u['role'] == 'owner':
            uid = d.get('id')
            role = d.get('role')
            if type(uid) is not int or role not in ('admin', 'player') or uid == u['id']:
                return self.send(400, {'error': 'Invalid role change'})
            with LOCK, conn() as c:
                c.execute(
                    "UPDATE users SET role=? WHERE id=? AND role!='owner'",
                    (role, uid)
                )
            return self.send(200, {'ok': True})

        if path == '/api/game':
            amount = d.get('amount')
            game = d.get('game')
            choice = d.get('choice')
            if type(amount) is not int or amount < 1 or amount > 1000000 or game not in ('coinflip', 'dice', 'slots', 'wheel'):
                return self.send(400, {'error': 'Invalid bet'})
            if game == 'coinflip' and choice not in ('heads', 'tails'):
                return self.send(400, {'error': 'Choose Heads or Tails'})
            if game == 'wheel' and choice not in ('red', 'black'):
                return self.send(400, {'error': 'Choose Red or Black'})

            with LOCK, conn() as c:
                balance = c.execute(
                    'SELECT balance FROM users WHERE id=?',
                    (u['id'],)
                ).fetchone()['balance']
                if balance < amount:
                    return self.send(409, {'error': 'Insufficient demo credits'})

                if game == 'coinflip':
                    win = secrets.randbelow(100) < 30
                    result = choice if win else ('tails' if choice == 'heads' else 'heads')
                    payout = 2
                    details = {'result': result, 'odds': 'Player 30%, house 70%'}

                elif game == 'dice':
                    roll = secrets.randbelow(6) + 1
                    win = roll == 6
                    payout = 5
                    details = {'roll': roll, 'odds': '1 in 6'}

                elif game == 'slots':
                    win = secrets.randbelow(16) == 0
                    payout = 8
                    symbols = ['7', '🍒', '💎', '⭐']
                    reels = [secrets.choice(symbols) for _ in range(3)]
                    if win:
                        reels = ['7', '7', '7']
                    elif reels == ['7', '7', '7']:
                        reels[2] = '⭐'
                    details = {'reels': reels, 'odds': '1 in 16'}

                else:
                    win = secrets.randbelow(100) < 40
                    payout = 2
                    result = choice if win else ('black' if choice == 'red' else 'red')
                    details = {'result': result, 'odds': 'Player 40%, house 60%'}

                profit = amount * (payout - 1) if win else -amount
                c.execute(
                    'UPDATE users SET balance=balance+? WHERE id=?',
                    (profit, u['id'])
                )

            return self.send(200, {
                'win': win, 'profit': profit, **details
            })

        return self.send(403, {'error': 'Not allowed'})

if __name__ == '__main__':
    init()
    port = int(os.getenv('PORT', '8000'))
    print(f'Listening on port {port}')
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
