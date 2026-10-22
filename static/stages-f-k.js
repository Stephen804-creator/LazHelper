/* LazHelper Stages F–K. Results are rendered as text; no file mutations are offered here. */
(() => {
  const main = document.querySelector("main");
  if (!main) return;
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const input = (id, label, placeholder = "", value = "") => {
    const wrap = make("div", undefined, "fk-field");
    const lab = make("label", label); lab.htmlFor = id;
    const el = make("input"); el.id = id; el.placeholder = placeholder; el.value = value; el.autocomplete = "off";
    wrap.append(lab, el); return {wrap, el};
  };
  const button = (label, action) => {
    const b = make("button", label, "secondary-button"); b.type = "button"; b.dataset.fkAction = action; return b;
  };
  const footer = main.querySelector("footer");
  const section = make("section", undefined, "workspace-card fk-card");
  section.id = "workspace-advanced";
  section.append(make("p", "STAGES F–K · RECOVERY, PROJECTS & LOCAL WORKFLOWS", "eyebrow"));
  section.append(make("h2", "Keep your work recoverable and connected."));
  section.append(make("p", "Review history, set up study or project workspaces, inspect ZIP archives safely, ask questions against local documents, and save repeatable read-only checks."));
  const root = () => (document.getElementById("relative-path")?.value || ".").trim() || ".";
  const status = make("p", "Choose an action. These tools will not move, rename, overwrite, extract, or delete workspace files.", "status-line");
  status.id = "fk-status"; status.setAttribute("role", "status");
  const output = make("div", undefined, "fk-output"); output.id = "fk-output"; output.setAttribute("aria-live", "polite");

  const recovery = make("div", undefined, "fk-panel");
  recovery.append(make("h3", "F · Recovery history"));
  recovery.append(make("p", "Export your operation journal as portable JSON or CSV."));
  recovery.append(button("Export history as JSON", "recovery-json"), button("Export history as CSV", "recovery-csv"));

  const project = make("form", undefined, "fk-panel fk-form"); project.id = "fk-project-form";
  project.append(make("h3", "G · Project / study workspace"));
  project.append(make("p", "Save a project profile and suggested folder structure. This records metadata only; it does not create folders."));
  const pname=input("fk-project-name","Workspace name","e.g. Cloud Computing 200L");
  const pkindWrap=make("div",undefined,"fk-field"); const pkindLabel=make("label","Workspace type"); pkindLabel.htmlFor="fk-project-kind";
  const pkind=make("select"); pkind.id="fk-project-kind";
  [["study","Study"],["research","Research"],["work","Work"],["development","Development"],["personal","Personal"],["other","Other"]].forEach(([v,l])=>{const o=make("option",l);o.value=v;pkind.append(o);});
  pkindWrap.append(pkindLabel,pkind);
  const pdesc=input("fk-project-description","Description","What is this workspace for?");
  const pfolder=input("fk-project-folder","Folder inside configured workspace",".",root());
  const ptags=input("fk-project-tags","Tags (comma-separated)","cloud, networking, assignments");
  const pstructure=input("fk-project-structure","Suggested folders (comma-separated)","Lecture Notes, Assignments, Research, Presentations");
  project.append(pname.wrap,pkindWrap,pdesc.wrap,pfolder.wrap,ptags.wrap,pstructure.wrap);
  const saveProject=make("button","Save project profile");saveProject.type="submit";project.append(saveProject);

  const archive=make("form",undefined,"fk-panel fk-form");archive.id="fk-archive-form";
  archive.append(make("h3","H · Safe ZIP inspection"));
  archive.append(make("p","Inspect an archive's contents and optionally preview small text files. Nothing is extracted."));
  const azip=input("fk-archive-path","ZIP path inside workspace","downloads/assignment.zip");
  const aPreviewWrap=make("label","Preview small text entries","fk-check");const aPreview=make("input");aPreview.type="checkbox";aPreview.id="fk-archive-preview";aPreviewWrap.prepend(aPreview);
  archive.append(azip.wrap,aPreviewWrap);const aSubmit=make("button","Inspect ZIP archive");aSubmit.type="submit";archive.append(aSubmit);

  const command=make("form",undefined,"fk-panel fk-form");command.id="fk-command-form";
  command.append(make("h3","I · Natural-language command preview"));
  command.append(make("p","Describe what you want. LazHelper maps supported requests to a preview; unsupported or destructive commands are not executed."));
  const cmd=input("fk-command","What would you like LazHelper to do?","Find my cloud computing notes");
  command.append(cmd.wrap);const cmdSubmit=make("button","Preview command");cmdSubmit.type="submit";command.append(cmdSubmit);

  const knowledge=make("form",undefined,"fk-panel fk-form");knowledge.id="fk-knowledge-form";
  knowledge.append(make("h3","J · Ask your local documents"));
  knowledge.append(make("p","Find relevant passages in supported files and show their source. This version retrieves evidence locally; it does not invent an answer or send documents to an AI service."));
  const question=input("fk-question","Your question","What services are common in cloud computing?");
  knowledge.append(question.wrap);const qSubmit=make("button","Find evidence");qSubmit.type="submit";knowledge.append(qSubmit);

  const workflows=make("div",undefined,"fk-panel");
  workflows.append(make("h3","K · Reusable read-only workflows"));
  workflows.append(make("p","Save one or more supported checks as a reusable workflow. Workflow runs only analyse files."));
  const wname=input("fk-workflow-name","Workflow name","Weekly workspace review");
  const wactionWrap=make("div",undefined,"fk-field");const wactionLabel=make("label","First check");wactionLabel.htmlFor="fk-workflow-action";
  const waction=make("select");waction.id="fk-workflow-action";
  [["health_report","Workspace health"],["search","Search content"],["relationships","Related files"],["duplicates","Duplicates and versions"],["knowledge_map","Knowledge map"]].forEach(([v,l])=>{const o=make("option",l);o.value=v;waction.append(o);});
  wactionWrap.append(wactionLabel,waction);
  const wquery=input("fk-workflow-query","Search phrase (only used for Search)","cloud computing");
  const saveWorkflow=button("Save workflow","save-workflow");
  const listWorkflows=button("Refresh saved workflows","list-workflows");
  workflows.append(wname.wrap,wactionWrap,wquery.wrap,saveWorkflow,listWorkflows);

  const panels=make("div",undefined,"fk-grid");
  [recovery,project,archive,command,knowledge,workflows].forEach(p=>panels.append(p));
  section.append(panels,status,output);
  if(footer) main.insertBefore(section,footer); else main.append(section);

  function setStatus(text,error=false){status.textContent=text;status.classList.toggle("error",error);}
  function show(title, description, rows=[]){
    const card=make("article",undefined,"fk-result");
    card.append(make("h3",title));
    if(description)card.append(make("p",description));
    if(rows.length){const ul=make("ul");rows.slice(0,100).forEach(row=>ul.append(make("li",typeof row==="string"?row:JSON.stringify(row))));card.append(ul);}
    output.prepend(card);
  }
  async function api(url, options={}){
    const response=await fetch(url,options);let data;
    try{data=await response.json();}catch{throw new Error("The server returned an unreadable response.");}
    if(!response.ok)throw new Error(data.detail||"Request failed.");
    return data;
  }
  async function run(label,fn){
    setStatus(label+"…");
    try{const data=await fn();setStatus(data.message||"Completed.");return data;}
    catch(e){setStatus(e.message||"Request failed.",true);throw e;}
  }
  function download(name,text,type){
    const url=URL.createObjectURL(new Blob([text],{type}));
    const a=make("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);
  }
  recovery.addEventListener("click",async e=>{
    const b=e.target.closest("[data-fk-action]");if(!b)return;
    const format=b.dataset.fkAction==="recovery-csv"?"csv":"json";
    try{const d=await run("Exporting history",()=>api("/api/recovery/history?limit=200&export_format="+format));
      const text=format==="csv"?d.content:JSON.stringify(d.operations,null,2);
      download(d.filename,text,format==="csv"?"text/csv":"application/json");
      show("Recovery export",`${d.count} journal records exported as ${format.toUpperCase()}.`);
    }catch{}
  });
  project.addEventListener("submit",async e=>{
    e.preventDefault();
    try{const d=await run("Saving project profile",()=>api("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      name:pname.el.value,kind:pkind.value,description:pdesc.el.value,folder_path:pfolder.el.value||".",
      tags:ptags.el.value.split(",").map(x=>x.trim()).filter(Boolean),
      structure:pstructure.el.value.split(",").map(x=>x.trim()).filter(Boolean)
    })}));
    show("Project workspace saved",`${d.name} · ${d.kind}. Metadata only; no folders were created.`,d.suggested_structure||[]);
    }catch{}
  });
  archive.addEventListener("submit",async e=>{
    e.preventDefault();
    try{const d=await run("Inspecting ZIP archive",()=>api("/api/archive/inspect",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({relative_path:azip.el.value,max_entries:500,preview_text:aPreview.checked})}));
      show(`ZIP inventory: ${d.archive}`,`${d.entries_inspected}/${d.entries_total} entries inspected · ${d.flagged_entries} flagged · extracted: ${d.extracted}`,
        d.entries.map(x=>`${x.name} · ${x.size_bytes} bytes${x.warnings.length?" · WARNINGS: "+x.warnings.join(", "):""}${x.text_preview?" · preview: "+x.text_preview:""}`));
    }catch{}
  });
  command.addEventListener("submit",async e=>{
    e.preventDefault();
    try{const d=await run("Previewing command",()=>api("/api/commands/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:cmd.el.value,relative_path:root()})}));
      show(d.understood?"Command understood: "+d.intent:"Command needs different wording",d.proposed_action||d.message,[JSON.stringify(d.parameters),d.requires_confirmation?"Requires confirmation before any supported action.":"No action proposed."]);
    }catch{}
  });
  knowledge.addEventListener("submit",async e=>{
    e.preventDefault();
    try{const d=await run("Searching local evidence",()=>api("/api/knowledge/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:question.el.value,relative_path:root(),max_sources:5})}));
      show("Evidence for: "+d.question,d.answer,d.sources.map(s=>`${s.path} · relevance ${Math.round(s.score*100)}% · “${s.evidence}”`));
    }catch{}
  });
  async function refreshWorkflows(){
    try{const d=await run("Loading workflows",()=>api("/api/workflows"));
      show("Saved workflows",`${d.count} saved workflow(s).`,d.workflows.map(w=>`#${w.id} ${w.name} · ${w.steps.map(s=>s.action).join(" → ")}`));
    }catch{}
  }
  workflows.addEventListener("click",async e=>{
    const b=e.target.closest("[data-fk-action]");if(!b)return;
    if(b.dataset.fkAction==="list-workflows"){await refreshWorkflows();return;}
    if(b.dataset.fkAction==="save-workflow"){
      const params={relative_path:root()};
      if(waction.value==="search")params.query=wquery.el.value.trim();
      try{const d=await run("Saving workflow",()=>api("/api/workflows",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:wname.el.value,description:"Saved from the LazHelper workspace interface.",steps:[{action:waction.value,parameters:params}]})}));
        show("Workflow saved",`#${d.id} ${d.name}. Run it through the workflow API; actions are read-only.`,d.steps.map(s=>s.action));
      }catch{}
    }
  });
  refreshWorkflows();
})();
