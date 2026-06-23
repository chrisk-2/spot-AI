#!/usr/bin/env python3
"""
Patch SpotActionCard in App.jsx:
- Fix risk color: low=teal, medium=gold, high=red
- Show confirm_required field
- Show any extra params not in the known-keys set
"""
import re, sys, ast

TARGET = "/home/ogre/spot-stack/starfleet-ui/src/App.jsx"

OLD = '''function SpotActionCard({action,onExecute,onDismiss}){
  const [executing,setExecuting]=useState(false),[result,setResult]=useState(null);
  const riskColor=action.risk==="medium"?"#FFD600":"#00FFCC";
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
      <div className="spot-action-header"><span className="spot-action-title" style={{color:riskColor}}>SPOT PROPOSES ACTION</span><span className="spot-action-risk" style={{color:riskColor}}>{(action.risk||"low").toUpperCase()} RISK</span></div>
      <div className="spot-action-body">
        <div className="spot-action-row"><span>ACTION</span><b>{action.action}</b></div>
        {action.target&&<div className="spot-action-row"><span>TARGET</span><b>{action.target}</b></div>}
        {action.reason&&<div className="spot-action-row"><span>REASON</span><b>{action.reason}</b></div>}
      </div>
      {result?(<div className="spot-action-result">{result}</div>):(
        <div className="spot-action-buttons">
          {action.risk==="medium"&&<div className="spot-action-warn">MEDIUM RISK - CONFIRM REQUIRED</div>}
          <button className="spot-exec-btn" onClick={execute} disabled={executing} style={{borderColor:riskColor,color:riskColor}}>{executing?"EXECUTING...":"EXECUTE"}</button>
          <button className="spot-dismiss-btn" onClick={onDismiss}>DISMISS</button>
        </div>
      )}
    </div>
  );
}'''

NEW = '''// RISK_META: maps allowlist risk levels to display color and confirm label
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
}'''

with open(TARGET, "r") as f:
    content = f.read()

if OLD not in content:
    print("ERROR: OLD block not found — check whitespace or prior edits")
    sys.exit(1)

patched = content.replace(OLD, NEW, 1)

if patched == content:
    print("ERROR: Replace had no effect")
    sys.exit(1)

with open(TARGET, "w") as f:
    f.write(patched)

print("OK: SpotActionCard patched successfully")
print(f"  - risk color: low=teal / medium=gold / high=red")
print(f"  - confirm_required field now shown")
print(f"  - extra params block added")
