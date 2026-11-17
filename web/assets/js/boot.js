(async()=>{
  /*
   * The legacy workspace used a synchronous XMLHttpRequest every five seconds.
   * A synchronous request blocks painting, typing and scrolling while the
   * network responds. Keep the same API and update semantics, but never block
   * the UI thread.
   */
  let refreshing=false;

  syncFilter();
  render();
  document.documentElement.dataset.workspaceReady='true';

  if(!shared)return;

  setInterval(async()=>{
    if(refreshing||document.visibilityState!=='visible'||document.querySelector('dialog[open]'))return;
    refreshing=true;
    try{
      const versionResponse=await fetch('/api/state/version',{credentials:'same-origin'});
      if(versionResponse.status===401){location.replace('/');return;}
      if(!versionResponse.ok)return;
      const meta=await versionResponse.json();
      if(meta.version!==version){
        const response=await fetch('/api/state',{credentials:'same-origin'});
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
