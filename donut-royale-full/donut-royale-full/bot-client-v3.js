'use strict';
const bedrock = require('bedrock-protocol');
const fs = require('fs');
const crypto = require('crypto');
const readline = require('readline');
const WEB_URL = 'https://donut-royale.onrender.com';
const env = fs.readFileSync('.env','utf8').replace(/^\uFEFF/,'');
const settings = Object.fromEntries(env.split(/\r?\n/).filter(l=>l.includes('=')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim()]}));
const key = settings.BOT_API_KEY;
if (!key) throw Error('Chybi BOT_API_KEY v .env');
const AUTO = settings.AUTO_WITHDRAW_LOCAL === '1';
const OUTBOX = 'payment-outbox.json';
let outbox = fs.existsSync(OUTBOX) ? JSON.parse(fs.readFileSync(OUTBOX,'utf8')) : [];
if (!Array.isArray(outbox)) throw Error('Neplatny payment-outbox.json');
function persist() {
  fs.writeFileSync(OUTBOX+'.tmp',JSON.stringify(outbox));
  fs.renameSync(OUTBOX+'.tmp',OUTBOX);
}
const log = (...x)=>console.log(new Date().toISOString(),...x);
let online=false, pollBusy=false, flushing=false, capture=null, queueSnapshot='';
const client=bedrock.createClient({
  host:'40.223.14.114',port:19132,username:'.LeXimJames7858',
  offline:false,profilesFolder:'./auth',raknetBackend:'raknet-native',
  useRaknetWorkers:false,skipPing:true
});
async function api(path, body) {
  const r=await fetch(WEB_URL+path,{
    method:body===undefined?'GET':'POST',
    headers:{'Content-Type':'application/json','X-Bot-Api-Key':key},
    body:body===undefined?undefined:JSON.stringify(body),
    signal:AbortSignal.timeout(20000)
  });
  const raw=await r.text();
  if(!r.ok)throw Error(r.status+' '+raw);
  return JSON.parse(raw);
}
async function flush() {
  if(flushing) return;
  flushing=true;
  try {
    while(outbox.length) {
      const entry=outbox[0];
      const result=await api('/api/bot/payment-event',entry);
      log('DEPOSIT WEB:',JSON.stringify(result));
      outbox.shift();
      try { persist(); } catch(e) {outbox.unshift(entry); throw e;}
    }
  } catch(e){log('DEPOSIT CEKA NA OPAKOVANE DORUCENI:',e.message);}
  finally{flushing=false;}
}
function command(value) {
  if(!online)throw Error('Bot neni online');
  const uuid=crypto.randomUUID();
  client.queue('command_request',{command:value,origin:{type:'player',uuid,request_id:'',player_entity_id:0n},internal:false,version:'latest'});
  return uuid;
}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function poll() {
  if(!online||pollBusy)return;
  pollBusy=true;
  try {
    const q=await api('/api/bot/withdrawals/pending');
    const snapshot=JSON.stringify(q);
    if(snapshot!==queueSnapshot){queueSnapshot=snapshot;log('WITHDRAW FRONTA:',q.mode,JSON.stringify(q.withdrawals));}
    // The operator has already selected exactly one diagnostic ticket on Render.
    // Regular payouts still require both local and backend opt-in.
    const test=q.mode==='diagnostic_one_shot';
    const jobs=Array.isArray(q.withdrawals)?q.withdrawals:[];
    if(!q.auto_payout_enabled||!jobs.length||!(AUTO||test)||!online)return;
    const job=jobs[0];
    if(test&&(jobs.length!==1||!Number.isSafeInteger(job.amount)||job.amount<1||job.amount>100)){log('DIAGNOSTIKA: Neocekavany pozadavek; nic neposilam');return;}
    const claim=await api('/api/bot/withdrawals/claim',{ticket_id:job.ticket_id});
    const lines=[];
    capture={lines,uuid:null};
    try {
      if(!online||!/^\.?[A-Za-z0-9_]{3,16}$/.test(claim.player)||!Number.isSafeInteger(claim.amount)||claim.amount<=0)throw Error('Neplatny nebo odpojeny vyber');
      if(claim.ticket_id!==job.ticket_id||claim.amount!==job.amount||claim.player.toLowerCase()!==job.player.toLowerCase())throw Error('Nesouhlasi prevzaty vyber');
      log('WITHDRAW POKUS:',claim.ticket_id,claim.player,claim.amount);
      capture.uuid=command('/pay '+claim.player+' '+claim.amount);
      await sleep(20000);
    }catch(e){log('WITHDRAW NEJISTY:',e.message);}
    finally{capture=null;}
    // A failed or uncertain command MUST NOT be sent again.
    const report={ticket_id:claim.ticket_id,attempt_token:claim.attempt_token,source:'system',evidence:lines.slice(0,30)};
    try{const r=await api('/api/bot/withdrawals/result',report);log('WITHDRAW VYSLEDEK:',r.status);}
    catch(e){log('VYSLEDEK NEULOZEN: NEOPAKOVAT VYPLATU',e.message);}
  }catch(e){log('WITHDRAW FRONTA:',e.message);}
  finally{pollBusy=false;}
}
client.on('join',()=>{online=true;log('DONUT ROYALE BOT v3 ONLINE');void flush();void poll();});
client.on('text',p=>{
  const msg=String(p.message||'').replace(/§[0-9a-fk-or]/gi,'').replace(/[\u00a0\u202f]/g,' ').trim();
  log('CHAT ['+p.type+']',msg);
  if(capture&&p.type==='system'&&msg.length<=500&&capture.lines.length<30)capture.lines.push(msg);
  const m=msg.match(/^(\.?[A-Za-z0-9_]{3,16}) paid you \$\s*([0-9,]+(?:\.[0-9]+)?)\s*([KMBT])?$/i);
  if(!m){if(/paid you|payment/i.test(msg))log('PLATEBNI ZPRAVA NEROZPOZNANA:',msg);return;}
  if(p.type!=='system'){log('IGNOROVANA NESYSTEMOVA PLATBA');return;}
  const amount=Number(m[2].replace(/,/g,''))*({'':1,K:1e3,M:1e6,B:1e9,T:1e12}[(m[3]||'').toUpperCase()]);
  if(!Number.isSafeInteger(amount)||amount<=0||amount>1e12){log('NEPODPOROVANA PLATBA',amount);return;}
  const entry={event_id:crypto.randomUUID(),player:m[1],amount,raw_message:msg,received_at:new Date().toISOString()};
  outbox.push(entry);
  try{persist();}catch(e){log('CHYBA ULOZENI DEPOSIT:',e.message);}
  log('DEPOSIT PRIJAT:',m[1],amount,entry.event_id);
  void flush();
});
client.on('command_output',p=>log('COMMAND OUTPUT:',JSON.stringify(p,(_,v)=>typeof v==='bigint'?v.toString():v)));
client.on('disconnect',p=>{online=false;log('ODPOJEN:',p);});
client.on('close',()=>{online=false;log('SPOJENI UKONCENO');});
client.on('error',e=>log('CHYBA:',e.message));
setInterval(()=>void flush(),5000);
setInterval(()=>void poll(),15000);
readline.createInterface({input:process.stdin,output:process.stdout,terminal:false}).on('line',line=>{
  if(line.trim().toLowerCase()==='balance'&&!pollBusy){try{command('/balance');}catch(e){log(e.message);}}
});
