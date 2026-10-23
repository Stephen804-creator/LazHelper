/* Stage Q profile controls; all changes use the local API. */
(function(){
 const main=document.querySelector("main"); if(!main||document.getElementById("assistant-profile"))return;
 const section=document.createElement("section"); section.id="assistant-profile"; section.className="workspace-card profile-card";
 const title=document.createElement("h2"); title.textContent="Assistant profile"; section.append(title);
 const select=document.createElement("select"); select.id="assistant-profile-choice"; select.setAttribute("aria-label","Assistant profile"); section.append(select);
 const toggle=document.createElement("input"); toggle.type="checkbox"; toggle.id="assistant-memory";
 const label=document.createElement("label"); label.append(toggle,document.createTextNode(" Enable saved instructions for local recommendations")); section.append(label);
 const status=document.createElement("p"); status.setAttribute("role","status"); section.append(status);
 const save=document.createElement("button"); save.type="button"; save.textContent="Save profile"; section.append(save);
 const footer=main.querySelector("footer"); if(footer)main.insertBefore(section,footer);else main.append(section);
 let profiles={};
 async function load(){
  try{
   const response=await fetch("/api/assistant-profile"); const data=await response.json(); if(!response.ok)throw new Error("Unable to load profile");
   profiles=data.profiles||{}; select.replaceChildren();
   Object.keys(profiles).forEach(function(key){const option=document.createElement("option");option.value=key;option.textContent=profiles[key].label;select.append(option);});
   select.value=data.profile||"general"; toggle.checked=Boolean(data.memory_enabled); status.textContent="Memory is off by default. Profiles do not change permissions.";
  }catch(error){status.textContent=error.message||"Profile settings unavailable.";}
 }
 save.addEventListener("click",async function(){
  save.disabled=true;
  try{
   const response=await fetch("/api/assistant-profile",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({profile:select.value,memory_enabled:toggle.checked})});
   const data=await response.json(); if(!response.ok)throw new Error(data.detail||"Unable to save");
   status.textContent="Profile saved. Permissions are unchanged.";
  }catch(error){status.textContent=error.message||"Unable to save profile.";}
  finally{save.disabled=false;}
 });
 load();
})();