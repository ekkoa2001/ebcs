async function accountRequest(path,body){let opts=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':serverUser.csrf},body:JSON.stringify(body)};let r=await fetch(path,opts);let data=await r.json();if(!r.ok)throw new Error(data.error||'操作失败');return data}
function accountMessage(id,e){$(id).textContent=e?.message||''}
