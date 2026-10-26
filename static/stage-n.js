/* Stage N — one text-and-voice assistant entry point. */
(() => {
  const main=document.querySelector("main");
  if(!main||document.getElementById("ask-lazhelper"))return;
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const card=el("section",undefined,"workspace-card ask-card");card.id="ask-lazhelper";
  card.append(el("p","STAGE N · ASK LAZHELPER","eyebrow"));
  card.append(el("h2","What would you like help with?"));
  card.append(el("p","Use the hosted workspace modes or choose device-local modes to work with files you have granted. Device-local Ask needs Laz Connector and Ollama on this computer. File changes are always reviewed before execution."));
  const form=el("form",undefined,"ask-form");
  const modeLabel=el("label","Request type");modeLabel.htmlFor="ask-mode";
  const mode=el("select");mode.id="ask-mode";
  [["question","Ask server workspace documents"],["task","Preview a workspace task"],["device_question","Ask my device files"],["device_task","Plan a task on my device"]].forEach(([v,t])=>{const o=el("option",t);o.value=v;mode.append(o);});
  const pathLabel=el("label","Workspace folder");pathLabel.htmlFor="ask-path";
  const path=el("input");path.id="ask-path";path.value=".";path.maxLength=500;path.autocomplete="off";
  const promptLabel=el("label","Your request");promptLabel.htmlFor="ask-prompt";
  const prompt=el("textarea");prompt.id="ask-prompt";prompt.rows=4;prompt.maxLength=500;prompt.placeholder="Ask a question or describe a task…";prompt.required=true;
  const actions=el("div",undefined,"ask-actions");
  const voice=el("button","🎙 Voice input","secondary-button");voice.type="button";voice.id="ask-voice";
  const stop=el("button","Stop listening","secondary-button");stop.type="button";stop.hidden=true;
  const deviceFolder=el("button","Choose device folder","secondary-button");deviceFolder.type="button";deviceFolder.hidden=true;
  const submit=el("button","Ask LazHelper","ask-submit");submit.type="submit";
  actions.append(voice,stop,deviceFolder,submit);
  form.append(modeLabel,mode,pathLabel,path,promptLabel,prompt,actions);
  const status=el("p","Ready. Voice input is optional; you can always type.","status-line");status.id="ask-status";status.setAttribute("role","status");
  const output=el("section",undefined,"ask-output");output.id="ask-output";output.setAttribute("aria-live","polite");output.hidden=true;
  const outputHead=el("div",undefined,"ask-output-head");
  const outputTitle=el("h3","Response");
  const speak=el("button","Read answer aloud","text-button");speak.type="button";speak.hidden=true;
  const silence=el("button","Stop speaking","text-button");silence.type="button";silence.hidden=true;
  const applyPlan=el("button","Review and apply plan","ask-submit");applyPlan.type="button";applyPlan.hidden=true;
  outputHead.append(outputTitle,speak,silence,applyPlan);
  const answer=el("p","");answer.id="ask-answer";
  const detail=el("pre","");detail.id="ask-detail";detail.hidden=true;
  const sources=el("div",undefined,"ask-sources");
  output.append(outputHead,answer,detail,sources);
  card.append(form,status,output);
  const footer=main.querySelector("footer");
  const scan=main.querySelector(".workspace-card");
  if(scan)main.insertBefore(card,scan);else if(footer)main.insertBefore(card,footer);else main.append(card);
  let lastSpoken="";
  let pendingPlan=[];
  const show=(message,error=false)=>{status.textContent=message;status.classList.toggle("error",error);};
  const buttonBusy=busy=>{submit.disabled=busy;submit.textContent=busy?"Working…":(mode.value==="task"?"Preview task":mode.value==="device_task"?"Plan device task":"Ask LazHelper");};
  mode.addEventListener("change",()=>{
    buttonBusy(false);
    const isDevice=mode.value==="device_question"||mode.value==="device_task";
    deviceFolder.hidden=!isDevice;
    pathLabel.textContent=isDevice?"Device folder":"Workspace folder";
    if(isDevice&&path.value.trim()===".")path.value="";
    if(!isDevice&&!path.value.trim())path.value=".";
    prompt.placeholder=(mode.value==="task"||mode.value==="device_task")?"e.g. Find duplicate notes or move PDFs into a folder":"e.g. What do my notes say about virtual networks?";
    if(isDevice)show("Device mode uses Laz Connector and a local Ollama model. It does not send device file contents to Render.");
  });
  const renderSources=rows=>{
    sources.replaceChildren();
    if(!Array.isArray(rows)||!rows.length)return;
    sources.append(el("h4","Local evidence"));
    rows.forEach(row=>{
      const item=el("article",undefined,"ask-source");
      item.append(el("strong",String(row.path||"Workspace source")));
      if(row.evidence)item.append(el("p",String(row.evidence)));
      if(row.score!==undefined)item.append(el("span","Relevance "+String(row.score),"ask-badge"));
      sources.append(item);
    });
  };
  const renderTask=data=>{
    outputTitle.textContent=data.local_connector?"Device task plan":"Task preview";
    answer.textContent=data.message||"This is a proposed action only. Nothing was executed.";
    detail.hidden=false;detail.textContent=JSON.stringify(data,null,2);
    pendingPlan=data.local_connector&&Array.isArray(data.operations)?data.operations:[];
    applyPlan.hidden=!pendingPlan.length;
    applyPlan.disabled=false;
    renderSources([]);
    lastSpoken=answer.textContent;
  };
  const renderQuestion=data=>{
    applyPlan.hidden=true;pendingPlan=[];
    outputTitle.textContent=data.local_connector?"Answer from your device":"Answer from workspace evidence";
    answer.textContent=data.answer||data.message||"No answer was returned.";
    detail.hidden=true;detail.textContent="";
    renderSources(data.sources||[]);
    lastSpoken=answer.textContent;
  };
  deviceFolder.addEventListener("click",async()=>{
    const api=window.LazHelperConnector;
    if(!api){show("Device connector is still loading. Try again in a moment.",true);return;}
    try{
      const grant=await api.chooseFolderForDownloads();
      if(grant){path.value=grant.path;show("Device folder selected. Your request will be processed locally.");}
      else if(!api.connected)show("Connect Device first, then choose a folder.",true);
    }catch(error){show(error.message||"Could not select a device folder.",true);}
  });

  applyPlan.addEventListener("click",async()=>{
    const api=window.LazHelperConnector;
    if(!api||!api.connected){show("Connect Device before applying a device task plan.",true);return;}
    if(!pendingPlan.length)return;
    applyPlan.disabled=true;
    const completed=[];
    try{
      for(const operation of pendingPlan){
        const preview=await api.request("/operations/preview",{method:"POST",body:JSON.stringify(operation)},15000);
        const label=operation.action.toUpperCase()+" "+operation.path+(operation.destination?" → "+operation.destination:"");
        if(!window.confirm("Review this local file operation:\n\n"+label+"\n\n"+(operation.reason||preview.message)+"\n\nApply this operation now?"))continue;
        const result=await api.request("/operations/execute",{method:"POST",body:JSON.stringify({...operation,approved:true})},15000);
        completed.push(result);
      }
      detail.textContent=JSON.stringify({proposed_operations:pendingPlan,completed_operations:completed},null,2);
      show(completed.length+" operation(s) completed. Declined operations were left unchanged.");
    }catch(error){show(error.message||"The plan could not be applied. Review the details before retrying.",true);}
    finally{applyPlan.disabled=false;}
  });

  form.addEventListener("submit",async event=>{
    event.preventDefault();
    const text=prompt.value.trim();
    if(!text)return show("Enter or dictate a request first.",true);
    path.value=(path.value.trim()||".");
    output.hidden=false;answer.textContent="";detail.textContent="";detail.hidden=true;sources.replaceChildren();
    show("Working on your request…");buttonBusy(true);
    try{
      const isDeviceQuestion=mode.value==="device_question";
      const isDeviceTask=mode.value==="device_task";
      let data;
      if(isDeviceQuestion||isDeviceTask){
        const api=window.LazHelperConnector;
        if(!api||!api.connected)throw new Error("Connect Device first. Your device files cannot be read by the hosted website.");
        const folder=path.value.trim();
        if(!folder||folder===".")throw new Error("Choose a device folder before asking about local files.");
        const approved=window.confirm("Allow Laz Helper to read the selected device folder for this request? File contents stay on this device and are sent only to the configured local AI model.");
        if(!approved){show("Request cancelled. No local files were read.");return;}
        data=await api.request(isDeviceTask?"/assistant/plan":"/assistant/ask",{
          method:"POST",
          body:JSON.stringify(isDeviceTask?{path:folder,command:text,approved:true}:{path:folder,question:text,approved:true})
        },120000);
        if(isDeviceTask)renderTask(data);else renderQuestion(data);
        show(isDeviceTask?(data.operations&&data.operations.length?"Local plan prepared. Nothing has changed yet.":data.message||"No safe operations were proposed."):"Answer prepared by the local AI model. File contents stayed on this device.");
      }else{
        const isTask=mode.value==="task";
        const response=await fetch(isTask?"/api/commands/preview":"/api/knowledge/ask",{
          method:"POST",headers:{"Content-Type":"application/json"},
          body:JSON.stringify(isTask?{command:text,relative_path:path.value}:{question:text,relative_path:path.value,max_sources:5})
        });
        data=await response.json();
        if(!response.ok)throw new Error(data.detail||"The request could not be completed.");
        if(isTask)renderTask(data);else renderQuestion(data);
        show(isTask?"Preview prepared. Review it; no task was executed.":(data.message||"Answer prepared from local evidence."));
      }
      speak.hidden=!lastSpoken;speak.disabled=!lastSpoken;
    }catch(error){answer.textContent=error.message||"Something went wrong.";lastSpoken=answer.textContent;speak.hidden=false;show(lastSpoken,true);}
    finally{buttonBusy(false);}
  });
  let recognition=null;
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognition){
    voice.disabled=true;voice.title="Speech recognition is not available in this browser.";
    voice.textContent="Voice unavailable";
    show("Voice input is not supported in this browser. Typing remains available.");
  }else{
    recognition=new SpeechRecognition();recognition.lang=document.documentElement.lang==="en"?"en-NG":"en-US";recognition.interimResults=true;recognition.continuous=false;
    recognition.onstart=()=>{voice.hidden=true;stop.hidden=false;show("Listening… speak your request, then review the transcript before sending.");};
    recognition.onresult=event=>{
      let transcript="";
      for(let i=0;i<event.results.length;i++)transcript+=event.results[i][0].transcript+" ";
      prompt.value=transcript.trim();
    };
    recognition.onerror=event=>show("Voice input: "+(event.error||"recognition failed")+". You can type your request instead.",true);
    recognition.onend=()=>{voice.hidden=false;stop.hidden=true;if(prompt.value.trim())show("Transcript ready. Review it, then choose Ask LazHelper.");};
    voice.addEventListener("click",()=>{try{recognition.start();}catch(error){show("Voice input is already starting. Please wait.",true);}});
    stop.addEventListener("click",()=>recognition.stop());
  }
  speak.addEventListener("click",()=>{
    if(!("speechSynthesis" in window)||!lastSpoken)return show("Read-aloud is not supported in this browser.",true);
    window.speechSynthesis.cancel();
    const utterance=new SpeechSynthesisUtterance(lastSpoken);
    utterance.lang="en-NG";utterance.onstart=()=>{silence.hidden=false;speak.hidden=true;};
    utterance.onend=()=>{silence.hidden=true;speak.hidden=false;};
    window.speechSynthesis.speak(utterance);
  });
  silence.addEventListener("click",()=>{window.speechSynthesis?.cancel();silence.hidden=true;speak.hidden=false;});
})();
