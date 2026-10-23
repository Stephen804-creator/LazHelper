/* Stage M — owner permissions and instruction policies. */
(() => {
  const main = document.querySelector("main");
  if (!main || document.getElementById("owner-controls")) return;
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const card = el("section", undefined, "workspace-card owner-card");
  card.id = "owner-controls";
  card.append(el("p", "STAGE M · YOUR RULES", "eyebrow"));
  card.append(el("h2", "Owner permissions"));
  card.append(el("p", "Choose what LazHelper is allowed to do. File-changing and command-execution permissions start disabled. These controls are enforced by the API, not just by this page."));
  card.append(el("p", "Scope: the configured LazHelper workspace only. Document text and AI suggestions can never grant themselves permissions.", "owner-safety"));
  const modeLabel = el("label", "Working mode");
  modeLabel.htmlFor = "owner-mode";
  const mode = el("select"); mode.id = "owner-mode";
  [["preview","Preview only"],["ask_before_changes","Ask before every change"],["authorised_automation","Authorised automation (still permission-limited)"]].forEach(([v,t]) => {
    const option = el("option",t); option.value=v; mode.append(option);
  });
  card.append(modeLabel, mode);
  const grid = el("div", undefined, "owner-permission-grid");
  const keys = [
    ["read_metadata","Read file names and metadata"],
    ["read_content","Read and search file contents"],
    ["create_files","Create files"],
    ["create_folders","Create folders"],
    ["edit_files","Edit existing files"],
    ["rename_files","Rename files"],
    ["move_files","Move files after approval"],
    ["copy_files","Copy files"],
    ["export_files","Export file contents or plans"],
    ["restore_moves","Undo a previous move"],
    ["delete_files","Delete files"],
    ["run_commands","Run shell commands or programs"]
  ];
  const controls = new Map();
  keys.forEach(([key,label]) => {
    const row=el("label",undefined,"owner-permission");
    const input=el("input"); input.type="checkbox"; input.id="permission-"+key;
    const copy=el("span",label);
    row.append(input,copy); grid.append(row); controls.set(key,input);
  });
  card.append(grid);
  const save = el("button","Save permissions","secondary-button"); save.type="button";
  const status = el("p","Loading current permissions…","status-line"); status.id="owner-permission-status"; status.setAttribute("role","status");
  card.append(save,status);

  const rules = el("section",undefined,"owner-instructions");
  rules.append(el("h3","Your instructions"));
  rules.append(el("p","Save guidance for recommendations. Instructions cannot enable actions, bypass approvals, or override safety checks."));
  const instructionList = el("div",undefined,"owner-instruction-list");
  const scopeLabel=el("label","Apply instruction to"); scopeLabel.htmlFor="instruction-scope";
  const scope=el("select"); scope.id="instruction-scope";
  [["global","All tasks"],["folder","A folder"],["task","A task type"]].forEach(([v,t])=>{const o=el("option",t);o.value=v;scope.append(o);});
  const pathLabel=el("label","Folder path (folder rules only)"); pathLabel.htmlFor="instruction-path";
  const path=el("input"); path.id="instruction-path"; path.placeholder="e.g. School/Assignments"; path.maxLength=500;
  const textLabel=el("label","Instruction"); textLabel.htmlFor="instruction-text";
  const instruction=el("textarea"); instruction.id="instruction-text"; instruction.rows=3; instruction.maxLength=2000; instruction.placeholder="Explain what you want LazHelper to prioritise…";
  const add=el("button","Add instruction","secondary-button"); add.type="button";
  const saveRules=el("button","Save instructions","secondary-button"); saveRules.type="button";
  const ruleStatus=el("p","No custom instructions loaded.","status-line"); ruleStatus.setAttribute("role","status");
  rules.append(scopeLabel,scope,pathLabel,path,textLabel,instruction,add,instructionList,saveRules,ruleStatus);
  card.append(rules);
  const footer=main.querySelector("footer"); if(footer) main.insertBefore(card,footer); else main.append(card);

  const request=async(url,options={})=>{
    const response=await fetch(url,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
    const data=await response.json();
    if(!response.ok) throw new Error(data.detail||"Request failed.");
    return data;
  };
  const show=(node,message,error=false)=>{node.textContent=message;node.classList.toggle("error",error);};
  async function loadPolicy(){
    try{
      const data=await request("/api/permissions");
      keys.forEach(([key])=>controls.get(key).checked=Boolean(data[key]));
      mode.value=data.mode||"preview";
      show(status,"Current permissions loaded.");
    }catch(error){show(status,error.message,true);}
  }
  save.addEventListener("click",async()=>{
    save.disabled=true;
    try{
      const payload={mode:mode.value,scope:"configured_workspace"};
      keys.forEach(([key])=>payload[key]=controls.get(key).checked);
      await request("/api/permissions",{method:"PUT",body:JSON.stringify(payload)});
      show(status,"Permissions saved and enforced by the backend.");
    }catch(error){show(status,error.message,true);}
    finally{save.disabled=false;}
  });
  let items=[];
  function renderRules(){
    instructionList.replaceChildren();
    items.forEach((item,index)=>{
      const row=el("article",undefined,"owner-instruction-row");
      const head=el("strong",item.scope==="folder"?"Folder: "+item.scope_path:item.scope==="task"?"Task type":"Global");
      const body=el("p",item.instruction);
      const toggle=el("input");toggle.type="checkbox";toggle.checked=item.enabled;
      const toggleLabel=el("label","Enabled");toggleLabel.prepend(toggle);
      const remove=el("button","Remove","text-button");remove.type="button";remove.addEventListener("click",()=>{items.splice(index,1);renderRules();});
      toggle.addEventListener("change",()=>item.enabled=toggle.checked);
      row.append(head,body,toggleLabel,remove);instructionList.append(row);
    });
  }
  async function loadRules(){
    try{const data=await request("/api/instructions");items=data.items||[];renderRules();show(ruleStatus,items.length+" instruction rule(s) loaded.");}
    catch(error){show(ruleStatus,error.message,true);}
  }
  scope.addEventListener("change",()=>{path.disabled=scope.value!=="folder";});
  scope.dispatchEvent(new Event("change"));
  add.addEventListener("click",()=>{
    const value=instruction.value.trim();
    if(!value)return show(ruleStatus,"Write an instruction first.",true);
    if(items.length>=50)return show(ruleStatus,"The 50-instruction limit has been reached.",true);
    items.push({scope:scope.value,scope_path:scope.value==="folder"?path.value.trim():"",instruction:value,enabled:true});
    instruction.value="";renderRules();show(ruleStatus,"Instruction added to the unsaved list.");
  });
  saveRules.addEventListener("click",async()=>{
    saveRules.disabled=true;
    try{const data=await request("/api/instructions",{method:"PUT",body:JSON.stringify({items})});items=data.items||[];renderRules();show(ruleStatus,"Instructions saved. They guide recommendations only.");}
    catch(error){show(ruleStatus,error.message,true);}
    finally{saveRules.disabled=false;}
  });
  loadPolicy();loadRules();
})();
