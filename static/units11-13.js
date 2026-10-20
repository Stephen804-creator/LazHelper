// LazyDesk Units 11–12: opt-in scheduled inbox review and local workspace insights.
(() => {
  const $=id=>document.getElementById(id);
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const card=el("section",undefined,"workspace-card advanced-card");card.id="sloth-insights";
  card.append(el("p","UNITS 11–12 · GENTLE AUTOMATION","eyebrow"),el("h2","Let the sloth do a quiet check."));
  card.append(el("p","Sloth Mode can review a folder on a schedule while LazyDesk is running. It prepares a report only: it never moves or deletes files in the background.","muted"));
  const form=el("form");form.id="sloth-form";
  const enabledLabel=el("label","Enable scheduled review ");const enabled=document.createElement("input");enabled.type="checkbox";enabled.id="sloth-enabled";enabledLabel.prepend(enabled);form.append(enabledLabel);
  const inboxLabel=el("label","Inbox folder (relative to workspace)");const inbox=document.createElement("input");inbox.id="sloth-inbox";inbox.value="inbox";inbox.required=true;inbox.autocomplete="off";inbox.spellcheck=false;inboxLabel.append(inbox);form.append(inboxLabel);
  const intervalLabel=el("label","Repeat every (15–1440 minutes)");const interval=document.createElement("input");interval.id="sloth-interval";interval.type="number";interval.min="15";interval.max="1440";interval.step="15";interval.value="60";intervalLabel.append(interval);form.append(intervalLabel);
  const actions=el("div",undefined,"advanced-controls");const save=el("button","Save Sloth Mode settings","primary-action");save.type="submit";const run=el("button","Run a review now","secondary-action");run.type="button";const map=el("button","Build Digital Mess Map","secondary-action");map.type="button";actions.append(save,run,map);form.append(actions);card.append(form);
  const status=el("p","Sloth Mode is off by default.","status-line");status.id="sloth-status";status.setAttribute("role","status");card.append(status);
  const output=el("div");output.id="insights-output";card.append(output);
  const previous=document.getElementById("organize-tools");if(previous)previous.after(card);else document.querySelector("main")?.append(card);
  const api=async(path,opts={})=>{const r=await fetch(path,{...opts,headers:{"Content-Type":"application/json",...(opts.headers||{})}});const d=await r.json();if(!r.ok)throw Error(d.detail||"Request failed");return d;};
  const show=data=>{output.replaceChildren();const pre=el("pre",JSON.stringify(data,null,2),"data-output");output.append(pre);};
  async function load(){try{const s=await api("/api/sloth-mode");enabled.checked=s.enabled;inbox.value=s.inbox;interval.value=String(s.interval_minutes);if(s.last_summary){status.textContent=s.enabled?"Scheduled review is enabled. Last summary follows.":"Sloth Mode is off. Last summary follows.";show(s.last_summary);}else status.textContent=s.enabled?"Scheduled review is enabled while LazyDesk is running.":"Sloth Mode is off by default.";}catch(e){status.textContent=e.message;}}
  form.addEventListener("submit",async e=>{e.preventDefault();save.disabled=true;try{const d=await api("/api/sloth-mode",{method:"PUT",body:JSON.stringify({enabled:enabled.checked,inbox:inbox.value.trim(),interval_minutes:Number(interval.value)})});status.textContent=d.enabled?"Sloth Mode enabled. It will prepare reports only while LazyDesk is running.":"Sloth Mode disabled.";show(d);}catch(e){status.textContent=e.message;}finally{save.disabled=false;}});
  run.addEventListener("click",async()=>{run.disabled=true;status.textContent="Reviewing the designated inbox. Files will not be moved.";try{const d=await api("/api/sloth-mode/run",{method:"POST",body:"{}"});status.textContent=d.message;show(d);}catch(e){status.textContent=e.message;}finally{run.disabled=false;}});
  map.addEventListener("click",async()=>{map.disabled=true;status.textContent="Building a local metadata-only workspace map…";try{const path=document.getElementById("relative-path")?.value.trim()||".";const d=await api("/api/insights?relative_path="+encodeURIComponent(path));status.textContent=d.message;show(d);}catch(e){status.textContent=e.message;}finally{map.disabled=false;}});
  load();
})();
