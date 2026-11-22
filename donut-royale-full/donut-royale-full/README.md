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

## Wallet support tickets and live Admin replies

Players can open **Wallet → Support**, choose Complaint, Payment, Game bug, or Other,
and exchange messages in their support ticket. The staff queue lets admins and owners
reply. The player-facing API only identifies the staff participant as **Admin**,
never by username, account ID, or Owner role. Closed tickets are read-only.

Support tickets and the message history are stored in SQLite or Postgres. Staff and
ticket owners are the only people authorized to read their conversations.

## Royal Staff → Bot & CMD

The CMD tab is a **read-only** window for console lines forwarded by the local Minecraft bot,
not a remote terminal. It never runs PowerShell, Windows CMD, or Minecraft commands.
Only logged-in Admin or Owner users can view the log. Bot uploads require the
server's `BOT_API_KEY` and sensitive-looking lines are filtered.

Your Windows bot in the screenshot runs in a separate local folder with `node index.js`.
The website cannot access that computer's terminal by itself. To enable log forwarding:

1. Copy `bot-console-forwarder.js` next to your local `index.js`.
2. Ensure that local `.env` contains the same `BOT_API_KEY` as the website backend.
   Optionally set `DONUT_ROYALE_URL=https://donut-royale.onrender.com`.
3. From the bot folder, run:
   ```powershell
   node -r ./bot-console-forwarder.js index.js
   ```

This automatically sends up to 20 console lines every 3 seconds while the bot is running.
`bot-client-v3.js` in this repository includes the same forwarder automatically.
Do **not** paste `.env`, passwords, or API keys into a support ticket or CMD log.
