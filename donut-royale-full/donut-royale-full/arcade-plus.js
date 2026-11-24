import {Chess} from './chess-rules.js';

const byId = id => document.getElementById(id);
const symbols = {w:"♙♘♗♖♕♔", b:"♟♞♝♜♛♚"};
const pieces = "pnbrqk";
const names = ["pawn","knight","bishop","rook","queen","king"];
const game = new Chess();
let selected=null, promotion=null, started=false;
let account=null, hooks=null, match=null, lastMatch=null, busy=false, synced=false;
let revision=0;
let paint3D=null, use3D=true, lastMoveError="";
const activeBet=()=>match?.outcome==="active";
const credit=n=>Number(n).toLocaleString("en-US");
async function request(path,body){
  const options=body?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:{};
  const response=await fetch("/api/chess/"+path,{...options,cache:"no-store"});
  const data=await response.json();
  if(!response.ok)throw Error(data.error||"Could not reach the chess table");
  return data;
}
function applyState(data,restore){
  synced=true;lastMatch=data.match?.id||null;hooks.balance(data.balance);
  if(!restore&&!match&&data.match?.outcome!=="active")return;
  if(!data.match){match=null;return;}
  match=data.match;
  selected=null;promotion=null;game.reset();
  for(const uci of match.moves)game.move({from:uci.slice(0,2),to:uci.slice(2,4),promotion:uci[4]});
}
async function loadMatch(restore=false){
  const owner=account, version=++revision;
  try{const state=await request("state");if(owner===account&&version===revision)applyState(state,restore);}
  catch{if(owner===account&&version===revision){synced=false;lastMoveError="Could not sync the stake. Reopen Chess to retry.";}}
  if(owner===account&&version===revision)renderChess();
}
async function submit(action,body){
  if(busy)return;
  const owner=account, version=++revision;busy=true;lastMoveError="";renderChess();
  try{const data=await request(action,body);if(owner===account&&version===revision)applyState(data,true);}
  catch(error){if(owner===account){if(action==="move")game.undo();
    lastMoveError=error.message;await loadMatch(true);}}
  finally{if(owner===account){busy=false;renderChess();}}
}
function pick(square){
  if(!square||busy||!synced||!activeBet()||promotion||game.turn()!=="w"||game.isGameOver()||(match&&!activeBet()))return;
  const move=selected&&game.moves({square:selected,verbose:true}).find(m=>m.to===square);
  if(move?.promotion){promotion={from:selected,to:square};renderChess();return;}
  if(move){play(selected,square);return;}
  selected=selected!==square&&game.get(square)?.color==="w"?square:null;renderChess();
}


function positionStatus(){
  if(match&&match.outcome!=="active")return ({win:"Checkmate · You win",lose:"Match lost",draw:"Draw"})[match.outcome];
  if(busy)return game.turn()==="b"?"Waiting for the bot’s reply…":"Processing match…";
  if(game.isCheckmate())return game.turn()==="w"?"Checkmate · Stockfish wins":"Checkmate · You win";
  if(game.isStalemate())return "Draw · Stalemate";
  if(game.isThreefoldRepetition())return "Draw · Threefold repetition";
  if(game.isInsufficientMaterial())return "Draw · Insufficient material";
  if(game.isDraw())return "Draw · Fifty-move rule";
  if(!activeBet())return synced?"Enter your stake to start a match.":"Loading match…";
  if(promotion)return "Choose a promotion piece.";
  return game.turn()==="w"?(game.isCheck()?"Your king is in check":"Your move · White"):"Stockfish is thinking…";
}
function renderChess(){
  const board=byId("chessBoard"), moves=selected?game.moves({square:selected,verbose:true}):[];
  drawSquares(board,game,selected,moves);
  const spatial=Boolean(paint3D&&use3D);
  byId("chessScene").hidden=!spatial;board.hidden=spatial;
  byId("chessView").hidden=!paint3D;byId("chessView").textContent=spatial?"Use 2D board":"Use 3D board";
  if(spatial)paint3D(game.board(),selected,moves);
  byId("chessNew").disabled=busy;byId("chessNew").hidden=!activeBet();
  byId("chessStake").disabled=busy||activeBet();
  byId("chessBet").disabled=busy||!synced||activeBet();
  let message="";
  if(match){const payout=match.outcome==="win"?2*match.stake:match.outcome==="draw"?match.stake:0;
    message=activeBet()?"In play: "+credit(match.stake)+" credits":"Stake: "+credit(match.stake)+" · Returned: "+credit(payout);}
  byId("chessBank").textContent=lastMoveError||message;
  byId("chessTurn").textContent=positionStatus();
  byId("chessPromotion").hidden=!promotion;
  byId("chessMoves").textContent=game.history().map((s,i)=>i%2?s:(i/2+1)+". "+s).join(" ");
}
function drawSquares(board,position,selected,moves,readOnly=false){
  const buttons=[];
  for(const [row,rank] of position.board().entries())for(const [col,piece] of rank.entries()){
    const square="abcdefgh"[col]+(8-row),button=document.createElement("button");
    if(readOnly)button.disabled=true;
    button.type="button";button.dataset.square=square;
    button.classList.toggle("dark",Boolean((row+col)%2));
    button.classList.toggle("selected",square===selected);
    button.classList.toggle("legal",moves.some(m=>m.to===square));
    button.setAttribute("aria-label",square+(piece?" "+(piece.color==="w"?"white ":"black ")+names[pieces.indexOf(piece.type)]:""));
    if(piece){button.textContent=symbols[piece.color][pieces.indexOf(piece.type)];button.classList.toggle("white-piece",piece.color==="w");}
    if(col===0||row===7){const mark=document.createElement("small");mark.textContent=(col===0?8-row:"")+(row===7?"abcdefgh"[col]:"");button.append(mark);}
    buttons.push(button);
  }
  board.replaceChildren(...buttons);
}
function play(from,to,promote){
  if(activeBet()){
    if(busy||!synced)return;
    game.move({from,to,promotion:promote});
    selected=null;promotion=null;
    void submit("move",{id:match.id,ply:match.moves.length,move:from+to+(promote||"")});return;
  }

}
export function openChess(options){
  const changed=account!==options.account;
  hooks=options;account=options.account;
  if(changed){match=null;lastMatch=null;busy=false;synced=false;lastMoveError="";selected=null;promotion=null;game.reset();}
  if(!busy)void loadMatch(changed);
  if(started){renderChess();return;}
  started=true;
  import("./chess-3d.js").then(({createBoard})=>{
    paint3D=createBoard(byId("chessScene"),pick);renderChess();
  }).catch(()=>{use3D=false;renderChess();});
  byId("chessView").onclick=()=>{use3D=!use3D;renderChess();};
  byId("chessBoard").onclick=e=>pick(e.target.closest("button")?.dataset.square);
  byId("chessBet").onclick=()=>{
    if(busy||!synced||activeBet())return;
    let stake;try{stake=hooks.parseStake(byId("chessStake").value);}catch{}
    if(!Number.isSafeInteger(stake)||stake<1||stake>3e9){lastMoveError="Enter a stake from 1 to 3B credits.";renderChess();return;}
    if(confirm("Start a new chess match for "+credit(stake)+" credits? A loss or resignation loses the stake.")){
      void submit("start",{stake,previous:lastMatch});
    }
  };
  byId("chessPromotion").querySelector("button").onclick=()=>{if(promotion)play(promotion.from,promotion.to,byId("chessPromotion").querySelector("select").value);};
  byId("chessNew").onclick=()=>{
    if(!busy&&activeBet()&&confirm("Resign and lose your stake of "+credit(match.stake)+" credits?"))
      void submit("resign",{id:match.id,ply:match.moves.length});
  };
  renderChess();
}

const titles={chess:"Chess",wheel:"Roulette",casebattle:"Case Battles",blackjack:"Blackjack"};
let watchSession=0;
export function watch(kind,art){
  const session=++watchSession, select=byId("watchTable"),stage=byId("watchStage");
  let tables=[];
  const visible=()=>session===watchSession&&!byId("screen-spectate").hidden&&!byId("gameOverlay").hidden;
  byId("watchTitle").textContent="Spectate · "+titles[kind];
  byId("watchPicker").hidden=true;stage.textContent="Loading tables…";select.replaceChildren();
  let mounted=null,fields={},info=null,phase=null;
  function mount(table){
    const selector={blackjack:".bj-casino-scene",wheel:".roulette-table",casebattle:".cb-arena"}[kind];
    const scene=kind==="chess"?document.createElement("div"):byId("screen-"+kind).querySelector(selector).cloneNode(true);
    fields={};
    if(kind==="chess"){scene.className="watch-board";fields.board=scene;}
    for(const node of [scene,...scene.querySelectorAll("[id]")]){
      if(node.id){fields[node.id]=node;node.removeAttribute("id");}
    }
    if(kind==="blackjack"){
      fields.bjPlayer.replaceChildren();fields.bjDealer.replaceChildren();
      fields.bjFlightLayer.replaceChildren();fields.bjPayoutPop.remove();
      const label=scene.querySelector(".bj-player-zone .bj-zone-title");
      label.firstChild.textContent="♠ "+table.player+" ";
    }
    const wrap=document.createElement("div");wrap.className="watch-"+kind;
    info=document.createElement("strong");info.className="watch-info";
    wrap.append(info,scene);stage.replaceChildren(wrap);mounted=table.id;phase=null;
  }
  function animatePart(node,end,ms,elapsed,easing){
    node.style.transform=end;
    if(typeof node.animate!=="function"||elapsed>=ms||window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
    const start=end.startsWith("rotate")?"rotate(0deg)":"translateY(0px)";
    const anim=node.animate([{transform:start},{transform:end}],{duration:ms,easing});
    anim.currentTime=Math.max(0,elapsed);
  }
  function draw(){
    const table=tables.find(t=>t.id===select.value);
    if(!table){mounted=null;stage.textContent="No active or recent tables. Waiting for a player…";return;}
    if(mounted!==table.id)mount(table);
    const header=(table.live?"LIVE":"FINISHED")+" · "+table.player+" · "+credit(table.stake)+" credits";
    if(kind==="chess"){
      info.textContent=header+" · "+({active:"Playing",win:"White wins",lose:"Bot wins",draw:"Draw"})[table.outcome];
      const count=table.moves.length;
      if(phase===count)return;
      const position=new Chess();
      const apply=uci=>position.move({from:uci.slice(0,2),to:uci.slice(2,4),promotion:uci[4]});
      const replay=phase!==null&&count===phase+2;
      table.moves.slice(0,replay?-1:undefined).forEach(apply);
      const board=fields.board;
      drawSquares(board,position,null,[],true);
      if(replay)setTimeout(()=>{
        if(!visible()||mounted!==table.id||phase!==count||fields.board!==board)return;
        apply(table.moves[count-1]);drawSquares(board,position,null,[],true);
      },350);
      phase=count;
    }else if(kind==="blackjack"){
      info.textContent=header+" · "+(table.live?"Playing":table.outcome);
      for(const [zone,ranks,node] of [["dealer",table.dealer,fields.bjDealer],["player",table.cards,fields.bjPlayer]]){
        ranks.forEach((rank,i)=>{
          const old=node.children[i];
          if(old?.dataset.rank===rank)return;
          const card=old||art.bjMakeCard(rank,zone,i);
          if(rank!=="🂠")art.bjFlip(card,rank,zone,i);
          if(!old)node.append(card);
        });
      }
      fields.bjScore.textContent=table.score;fields.bjDealerScore.textContent=table.dealer_score??"?";
    }else if(kind==="wheel"){
      info.textContent=header+" · Bet on "+table.choice;
      fields.rouletteCenterLabel.textContent=table.live?"BALL IN MOTION":"BALL LANDED ON";
      fields.rouletteCenterValue.textContent=table.live?"SPINNING":table.result.toUpperCase();
      fields.rouletteCenterValue.className="roulette-center-number"+(table.live?"":" is-result-"+table.result);
      fields.rouletteCenterDetail.textContent="RED / BLACK";
      if(phase!==table.live){
        phase=table.live;const deg=1800+table.pocket*360/37;
        animatePart(fields.rouletteBallTrack,"rotate("+deg+"deg)",5000,table.elapsed_ms,"cubic-bezier(.13,.66,.18,1)");
      }
    }else{
      const shown=table.drops.length,round=table.live?shown:shown-1;
      const roundKey=round+":"+table.live;
      info.textContent=header+" · "+table.case+" · Round "+(round+1)+" / "+table.rounds;
      if(phase===roundKey)return;
      phase=roundKey;fields.cbPlayerName.textContent=table.player;
      const drop=table.rolling||table.drops[round];
      let scores=[];
      for(const [side,key] of [["player","Player"],["bot","Bot"]]){
        const history=fields["cb"+key+"History"];history.replaceChildren();
        let score=0;
        for(const [i,d] of table.drops.entries()){
          const item=d[side];score+=item.value;
          const row=document.createElement("div");row.textContent=(i+1)+". "+item.name+" · "+credit(item.value);history.prepend(row);
        }
        fields["cb"+key+"Score"].textContent=credit(score);scores.push(score);
        if(drop){
          const reel=art.cbReelPrepare(fields["cb"+key+"Reel"],drop[side],table.pool,table.seed+round*2+(side==="bot"?1:0));
          animatePart(reel.track,"translateY(-"+reel.offset+"px)",2350,table.live?table.elapsed_ms-round*2770:2350,"cubic-bezier(.12,.66,.12,1)");
        }
      }
      if(!table.live)info.textContent+=" · "+(scores[0]>scores[1]?"Player wins":"Royal Bot wins");
    }
  }
  select.onchange=draw;
  async function poll(){
    if(!visible())return;
    try{
      const response=await fetch("/api/spectate/"+kind,{cache:"no-store"});
      if(!response.ok)throw Error();
      const data=await response.json();if(!visible())return;
      const previous=select.value;tables=data.tables;
      const choices=tables.map(t=>[(t.live?"Live":"Finished")+" · "+t.player+" · "+t.id.slice(-4),t.id]);
      if(select.length!==choices.length||choices.some(([label,id],i)=>select.options[i].value!==id||select.options[i].text!==label))
        select.replaceChildren(...choices.map(([label,id])=>new Option(label,id)));
      if(tables.some(t=>t.id===previous))select.value=previous;
      byId("watchPicker").hidden=!tables.length;draw();
    }catch{if(visible()){mounted=null;stage.textContent="Connection interrupted. Reconnecting…";byId("watchPicker").hidden=true;}}
    if(visible())setTimeout(poll,850);
  }
  poll();
}
