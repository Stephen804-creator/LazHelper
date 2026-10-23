/* Stage Q — selectable assistant profiles and opt-in preference memory. */
(() => {
  const main=document.querySelector("main");
  if(!main||document.getElementById("assistant-profile"))return;
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const card=el("section",undefined,"workspace-card profile-card");card.id="assistant-profile";
  card.append(el("p","STAGE Q · PROFILES & PERSONAL MEMORY","eyebrow"));
  card.append(el("h2","Choose how LazHelper helps"));
  card.append(el("p","Profiles tune recommendation style. Personal memory is optional and uses only the preferences you save. Neither feature changes permissions."));
  const profileLabel=el("label","Assistant profile");profileLabel.htmlFor="assistant-profile-choice";
  const profile=el("select");profile.id="assistant-profile-choice";
  const description=el("p","Loading profile details…","profile-description");
  const memoryLabel=el("label",undefined,"profile-memory");
  const memory=el("input");memory.type="checkbox";memory.id="assistant-memory";
  memoryLabel.append(memory,el("span","Use saved instructions when generating local Gemma recommendations"));
  const note=el("p","Memory is off by default. When enabled, applicable global, folder, and task instructions are added to the local recommendation prompt. They cannot grant permissions.","profile-note");
  const save=el("button","Save profile and memory","secondary-button");save.type="button";
  const status=el("p","Loading profile…","status-line");status.setAttribute("role","status");
  const summary=el("div",undefined,"profile-summary");
  card.append(profileLabel,profile,description,memoryLabel,note,save,status,summary);
  const owner=document.getElementById("owner-controls"),footer=main.querySelector("footer");
  if(owner)main.insertBefore(card,owner);else if(footer)main.insertBefore(card,footer);else main.append(card);
  const show=(message,error=false)=>{status.textContent=message;status.classList.toggle("error",error);};
  let profiles={};
  async function request(url,options={}){
    const response=await fetch(url,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
    const data=await response.json();if(!response.ok)throw new Error(data.detail||"Request failed.");return data;
  }
  function renderDescription(){description.textContent=profiles[profile.value]?.description||"Use your own saved preferences.";}
  async function load(){
    try{
      const data=await request("/api/assistant-profile");profiles=data.profiles||{};
      profile.replaceChildren();
      Object.entries(profiles).forEach(([value,item])=>{const o=el("option",item.label);o.value=value;profile.append(o);});
      profile.value=data.profile||"general";memory.checked=Boolean(data.memory_enabled);renderDescription();
      const instructions=await request("/api/instructions");
      const enabled=(instructions.items||[]).filter(item=>item.enabled);
      summary.replaceChildren(el("strong",enabled.length+" enabled instruction rule(s) saved"));
      summary.append(el("p","Saved rules are stored locally. They are not sent to a cloud provider by this feature."));
      show("Profile settings loaded. Current profile: "+(profiles[profile.value]?.label||profile.value)+".");
    }catch(error){show(error.message||"Profile settings could not be loaded.",true);}
  }
  profile.addEventListener("change",renderDescription);
  save.addEventListener("click",async()=>{
    save.disabled=true;
    try{
      const data=await request("/api/assistant-profile",{method:"PUT",body:JSON.stringify({profile:profile.value,memory_enabled:memory.checked})});
      memory.checked=Boolean(data.memory_enabled);renderDescription();
      show("Saved. The selected profile guides Gemma recommendations; memory is "+(memory.checked?"enabled.":"disabled.")+" Permissions are unchanged.");
    }catch(error){show(error.message||"Settings could not be saved.",true);}
    finally{save.disabled=false;}
  });
  load();
})();
