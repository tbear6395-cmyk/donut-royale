'use strict';

const $ = id => document.getElementById(id);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const format = n => Number(n).toLocaleString('en-US');

let me = null;
let authMode = 'login';
let side = 'heads';
let color = 'red';
let playing = false;
let coinAngle = 0;
let wheelAngle = 0;
let diceAngles = {x:-18,y:-24};
let toastTimeout;

function toast(message) {
  $('toast').textContent = String(message);
  $('toast').style.display = 'block';
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    $('toast').style.display = 'none';
  }, 4300);
}

async function api(path, data) {
  const r = await fetch('/api/' + path, {
    method: data === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type':'application/json'},
    body: data === undefined ? undefined : JSON.stringify(data)
  });

  let x;
  try {
    x = await r.json();
  } catch {
    throw Error('Server response is invalid. Check Render logs.');
  }

  if (!r.ok) throw Error(x.error || 'Request failed (' + r.status + ')');
  return x;
}

function parseAmount(raw) {
  const value = String(raw).trim().toUpperCase().replace(/\s/g,'');
  const match = /^(\d+(?:[.,]\d+)?)([KMB]?)$/.exec(value);

  if (!match) throw Error('Enter an amount like 100, 10K or 1M.');

  const multiplier = {
    '':1, K:1000, M:1000000, B:1000000000
  }[match[2]];

  const n = Number(match[1].replace(',','.')) * multiplier;

  if (!Number.isSafeInteger(n) || n < 0) {
    throw Error('Amount must be a whole number.');
  }

  return n;
}

function el(tag,text) {
  const n = document.createElement(tag);
  n.textContent = String(text);
  return n;
}

function action(label,fn) {
  const b = el('button',label);
  b.type = 'button';
  b.onclick = fn;
  return b;
}

function item(parent,...children) {
  const d = document.createElement('div');
  d.className = 'item';
  d.append(...children);
  parent.append(d);
  return d;
}

/* LOGIN */

function setMode(mode) {
  authMode = mode;
  $('loginTab').classList.toggle('selected',mode === 'login');
  $('registerTab').classList.toggle('selected',mode === 'register');
  $('authSubmit').textContent = mode === 'login' ? 'LOG IN' : 'REGISTER';
}

$('loginTab').onclick = () => setMode('login');
$('registerTab').onclick = () => setMode('register');

$('authForm').onsubmit = async event => {
  event.preventDefault();

  try {
    await api(authMode,{
      username:$('username').value.trim(),
      password:$('password').value
    });

    $('password').value = '';
    await refresh();
    toast('Welcome to DONUT ROYALE!');
  } catch(e) {
    toast(e.message);
  }
};

async function refresh() {
  const r = await api('me');
  me = r.user || null;

  $('auth').hidden = !!me;
  $('dashboard').hidden = !me;
  $('account').replaceChildren();

  if (!me) {
    $('topBalance').textContent = '0';
    $('adminNav').hidden = true;
    return;
  }

  $('account').append(
    el('span',me.username),
    action('LOG OUT',async () => {
      if (playing) return;
      try {
        await api('logout',{});
        closeGame();
        await refresh();
      } catch(e) {
        toast(e.message);
      }
    })
  );

  $('balance').textContent = format(me.balance);
  $('topBalance').textContent = format(me.balance);
  $('displayName').textContent = me.username;
  $('role').textContent = me.role.toUpperCase();

  const admin = ['admin','owner'].includes(me.role);
  $('admin').hidden = !admin;
  $('adminNav').hidden = !admin;

  try {
    await loadTickets();
    if (admin) await loadUsers();
  } catch(e) {
    toast(e.message);
  }
}

/* OPEN GAME */

function openGame(game) {
  if (!me) {
    $('auth').scrollIntoView({behavior:'smooth'});
    toast('Log in to play.');
    return;
  }

  if (playing) return;
  if (!['coinflip','dice','slots','wheel'].includes(game)) return;

  document.querySelectorAll('.game-screen').forEach(s => {
    s.hidden = true;
  });

  $('screen-' + game).hidden = false;
  $('gameOverlay').hidden = false;
  document.body.style.overflow = 'hidden';
  $('closeGame').focus();
}

function closeGame() {
  if (playing) return;
  $('gameOverlay').hidden = true;
  document.body.style.overflow = '';
}

document.querySelectorAll('[data-game]').forEach(b => {
  b.addEventListener('click',() => openGame(b.dataset.game));
});

$('closeGame').onclick = closeGame;

$('gameOverlay').onclick = e => {
  if (e.target === $('gameOverlay')) closeGame();
};

document.addEventListener('keydown',e => {
  if (e.key === 'Escape') closeGame();
});

$('heroPlay').onclick = () => {
  document.querySelector(me ? '.game-grid' : '#auth')
    .scrollIntoView({behavior:'smooth'});
};

document.querySelectorAll('.side').forEach(b => {
  b.onclick = () => {
    side = b.dataset.side;
    document.querySelectorAll('.side').forEach(x => {
      x.classList.toggle('selected',x === b);
    });
  };
});

document.querySelectorAll('.wheel-choice').forEach(b => {
  b.onclick = () => {
    color = b.dataset.color;
    document.querySelectorAll('.wheel-choice').forEach(x => {
      x.classList.toggle('selected',x === b);
    });
  };
});

document.querySelectorAll('.quick-bets').forEach(group => {
  group.querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      $(group.dataset.input).value = b.dataset.value;
    };
  });
});

/* COINFLIP ANIMATION */

async function animateCoin(promise) {
  const coin = $('coinVisual');
  const result = await promise;

  if (!['heads','tails'].includes(result.result)) {
    throw Error('Invalid coin result.');
  }

  const target = result.result === 'heads' ? 0 : 180;
  const end = coinAngle + 1800 +
    ((target - (coinAngle % 360) + 360) % 360);

  const animation = coin.animate([
    {transform:`rotateY(${coinAngle}deg)`},
    {transform:`rotateY(${end}deg)`}
  ],{
    duration:1900,
    easing:'cubic-bezier(.16,.73,.19,1)'
  });

  await animation.finished;
  coinAngle = end;
  coin.style.transform = `rotateY(${coinAngle}deg)`;

  return result;
}

/* 3D DICE ANIMATION */

async function animateDice(promise) {
  const cube = $('diceVisual');
  const result = await promise;
  const face = Number(result.roll);

  if (!Number.isInteger(face) || face < 1 || face > 6) {
    throw Error('Invalid dice result.');
  }

  const orientations = {
    1:[0,0],
    2:[0,-90],
    3:[-90,0],
    4:[90,0],
    5:[0,90],
    6:[0,180]
  };

  const [tx,ty] = orientations[face];

  const from =
    `rotateX(${diceAngles.x}deg) rotateY(${diceAngles.y}deg)`;

  const toX = tx + 1440;
  const toY = ty + 1800;

  const animation = cube.animate([
    {transform:from},
    {transform:`rotateX(${toX}deg) rotateY(${toY}deg)`}
  ],{
    duration:1600,
    easing:'cubic-bezier(.2,.75,.2,1)'
  });

  await animation.finished;

  diceAngles = {x:tx,y:ty};
  cube.style.transform = `rotateX(${tx}deg) rotateY(${ty}deg)`;

  return result;
}

/* SLOTS ANIMATION */

async function animateSlots(promise) {
  const reels = [...$('slotsVisual').querySelectorAll('.reel')];
  const symbols = ['7','🍒','💎','⭐'];
  const timers = [];

  reels.forEach((reel,i) => {
    reel.classList.add('rolling');

    timers[i] = setInterval(() => {
      reel.querySelector('span').textContent =
        symbols[Math.floor(Math.random() * symbols.length)];
    },70 + i * 15);
  });

  try {
    const result = await promise;

    if (!Array.isArray(result.reels) || result.reels.length !== 3) {
      throw Error('Invalid slots result.');
    }

    for (let i = 0; i < 3; i++) {
      await sleep(i === 0 ? 650 : 380);

      clearInterval(timers[i]);
      reels[i].classList.remove('rolling');
      reels[i].querySelector('span').textContent =
        String(result.reels[i]);
    }

    return result;
  } finally {
    timers.forEach(clearInterval);
    reels.forEach(x => x.classList.remove('rolling'));
  }
}

/* ROULETTE ANIMATION */

async function animateWheel(promise) {
  const wheel = $('wheelVisual');
  const result = await promise;

  if (!['red','black'].includes(result.result)) {
    throw Error('Invalid wheel result.');
  }

  const target = result.result === 'red' ? 0 : 30;
  const offset = (target - (wheelAngle % 360) + 360) % 360;
  const end = wheelAngle + 2160 + offset;

  const animation = wheel.animate([
    {transform:`rotate(${wheelAngle}deg)`},
    {transform:`rotate(${end}deg)`}
  ],{
    duration:2700,
    easing:'cubic-bezier(.12,.72,.15,1)'
  });

  await animation.finished;

  wheelAngle = end;
  wheel.style.transform = `rotate(${wheelAngle}deg)`;

  return result;
}

/* PLAY GAME */

async function play(game,inputId,resultId,buttonId,extra = {}) {
  if (playing) return;

  let amount;

  try {
    amount = parseAmount($(inputId).value);
  } catch(e) {
    toast(e.message);
    return;
  }

  if (amount < 1 || amount > 1000000) {
    toast('Bet must be between 1 and 1M.');
    return;
  }

  if (!me || amount > Number(me.balance)) {
    toast('Not enough demo credits.');
    return;
  }

  playing = true;
  const button = $(buttonId);
  button.disabled = true;
  $(resultId).textContent = 'Spinning...';

  try {
    const request = api('game',{game,amount,...extra});

    const animations = {
      coinflip:animateCoin,
      dice:animateDice,
      slots:animateSlots,
      wheel:animateWheel
    };

    const result = await animations[game](request);

    let prefix = '';

    if (game === 'coinflip') {
      prefix = (result.result === 'heads'
        ? '👑 HEADS'
        : '🍩 TAILS') + ' · ';
    }

    if (game === 'dice') {
      prefix = '🎲 ' + result.roll + ' · ';
    }

    if (game === 'wheel') {
      prefix = (result.result === 'red'
        ? '🔴 RED'
        : '⚫ BLACK') + ' · ';
    }

    $(resultId).textContent = prefix + (
      result.win
        ? '✨ YOU WIN! +' + format(result.profit)
        : 'HOUSE WINS · -' + format(amount)
    );

    try {
      await refresh();
    } catch(e) {
      toast('Balance refresh failed: ' + e.message);
    }

  } catch(e) {
    $(resultId).textContent = '';
    toast(e.message);
  } finally {
    playing = false;
    button.disabled = false;
  }
}

$('flip').onclick = () =>
  play('coinflip','bet','gameResult','flip',{choice:side});

$('dicePlay').onclick = () =>
  play('dice','diceBet','diceResult','dicePlay');

$('slotsPlay').onclick = () =>
  play('slots','slotsBet','slotsResult','slotsPlay');

$('wheelPlay').onclick = () =>
  play('wheel','wheelBet','wheelResult','wheelPlay',{choice:color});

/* TICKETS */

function updateTicketForm() {
  const kind = $('kind').value;

  $('amount').disabled = kind === 'support';
  $('payInfo').hidden = kind !== 'deposit';

  if (kind === 'deposit') {
    try {
      $('payCommand').textContent =
        '/pay matejicekjepica ' + parseAmount($('amount').value);
    } catch {
      $('payCommand').textContent =
        '/pay matejicekjepica AMOUNT';
    }
  }
}

$('kind').onchange = updateTicketForm;
$('amount').oninput = updateTicketForm;

$('ticketForm').onsubmit = async e => {
  e.preventDefault();

  let amount = 0;

  try {
    if ($('kind').value !== 'support') {
      amount = parseAmount($('amount').value);

      if (amount < 1 || amount > 1000000000) {
        throw Error('Ticket amount must be between 1 and 1B.');
      }
    }

    await api('tickets',{
      kind:$('kind').value,
      amount,
      message:$('message').value.trim()
    });

    $('message').value = '';
    toast('Ticket created.');
    await loadTickets();
  } catch(err) {
    toast(err.message);
  }
};

async function loadTickets() {
  const r = await api('tickets');
  const tickets = r.tickets || [];

  $('tickets').replaceChildren();
  $('adminTickets').replaceChildren();

  const own = tickets.filter(t =>
    Number(t.user_id) === Number(me.id)
  );

  if (!own.length) {
    $('tickets').append(el('p','No tickets yet.'));
  }

  own.forEach(t => {
    const d = item(
      $('tickets'),
      el('strong','#' + t.id + ' · ' + t.kind.toUpperCase() + ' · ' + t.status),
      el('small','Amount: ' + format(t.amount) + ' · ' + (t.created || '')),
      el('p',t.message || 'No message')
    );

    if (t.response) d.append(el('p','Admin: ' + t.response));
  });

  if (!['admin','owner'].includes(me.role)) return;

  tickets.forEach(t => {
    const d = item(
      $('adminTickets'),
      el('strong','#' + t.id + ' · ' + t.username + ' · ' + t.kind + ' · ' + t.status),
      el('small','Amount: ' + format(t.amount)),
      el('p',t.message || 'No message')
    );

    if (t.response) d.append(el('p','Admin: ' + t.response));
    if (t.status !== 'open') return;

    ['approved','rejected','closed'].forEach(status => {
      if (status === 'approved' && t.kind === 'support') return;

      d.append(action(status.toUpperCase(),async () => {
        if (status === 'approved' &&
            !confirm('Have you independently verified this request?')) {
          return;
        }

        const response = prompt('Admin response (optional):');
        if (response === null) return;

        try {
          await api('ticket/review',{
            id:t.id,
            status,
            response
          });
          await refresh();
          toast('Ticket updated.');
        } catch(e) {
          toast(e.message);
        }
      }));
    });
  });
}

/* ADMIN ROLES */

async function loadUsers() {
  const r = await api('users');
  $('users').replaceChildren();

  (r.users || []).forEach(u => {
    const d = item(
      $('users'),
      el('strong',u.username + ' · ' + u.role),
      el('small','Balance: ' + format(u.balance))
    );

    if (me.role !== 'owner' || u.role === 'owner') return;

    const newRole = u.role === 'admin' ? 'player' : 'admin';

    d.append(action(
      u.role === 'admin' ? 'REMOVE ADMIN' : 'MAKE ADMIN',
      async () => {
        if (!confirm('Change ' + u.username + ' to ' + newRole + '?')) {
          return;
        }

        try {
          await api('role',{id:u.id,role:newRole});
          await refresh();
          toast('Role updated.');
        } catch(e) {
          toast(e.message);
        }
      }
    ));
  });
}

updateTicketForm();
refresh().catch(e => toast(e.message));
