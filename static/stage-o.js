/* Stage O — accessible navigation and persistent light/dark/system theme. */
(() => {
  const root=document.documentElement;
  const theme=document.getElementById("theme-choice");
  const menu=document.getElementById("primary-nav");
  const toggle=document.getElementById("nav-toggle");
  if(theme){
    const valid=new Set(["system","light","dark"]);
    let saved="system";
    try{const value=localStorage.getItem("lazhelper-theme");if(valid.has(value))saved=value;}catch(_){}
    theme.value=saved;
    const apply=value=>{
      if(value==="system")root.removeAttribute("data-theme");
      else root.setAttribute("data-theme",value);
      const meta=document.querySelector('meta[name="theme-color"]');
      if(meta)meta.content=value==="dark"?"#17221b":"#f5f4ee";
    };
    apply(saved);
    theme.addEventListener("change",()=>{
      const value=valid.has(theme.value)?theme.value:"system";
      apply(value);
      try{localStorage.setItem("lazhelper-theme",value);}catch(_){}
    });
  }
  if(menu&&toggle){
    const close=()=>{menu.classList.remove("is-open");toggle.setAttribute("aria-expanded","false");};
    toggle.addEventListener("click",()=>{
      const open=!menu.classList.contains("is-open");
      menu.classList.toggle("is-open",open);
      toggle.setAttribute("aria-expanded",String(open));
    });
    menu.querySelectorAll("a").forEach(link=>link.addEventListener("click",close));
    document.addEventListener("keydown",event=>{if(event.key==="Escape")close();});
    document.addEventListener("click",event=>{if(!menu.contains(event.target)&&event.target!==toggle)close();});
  }
})();
