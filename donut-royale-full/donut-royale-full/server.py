
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DONUT ROYALE 🍩</title>

<style>
:root {
  --bg: #080d18;
  --sidebar: #0c1422;
  --panel: #172232;
  --panel2: #101a29;
  --line: #2a3950;
  --text: #f1f5ff;
  --muted: #94a6bc;
  --purple: #8663ff;
  --green: #31c875;
  --gold: #f7cc67;
  --red: #ff728d;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(circle at 80% 0%, #2a1b49 0%, transparent 35%),
    radial-gradient(circle at 10% 90%, #122b44 0%, transparent 40%),
    var(--bg);
  color: var(--text);
  font-family: Inter, Arial, sans-serif;
}

button, input, select, textarea {
  font: inherit;
}

button {
  border: none;
  cursor: pointer;
  color: white;
  transition: filter .2s, transform .2s;
}

button:hover { filter: brightness(1.12); }
button:disabled { opacity: .5; cursor: not-allowed; }

input, select, textarea {
  width: 100%;
  padding: 13px;
  background: #0b1421;
  border: 1px solid #3b4a63;
  border-radius: 9px;
  color: white;
  outline: none;
}

input:focus, select:focus, textarea:focus {
  border-color: #5cb4ff;
  box-shadow: 0 0 0 2px #5cb4ff33;
}

h1, h2, h3, p { margin-top: 0; }

.hidden { display: none !important; }

.muted { color: var(--muted); }
.small { font-size: 12px; }

.primary {
  padding: 13px 18px;
  background: linear-gradient(110deg, #7958ff, #aa64fa);
  border-radius: 10px;
  font-weight: 800;
}

.secondary {
  padding: 12px 16px;
  background: #304057;
  border-radius: 9px;
  font-weight: 700;
}

.success {
  padding: 10px 13px;
  background: #247f5a;
  border-radius: 9px;
  font-weight: 700;
}

.danger {
  padding: 10px 13px;
  background: #994158;
  border-radius: 9px;
  font-weight: 700;
}

/* AUTHENTICATION */

#authScreen {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  overflow-y: auto;
  background: #070c15;
}

.auth-background {
  position: fixed;
  inset: -20px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px;
  padding: 100px 12%;
  filter: blur(8px);
  opacity: .38;
  pointer-events: none;
}

.preview-game {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 190px;
  border-radius: 20px;
  border: 1px solid #586087;
  font-size: 27px;
  font-weight: 900;
  text-align: center;
  padding: 20px;
}

.preview-game:nth-child(1) {
  background: linear-gradient(135deg, #654316, #ba882b);
}

.preview-game:nth-child(2) {
  background: linear-gradient(135deg, #33206b, #7931aa);
}

.preview-game:nth-child(3) {
  background: linear-gradient(135deg, #163b61, #1969c1);
}

.preview-game:nth-child(4) {
  background: linear-gradient(135deg, #12513d, #209d67);
}

.preview-game:nth-child(5) {
  background: linear-gradient(135deg, #5b1c48, #a82d85);
}

.preview-game:nth-child(6) {
  background: linear-gradient(135deg, #243f6b, #6154b8);
}

.auth-modal {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 405px;
  padding: 23px;
  border: 1px solid #354258;
  border-radius: 13px;
  background: #192331;
  box-shadow: 0 30px 100px #000b;
}

.auth-logo {
  margin-bottom: 25px;
  font-size: 24px;
  font-weight: 950;
  font-style: italic;
  color: #eaf6ff;
  text-shadow: 0 0 12px #389cff88;
}

.auth-logo span { color: #68b8ff; }

.auth-label {
  margin-bottom: 7px;
  color: #8295ad;
  font-size: 11px;
  letter-spacing: 1px;
  font-weight: 900;
}

.auth-modal h2 {
  margin-bottom: 17px;
  font-size: 23px;
}

.responsible-box {
  padding: 13px;
  margin-bottom: 14px;
  background: #101a27;
  border: 1px solid #29374b;
  border-radius: 9px;
  font-size: 13px;
}

.responsible-box p {
  margin: 7px 0 0;
  color: #a3b0c2;
  font-size: 12px;
  line-height: 1.6;
}

.bonus-box {
  padding: 12px;
  margin-bottom: 17px;
  background: #25271f;
  border: 1px solid #92743b;
  border-radius: 8px;
  color: #f5cf75;
  font-size: 12px;
  font-weight: 800;
}

#authForm {
  display: grid;
  gap: 11px;
}

.field-title {
  font-size: 13px;
  font-weight: 800;
}

.field-help {
  margin: -5px 0 0;
  font-size: 12px;
  color: #95a5b9;
  line-height: 1.5;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 13px;
  border: 1px solid #2b394d;
  border-radius: 8px;
  background: #101a27;
  cursor: pointer;
}

.check-row input {
  width: 17px;
  height: 17px;
  margin: 1px 0 0;
  flex-shrink: 0;
  accent-color: #32c875;
}

.check-row span {
  display: grid;
  gap: 5px;
  font-size: 12px;
}

.check-row small {
  color: #91a3b9;
  line-height: 1.4;
}

.continue-btn {
  width: 100%;
  padding: 13px;
  border-radius: 8px;
  background: var(--green);
  color: #06140d;
  font-weight: 900;
}

#authMessage {
  min-height: 15px;
  margin: 12px 0;
  color: #ff8ba0;
  font-size: 12px;
}

.auth-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #8fa0b5;
  font-size: 12px;
  margin: 12px 0;
}

.auth-divider::before,
.auth-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: #334157;
}

.auth-tabs {
  display: flex;
  gap: 10px;
}

.auth-tabs button {
  flex: 1;
  padding: 12px;
  background: #344258;
  border-radius: 8px;
  font-weight: 800;
}

.auth-tabs button.active {
  background: #575cf0;
}

/* MAIN APP */

#app {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 235px;
  flex-shrink: 0;
  padding: 25px 16px;
  background: #0d1423;
  border-right: 1px solid #27344c;
}

.logo {
  font-size: 21px;
  font-weight: 950;
  margin-bottom: 32px;
}

.logo span { color: #c47bff; }

.nav {
  display: grid;
  gap: 7px;
}

.nav-button {
  width: 100%;
  padding: 14px;
  text-align: left;
  background: transparent;
  border-radius: 10px;
  color: #c4cee1;
  font-weight: 700;
}

.nav-button.active,
.nav-button:hover {
  background: #342c5e;
  color: white;
}

.main {
  flex: 1;
  min-width: 0;
  padding: 28px 35px 100px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  flex-wrap: wrap;
  margin-bottom: 30px;
}

.balance-pill {
  padding: 12px 18px;
  border: 1px solid #69509b;
  border-radius: 12px;
  background: #252441;
  color: var(--gold);
  font-weight: 900;
}

.hero {
  padding: 33px;
  margin-bottom: 25px;
  border-radius: 22px;
  border: 1px solid #6350a3;
  background: linear-gradient(115deg, #492782, #1e254b);
}

.hero h1 { font-size: 34px; }

.games-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel {
  padding: 23px;
  background: #151f30;
  border: 1px solid #34435c;
  border-radius: 18px;
  min-width: 0;
}

.game-icon {
  font-size: 43px;
  margin: 17px 0;
}

.game-controls {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.game-result {
  min-height: 25px;
  margin-top: 15px;
  font-weight: 900;
  color: var(--gold);
}

.coin-stage {
  width: 180px;
  height: 180px;
  margin: 22px auto;
  perspective: 1000px;
}

.coin {
  width: 180px;
  height: 180px;
  position: relative;
  transform-style: preserve-3d;
}

.coin-face {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 50%;
  backface-visibility: hidden;
  border: 9px solid #e7b849;
  background: radial-gradient(circle at 35% 25%, #fff5bd, #e9b341 65%, #a46c18);
  box-shadow:
    inset 0 0 18px #fff8,
    0 0 27px #e9b44455,
    0 12px 24px #0007;
}

.coin-face.back {
  transform: rotateY(180deg);
}

.coin-face img {
  width: 90%;
  height: 90%;
  object-fit: contain;
}

.coin-letter {
  font-size: 75px;
  font-weight: 1000;
}

.coin-blue { color: #1476ef; }
.coin-orange { color: #ed8c22; }

.ticket-list, .user-list {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.ticket-item, .user-item {
  padding: 17px;
  background: #1c2940;
  border: 1px solid #394962;
  border-radius: 13px;
  overflow-wrap: anywhere;
}

.form-grid {
  display: grid;
  gap: 12px;
  max-width: 550px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.notice {
  min-height: 20px;
  margin-top: 12px;
  color: var(--green);
}

.rules-footer {
  position: fixed;
  right: 12px;
  bottom: 10px;
  max-width: 300px;
  padding: 9px 11px;
  background: #0b1422f5;
  border: 1px solid #42506b;
  border-radius: 8px;
  color: #d6dff0;
  font-size: 11px;
  line-height: 1.5;
  z-index: 20;
}

@media (max-width: 800px) {
  #app { flex-direction: column; }

  .sidebar {
    width: 100%;
    padding: 15px;
    border-right: 0;
    border-bottom: 1px solid #27344c;
  }

  .logo { margin-bottom: 15px; }

  .nav {
    display: flex;
    flex-wrap: wrap;
  }

  .nav-button {
    width: auto;
    padding: 10px;
    font-size: 13px;
  }

  .main { padding: 20px 15px 120px; }
  .games-grid { grid-template-columns: 1fr; }
  .hero { padding: 24px; }
  .hero h1 { font-size: 27px; }
  .auth-background { padding: 30px; }
}

@media (max-width: 480px) {
  .auth-modal { padding: 18px; }
  .auth-background { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>

<body>

<!-- REGISTER / LOGIN -->
<div id="authScreen">

  <div class="auth-background">
    <div class="preview-game">🪙 COINFLIP</div>
    <div class="preview-game">🎲 LUCKY DICE</div>
    <div class="preview-game">🎰 TRIPLE SEVENS</div>
    <div class="preview-game">🎡 COLOR WHEEL</div>
    <div class="preview-game">💎 DONUT ROYALE</div>
    <div class="preview-game">🏆 ARCADE</div>
  </div>

  <div class="auth-modal">

    <div class="auth-logo">🍩 DONUT <span>ROYALE</span></div>

    <div class="auth-label" id="authStepLabel">SIGN UP</div>
    <h2 id="authTitle">Join DONUT ROYALE</h2>

    <div class="responsible-box">
      <strong>Play responsibly</strong>
      <p>
        You must be 18 or older to play.
        DONUT ROYALE uses in-game credits only.
        If playing stops being fun, take a break.
      </p>
    </div>

    <div class="bonus-box">
      🎁 Create your DONUT ROYALE account
    </div>

    <form id="authForm">

      <label class="field-title" for="authUsername">
        Minecraft username
      </label>

      <p class="field-help">
        Enter your Minecraft username to continue.
      </p>

      <input
        id="authUsername"
        type="text"
        placeholder="Minecraft username"
        maxlength="16"
        autocomplete="username"
        required
      >

      <label class="check-row">
        <input type="checkbox" id="bedrockCheck">
        <span>
          <strong>I play Bedrock Edition</strong>
          <small>
            Use your normal Minecraft username.
            This does not verify Minecraft account ownership.
          </small>
        </span>
      </label>

      <label class="field-title" for="authPassword">
        Password
      </label>

      <input
        id="authPassword"
        type="password"
        placeholder="Password (min. 8 characters)"
        minlength="8"
        autocomplete="new-password"
        required
      >

      <label class="check-row" id="ageRow">
        <input type="checkbox" id="ageCheck" required>
        <span>
          <strong>I'm 18 or older and agree to the game rules</strong>
        </span>
      </label>

      <button class="continue-btn" id="authSubmit" type="submit">
        Create Account
      </button>

    </form>

    <p id="authMessage"></p>

    <div class="auth-divider">or</div>

    <div class="auth-tabs">
      <button id="loginTab" type="button">Log In</button>
      <button id="registerTab" class="active" type="button">
        Register
      </button>
    </div>

  </div>
</div>

<!-- APP: HIDDEN UNTIL LOGGED IN -->
<div id="app" class="hidden">

  <aside class="sidebar">

    <div class="logo">🍩 DONUT <span>ROYALE</span></div>

    <nav class="nav">

      <button class="nav-button" data-page="home">
        🏠 Home
      </button>

      <button class="nav-button active" data-page="games">
        🎮 Games
      </button>

      <button class="nav-button" data-page="tickets">
        🎫 Tickets
      </button>

      <button
        class="nav-button hidden"
        data-page="admin"
        id="adminNav"
      >
        🛡️ Admin
      </button>

      <button class="nav-button" id="logoutBtn">
        🚪 Log Out
      </button>

    </nav>
  </aside>

  <main class="main">

    <div class="topbar">

      <div>
        <strong id="welcomeUser">Player</strong>
        <div class="muted small" id="roleText">PLAYER</div>
      </div>

      <div class="balance-pill">
        💰 <span id="balance">0</span>
      </div>

    </div>

    <!-- HOME -->
    <section id="page-home" class="page hidden">

      <div class="hero">
        <h1>Welcome to DONUT ROYALE 🍩</h1>
        <p>
          Play arcade minigames, manage your balance
          and create support tickets.
        </p>

        <button class="primary" onclick="showPage('games')">
          Explore Games
        </button>
      </div>

      <div class="games-grid">

        <div class="panel">
          <div class="game-icon">🪙</div>
          <h3>Coinflip</h3>
          <p class="muted">Choose Sonic or Tails.</p>
          <button class="primary" onclick="showPage('games')">
            Play Now
          </button>
        </div>

        <div class="panel">
          <div class="game-icon">🎲</div>
          <h3>Lucky Dice</h3>
          <p class="muted">Roll 5 or 6 to win.</p>
          <button class="primary" onclick="showPage('games')">
            Play Now
          </button>
        </div>

        <div class="panel">
          <div class="game-icon">🎰</div>
          <h3>Triple Sevens</h3>
          <p class="muted">Get three sevens.</p>
          <button class="primary" onclick="showPage('games')">
            Play Now
          </button>
        </div>

        <div class="panel">
          <div class="game-icon">🎡</div>
          <h3>Color Wheel</h3>
          <p class="muted">Choose red or black.</p>
          <button class="primary" onclick="showPage('games')">
            Play Now
          </button>
        </div>

      </div>
    </section>

    <!-- GAMES -->
    <section id="page-games" class="page">

      <h1>🎮 Arcade Games</h1>

      <p class="muted">
        Choose your game. Maximum bet: 3B.
      </p>

      <div class="games-grid">

        <!-- COINFLIP -->
        <div class="panel">

          <h2>🪙 Coinflip</h2>
          <p class="muted">Sonic vs. Tails</p>

          <div class="coin-stage">
            <div class="coin" id="coinVisual">

              <div class="coin-face front">
                <img
                  src="/coin-heads.png"
                  alt="Sonic"
                  onerror="this.style.display='none';this.nextElementSibling.style.display='block'"
                >
                <span class="coin-letter coin-blue" style="display:none">
                  S
                </span>
              </div>

              <div class="coin-face back">
                <img
                  src="/coin-tails.png"
                  alt="Tails"
                  onerror="this.style.display='none';this.nextElementSibling.style.display='block'"
                >
                <span class="coin-letter coin-orange" style="display:none">
                  T
                </span>
              </div>

            </div>
          </div>

          <div class="game-controls">

            <select id="coinChoice">
              <option value="heads">Sonic (Heads)</option>
              <option value="tails">Tails (Tails)</option>
            </select>

            <input
              id="coinBet"
              type="number"
              min="1"
              max="3000000000"
              placeholder="Bet amount"
            >

            <button class="primary" onclick="playGame('coinflip')">
              Flip Coin
            </button>

          </div>

          <div class="game-result" id="coinResult"></div>

        </div>

        <!-- DICE -->
        <div class="panel">

          <h2>🎲 Lucky Dice</h2>

          <p class="muted">Roll 5 or 6 to win.</p>

          <div class="game-icon" id="diceVisual">🎲</div>

          <div class="game-controls">

            <input
              id="diceBet"
              type="number"
              min="1"
              max="3000000000"
              placeholder="Bet amount"
            >

            <button class="primary" onclick="playGame('dice')">
              Roll Dice
            </button>

          </div>

          <div class="game-result" id="diceResult"></div>

        </div>

        <!-- SLOTS -->
        <div class="panel">

          <h2>🎰 Triple Sevens</h2>

          <p class="muted">Match three sevens to win.</p>

          <div class="game-icon" id="slotsVisual">
            7️⃣ 7️⃣ 7️⃣
          </div>

          <div class="game-controls">

            <input
              id="slotsBet"
              type="number"
              min="1"
              max="3000000000"
              placeholder="Bet amount"
            >

            <button class="primary" onclick="playGame('slots')">
              Spin Slots
            </button>

          </div>

          <div class="game-result" id="slotsResult"></div>

        </div>

        <!-- WHEEL -->
        <div class="panel">

          <h2>🎡 Color Wheel</h2>

          <p class="muted">Choose red or black.</p>

          <div class="game-icon" id="wheelVisual">🎡</div>

          <div class="game-controls">

            <select id="wheelChoice">
              <option value="red">🔴 Red</option>
              <option value="black">⚫ Black</option>
            </select>

            <input
              id="wheelBet"
              type="number"
              min="1"
              max="3000000000"
              placeholder="Bet amount"
            >

            <button class="primary" onclick="playGame('wheel')">
              Spin Wheel
            </button>

          </div>

          <div class="game-result" id="wheelResult"></div>

        </div>

      </div>
    </section>

    <!-- TICKETS -->
    <section id="page-tickets" class="page hidden">

      <h1>🎫 Tickets</h1>

      <p class="muted">
        Deposit, withdraw or contact support.
      </p>

      <div class="panel">

        <form id="ticketForm" class="form-grid">

          <select id="ticketKind">
            <option value="deposit">Deposit</option>
            <option value="withdraw">Withdraw</option>
            <option value="support">Support</option>
          </select>

          <input
            id="ticketAmount"
            type="number"
            min="0"
            placeholder="Amount"
          >

          <textarea
            id="ticketMessage"
            rows="4"
            maxlength="1000"
            placeholder="Your message"
          ></textarea>

          <button class="primary" type="submit">
            Create Ticket
          </button>

        </form>

        <div class="notice" id="ticketStatus"></div>

      </div>

      <h2 style="margin-top:30px">Open Tickets</h2>

      <div id="ticketList" class="ticket-list"></div>

    </section>

    <!-- ADMIN -->
    <section id="page-admin" class="page hidden">

      <h1>🛡️ Admin Panel</h1>

      <p class="muted">
        Manage tickets and player roles.
      </p>

      <div class="panel">

        <h2>Open Tickets</h2>

        <div id="adminTicketList" class="ticket-list"></div>

      </div>

      <div class="panel" style="margin-top:20px">

        <h2>Players</h2>

        <div id="userList" class="user-list"></div>

      </div>

    </section>

  </main>
</div>

<!-- VISIBLE GAME RULES -->
<div class="rules-footer hidden" id="rulesFooter">
  Game rules: 10% win chance, 90% loss chance.
  Wins return 2× the bet. All-in bets always lose.
  Maximum bet: 3B.
</div>

<script>
const $ = id => document.getElementById(id);

let me = null;
let authMode = "register";
let busy = false;

function formatMoney(value) {
  const n = Number(value) || 0;
  const abs = Math.abs(n);

  for (const [size, suffix] of [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"]
  ]) {
    if (abs >= size) {
      return Number((n / size).toFixed(1)) + suffix;
    }
  }

  return String(n);
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function api(path, method = "GET", body = null) {
  const options = {
    method,
    credentials: "same-origin",
    headers: {}
  };

  if (body !== null) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong");
  }

  return data;
}

function setAuthMode(mode) {
  authMode = mode;

  const registering = mode === "register";

  $("authStepLabel").textContent =
    registering ? "SIGN UP" : "SIGN IN";

  $("authTitle").textContent =
    registering ? "Join DONUT ROYALE" : "Welcome Back";

  $("authSubmit").textContent =
    registering ? "Create Account" : "Log In";

  $("authPassword").autocomplete =
    registering ? "new-password" : "current-password";

  $("ageRow").classList.toggle("hidden", !registering);
  $("ageCheck").required = registering;

  $("loginTab").classList.toggle("active", !registering);
  $("registerTab").classList.toggle("active", registering);

  $("authMessage").textContent = "";
}

$("loginTab").onclick = () => setAuthMode("login");
$("registerTab").onclick = () => setAuthMode("register");

$("authForm").onsubmit = async event => {
  event.preventDefault();

  const username = $("authUsername").value.trim();
  const password = $("authPassword").value;

  $("authMessage").textContent = "";
  $("authSubmit").disabled = true;

  try {
    await api("/api/" + authMode, "POST", {
      username,
      password
    });

    $("authPassword").value = "";

    await refreshMe();

    if (me) {
      // Immediately open minigames after registration or login.
      showPage("games");
    }

  } catch (error) {
    $("authMessage").textContent = error.message;

  } finally {
    $("authSubmit").disabled = false;
  }
};

async function refreshMe() {
  const data = await api("/api/me");
  me = data.user;

  if (!me) {
    $("authScreen").classList.remove("hidden");
    $("app").classList.add("hidden");
    $("rulesFooter").classList.add("hidden");
    return;
  }

  $("authScreen").classList.add("hidden");
  $("app").classList.remove("hidden");
  $("rulesFooter").classList.remove("hidden");

  $("welcomeUser").textContent = "👤 " + me.username;
  $("roleText").textContent = me.role.toUpperCase();
  $("balance").textContent = formatMoney(me.balance);

  const isStaff = ["owner", "admin"].includes(me.role);

  $("adminNav").classList.toggle("hidden", !isStaff);

  if (
    !isStaff
    && !$("page-admin").classList.contains("hidden")
  ) {
    showPage("games");
  }
}

function showPage(page) {
  if (!me) return;

  if (
    page === "admin"
    && !["owner", "admin"].includes(me.role)
  ) {
    return;
  }

  document.querySelectorAll(".page").forEach(element => {
    element.classList.add("hidden");
  });

  $("page-" + page).classList.remove("hidden");

  document.querySelectorAll(".nav-button[data-page]").forEach(button => {
    button.classList.toggle(
      "active",
      button.dataset.page === page
    );
  });

  if (page === "tickets") loadTickets();
  if (page === "admin") loadAdmin();
}

document.querySelectorAll(".nav-button[data-page]").forEach(button => {
  button.onclick = () => showPage(button.dataset.page);
});

$("logoutBtn").onclick = async () => {
  try {
    await api("/api/logout", "POST", {});
  } catch (error) {
    console.error(error);
  }

  me = null;
  await refreshMe();
  setAuthMode("login");
};

async function playGame(game) {
  if (!me || busy) return;

  const bet = Number($(game + "Bet").value);

  if (
    !Number.isSafeInteger(bet)
    || bet < 1
    || bet > 3_000_000_000
  ) {
    alert("Enter a bet between 1 and 3B.");
    return;
  }

  if (bet > me.balance) {
    alert("Not enough balance.");
    return;
  }

  if (bet === me.balance) {
    const confirmed = confirm(
      "WARNING: All-in bets always lose. " +
      "You will lose your entire balance. Continue?"
    );

    if (!confirmed) return;
  }

  const resultIds = {
    coinflip: "coinResult",
    dice: "diceResult",
    slots: "slotsResult",
    wheel: "wheelResult"
  };

  const resultElement = $(resultIds[game]);
  resultElement.textContent = "Playing...";

  let choice = null;

  if (game === "coinflip") {
    choice = $("coinChoice").value;
  }

  if (game === "wheel") {
    choice = $("wheelChoice").value;
  }

  busy = true;

  try {
    const data = await api("/api/game", "POST", {
      game,
      amount: bet,
      choice
    });

    if (game === "coinflip") {
      const coin = $("coinVisual");

      const end = data.result === "heads" ? 1800 : 1980;

      coin.animate([
        { transform: "rotateY(0deg) translateY(0)" },
        { transform: "rotateY(900deg) translateY(-22px)" },
        { transform: `rotateY(${end}deg) translateY(0)` }
      ], {
        duration: 1600,
        easing: "ease-out"
      });

      coin.style.transform =
        `rotateY(${data.result === "heads" ? 0 : 180}deg)`;
    }

    if (game === "dice") {
      $("diceVisual").textContent = "🎲 " + data.roll;
    }

    if (game === "slots") {
      $("slotsVisual").textContent = data.reels.join(" ");
    }

    if (game === "wheel") {
      $("wheelVisual").textContent =
        data.result === "red" ? "🔴" : "⚫";
    }

    const details = {
      coinflip: data.result,
      dice: "Rolled " + data.roll,
      slots: data.reels?.join(" ") || "",
      wheel: data.result
    }[game];

    resultElement.textContent =
      (data.win ? "🎉 YOU WIN! +" : "❌ YOU LOSE! ") +
      formatMoney(Math.abs(data.profit)) +
      " — " + details;

    await refreshMe();

  } catch (error) {
    resultElement.textContent = error.message;

  } finally {
    busy = false;
  }
}

$("ticketKind").onchange = () => {
  const support = $("ticketKind").value === "support";

  $("ticketAmount").disabled = support;
  $("ticketAmount").value = support ? "0" : "";
};

$("ticketForm").onsubmit = async event => {
  event.preventDefault();

  const kind = $("ticketKind").value;
  const amount =
    kind === "support" ? 0 : Number($("ticketAmount").value);

  const message = $("ticketMessage").value.trim();

  if (
    !Number.isSafeInteger(amount)
    || amount < 0
    || (kind !== "support" && amount < 1)
  ) {
    $("ticketStatus").textContent = "Invalid amount.";
    return;
  }

  if (kind === "withdraw" && amount > me.balance) {
    $("ticketStatus").textContent =
      "Not enough balance for withdrawal.";
    return;
  }

  try {
    await api("/api/tickets", "POST", {
      kind,
      amount,
      message
    });

    $("ticketStatus").textContent =
      "Ticket created successfully.";

    $("ticketMessage").value = "";
    $("ticketAmount").value =
      kind === "support" ? "0" : "";

    await loadTickets();

  } catch (error) {
    $("ticketStatus").textContent = error.message;
  }
};

async function loadTickets() {
  try {
    const data = await api("/api/tickets");

    const mine = data.tickets.filter(
      ticket => ticket.user_id === me.id
    );

    $("ticketList").innerHTML = mine.length
      ? mine.map(ticket => `
        <div class="ticket-item">
          <strong>
            #${ticket.id} —
            ${escapeHTML(ticket.kind.toUpperCase())}
          </strong>

          <p class="muted small">
            Amount: ${formatMoney(ticket.amount)}
          </p>

          <p>${escapeHTML(ticket.message)}</p>

          <span class="muted small">Status: OPEN</span>
        </div>
      `).join("")
      : '<p class="muted">No open tickets.</p>';

  } catch (error) {
    $("ticketList").textContent = error.message;
  }
}

async function loadAdmin() {
  if (!me || !["owner", "admin"].includes(me.role)) return;

  try {
    const [ticketData, userData] = await Promise.all([
      api("/api/tickets"),
      api("/api/users")
    ]);

    $("adminTicketList").innerHTML = ticketData.tickets.length
      ? ticketData.tickets.map(ticket => `
        <div class="ticket-item">

          <strong>
            #${ticket.id} —
            ${escapeHTML(ticket.username)}
          </strong>

          <p class="muted small">
            ${escapeHTML(ticket.kind.toUpperCase())}
            · ${formatMoney(ticket.amount)}
          </p>

          <p>${escapeHTML(ticket.message)}</p>

          <textarea
            id="reply-${ticket.id}"
            rows="2"
            placeholder="Reply to player"
          ></textarea>

          <div class="actions">

            <button
              class="success"
              onclick="reviewTicket(${ticket.id}, 'approved')"
            >
              Approve
            </button>

            <button
              class="danger"
              onclick="reviewTicket(${ticket.id}, 'rejected')"
            >
              Reject
            </button>

            <button
              class="secondary"
              onclick="reviewTicket(${ticket.id}, 'closed')"
            >
              Close
            </button>

          </div>
        </div>
      `).join("")
      : '<p class="muted">No open tickets.</p>';

    $("userList").innerHTML = userData.users.length
      ? userData.users.map(player => {
        const canChange =
          me.role === "owner"
          && player.role !== "owner";

        return `
          <div class="user-item">

            <strong>${escapeHTML(player.username)}</strong>

            <p class="muted small">
              ${escapeHTML(player.role.toUpperCase())}
              · ${formatMoney(player.balance)}
            </p>

            ${canChange ? `
              <div class="actions">

                <button
                  class="success"
                  onclick="changeRole(${player.id}, 'admin')"
                >
                  Make Admin
                </button>

                <button
                  class="secondary"
                  onclick="changeRole(${player.id}, 'player')"
                >
                  Remove Admin
                </button>

              </div>
            ` : ""}

          </div>
        `;
      }).join("")
      : '<p class="muted">No players.</p>';

  } catch (error) {
    $("adminTicketList").textContent = error.message;
  }
}

async function reviewTicket(id, status) {
  const response = $("reply-" + id)?.value.trim() || "";

  if (!confirm("Confirm ticket action: " + status + "?")) {
    return;
  }

  try {
    await api("/api/ticket/review", "POST", {
      id,
      status,
      response
    });

    await refreshMe();
    await loadAdmin();

  } catch (error) {
    alert(error.message);
  }
}

async function changeRole(id, role) {
  if (!confirm("Change player role to " + role + "?")) {
    return;
  }

  try {
    await api("/api/role", "POST", { id, role });
    await loadAdmin();

  } catch (error) {
    alert(error.message);
  }
}

(async function start() {
  setAuthMode("register");

  try {
    await refreshMe();

    if (me) {
      showPage("games");
    }

  } catch (error) {
    $("authScreen").classList.remove("hidden");
    $("app").classList.add("hidden");
    $("authMessage").textContent =
      "Cannot connect to server. Please try again.";
  }
})();
</script>

</body>
</html>
