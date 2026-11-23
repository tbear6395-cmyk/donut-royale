// Both the server and browser use the same rules and Stockfish release.
const fs = require("node:fs");
const path = require("node:path");
const stockfish = require("./chess-worker.js");

async function run() {
  const source = fs.readFileSync(path.join(__dirname, "chess-rules.js"));
  const {Chess} = await import("data:text/javascript;base64," + source.toString("base64"));
  const request = JSON.parse(fs.readFileSync(0,"utf8"));
  const board = new Chess();
  const apply = uci => board.move({from:uci.slice(0,2),to:uci.slice(2,4),promotion:uci[4]});
  request.moves.forEach(apply);
  let played;
  try { played = apply(request.move).lan; } catch { process.stdout.write(JSON.stringify({invalid:true})); return; }
  const moves = [...request.moves, played];
  if (!board.isGameOver()) {
    let command;
    const best = new Promise((resolve,reject) => {
      stockfish()({wasmBinary:fs.readFileSync(process.argv[2]), listener:line=>{
        if(line==="uciok"){
          command("setoption name UCI_LimitStrength value true");
          command("setoption name UCI_Elo value 1600"); command("isready");
        }else if(line==="readyok"){
          command("position startpos moves "+moves.join(" "));command("go movetime 700");
        }else if(line.startsWith("bestmove "))resolve(line.split(" ")[1]);
      }}).then(engine=>{command=s=>setImmediate(()=>engine.ccall("command",null,["string"],[s],{async:s.startsWith("go ")}));command("uci");}).catch(reject);
    });
    const reply=await best;
    apply(reply);moves.push(reply);
  }
  const outcome=board.isCheckmate()?(board.turn()==="b"?"win":"lose"):board.isDraw()?"draw":"active";
  process.stdout.write(JSON.stringify({moves,outcome}));
}
run().catch(err=>{console.error(err.message);process.exitCode=1;});
