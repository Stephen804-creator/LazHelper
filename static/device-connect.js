/* Laz Helper local-device connection. Additive module: it does not replace the existing interface. */
(() => {
  "use strict";
  const AGENT = "http://127.0.0.1:43179/v1";
  const TOKEN_KEY = "laz-helper-connector-token-v1";
  const DISMISS_KEY = "laz-helper-connector-welcome-dismissed-v1";
  const RELEASES = "https://github.com/Stephen804-creator/LazHelper/releases/latest";
  const GUIDE = "https://github.com/Stephen804-creator/LazHelper/tree/main/connector";
  const CAPABILITIES = [["read","Read files"],["create","Create files"],["edit","Edit files"],["move","Move files"],["rename","Rename files"],["delete","Delete to quarantine"]];
  const $ = (tag, cls, text) => { const n=document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; };
  let connected=false, agentVersion="", pollTimer=null;
  const state = { token: localStorage.getItem(TOKEN_KEY) || "", connection:null };
  const launcher = $("button","laz-connect-launcher");
  launcher.type="button"; launcher.setAttribute("aria-label","Connect Device"); launcher.innerHTML='<span class="laz-connect-dot" aria-hidden="true"></span><span>Connect Device</span>';
  const backdrop = $("div","laz-connect-backdrop");
  const dialog = $("section","laz-connect-dialog");
  dialog.setAttribute("role","dialog"); dialog.setAttribute("aria-modal","true"); dialog.setAttribute("aria-labelledby","laz-connect-title");
  backdrop.append(dialog); document.body.append(launcher,backdrop);
  function button(label, cls, fn) { const b=$("button","laz-connect-btn"+(cls?" "+cls:""),label); b.type="button"; if(fn)b.addEventListener("click",fn); return b; }
  function field(labelText, input) { const wrap=$("label","laz-connect-field"); wrap.append($("span","",labelText),input); return wrap; }
  function status(message, kind="info") { const s=$("p","laz-connect-status",message); s.dataset.kind=kind; s.setAttribute("role","status"); return s; }
  function open() { backdrop.classList.add("is-open"); render(); const closeBtn=dialog.querySelector(".laz-connect-close"); if(closeBtn)closeBtn.focus(); }
  function closeModal() { localStorage.setItem(DISMISS_KEY,"1"); backdrop.classList.remove("is-open"); }
  function updateLauncher() { launcher.dataset.state=connected?"connected":"disconnected"; launcher.querySelector("span:last-child").textContent=connected?"Device connected":"Connect Device"; launcher.setAttribute("aria-label",connected?"Device connected; open device permissions":"Connect Device"); }
  function setStatus(message, kind="info") { const node=dialog.querySelector("#laz-connect-status"); if(node){node.textContent=message;node.dataset.kind=kind;} }
  async function request(path, options={}, timeoutMs=6000) {
    const headers={"Content-Type":"application/json",...(state.token?{"Authorization":"Bearer "+state.token}:{})};
    const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),timeoutMs);
    try {
      const response=await fetch(AGENT+path,{...options,headers:{...headers,...(options.headers||{})},signal:controller.signal,cache:"no-store"});
      let data={}; try{data=await response.json()}catch{}
      if(!response.ok)throw new Error(data.detail||"The connector rejected the request.");
      return data;
    } finally {clearTimeout(timer);}
  }
  async function checkAgent() {
    try {
      const health=await request("/health");
      if(health.identity!=="laz-helper-local-connector")throw new Error("A service responded, but it is not Laz Connector.");
      agentVersion=health.version||"";
      if(state.token) {
        try { state.connection=await request("/connection"); connected=state.connection.connected===true; }
        catch { connected=false; }
      } else connected=false;
      updateLauncher();
      return {installed:true,health};
    } catch(e) {
      connected=false; state.connection=null; updateLauncher();
      return {installed:false,error:e.name==="AbortError"?"The connector did not respond in time.":e.message};
    }
  }
  function render() {
    dialog.replaceChildren();
    const heading=$("div","laz-connect-heading");
    const titleWrap=$("div","");
    titleWrap.append($("h2","","Connect your device"),$("p","laz-connect-muted","Laz Helper needs the local connector to work with files on this computer. The hosted website cannot read your private device folders by itself."));
    const closeBtn=button("×","",closeModal); closeBtn.classList.add("laz-connect-close"); closeBtn.setAttribute("aria-label","Close connection panel");
    heading.append(titleWrap,closeBtn); dialog.append(heading);
    const s=status(connected?"Your device is connected.":"Checking for Laz Connector…",connected?"ok":"info"); s.id="laz-connect-status"; dialog.append(s);
    if(!connected) {
      const pairLabel=$("label","laz-connect-field");
      pairLabel.append($("span","","One-time pairing code (optional; native approval is tried first)"));
      const code=$("input",""); code.type="text"; code.autocomplete="one-time-code"; code.inputMode="text"; code.maxLength=7; code.placeholder="Leave blank for OS confirmation"; code.setAttribute("aria-label","Optional one-time pairing code"); pairLabel.append(code); dialog.append(pairLabel);dialog.append($("p","laz-connect-muted","Click Pair this device to approve the connection in a local system dialog. If the dialog is unavailable, enter the one-time code printed by the connector."));
      dialog.append(button("Check connector","",async()=>{setStatus("Checking for Laz Connector…");const r=await checkAgent();if(r.installed)setStatus("Connector found"+(agentVersion?" · version "+agentVersion:"")+". Enter the one-time code to pair.","ok");else setStatus("Connector not detected. Install and start Laz Connector, then try again. "+r.error,"error");}));
      dialog.append(button("Pair this device","primary",async()=>{
        const value=code.value.trim().toUpperCase();
        if(!value){setStatus("Enter the one-time pairing code printed by Laz Connector.","error");return;}
        const b=dialog.querySelector(".laz-connect-btn.primary"); b.disabled=true;
        try{const r=await request("/pair",{method:"POST",body:JSON.stringify(value?{code:value}:{})},60000);state.token=r.token;localStorage.setItem(TOKEN_KEY,r.token);connected=true;state.connection=await request("/connection");updateLauncher();localStorage.setItem(DISMISS_KEY,"1");render();setStatus("Device connected. Your pairing will be reused on future visits.","ok");await loadPermissions();}
        catch(e){setStatus(e.message,"error");}
        finally{if(b.isConnected)b.disabled=false;}
      }));
      const info=$("p","laz-connect-muted","If the connector is missing, install a Laz Connector release. If no release is published yet, follow the development instructions in the repository guide.");
      const links=$("p","laz-connect-muted"); const releases=$("a","", "Download connector");releases.href=RELEASES;releases.target="_blank";releases.rel="noopener noreferrer";const guide=$("a","","Installation guide");guide.href=GUIDE;guide.target="_blank";guide.rel="noopener noreferrer";links.append(releases,$("span",""," · "),guide);dialog.append(info,links);
      return;
    }
    dialog.append($("p","laz-connect-muted","Connector "+agentVersion+" · paired browser token stored on this device."));
    dialog.append(button("Refresh connection","",async()=>{const r=await checkAgent();setStatus(r.installed?(connected?"Connection is healthy.":"Connector is running but pairing needs attention."):"Connector unavailable. Start it again to reconnect.",connected?"ok":"error");if(connected)await loadPermissions();}));
    const section=$("div","laz-connect-section");section.append($("h3","","Permissions and approvals"));
    const scope=$("select","");scope.id="laz-scope";[["permitted_locations","All explicitly permitted locations"],["selected_folders","Selected folders only"],["selected_files","Selected files only"],["ask_every_time","Ask every time"]].forEach(([v,t])=>{const o=$("option","",t);o.value=v;scope.append(o);});
    const approval=$("select","");approval.id="laz-approval";[["ask_every_time","Ask before every file change"],["routine_auto","Auto-approve routine create/edit only"]].forEach(([v,t])=>{const o=$("option","",t);o.value=v;approval.append(o);});
    section.append(field("Access scope",scope),field("Approval preference",approval));
    section.append($("p","laz-connect-muted","No folders or files are granted by default. Read, create, edit, move, rename, and delete-to-quarantine permissions are separate. Move, rename, and delete always require explicit approval. Protected operating-system locations are blocked."));
    const perms=$("div","laz-connect-perms");
    CAPABILITIES.forEach(([key,label])=>{const l=$("label","");const cb=$("input","");cb.type="checkbox";cb.value=key;cb.checked=key==="read";cb.dataset.capability=key;l.append(cb,$("span","",label));perms.append(l);});
    section.append(perms);
    section.append(button("Choose folder…","primary",()=>pick("folder")),button("Choose file…","",()=>pick("file")));
    const grants=$("div","");grants.id="laz-connect-grants";grants.append($("p","laz-connect-muted","Loading permission grants…"));section.append(grants);
    section.append(button("Save permission preferences","",async()=>{try{await request("/permissions/preferences",{method:"PUT",body:JSON.stringify({scope_mode:scope.value,approval_mode:approval.value})});setStatus("Permission preferences saved.","ok");await loadPermissions();}catch(e){setStatus(e.message,"error");}}));
    const duplicateSection=$("div","laz-connect-section");duplicateSection.append($("h3","","Duplicate review"));
    duplicateSection.append($("p","laz-connect-muted","Find exact copies inside a folder you have granted read access to. This scan is read-only and never deletes files."));
    const duplicateFolder=$("select","");duplicateFolder.id="laz-duplicate-folder";
    duplicateSection.append(field("Granted folder to scan",duplicateFolder));
    const duplicateResults=$("div","");duplicateResults.id="laz-connect-duplicates";
    duplicateSection.append(button("Find exact duplicates","",async()=>{if(!duplicateFolder.value){setStatus("Grant read access to a folder first.","error");return;}setStatus("Checking for exact copies…");try{const result=await request("/duplicates?path="+encodeURIComponent(duplicateFolder.value)+"&approved=true");duplicateResults.replaceChildren();if(!result.groups.length)duplicateResults.append($("p","laz-connect-muted","No exact duplicate groups found."));result.groups.forEach(g=>{const card=$("div","laz-connect-grant"),left=$("div","");left.append($("strong","",g.count+" identical files · "+g.size_bytes+" bytes each"));g.files.forEach(p=>left.append($("small","",p)));card.append(left);duplicateResults.append(card);});if(result.truncated)duplicateResults.append($("p","laz-connect-muted","The scan reached its safety limit; results may be incomplete."));setStatus(result.message,"ok");}catch(e){setStatus(e.message,"error");}}),duplicateResults);
    const activity=$("div","laz-connect-section");activity.append($("h3","","Recent activity"));const activityList=$("div","");activityList.id="laz-connect-activity";activityList.append($("p","laz-connect-muted","Loading activity…"));activity.append(activityList);
    dialog.append(section,duplicateSection,activity);
    loadPermissions();
  }
  async function pick(kind) {
    const caps=[...dialog.querySelectorAll("[data-capability]:checked")].map(x=>x.dataset.capability);
    if(!caps.length){setStatus("Choose at least one capability before granting access.","error");return;}
    setStatus("Choose the "+kind+" in the operating-system dialog…");
    try{const result=await request("/permissions/pick",{method:"POST",body:JSON.stringify({kind,capabilities:caps})});if(result.cancelled){setStatus("No permission was added.","info");return;}setStatus("Permission granted for "+result.grant.label+".","ok");await loadPermissions();}
    catch(e){setStatus(e.message,"error");return null;}
  }
  async function loadPermissions() {
    if(!connected)return;
    try {
      const p=await request("/permissions");
      const scope=dialog.querySelector("#laz-scope"),approval=dialog.querySelector("#laz-approval");
      if(scope)scope.value=p.scope_mode;if(approval)approval.value=p.approval_mode;
      const duplicateFolder=dialog.querySelector("#laz-duplicate-folder");
      if(duplicateFolder){const previous=duplicateFolder.value;duplicateFolder.replaceChildren();p.grants.filter(g=>g.kind==="folder"&&g.capabilities.includes("read")&&p.scope_mode!=="selected_files").forEach(g=>{const o=$("option","",g.label+" — "+g.path);o.value=g.path;duplicateFolder.append(o);});if([...duplicateFolder.options].some(o=>o.value===previous))duplicateFolder.value=previous;}
      const list=dialog.querySelector("#laz-connect-grants");
      if(list){list.replaceChildren();if(!p.grants.length)list.append($("p","laz-connect-muted","No file or folder grants yet."));
        p.grants.forEach(g=>{const row=$("div","laz-connect-grant"),left=$("div","");left.append($("strong","",g.label+" · "+g.kind),$("small","",g.path),$("small","",g.capabilities.join(", ")));const revoke=button("Revoke","",async()=>{try{await request("/permissions/grants/"+encodeURIComponent(g.id),{method:"DELETE"});setStatus("Permission revoked.","ok");await loadPermissions();}catch(e){setStatus(e.message,"error");}});row.append(left,revoke);list.append(row);});}
      const activity=await request("/activity?limit=12");const box=dialog.querySelector("#laz-connect-activity");
      if(box){box.replaceChildren();if(!activity.items.length)box.append($("p","laz-connect-muted","No connector activity yet."));activity.items.forEach(i=>{const row=$("div","laz-connect-grant");row.append($("div","",i.action+" · "+i.status),$("small","laz-connect-muted",new Date(i.at).toLocaleString()+" — "+i.detail));box.append(row);});}
    } catch(e){setStatus(e.message,"error");}
  }
  window.LazHelperConnector = {
    get connected(){ return connected; },
    request,
    open,
    async chooseFolderForDownloads(){
      if(!connected){open();setStatus("Connect Laz Connector first, then choose your Downloads folder.","info");return null;}
      open();
      await new Promise(resolve=>setTimeout(resolve,0));
      dialog.querySelectorAll("[data-capability]").forEach(cb=>{cb.checked=cb.dataset.capability==="read";});
      const grant=await pick("folder");
      return grant && grant.kind==="folder" && grant.capabilities.includes("read") ? grant : null;
    }
  };
  launcher.addEventListener("click",open);
  backdrop.addEventListener("click",e=>{if(e.target===backdrop)closeModal();});
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&backdrop.classList.contains("is-open"))closeModal();});
  async function start() {
    if(!localStorage.getItem(DISMISS_KEY)) {
      open();
      const s=dialog.querySelector("#laz-connect-status");
      if(s)s.textContent="Welcome. Connect Laz Connector to work with files on this device.";
      const dismiss=button("Not now","",closeModal);dialog.append(dismiss);
    }
    await checkAgent();
    if(state.token&&connected){localStorage.setItem(DISMISS_KEY,"1");if(backdrop.classList.contains("is-open"))render();}
    if(!pollTimer)pollTimer=setInterval(async()=>{await checkAgent();if(backdrop.classList.contains("is-open"))render();},30000);
  }
  start();
})();
