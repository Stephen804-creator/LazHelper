/* Local Downloads page. Files remain on the user's device; only metadata is displayed. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const folderSelect = $("downloads-folder");
  const rows = $("downloads-rows");
  const status = $("downloads-status");
  const badge = $("downloads-connection-state");
  const connectButton = $("downloads-connect-folder");
  const refreshButton = $("downloads-refresh");
  const empty = $("downloads-empty");
  if (!folderSelect || !rows) return;
  const KEY = "laz-helper-downloads-folder-v1";
  let poll = null;
  let scopeMode = "ask_every_time";
  let connectorAvailable = false;
  const make = (tag, cls, text) => { const el=document.createElement(tag); if(cls)el.className=cls; if(text!==undefined)el.textContent=text; return el; };
  const setStatus = (message, kind="info") => { status.textContent=message; status.dataset.kind=kind; };
  const bytes = (n) => {
    if(n===null||n===undefined)return "—";
    if(n<1024)return n+" B";
    const units=["KB","MB","GB","TB"]; let value=n/1024, i=0;
    while(value>=1024&&i<units.length-1){value/=1024;i++;}
    return value.toFixed(value<10?1:0)+" "+units[i];
  };
  function stopPolling(){ if(poll){clearInterval(poll);poll=null;} }
  function startPolling(){
    stopPolling();
    if(scopeMode!=="ask_every_time" && document.visibilityState==="visible") {
      poll=setInterval(()=>{ if(document.visibilityState==="visible")loadFiles({automatic:true}); },15000);
    }
  }
  function showDisconnected(message){
    connectorAvailable=false; badge.textContent="Connector disconnected"; badge.dataset.state="disconnected";
    folderSelect.replaceChildren();folderSelect.append(new Option("Connect a folder first",""));
    rows.replaceChildren();empty.hidden=false;empty.textContent="Connect Laz Connector and grant read access to your Downloads folder to see downloaded files.";
    refreshButton.disabled=true;stopPolling();setStatus(message,"error");
  }
  async function loadPermissions(preferredPath){
    const api=window.LazHelperConnector;
    if(!api || !api.connected){showDisconnected("Laz Connector is not connected. Use Connect Device, then return here.");return;}
    try{
      const p=await api.request("/permissions");
      connectorAvailable=true;scopeMode=p.scope_mode||"ask_every_time";
      badge.textContent="Device connected";badge.dataset.state="connected";
      const folders=p.grants.filter(g=>g.kind==="folder"&&g.capabilities.includes("read")&&scopeMode!=="selected_files");
      const saved=preferredPath||sessionStorage.getItem(KEY)||"";
      folderSelect.replaceChildren();
      if(!folders.length){
        folderSelect.append(new Option("No read-enabled folders yet",""));
        refreshButton.disabled=true;
        setStatus("Choose your Downloads folder below. Laz Helper will request read access only.","info");
      }else{
        folders.sort((a,b)=>{
          const ad=/downloads/i.test(a.label+" "+a.path)?0:1;
          const bd=/downloads/i.test(b.label+" "+b.path)?0:1;
          return ad-bd || a.label.localeCompare(b.label);
        });
        folders.forEach(g=>folderSelect.append(new Option(g.label+" — "+g.path,g.path)));
        const chosen=folders.find(g=>g.path===saved)||folders.find(g=>/downloads/i.test(g.label+" "+g.path))||folders[0];
        folderSelect.value=chosen.path;sessionStorage.setItem(KEY,chosen.path);
        refreshButton.disabled=false;
        setStatus(scopeMode==="ask_every_time"?"Folder connected. Each refresh will ask for approval.":"Folder connected. This page checks for new files while it remains open.","ok");
      }
      startPolling();
    }catch(e){showDisconnected(e.message||"Could not read connector permissions.");}
  }
  async function loadFiles(options={}){
    const api=window.LazHelperConnector;
    if(!api || !api.connected){showDisconnected("Laz Connector is not connected. Reconnect and try again.");return;}
    const path=folderSelect.value;
    if(!path){setStatus("Choose your Downloads folder first.");return;}
    if(scopeMode==="ask_every_time" && !options.automatic){
      if(!window.confirm("Allow Laz Helper to read the selected folder and list its file names for this refresh?"))return;
    }
    refreshButton.disabled=true;
    setStatus(options.automatic?"Checking for new downloads…":"Reading the selected Downloads folder…");
    try{
      const data=await api.request("/files?path="+encodeURIComponent(path)+"&approved=true");
      rows.replaceChildren();
      const items=(data.items||[]).sort((a,b)=>b.modified_at.localeCompare(a.modified_at));
      items.forEach(item=>{
        const tr=document.createElement("tr");
        const name=make("td");name.append(make("div","downloads-file-name",item.name),make("div","downloads-kind",item.kind==="folder"?"Folder":"File"));
        const type=make("td","",item.kind==="folder"?"Folder":(item.name.includes(".")?item.name.split(".").pop().toUpperCase()+" file":"File"));
        const size=make("td","",bytes(item.size_bytes));
        const modified=make("td","",item.modified_at?new Date(item.modified_at).toLocaleString():"—");
        tr.append(name,type,size,modified);rows.append(tr);
      });
      empty.hidden=items.length>0;empty.textContent=items.length?"":"No files found in this folder yet.";
      setStatus(items.length+" item"+(items.length===1?"":"s")+" found in "+data.path+". "+(scopeMode==="ask_every_time"?"No background refresh is running because your scope requires approval each time.":"The list will refresh while this page is open."),"ok");
    }catch(e){setStatus(e.message||"Could not read the selected folder. Check its permission grant.","error");}
    finally{refreshButton.disabled=false;}
  }
  connectButton.addEventListener("click",async()=>{
    const api=window.LazHelperConnector;
    if(!api){setStatus("The connector interface is still loading. Try again in a moment.");return;}
    if(!api.connected){api.open();setStatus("Connect your device first. Then choose Downloads folder here.");return;}
    connectButton.disabled=true;
    try{
      const grant=await api.chooseFolderForDownloads();
      if(grant){sessionStorage.setItem(KEY,grant.path);await loadPermissions(grant.path);await loadFiles({automatic:false});}
      else await loadPermissions();
    }catch(e){setStatus(e.message||"Folder selection did not complete.","error");}
    finally{connectButton.disabled=false;}
  });
  refreshButton.addEventListener("click",()=>loadFiles({automatic:false}));
  folderSelect.addEventListener("change",()=>{sessionStorage.setItem(KEY,folderSelect.value);loadFiles({automatic:false});});
  document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="hidden")stopPolling();else if(connectorAvailable){startPolling();}});
  window.addEventListener("focus",()=>{if(connectorAvailable)loadPermissions(folderSelect.value);});
  async function init(){
    await new Promise(resolve=>setTimeout(resolve,0));
    if(window.LazHelperConnector&&window.LazHelperConnector.connected)await loadPermissions();
    else showDisconnected("Connect Laz Connector to see files downloaded from websites.");
    setInterval(async()=>{const api=window.LazHelperConnector;if(!api||!api.connected){showDisconnected("Laz Connector is not running. Start it again to reconnect.");}else if(!connectorAvailable){await loadPermissions();}},5000);
  }
  init();
})();
