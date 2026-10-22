// Units 6–10: review-first organisation, exact duplicate discovery, queue, journal and preferences.
(() => {
  const $ = id => document.getElementById(id);
  const make = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
  let latestPlan=[];
  const section=make("section",undefined,"workspace-card advanced-card");
  section.id="organize-tools";
  section.append(make("p","UNITS 6–10 · YOUR CHOICE, ALWAYS","eyebrow"),make("h2","A calmer place for every file"));
  section.append(make("p","Build a plan first. Nothing moves until you approve individual moves. Exact duplicate matches are only suggestions; LazyDesk never deletes files.","muted"));
  const controls=make("div",undefined,"advanced-controls");
  const planBtn=make("button","Build organisation preview","primary-action");
  const dupBtn=make("button","Find exact duplicates","secondary-action");
  const queueBtn=make("button","Not Sure queue","secondary-action");
  const journalBtn=make("button","Operation journal / undo","secondary-action");
  const prefsBtn=make("button","Personal preferences","secondary-action");
  [planBtn,dupBtn,queueBtn,journalBtn,prefsBtn].forEach(b=>{b.type="button";controls.append(b);});
  section.append(controls);
  const status=make("p","Ready. Preview first; apply only after checking each move.","status-line"); status.id="advanced-status";status.setAttribute("role","status");section.append(status);
  const output=make("div");output.id="advanced-output";section.append(output);
  const results=$("results-section"); if(results)results.after(section); else document.querySelector("main")?.append(section);
  const setStatus=(s,err=false)=>{status.textContent=s;status.style.color=err?"#a24432":"";};
  const api=async(path,opts={})=>{const r=await fetch(path,{...opts,headers:{"Content-Type":"application/json",...(opts.headers||{})}});const d=await r.json();if(!r.ok)throw Error(d.detail||"Request failed");return d;};
  const clear=()=>output.replaceChildren();
  const renderPlan=plan=>{
    clear(); latestPlan=plan;
    const note=make("p", "Review every destination. Tick only the moves you explicitly approve; conflicts and uncertain files cannot be applied.");output.append(note);
    const table=make("table"),thead=make("thead"),hr=make("tr");
    ["Approve","Source","Proposed destination","Status"].forEach(t=>hr.append(make("th",t)));
    thead.append(hr);const body=make("tbody");
    plan.forEach((item,i)=>{const tr=make("tr"),td=make("td");const cb=document.createElement("input");cb.type="checkbox";cb.checked=false;cb.disabled=item.status!=="ready";cb.setAttribute("aria-label","Approve move for "+item.source);cb.dataset.index=String(i);td.append(cb);tr.append(td,make("td",item.source),make("td",item.destination||"—"),make("td",item.status+" — "+item.reason));body.append(tr);});
    table.append(thead,body);const wrap=make("div",undefined,"table-wrap");wrap.append(table);output.append(wrap);
    const apply=make("button","Apply approved moves");apply.type="button";apply.className="primary-action";
    apply.addEventListener("click",async()=>{const items=[];output.querySelectorAll('input[type="checkbox"]:checked').forEach(cb=>{const x=latestPlan[Number(cb.dataset.index)];items.push({...x,approved:true});});if(!items.length){setStatus("Tick at least one ready move first.",true);return;}if(!confirm("Move "+items.length+" file(s)? No existing file will be overwritten."))return;apply.disabled=true;try{const result=await api("/api/organize/apply",{method:"POST",body:JSON.stringify({items})});setStatus("Applied "+result.files_changed+" move(s). See the journal if you need to undo.");renderSimple(result);}catch(e){setStatus(e.message,true);}finally{apply.disabled=false;}});
    output.append(apply);
  };
  const renderSimple=data=>{clear();const pre=make("pre",JSON.stringify(data,null,2));pre.className="data-output";output.append(pre);};
  planBtn.addEventListener("click",async()=>{setStatus("Building a preview. No files are being changed.");planBtn.disabled=true;try{let files=window.lazyDeskFiles;if(!Array.isArray(files)||!files.length){const d=await api("/api/scan",{method:"POST",body:JSON.stringify({relative_path:$("relative-path")?.value.trim()||"."})});files=d.files||[];}const selected=files.filter(f=>f.readable).map(f=>f.relative_path);if(!selected.length)throw Error("Scan a workspace containing supported files first.");const plan=await api("/api/organize/plan",{method:"POST",body:JSON.stringify({relative_paths:selected})});setStatus("Preview ready: "+plan.ready_count+" ready, "+plan.review_count+" need review, "+plan.conflict_count+" conflicts. Nothing has moved.");renderPlan(plan.plan);}catch(e){setStatus(e.message,true);}finally{planBtn.disabled=false;}});
  dupBtn.addEventListener("click",async()=>{setStatus("Checking exact file contents in bounded chunks…");try{const d=await api("/api/duplicates",{method:"POST",body:JSON.stringify({relative_path:$("relative-path")?.value.trim()||"."})});setStatus(d.message);renderSimple(d);}catch(e){setStatus(e.message,true);}});
  queueBtn.addEventListener("click",async()=>{try{const d=await api("/api/review-queue");clear();if(!d.items.length){output.append(make("p","Your Not Sure queue is empty. Files without matching category rules will appear here after you build a plan."));return;}d.items.forEach(item=>{const row=make("div",undefined,"queue-row");row.append(make("strong",item.path),make("p",item.reason));["reviewed","dismissed"].forEach(decision=>{const b=make("button",decision==="reviewed"?"Mark reviewed":"Dismiss","secondary-action");b.type="button";b.addEventListener("click",async()=>{try{await api("/api/review-queue/decision",{method:"POST",body:JSON.stringify({path:item.path,decision})});row.remove();setStatus("Queue updated.");}catch(e){setStatus(e.message,true);}});row.append(b);});output.append(row);});setStatus("Showing files that need a human decision.");}catch(e){setStatus(e.message,true);}});
  journalBtn.addEventListener("click",async()=>{try{const d=await api("/api/journal");clear();if(!d.operations.length){output.append(make("p","No file moves have been recorded yet."));return;}d.operations.forEach(op=>{const row=make("div",undefined,"journal-row");row.append(make("p","#"+op.id+" · "+op.status+" · "+op.source_path+" → "+op.destination_path));if(op.status==="applied"&&!op.undone_at){const b=make("button","Undo this move","secondary-action");b.type="button";b.addEventListener("click",async()=>{if(!confirm("Restore this file to its original path? Existing files will not be overwritten."))return;try{const result=await api("/api/journal/"+op.id+"/undo",{method:"POST",body:"{}"});setStatus("Restored "+result.restored_path);row.append(make("span"," · undone"));b.disabled=true;}catch(e){setStatus(e.message,true);}});row.append(b);}output.append(row);});setStatus("Journal loaded. Undo is available only when the original path is free.");}catch(e){setStatus(e.message,true);}});
  prefsBtn.addEventListener("click",async()=>{try{const d=await api("/api/preferences");clear();const label=make("label","Category rules (JSON)");const ta=document.createElement("textarea");ta.rows=12;ta.value=JSON.stringify(d.category_rules,null,2);ta.className="preferences-json";label.append(ta);output.append(label);const checks=[];for(const key of ["keep_originals","review_all_moves","include_date_in_plan"]){const l=make("label",key.replaceAll("_"," "));const cb=document.createElement("input");cb.type="checkbox";cb.checked=Boolean(d[key]);checks.push([key,cb]);l.prepend(cb);output.append(l);}const save=make("button","Save preferences","primary-action");save.type="button";save.addEventListener("click",async()=>{try{const rules=JSON.parse(ta.value);const payload={category_rules:rules};checks.forEach(([k,cb])=>payload[k]=cb.checked);const saved=await api("/api/preferences",{method:"PUT",body:JSON.stringify(payload)});setStatus("Preferences saved locally.");renderSimple(saved);}catch(e){setStatus("Preferences not saved: "+e.message,true);}});output.append(save);setStatus("Preferences are stored locally on this computer.");}catch(e){setStatus(e.message,true);}});
  // The original dashboard owns the scan inventory; share a copy after each scan.
  document.addEventListener("click",()=>{const rows=$("file-rows");if(rows){window.lazyDeskFiles=Array.from(rows.querySelectorAll("tr")).map(tr=>{const cells=tr.querySelectorAll("td");return {name:cells[0]?.textContent||"",relative_path:cells[0]?.title||cells[0]?.textContent||"",detected_type:cells[1]?.textContent||"",readable:!cells[3]?.querySelector("button")?.disabled};});}});
})();
