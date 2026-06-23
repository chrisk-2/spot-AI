import { useEffect, useState, useRef, useCallback } from "react";
import "./App.css";

const READINESS_URL = "/operator/readiness";
const ALERTS_LOG    = "/operator/alerts";
const API_BASE      = "https://api.starfleetcore.com";
const ADMIN_TOKEN   = "39f35fb1c5825708704a40bfe015f5b547ea23f74fffc2fd813253ef7593d156";
const POLL_MS       = 10_000;
const ALERTS_POLL   = 15_000;

async function sha256hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,"0")).join("");
}

function useAuth() {
  const [authed, setAuthed] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [authErr, setAuthErr] = useState(false);
  async function tryAuth(passphrase) {
    const hash = await sha256hex(passphrase.trim());
    if (hash === "bc722a35347a3224ad4770057548560019c5bf023e92e50c8d6be2943cb0126d") { setAuthed(true); setShowLogin(false); setAuthErr(false); }
    else { setAuthErr(true); }
  }
  function logout() { setAuthed(false); setAuthErr(false); }
  return { authed, showLogin, setShowLogin, authErr, setAuthErr, tryAuth, logout };
}

function LoginModal({ authErr, setAuthErr, tryAuth, onClose }) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit() {
    if (!input.trim() || busy) return;
    setBusy(true); await tryAuth(input); setBusy(false);
  }
  return (
    <div className="modal-overlay" onClick={e=>{if(e.target===e.currentTarget){onClose();setAuthErr(false);}}}>
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo"><img src="/spot-core-badge.png" alt="Spot Core" className="login-badge"/></div>
          <div className="login-title-block">
            <span className="login-title">OPERATOR ACCESS</span>
            <span className="login-sub">STARFLEET COMMAND · SECURE CHANNEL</span>
          </div>
        </div>
        <div className="login-divider"/>
        <div className="login-body">
          <div className="login-label">ENTER ACCESS CODE</div>
          <div className="login-field-wrap">
            <input className={`login-input${authErr?" login-input-err":""}`} type="password"
              placeholder="Access code..." value={input}
              onChange={e=>{setInput(e.target.value);setAuthErr(false);}}
              onKeyDown={e=>e.key==="Enter"&&submit()} autoFocus/>
            <button className="login-btn" onClick={submit} disabled={busy}>{busy?"...":"AUTHENTICATE"}</button>
          </div>
          {authErr&&<div className="login-err">ACCESS DENIED - INVALID CODE</div>}
        </div>
        <div className="login-footer"><span className="login-footer-text">AUTHORIZED PERSONNEL ONLY</span></div>
      </div>
    </div>
  );
}

function useFleet() {
  const [data,setData]=useState(null);
  const [error,setError]=useState(false);
  useEffect(()=>{
    async function poll(){
      try{const r=await fetch(READINESS_URL);if(!r.ok)throw new Error();setData(await r.json());setError(false);}
      catch{setError(true);}
    }
    poll();const id=setInterval(poll,POLL_MS);return()=>clearInterval(id);
  },[]);
  return{data,error};
}

function useAlerts() {
  const [alerts,setAlerts]=useState([]);
  const fetchAlerts=useCallback(async()=>{
    try{
      const r=await fetch(ALERTS_LOG);if(!r.ok)throw new Error();
      const text=await r.text();
      const parsed=text.trim().split("\n").filter(Boolean).map(l=>{try{return JSON.parse(l);}catch{return null;}}).filter(Boolean);
      const alertEvents=["recover_fail","recover_success","recover_attempt_start","wake_send","wake_sent","recover_ping_fail","recover_cooldown_skip","spot_assessment"];
      setAlerts(parsed.filter(e=>alertEvents.includes(e.event)).slice(-50).reverse());
    }catch{}
  },[]);
  useEffect(()=>{fetchAlerts();const id=setInterval(fetchAlerts,ALERTS_POLL);return()=>clearInterval(id);},[fetchAlerts]);
  return alerts;
}

function useClock(){
  const [now,setNow]=useState(new Date());
  useEffect(()=>{const id=setInterval(()=>setNow(new Date()),1000);return()=>clearInterval(id);},[]);
  return now;
}

function fmt(d){return d?d.toISOString().replace("T"," ").slice(0,19):"—";}
function healthPct(fleet){
  if(!fleet)return 100;
  const t=fleet.worker_count||1,b=(fleet.worker_failures||0)+(fleet.quarantined||0);
  return Math.round(((t-b)/t)*100);
}
function workerStatus(w){
  if(!w)return{label:"—",cls:"dim"};
  if(w.quarantined)return{label:"QUARANTINE",cls:"bad"};
  if(w.degraded)return{label:"DEGRADED",cls:"warn"};
  if(!w.ok)return{label:"OFFLINE",cls:"bad"};
  if((w.latency?.p50_total_ms||0)>5000)return{label:"SLOW",cls:"warn"};
  return{label:"ONLINE",cls:"ok"};
}
function alertMeta(event){
  const m={
    recover_fail:{cls:"bad",label:"RECOVERY FAILED",icon:"X"},
    recover_ping_fail:{cls:"bad",label:"PING FAILED",icon:"X"},
    recover_success:{cls:"ok",label:"RECOVERED",icon:"OK"},
    recover_attempt_start:{cls:"warn",label:"RECOVERY ATTEMPT",icon:">>"},
    wake_send:{cls:"warn",label:"WOL PACKET SENT",icon:"!"},
    wake_sent:{cls:"ok",label:"WOL SENT OK",icon:"!"},
    recover_cooldown_skip:{cls:"dim",label:"COOLDOWN",icon:"-"},
    spot_assessment:{cls:"warn",label:"SPOT ASSESSMENT",icon:"*"},
  };
  return m[event]||{cls:"dim",label:event.toUpperCase(),icon:"."};
}
function relTime(ts){
  const d=Math.floor((Date.now()-new Date(ts).getTime())/1000);
  if(d<60)return`${d}s ago`;if(d<3600)return`${Math.floor(d/60)}m ago`;
  return`${Math.floor(d/3600)}h ago`;
}
function parseSpotAction(text){
  const m=text.match(/```spot_action\s*([\s\S]*?)```/);if(!m)return null;
  try{return JSON.parse(m[1].trim());}catch{return null;}
}
function stripSpotAction(text){return text.replace(/```spot_action[\s\S]*?```/g,"").trim();}

const NAV_ITEMS_PUBLIC=[["DASHBOARD","#FFB347"],["ASSETS","#CC44FF"]];
const NAV_ITEMS_OPERATOR=[["DASHBOARD","#FFB347"],["SYSTEMS","#3399FF"],["ASSETS","#CC44FF"],["ALERTS","#FF3366"],["LOGS","#00FFCC"],["SETTINGS","#446688"],["DOCS","#335566"]];

function NavRail({active,setActive,authed}){
  const items=authed?NAV_ITEMS_OPERATOR:NAV_ITEMS_PUBLIC;
  return(
    <aside className="nav-rail">
      <div className="lcars-elbow-top"><div className="elbow-body"/><div className="elbow-cutout"/></div>
      <div className="nav-brand">
        <span className="brand-sf">STARFLEET</span><span className="brand-cmd">COMMAND</span>
        <span className="brand-net">OPERATIONS NETWORK</span>
      </div>
      <div className="nav-list">
        {items.map(([label,color],i)=>(
          <button key={label} className={`nav-item${active===i?" active":""}`} onClick={()=>setActive(i)}>
            <div className="nav-bar" style={{background:color}}>{label}</div>
          </button>
        ))}
      </div>
      <div className="core-badge">
        <img src="/spot-core-badge.png" alt="Spot Core"/>
        <span className="badge-name">SPOT CORE</span>
        <span className="badge-auth">{authed?"AUTHORITY: OPERATOR":"READ ONLY"}</span>
      </div>
      <div className="lcars-elbow-bot"><div className="elbow-body-bot"/><div className="elbow-cutout-bot"/></div>
    </aside>
  );
}

function TopBar({data,error,now,authed,onLoginClick,onLogout}){
  const ok=data?.ok&&!error;
  return(
    <header className="top-bar">
      <div className="top-seg seg-gold"/><div className="top-seg seg-violet">STARFLEET</div>
      <div className="top-seg seg-blue">COMMAND</div>
      <div className="top-title">OPERATIONS NETWORK</div>
      <div className="top-seg seg-dark">SECTOR ALPHA-7</div>
      <div className="top-status">
        <span className={`sdot ${ok?"ok":"bad"}`}/>
        <div><b className={ok?"c-teal":"c-alert"}>{ok?"ALL SYSTEMS NOMINAL":error?"CONNECTION LOST":"LOADING..."}</b><em>{fmt(now)}</em></div>
      </div>
      {authed
        ?<button className="op-btn op-btn-out" onClick={onLogout}>LOGOUT</button>
        :<button className="op-btn op-btn-in" onClick={onLoginClick}>OPERATOR</button>
      }
    </header>
  );
}

function MetricsRow({data,error}){
  const fleet=data?.fleet,core=data?.core,routing=data?.routing;
  const healthy=fleet?fleet.worker_count-(fleet.worker_failures||0)-(fleet.quarantined||0):"—";
  const total=fleet?.worker_count??"—",alerts=fleet?(fleet.worker_failures||0)+(fleet.slow_workers?.length||0):"—";
  const uptime=core?.uptime_sec!=null?`${Math.floor(core.uptime_sec/3600)}h ${Math.floor((core.uptime_sec%3600)/60)}m`:"—";
  return(
    <div className="metrics-row">
      <div className="metric" data-accent="teal"><div className="metric-label">WORKERS ONLINE</div><div className="metric-val c-teal">{error?"—":`${healthy}/${total}`}</div><div className="metric-sub">PRIMARY GRID</div></div>
      <div className="metric" data-accent="blue"><div className="metric-label">ROUTING HEALTH</div><div className="metric-val c-blue">{routing?`${routing.primaries}P / ${routing.fallbacks}F`:"—"}</div><div className="metric-sub">{routing?.violations?`${routing.violations} VIOLATIONS`:"NO VIOLATIONS"}</div></div>
      <div className="metric" data-accent="violet"><div className="metric-label">ACTIVE ALERTS</div><div className={`metric-val ${alerts>0?"c-gold":"c-violet"}`}>{error?"—":alerts}</div><div className="metric-sub">{alerts>0?"ATTENTION NEEDED":"NO ACTIVE ALERTS"}</div></div>
      <div className="metric" data-accent="gold"><div className="metric-label">CONTROL PLANE</div><div className={`metric-val ${core?.ok?"c-gold":"c-alert"}`}>{error?"—":core?.ok?"NOMINAL":"ERROR"}</div><div className="metric-sub">UPTIME {uptime}</div></div>
    </div>
  );
}

const LEFT_TABS=["HEALTH","GOVERNANCE","ROUTING","ALERTS"];
function LeftPanel({data}){
  const [tab,setTab]=useState(0);
  const fleet=data?.fleet,routing=data?.routing;
  const pct=healthPct(fleet),slow=fleet?.slow_workers?.length||0,alerts=fleet?(fleet.worker_failures||0)+slow:0;
  return(
    <div className="panel left-panel">
      <div className="tab-bar">{LEFT_TABS.map((t,i)=>(<button key={t} className={`tab${tab===i?" active":""}`} onClick={()=>setTab(i)}>{t}</button>))}</div>
      {tab===0&&(<div className="tab-content">
        <div className="gauge-bar" style={{"--pct":`${pct}%`}}><span>{pct}% FLEET HEALTH</span></div>
        {[["Workers Online",fleet?`${fleet.worker_count-(fleet.worker_failures||0)}/${fleet.worker_count}`:"—",""],["Quarantined",fleet?.quarantined??"—",fleet?.quarantined?"warn":""],["Degraded",fleet?.degraded??"—",fleet?.degraded?"warn":""],["Slow Workers",slow,slow?"warn":""],["Review Gate",routing?.violations?"REVIEW":"CLEAR",routing?.violations?"warn":"ok"],["Core Uptime",data?.core?.uptime_sec!=null?`${Math.floor(data.core.uptime_sec/3600)}h ${Math.floor((data.core.uptime_sec%3600)/60)}m`:"—",""]].map(([k,v,cls])=>(<div className="info-row" key={k}><span>{k}</span><b className={cls}>{String(v)}</b></div>))}
      </div>)}
      {tab===1&&(<div className="tab-content">
        {[["Compliance","100%","ok"],["Risk Posture","LOW","ok"],["Policy Drift",routing?.violations??0,routing?.violations?"warn":"ok"],["Exceptions","0","ok"],["Auto Review","ENABLED","ok"],["Gate State",routing?.violations?"REVIEW":"CLEAR",routing?.violations?"warn":"ok"],["Last Violation",routing?.last_violation_ts?new Date(routing.last_violation_ts*1000).toLocaleTimeString():"NONE","ok"],["Manual Ovr",routing?.manual_overrides??0,""]].map(([k,v,cls])=>(<div className="info-row" key={k}><span>{k}</span><b className={cls}>{String(v)}</b></div>))}
      </div>)}
      {tab===2&&(<div className="tab-content">
        {[["Window",routing?.window_count??"—",""],["Primaries",routing?.primaries??"—","ok"],["Fallbacks",routing?.fallbacks??"—",routing?.fallbacks?"warn":"ok"],["Violations",routing?.violations??"—",routing?.violations?"bad":"ok"],["Manual Ovr",routing?.manual_overrides??"—",""]].map(([k,v,cls])=>(<div className="info-row" key={k}><span>{k}</span><b className={cls}>{String(v)}</b></div>))}
      </div>)}
      {tab===3&&(<div className="tab-content">
        {alerts===0?(<div className="no-alerts"><span className="sdot ok lg"/><p>NO ACTIVE ALERTS</p></div>):(<>{slow>0&&fleet?.slow_workers?.map(sw=>(<div className="alert-item warn" key={sw.worker}><b>SLOW WORKER</b><span>{sw.worker}</span><em>P50: {(sw.p50_total_ms/1000).toFixed(1)}s</em></div>))}{fleet?.worker_failures>0&&(<div className="alert-item bad"><b>WORKER FAILURES</b><span>{fleet.worker_failures} workers offline</span></div>)}</>)}
      </div>)}
    </div>
  );
}

function RadarMap({data}){
  const workers=data?.fleet?.workers||[],wHealth={};
  workers.forEach(w=>{const n=w.worker.replace("spot-worker-0","").replace("spot-worker-","");wHealth[n]=workerStatus(w).cls;});
  const nc=cls=>cls==="ok"?"#00FFCC":cls==="warn"?"#FFD600":cls==="bad"?"#FF3366":"#334455";
  const stars=[[32,22],[88,48],[145,18],[210,35],[328,20],[412,44],[488,28],[518,65],[18,95],[65,138],[492,85],[525,118],[28,188],[534,168],[12,288],[522,308],[42,368],[515,388],[85,438],[485,455],[208,468],[358,470],[448,425],[105,408],[175,388],[438,378],[125,65],[458,75],[308,55],[388,28],[58,248],[505,248],[278,15],[278,470],[158,158],[398,158],[158,338],[398,338],[250,90],[420,200],[80,320],[340,400],[480,150],[60,190],[290,470],[520,220],[170,480],[440,320],[100,150],[360,80]];
  return(
    <section className="panel map-panel">
      <svg className="radar-svg" viewBox="0 20 540 470" preserveAspectRatio="none">
        <defs>
          <radialGradient id="bgGlow" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#001835" stopOpacity="0.9"/><stop offset="100%" stopColor="#000810" stopOpacity="0"/></radialGradient>
          <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#00FFCC" stopOpacity="0.2"/><stop offset="100%" stopColor="#00FFCC" stopOpacity="0"/></radialGradient>
          <filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        <rect x="0" y="0" width="540" height="500" fill="#000810" rx="8"/>
        <ellipse cx="270" cy="240" rx="250" ry="220" fill="url(#bgGlow)"/>
        {stars.map(([x,y],i)=>(<circle key={i} cx={x} cy={y} r={i%5===0?1.4:i%3===0?1.0:0.6} fill="#ffffff" opacity={0.15+((i*37)%100)/300}/>))}
        {[70,120,170,220].map(r=>(<circle key={r} cx="270" cy="240" r={r} fill="none" stroke="#0a2850" strokeWidth="0.5"/>))}
        <line x1="30" y1="240" x2="510" y2="240" stroke="#0a2850" strokeWidth="0.5"/>
        <line x1="270" y1="15" x2="270" y2="465" stroke="#0a2850" strokeWidth="0.5"/>
        {[[270,70],[110,125],[430,125],[492,240],[55,278],[110,362],[202,416],[338,416],[430,362],[485,278]].map(([x,y],i)=>(<line key={i} x1="270" y1="240" x2={x} y2={y} stroke="#1a4060" strokeWidth="0.5" strokeDasharray="4 5" opacity="0.7"/>))}
        <ellipse cx="270" cy="240" rx="60" ry="60" fill="url(#coreGlow)"/>
        <g transform="translate(270,240)" filter="url(#glow)">
          <circle cx="0" cy="0" r="38" fill="none" stroke="#00FFCC" strokeWidth="5" opacity="0.7"/>
          <circle cx="0" cy="0" r="38" fill="none" stroke="#001a30" strokeWidth="3" opacity="0.5"/>
          {[0,30,60,90,120,150,180,210,240,270,300,330].map((deg,i)=>{const r=deg*Math.PI/180;return <circle key={i} cx={Math.cos(r)*38} cy={Math.sin(r)*38} r="2.5" fill="#001a30" stroke="#00FFCC" strokeWidth="1"/>;  })}
          <circle cx="0" cy="0" r="14" fill="#001a30" stroke="#00FFCC" strokeWidth="2"/>
          <circle cx="0" cy="0" r="9" fill="#002535" stroke="#00FFCC" strokeWidth="1.5"/>
          <circle cx="0" cy="0" r="5" fill="#003a50" stroke="#00FFCC" strokeWidth="1"/>
          <circle cx="0" cy="0" r="2" fill="#00FFCC" opacity="0.9"/>
          {[270,30,150].map((deg,i)=>{const r=deg*Math.PI/180,ix=Math.cos(r)*14,iy=Math.sin(r)*14,ox=Math.cos(r)*38,oy=Math.sin(r)*38,c1=Math.cos(r)*24+Math.sin(r)*10,c2=Math.sin(r)*24-Math.cos(r)*10;return(<g key={i}><path d={"M"+ix+","+iy+" Q"+c1+","+c2+" "+ox+","+oy} fill="none" stroke="#00FFCC" strokeWidth="2.5"/><ellipse cx={ox*1.12} cy={oy*1.12} rx="5" ry="3" transform={"rotate("+deg+" "+ox*1.12+" "+oy*1.12+")"} fill="#001a30" stroke="#00FFCC" strokeWidth="1.2"/><circle cx={ox*1.12} cy={oy*1.12} r="2" fill="#00FFCC" opacity="0.8"/></g>);})}
          <text x="0" y="62" textAnchor="middle" fill="#00FFCC" fontFamily="Orbitron,monospace" fontSize="8" fontWeight="700" letterSpacing="1">SPOT CORE</text>
        </g>
        <g transform="translate(270,70)" filter="url(#glow)">
          <ellipse cx="0" cy="0" rx="16" ry="6" fill="#001830" stroke="#66CCFF" strokeWidth="1.2"/>
          <ellipse cx="0" cy="0" rx="8" ry="3.5" fill="#001830" stroke="#66CCFF" strokeWidth="0.8"/>
          <rect x="-3" y="5" width="6" height="8" fill="#001830" stroke="#66CCFF" strokeWidth="0.8" rx="1"/>
          <line x1="-7" y1="6" x2="-22" y2="12" stroke="#66CCFF" strokeWidth="1.2"/>
          <line x1="7" y1="6" x2="22" y2="12" stroke="#66CCFF" strokeWidth="1.2"/>
          <ellipse cx="-22" cy="12" rx="4" ry="2" fill="#001830" stroke="#66CCFF" strokeWidth="1"/>
          <ellipse cx="22" cy="12" rx="4" ry="2" fill="#001830" stroke="#66CCFF" strokeWidth="1"/>
          <circle cx="-22" cy="12" r="1.2" fill="#66CCFF" opacity="0.9"/>
          <circle cx="22" cy="12" r="1.2" fill="#66CCFF" opacity="0.9"/>
          <circle cx="0" cy="0" r="2" fill="#66CCFF" opacity="0.9"/>
          <text x="0" y="-16" textAnchor="middle" fill="#66CCFF" fontFamily="Rajdhani,sans-serif" fontSize="9" fontWeight="700">STARFLEET CORE</text>
        </g>
        <g transform="translate(110,120) scale(1.25)" filter="url(#glow)">
          <ellipse cx="0" cy="0" rx="13" ry="5" fill="#001830" stroke="#66CCFF" strokeWidth="1"/>
          <rect x="-2.5" y="4" width="5" height="9" fill="#001830" stroke="#66CCFF" strokeWidth="0.8" rx="1"/>
          <line x1="-5" y1="5" x2="-18" y2="10" stroke="#66CCFF" strokeWidth="1"/>
          <line x1="5" y1="5" x2="18" y2="10" stroke="#66CCFF" strokeWidth="1"/>
          <ellipse cx="-18" cy="10" rx="3.5" ry="1.8" fill="#001830" stroke="#66CCFF" strokeWidth="0.8"/>
          <ellipse cx="18" cy="10" rx="3.5" ry="1.8" fill="#001830" stroke="#66CCFF" strokeWidth="0.8"/>
          <circle cx="-18" cy="10" r="1" fill="#66CCFF" opacity="0.7"/>
          <circle cx="18" cy="10" r="1" fill="#66CCFF" opacity="0.7"/>
          <text x="0" y="-13" textAnchor="middle" fill="#66CCFF" fontFamily="Rajdhani,sans-serif" fontSize="9" fontWeight="700">SF TOWER</text>
        </g>
        <g transform="translate(430,120) scale(1.25)" filter="url(#glow)">
          <ellipse cx="0" cy="0" rx="15" ry="5.5" fill="#001830" stroke="#3399FF" strokeWidth="1.2"/>
          <ellipse cx="0" cy="0" rx="7" ry="3" fill="#001830" stroke="#3399FF" strokeWidth="1"/>
          <line x1="-7" y1="2.5" x2="-17" y2="7" stroke="#3399FF" strokeWidth="1.2"/>
          <line x1="7" y1="2.5" x2="17" y2="7" stroke="#3399FF" strokeWidth="1.2"/>
          <circle cx="-17" cy="7" r="2" fill="#3399FF" opacity="0.8"/>
          <circle cx="17" cy="7" r="2" fill="#3399FF" opacity="0.8"/>
          <circle cx="0" cy="0" r="2.5" fill="#3399FF" opacity="0.9"/>
          <text x="0" y="-13" textAnchor="middle" fill="#3399FF" fontFamily="Rajdhani,sans-serif" fontSize="9" fontWeight="700">DNS CORE</text>
        </g>
        <g transform="translate(492,240)" filter="url(#glow)">
          <rect x="-13" y="-13" width="26" height="26" fill="#001020" stroke="#3399FF" strokeWidth="1.2"/>
          {[-6,0,6].map(v=>(<g key={v}><line x1="-13" y1={v} x2="13" y2={v} stroke="#3399FF" strokeWidth="0.4" opacity="0.5"/><line x1={v} y1="-13" x2={v} y2="13" stroke="#3399FF" strokeWidth="0.4" opacity="0.5"/></g>))}
          <rect x="-4" y="-4" width="8" height="8" fill="#3399FF" opacity="0.3"/>
          <text x="0" y="-18" textAnchor="middle" fill="#3399FF" fontFamily="Rajdhani,sans-serif" fontSize="9" fontWeight="700">UNIMATRIX</text>
        </g>
        {[{id:"1",x:38,y:310,label:"W-01"},{id:"2",x:85,y:395,label:"W-02"},{id:"3",x:175,y:440,label:"W-03"},{id:"4",x:318,y:448,label:"W-04"},{id:"5",x:420,y:400,label:"W-05"},{id:"6",x:490,y:318,label:"W-06"}].map(({id,x,y,label})=>{
          const c=nc(wHealth[id]||"dim");
          return(<g key={id} transform={"translate("+x+","+y+")"} filter="url(#glow)">
            <ellipse cx="0" cy="0" rx="22" ry="8" fill="#001520" stroke={c} strokeWidth="1.5"/>
            <ellipse cx="4" cy="-2" rx="8" ry="4" fill="#001a28" stroke={c} strokeWidth="1"/>
            <circle cx="20" cy="0" r="3" fill="#001520" stroke={c} strokeWidth="1"/>
            <line x1="-8" y1="3" x2="-18" y2="10" stroke={c} strokeWidth="1.5"/>
            <line x1="-8" y1="-3" x2="-18" y2="-10" stroke={c} strokeWidth="1.5"/>
            <rect x="-28" y="8" width="20" height="5" fill="#001020" stroke={c} strokeWidth="1" rx="2"/>
            <rect x="-28" y="-13" width="20" height="5" fill="#001020" stroke={c} strokeWidth="1" rx="2"/>
            <circle cx="-26" cy="10.5" r="2" fill={c} opacity="0.9"/>
            <circle cx="-26" cy="-10.5" r="2" fill={c} opacity="0.9"/>
            <text x="0" y="-22" textAnchor="middle" fill={c} fontFamily="Rajdhani,sans-serif" fontSize="11" fontWeight="700">{label}</text>
          </g>);
        })}
      </svg>
    </section>
  );
}

const ROLE_COLORS_MAP={general:"#00FFCC",utility:"#66CCFF",coding:"#CC44FF",heavy:"#FFB347",review:"#FF3366",reasoning:"#3399FF"};
function WorkerLanes({data}){
  const workers=data?.fleet?.workers||[{worker:"spot-worker-01",primary_role:"general",ok:null},{worker:"spot-worker-02",primary_role:"utility",ok:null},{worker:"spot-worker-03",primary_role:"coding",ok:null},{worker:"spot-worker-04",primary_role:"heavy",ok:null},{worker:"spot-worker-05",primary_role:"review",ok:null},{worker:"spot-worker-06",primary_role:"reasoning",ok:null}];
  return(
    <section className="worker-section">
      <div className="worker-header"><span className="worker-title">STARFLEET WORKER LANES</span><div className="worker-header-line"/></div>
      <div className="worker-grid">
        {workers.map((w,i)=>{
          const st=workerStatus(w),role=w.primary_role||"",rc=ROLE_COLORS_MAP[role]||"#66CCFF";
          const toks=w.latency?.avg_tok_per_sec!=null?`${w.latency.avg_tok_per_sec.toFixed(1)}`:"—";
          const p50=w.latency?.p50_total_ms!=null?`${(w.latency.p50_total_ms/1000).toFixed(1)}s`:"—";
          const stColor=st.cls==="ok"?"#00FFCC":st.cls==="warn"?"#FFD600":"#FF3366";
          return(<div className="worker-card" key={w.worker} style={{"--role-color":rc}}>
            <div className={`worker-dot ${st.cls}`}/><div className="worker-id">W-{i+1}</div>
            <div className="worker-host">{w.worker}</div>
            <div className="worker-rows">
              <div className="wrow"><span>ROLE</span><b style={{color:rc}}>{role.toUpperCase()||"—"}</b></div>
              <div className="wrow"><span>STATUS</span><b style={{color:stColor}}>{st.label}</b></div>
              <div className="wrow"><span>P50</span><b>{p50}</b></div>
              <div className="wrow"><span>TOK/S</span><b>{toks}</b></div>
            </div>
          </div>);
        })}
      </div>
    </section>
  );
}

function AiPanel({authed}){
  const [msgs,setMsgs]=useState([{from:"spot",text:"Systems online."},{from:"spot",text:"Awaiting operator input."}]);
  const [input,setInput]=useState(""),[ busy,setBusy]=useState(false),boxRef=useRef(null);
  useEffect(()=>{if(boxRef.current)boxRef.current.scrollTop=boxRef.current.scrollHeight;},[msgs]);
  async function send(){
    const text=input.trim();if(!text||busy)return;
    setMsgs(m=>[...m,{from:"user",text}]);setInput("");setBusy(true);
    try{
      const r=await fetch(`${API_BASE}/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,role:"general",source:"starfleet-ui",mode:"advisory"})});
      const d=await r.json();setMsgs(m=>[...m,{from:"spot",text:d.reply||"No response."}]);
    }catch{setMsgs(m=>[...m,{from:"spot",text:"Comm channel error."}]);}
    setBusy(false);
  }
  return(
    <div className="ai-stack">
      <section className="panel ai-panel">
        <div className="panel-title-bar"><span className="panel-title c-violet">SPOT AI ASSISTANT</span></div>
        <div className="accent-bars"><span style={{background:"#FFB347"}}/><span style={{background:"#FF3366"}}/><span style={{background:"#aa33ee"}}/><span style={{background:"#CC44FF"}}/><span style={{background:"#3399FF"}}/></div>
        <div className="ai-avatar-wrap"><img src="/spot-avatar.png" alt="Spot AI" className="ai-avatar"/></div>
        <div className="ai-state"><b><span className="sdot ok sm"/>SPOT ONLINE</b><span>{busy?"THINKING...":"IDLE"}</span></div>
      </section>
      <section className="panel chat-panel">
        <div className="panel-title-bar"><span className="panel-title c-blue">SPOT CHAT</span></div>
        <div className="chat-box" ref={boxRef}>
          {msgs.map((m,i)=>(<p key={i} className={m.from==="user"?"chat-user":"chat-spot"}>{m.from==="spot"&&<em>SPOT: </em>}{m.text}</p>))}
          {busy&&<p className="chat-spot"><em>SPOT: </em><span className="blink">|</span></p>}
        </div>
        <div className="chat-row">
          <input placeholder={authed?"Ask Spot...":"Operator access required"} value={input} disabled={!authed} onChange={e=>authed&&setInput(e.target.value)} onKeyDown={e=>authed&&e.key==="Enter"&&send()} style={{opacity:authed?1:0.4,cursor:authed?"text":"not-allowed"}}/>
          <button onClick={send} disabled={!authed||busy} style={{opacity:authed?1:0.4,cursor:authed?"pointer":"not-allowed"}}>SEND</button>
        </div>
      </section>
    </div>
  );
}

// RISK_META: maps allowlist risk levels to display color and confirm label
const RISK_META={
  low:  {color:"#00FFCC", label:"LOW RISK",    warn:null},
  medium:{color:"#FFD600", label:"MEDIUM RISK", warn:"MEDIUM RISK — CONFIRM REQUIRED"},
  high: {color:"#FF3366", label:"HIGH RISK",   warn:"HIGH RISK — OPERATOR CONFIRMATION REQUIRED"},
};
// Keys shown as dedicated rows — everything else goes into PARAMS block
const ACTION_KNOWN_KEYS=new Set(["action","target","reason","risk","confirm_required"]);

function SpotActionCard({action,onExecute,onDismiss}){
  const [executing,setExecuting]=useState(false),[result,setResult]=useState(null);
  const risk=(action.risk||"low").toLowerCase();
  const meta=RISK_META[risk]||RISK_META.low;
  const riskColor=meta.color;

  // Collect extra params not shown as dedicated rows
  const extraParams=Object.entries(action).filter(([k])=>!ACTION_KNOWN_KEYS.has(k));

  async function execute(){
    setExecuting(true);
    try{
      const r=await fetch(`${API_BASE}/chat/execute`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:ADMIN_TOKEN,action:action.action,target:action.target||null,reason:action.reason||"operator_confirmed",confirmed:true})});
      const d=await r.json();setResult(d.ok?"OK: EXECUTED":"FAILED");
      if(d.ok)setTimeout(()=>onExecute(d),1800);
    }catch{setResult("COMM ERROR");}
    setExecuting(false);
  }
  return(
    <div className="spot-action-card" style={{borderColor:riskColor}}>
      <div className="spot-action-header">
        <span className="spot-action-title" style={{color:riskColor}}>SPOT PROPOSES ACTION</span>
        <span className="spot-action-risk" style={{color:riskColor}}>{meta.label}</span>
      </div>
      <div className="spot-action-body">
        <div className="spot-action-row"><span>ACTION</span><b>{action.action}</b></div>
        {action.target&&<div className="spot-action-row"><span>TARGET</span><b>{action.target}</b></div>}
        {action.reason&&<div className="spot-action-row"><span>REASON</span><b>{action.reason}</b></div>}
        {action.confirm_required!=null&&(
          <div className="spot-action-row"><span>CONFIRM REQ</span><b style={{color:action.confirm_required?meta.color:"#446688"}}>{action.confirm_required?"YES":"NO"}</b></div>
        )}
        {extraParams.length>0&&(
          <div className="spot-action-params">
            <div className="spot-action-params-label">PARAMS</div>
            {extraParams.map(([k,v])=>(
              <div className="spot-action-row spot-action-param-row" key={k}>
                <span>{k.toUpperCase()}</span>
                <b>{typeof v==="object"?JSON.stringify(v):String(v)}</b>
              </div>
            ))}
          </div>
        )}
      </div>
      {result?(<div className="spot-action-result">{result}</div>):(
        <div className="spot-action-buttons">
          {meta.warn&&<div className="spot-action-warn" style={{color:riskColor,borderColor:riskColor}}>{meta.warn}</div>}
          <button className="spot-exec-btn" onClick={execute} disabled={executing} style={{borderColor:riskColor,color:riskColor}}>{executing?"EXECUTING...":"EXECUTE"}</button>
          <button className="spot-dismiss-btn" onClick={onDismiss}>DISMISS</button>
        </div>
      )}
    </div>
  );
}

function SpotTab(){
  const [msgs,setMsgs]=useState([{from:"spot",text:"Spot online. Full command interface ready."}]);
  const [input,setInput]=useState(""),[ busy,setBusy]=useState(false),boxRef=useRef(null);
  useEffect(()=>{if(boxRef.current)boxRef.current.scrollTop=boxRef.current.scrollHeight;},[msgs]);
  function dismissAction(idx){setMsgs(m=>m.map((msg,i)=>i===idx?{...msg,action:null}:msg));}
  function onExecuted(idx,res){setMsgs(m=>[...m.map((msg,i)=>i===idx?{...msg,action:null}:msg),{from:"system",text:res.ok?`OK: ${res.action} executed.`:`FAILED: ${res.action}`}]);}
  async function send(){
    const text=input.trim();if(!text||busy)return;
    setMsgs(m=>[...m,{from:"user",text}]);setInput("");setBusy(true);
    try{
      const r=await fetch(`${API_BASE}/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,role:"general",source:"starfleet-ui-spot-tab",mode:"advisory"})});
      const d=await r.json();const raw=d.reply||"No response.",action=parseSpotAction(raw),clean=stripSpotAction(raw);
      setMsgs(m=>[...m,{from:"spot",text:clean,action}]);
    }catch{setMsgs(m=>[...m,{from:"spot",text:"Comm channel error."}]);}
    setBusy(false);
  }
  return(
    <div className="spot-tab">
      <div className="spot-tab-left">
        <div className="spot-tab-avatar-wrap"><img src="/spot-avatar.png" alt="Spot" className="spot-tab-avatar"/></div>
        <div className="spot-tab-info">
          <div className="spot-tab-name">SPOT</div><div className="spot-tab-sub">AI OPERATIONS ASSISTANT</div>
          <div className="spot-tab-status"><span className="sdot ok sm"/><span>ONLINE - STARFLEET COMMAND</span></div>
          <div className="spot-tab-divider"/>
          <div className="spot-tab-meta">
            <div className="spot-meta-row"><span>MODE</span><b className="ok">ADVISORY</b></div>
            <div className="spot-meta-row"><span>AUTHORITY</span><b>OPERATOR</b></div>
            <div className="spot-meta-row"><span>FLEET</span><b className="ok">NOMINAL</b></div>
          </div>
        </div>
      </div>
      <div className="spot-tab-chat">
        <div className="spot-tab-chat-header"><span className="panel-title c-blue">SPOT COMMAND INTERFACE</span><span className="panel-sub">SECURE CHANNEL</span></div>
        <div className="spot-tab-messages" ref={boxRef}>
          {msgs.map((m,i)=>(
            <div key={i}>
              <div className={"spot-msg "+(m.from==="user"?"spot-msg-user":m.from==="system"?"spot-msg-system":"spot-msg-spot")}>
                <div className={"spot-msg-from"+(m.from==="user"?" user-from":m.from==="system"?" sys-from":"")}>{m.from==="user"?"OPERATOR":m.from==="system"?"SYSTEM":"SPOT"}</div>
                <div className="spot-msg-text">{m.text}</div>
              </div>
              {m.action&&<SpotActionCard action={m.action} onExecute={r=>onExecuted(i,r)} onDismiss={()=>dismissAction(i)}/>}
            </div>
          ))}
          {busy&&<div className="spot-msg spot-msg-spot"><div className="spot-msg-from">SPOT</div><div className="spot-msg-text"><span className="blink">|</span> Processing...</div></div>}
        </div>
        <div className="spot-tab-input-row">
          <input className="spot-tab-input" placeholder="Enter command or query..." value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()}/>
          <button className="spot-tab-send" onClick={send} disabled={busy}>{busy?"...":"TRANSMIT"}</button>
        </div>
      </div>
    </div>
  );
}

function AlertsView({data,alerts}){
  const fleet=data?.fleet,workers=fleet?.workers||[];
  const offline=workers.filter(w=>!w.ok&&!w.quarantined);
  const slow=fleet?.slow_workers||[];
  const assessments=alerts.filter(a=>a.event==="spot_assessment").slice(0,10);
  const log=alerts.filter(a=>a.event!=="recover_cooldown_skip").slice(0,50);
  return(
    <div className="alerts-view">
      <div className="alerts-queue-row">
        <div className="alerts-queue-panel">
          <div className="alerts-queue-header"><span className="aq-dot active-dot"/><span className="aq-title">AUTONOMOUS ACTIONS</span><span className="aq-count">{offline.length+slow.length}</span></div>
          <div className="aq-body">
            {offline.length===0&&slow.length===0?(<div className="aq-empty"><span className="sdot ok"/>ALL WORKERS NOMINAL</div>):(<>
              {offline.map(w=>(<div className="aq-item active" key={w.worker}><span className="aq-icon">R</span><div className="aq-detail"><b>{w.worker}</b><span>RECOVERY IN PROGRESS</span></div><span className="aq-badge warn">AUTO</span></div>))}
              {slow.map(sw=>(<div className="aq-item slow" key={sw.worker}><span className="aq-icon">!</span><div className="aq-detail"><b>{sw.worker}</b><span>SLOW - P50 {(sw.p50_total_ms/1000).toFixed(1)}s</span></div><span className="aq-badge warn">WATCH</span></div>))}
            </>)}
          </div>
        </div>
        <div className="alerts-queue-panel">
          <div className="alerts-queue-header"><span className="aq-dot needs-dot"/><span className="aq-title">SPOT ASSESSMENTS</span><span className={`aq-count ${assessments.length>0?"bad-count":""}`}>{assessments.length}</span></div>
          <div className="aq-body">
            {assessments.length===0?(<div className="aq-empty"><span className="sdot ok"/>NO PENDING ASSESSMENTS</div>):assessments.map((a,i)=>(
              <div className="aq-item warn" key={i}><span className="aq-icon">*</span><div className="aq-detail"><b>{a.worker||"fleet"}</b><span>{a.detail||"assessment logged"}</span>{a.action&&<span className="aq-proposed">ACTION: {a.action}</span>}</div><span className="aq-badge warn">{a.action?"ACTION":"INFO"}</span></div>
            ))}
          </div>
        </div>
      </div>
      <div className="alerts-log-panel">
        <div className="alerts-log-header"><span className="panel-title c-alert">ALERT LOG</span><span className="panel-sub">LAST {log.length} EVENTS</span></div>
        <div className="alerts-log-body">
          {log.length===0?(<div className="aq-empty" style={{padding:"20px"}}><span className="sdot ok"/>NO ALERT EVENTS</div>):(
            <table className="alert-table">
              <thead><tr><th>TIME</th><th>AGO</th><th>EVENT</th><th>HOST</th><th>DETAIL</th></tr></thead>
              <tbody>{log.map((a,i)=>{const meta=alertMeta(a.event);return(<tr key={i} className={`alert-row ${meta.cls}`}><td className="at-time">{a.ts?.slice(11,19)||"—"}</td><td className="at-ago">{a.ts?relTime(a.ts):"—"}</td><td className="at-event">{meta.label}</td><td className="at-host">{a.worker||"—"}</td><td className="at-detail">{a.detail||a.reason||""}</td></tr>);})}</tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function PublicBanner(){
  return(
    <div className="public-banner">
      <span className="sdot ok sm"/>
      <span>STARFLEET COMMAND - LIVE FLEET STATUS - READ ONLY</span>
    </div>
  );
}

export default function App(){
  const{authed,showLogin,setShowLogin,authErr,setAuthErr,tryAuth,logout}=useAuth();
  const{data,error}=useFleet();
  const alerts=useAlerts();
  const now=useClock();
  const[activeNav,setActiveNav]=useState(0);
  function handleLogout(){logout();setActiveNav(0);}
  const mainContent=()=>{
    if(authed){
      if(activeNav===1)return <SpotTab/>;
      if(activeNav===3)return <div className="alerts-main"><AlertsView data={data} alerts={alerts}/></div>;
      return(<div className="dashboard-grid"><LeftPanel data={data}/><RadarMap data={data}/><AiPanel authed={authed}/></div>);
    }
    return(
      <div className="dashboard-grid"><LeftPanel data={data}/><RadarMap data={data}/><AiPanel authed={false}/></div>
    );
  };
  return(
    <div className="app-shell">
      {showLogin&&<LoginModal authErr={authErr} setAuthErr={setAuthErr} tryAuth={tryAuth} onClose={()=>setShowLogin(false)}/>}
      <NavRail active={activeNav} setActive={setActiveNav} authed={authed}/>
      <div className="main-console">
        <TopBar data={data} error={error} now={now} authed={authed} onLoginClick={()=>setShowLogin(true)} onLogout={handleLogout}/>
        <MetricsRow data={data} error={error}/>
        <div className="content-area">{mainContent()}</div>
        <WorkerLanes data={data}/>
      </div>
    </div>
  );
}

