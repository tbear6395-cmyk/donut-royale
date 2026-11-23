import {Chess} from './chess-rules.js';

const byId = id => document.getElementById(id);
const symbols = {w:"♙♘♗♖♕♔", b:"♟♞♝♜♛♚"};
const pieces = "pnbrqk";
const names = ["pawn","knight","bishop","rook","queen","king"];
const game = new Chess();
let selected = null, promotion = null, engine = null, ready = false;
let pending = false, failure = false, started = false, generation = 0;
const wasmUrl = "https://unpkg.com/stockfish@17.1.0/src/stockfish-17.1-lite-single-03e3232.wasm";
let binary = null;

function positionStatus(){
  if(game.isCheckmate())return game.turn()==="w"?"Checkmate · Stockfish wins":"Checkmate · You win";
  if(game.isStalemate())return "Draw · Stalemate";
  if(game.isThreefoldRepetition())return "Draw · Threefold repetition";
  if(game.isInsufficientMaterial())return "Draw · Insufficient material";
  if(game.isDraw())return "Draw · Fifty-move rule";
  if(failure)return "Engine could not load. Check your connection and retry.";
  if(!ready)return "Loading Stockfish…";
  if(promotion)return "Choose a promotion piece.";
  return game.turn()==="w"?(game.isCheck()?"Your king is in check":"Your move · White"):"Stockfish is thinking…";
}
function renderChess(){
  const board=byId("chessBoard"), moves=selected?game.moves({square:selected,verbose:true}):[];
  const buttons=[];
  for(const [row,rank] of game.board().entries())for(const [col,piece] of rank.entries()){
    const square="abcdefgh"[col]+(8-row),button=document.createElement("button");
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
  byId("chessTurn").textContent=positionStatus();
  byId("chessPromotion").hidden=!promotion;byId("chessRetry").hidden=!failure;
  byId("chessMoves").textContent=game.history().map((s,i)=>i%2?s:(i/2+1)+". "+s).join(" ");
}
function think(){
  if(!ready||pending||game.turn()!=="b"||game.isGameOver())return;
  pending=true;
  const moves=game.history({verbose:true}).map(m=>m.from+m.to+(m.promotion||""));
  engine.postMessage("position startpos moves "+moves.join(" "));
  engine.postMessage("go movetime 750");
}
async function launch(){
  const token=++generation;
  engine?.terminate();engine=null;ready=false;failure=false;pending=false;renderChess();
  const fail=()=>{
    if(token!==generation)return;
    engine?.terminate();engine=null;ready=false;pending=false;failure=true;renderChess();
  };
  try{
    if(!binary){
      const response=await fetch(wasmUrl,{integrity:"sha256-fKMb7dFmFIkxocyE29jdnPABdE6ZlMryOjxv9JiNcIY=",signal:AbortSignal.timeout(45000)});
      if(!response.ok)throw Error("Engine download failed");
      binary=URL.createObjectURL(new Blob([await response.arrayBuffer()],{type:"application/wasm"}));
    }
    if(token!==generation)return;
    engine=new Worker("/chess-worker.js#"+encodeURIComponent(binary));
    engine.onerror=fail;
    engine.onmessage=({data})=>{
      if(token!==generation||typeof data!=="string")return;
      if(data==="uciok"){
        engine.postMessage("setoption name UCI_LimitStrength value true");
        engine.postMessage("setoption name UCI_Elo value 1600");
        engine.postMessage("ucinewgame");engine.postMessage("isready");
      }else if(data==="readyok"){ready=true;renderChess();think();}
      else if(data.startsWith("bestmove ")&&pending){
        const move=data.split(" ")[1];pending=false;
        try{game.move({from:move.slice(0,2),to:move.slice(2,4),promotion:move[4]});renderChess();}
        catch{fail();}
      }
    };
    engine.postMessage("uci");
  }catch{fail();}
}
function play(from,to,promote){
  game.move({from,to,promotion:promote});selected=null;promotion=null;renderChess();think();
}
export function openChess(){
  if(started){renderChess();return;}
  started=true;
  byId("chessBoard").onclick=e=>{
    const square=e.target.closest("button")?.dataset.square;
    if(!square||!ready||promotion||game.turn()!=="w"||game.isGameOver())return;
    const move=selected&&game.moves({square:selected,verbose:true}).find(m=>m.to===square);
    if(move?.promotion){promotion={from:selected,to:square};renderChess();return;}
    if(move){play(selected,square);return;}
    selected=selected!==square&&game.get(square)?.color==="w"?square:null;renderChess();
  };
  byId("chessPromotion").querySelector("button").onclick=()=>{if(promotion)play(promotion.from,promotion.to,byId("chessPromotion").querySelector("select").value);};
  byId("chessRetry").onclick=launch;
  byId("chessNew").onclick=()=>{
    if(game.history().length&&!game.isGameOver()&&!confirm("Start a new chess game?"))return;
    selected=null;promotion=null;game.reset();launch();
  };
  launch();
}

const titles={wheel:"Roulette",casebattle:"Case Battles",blackjack:"Blackjack"};
let watchSession=0;
export function watch(kind){
  const session=++watchSession, select=byId("watchTable"),stage=byId("watchStage");
  let tables=[];
  const visible=()=>session===watchSession&&!byId("screen-spectate").hidden&&!byId("gameOverlay").hidden;
  byId("watchTitle").textContent="Spectate · "+titles[kind];
  byId("watchPicker").hidden=true;stage.textContent="Loading tables…";select.replaceChildren();
  function draw(){
    const table=tables.find(t=>t.id===select.value);
    stage.replaceChildren();
    if(!table){stage.textContent="No active or recent tables. Waiting for a player…";return;}
    const line=(text,tag="p")=>{const node=document.createElement(tag);node.textContent=text;stage.append(node);};
    line((table.live?"LIVE":"FINISHED")+" · "+table.player+" · "+table.stake.toLocaleString()+" credits","strong");
    if(kind==="wheel"){line("Bet on "+table.choice);line(table.live?"Ball spinning…":"Ball landed on "+table.result.toUpperCase());}
    if(kind==="blackjack"){line("Dealer   "+table.dealer.join("  "));line("Player   "+table.cards.join("  "));line(table.live?"Waiting for the player’s move…":"Result: "+table.outcome);}
    if(kind==="casebattle"){
      line(table.case+" · "+table.drops.length+" / "+table.rounds+" rounds revealed");
      let player=0,bot=0;
      table.drops.forEach((d,i)=>{player+=d.player.value;bot+=d.bot.value;line((i+1)+". "+d.player.name+" ("+d.player.value+") vs "+d.bot.name+" ("+d.bot.value+")");});
      line("Score   "+player+" — "+bot);
      line(table.live?"Opening next case…":player>bot?"Player wins":"Royal Bot wins");
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
      select.replaceChildren(...tables.map(t=>new Option((t.live?"Live":"Finished")+" · "+t.player+" · "+t.id.slice(-4),t.id)));
      if(tables.some(t=>t.id===previous))select.value=previous;
      byId("watchPicker").hidden=!tables.length;draw();
    }catch{if(visible()){stage.textContent="Connection interrupted. Reconnecting…";byId("watchPicker").hidden=true;}}
    if(visible())setTimeout(poll,1500);
  }
  poll();
}
