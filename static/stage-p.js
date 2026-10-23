/* Stage P — truthful in-flight progress and local API activity history. */
(() => {
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const header=document.querySelector(".topbar");
  const progress=el("section",undefined,"request-progress");progress.id="request-progress";progress.hidden=true;
  const label=el("p","A request is running. Completion percentage is not available for this operation.","request-progress-label");
  const bar=el("progress");bar.setAttribute("aria-label","Request in progress");bar.removeAttribute("value");
  progress.append(label,bar);
  if(header)header.insertAdjacentElement("afterend",progress);
  let active=0,hideTimer=null;
  const originalFetch=window.fetch.bind(window);
  window.fetch=async(input,init)=>{
    let api=false,activityEndpoint=false;
    try{
      const raw=input instanceof Request?input.url:String(input);
      const url=new URL(raw,window.location.href);
      api=url.origin===window.location.origin&&url.pathname.startsWith("/api/");
      activityEndpoint=url.pathname==="/api/activity";
    }catch(_){}
    const tracked=api&&!activityEndpoint;
    if(tracked){
      active++;clearTimeout(hideTimer);progress.hidden=false;
      label.textContent=active===1?"A request is running. Completion percentage is not available for this operation.":active+" requests are running. Completion percentage is not available.";
    }
    try{
      const response=await originalFetch(input,init);
      if(tracked&&!response.ok)label.textContent="A request returned HTTP "+response.status+". Review the Activity Centre for details.";
      return response;
    }catch(error){
      if(tracked)label.textContent="A request failed to connect. Review the Activity Centre and try again.";
      throw error;
    }finally{
      if(tracked){
        active=Math.max(0,active-1);
        if(active===0)hideTimer=setTimeout(()=>{progress.hidden=true;},500);
        else label.textContent=active+" request(s) still running. Completion percentage is not available.";
      }
    }
  };
  const main=document.querySelector("main");
  if(!main||document.getElementById("activity-centre"))return;
  const card=el("section",undefined,"workspace-card activity-card");card.id="activity-centre";
  card.append(el("p","STAGE P · PROGRESS & ACTIVITY","eyebrow"));
  card.append(el("h2","See what LazHelper actually did"));
  card.append(el("p","The progress strip above appears only while API requests are in flight. This history records routes, status codes, and measured durations—not prompts or document contents."));
  const actions=el("div",undefined,"activity-actions");
  const refresh=el("button","Refresh activity","secondary-button");refresh.type="button";
  const status=el("p","Activity has not been loaded yet.","status-line");status.setAttribute("role","status");
  actions.append(refresh);
  const activeList=el("div",undefined,"activity-active");
  const list=el("div",undefined,"activity-list");
  card.append(actions,status,activeList,el("h3","Recent requests"),list);
  const footer=main.querySelector("footer");if(footer)main.insertBefore(card,footer);else main.append(card);
  const show=(message,error=false)=>{status.textContent=message;status.classList.toggle("error",error);};
  const render=(data)=>{
    activeList.replaceChildren();
    if(data.active?.length){
      activeList.append(el("h3","Currently running"));
      data.active.forEach(item=>{
        const row=el("article",undefined,"activity-row is-running");
        row.append(el("strong",item.method+" "+item.path),el("span","Running"));
        activeList.append(row);
      });
    }
    list.replaceChildren();
    if(!data.events?.length){list.append(el("p","No completed API requests recorded yet."));return;}
    data.events.forEach(item=>{
      const row=el("article",undefined,"activity-row");
      const ok=item.status_code>=200&&item.status_code<400;
      row.append(el("strong",item.method+" "+item.path));
      row.append(el("span","HTTP "+item.status_code,ok?"activity-success":"activity-failure"));
      row.append(el("p",new Date(item.started_at).toLocaleString()+" · "+item.duration_ms+" ms"));
      list.append(row);
    });
  };
  async function load(){
    refresh.disabled=true;show("Loading recorded activity…");
    try{
      const response=await originalFetch("/api/activity?limit=50",{headers:{Accept:"application/json"}});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Activity could not be loaded.");
      render(data);show(data.count+" completed request(s) in local history; retention is limited to "+data.retention_limit+". "+data.privacy);
    }catch(error){show(error.message||"Activity could not be loaded.",true);}
    finally{refresh.disabled=false;}
  }
  refresh.addEventListener("click",load);
  load();
})();
