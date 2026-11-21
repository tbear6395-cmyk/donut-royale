# DONUT ROYALE — English full-stack demo

Requires Python 3.9+; no third-party dependencies.

## Start locally

macOS/Linux:
```bash
export OWNER_USERNAME=YourMinecraftNick
export OWNER_PASSWORD='choose-a-unique-password-at-least-12-characters'
python3 server.py
```

Windows PowerShell:
```powershell
$env:OWNER_USERNAME='YourMinecraftNick'
$env:OWNER_PASSWORD='choose-a-unique-password-at-least-12-characters'
python server.py
```

Visit http://localhost:8000. Register normal player accounts on the website. The initial owner account is created on first launch, using the environment variables. Keep your owner password private.

## Features
- Server-side password hashing (PBKDF2), login sessions, SQLite user database.
- Games are inaccessible until login; server checks balance and login for each bet.
- Private support/deposit/withdraw tickets, admin ticket approvals and balance adjustments.
- Owner can grant/revoke admin privileges. Admins cannot grant admin privileges.
- 30% player / 70% house coinflip, clearly available in Game Info.
- Deposit command `/pay matejicekjepica AMOUNT` is instructional only. Admins must independently verify payment; no automated DonutSMP integration.

## IMPORTANT: production deployment
This is a functional local prototype, not a production-hardened money or item custody service. Do NOT deploy to a public gambling website or accept real payments using it as-is. It has no automatic game-payment verification, fraud controls, audit log, rate limiting, CSRF protection, persistent session storage, or external identity verification. The username is self-declared, not verified against Minecraft account ownership. For internet hosting, use HTTPS, `COOKIE_SECURE=1`, persistent protected storage, a reverse proxy, rate limiting, CSRF protections, backups and a security review. Netlify Drop cannot run the Python backend. Use a Python-capable host with persistent SQLite storage or managed database instead.

All balance credits are demo credits. Never approve a deposit from a screenshot alone.
