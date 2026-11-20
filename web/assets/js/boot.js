(async()=>{
  let refreshing=false;

  syncFilter();
  if(!shared){
    render();
    document.documentElement.dataset.workspaceReady='true';
    return;
  }

  const listEl=document.getElementById('list');
  if(listEl&&(!entries||!entries.length)){
    listEl.innerHTML='<div class="ekko-skeleton-grid" style="display:grid;gap:12px;padding:12px 0"><div style="height:84px;border-radius:10px;background:#eef2f7"></div><div style="height:84px;border-radius:10px;background:#eef2f7"></div></div>';
  }

  try{
    const bootRes=await fetch('/api/bootstrap',{credentials:'same-origin',cache:'no-store'});
    if(bootRes.status===401){location.replace('/');return;}
    if(bootRes.ok){
      const boot=await bootRes.json();
      if(boot.state){
        version=boot.state.version;
        entries=boot.state.entries||[];
      }
    }
  }catch{
    /* Fallback to existing state if bootstrap fails */
  }

  render();
  document.documentElement.dataset.workspaceReady='true';

  setInterval(async()=>{
    if(refreshing||document.visibilityState!=='visible'||document.querySelector('dialog[open]'))return;
    refreshing=true;
    try{
      const versionResponse=await fetch('/api/state/version',{credentials:'same-origin',cache:'no-store'});
      if(versionResponse.status===401){location.replace('/');return;}
      if(!versionResponse.ok)return;
      const meta=await versionResponse.json();
      if(meta.version!==version){
        const response=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'});
        if(response.status===401){location.replace('/');return;}
        if(!response.ok)return;
        const next=await response.json();
        version=next.version;
        entries=next.entries||[];
        render();
      }
    }catch{
      /* Keep the current UI usable when the local service is temporarily unavailable. */
    }finally{
      refreshing=false;
    }
  },5000);
})();
