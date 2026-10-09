let state=null,pending=false,view='overview';
const I=window.CacheflowI18n,t=(key,variables)=>I.t(key,variables),UX=window.CacheflowUX;
const cfg=()=>({nightStart:'01:00',nightEnd:'07:00',timezone:'Europe/Brussels',...(state?.config||{})});
function loginCommand(){const c=cfg();const command=c.loginCommand||'docker compose run --rm prefill select-apps';return c.sshHost?`ssh -t ${c.sshUser||'root'}@${c.sshHost} ${command}`:command;}

const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(n,unit=t('unit.gib'))=>(n/1024**3).toLocaleString(I.locale,{maximumFractionDigits:1})+`<em>${unit}</em>`;
function toast(text,error=false){UX.toast(text,{error});}
let previousSession=null;
function observeSession(next){
 const active=next.active.length>0;
 if(previousSession?.active&&!active){
   const failed=next.jobStatus==='failed';
   UX.feedback(t(failed?'feedback.sessionFailed':'feedback.sessionEnded'),t('feedback.sessionReview'),failed?'error':'info',true);
   toast(t(failed?'feedback.sessionFailed':'feedback.sessionEnded'),failed);
 }
 previousSession={active};
}
async function refresh(manual=false){
 const button=$('#refresh');if(manual){button.disabled=true;button.classList.add('is-loading');button.setAttribute('aria-busy','true');}
 try{
  const res=await fetch('/api/state');if(!res.ok)throw Error(t('server.unavailable'));
  const next=await res.json();if(!next.games){$('#live-label').textContent=t('server.initializing');if(manual)UX.feedback(t('server.initializing'),t('server.help'),'info');return false;}
  if(next.error||Date.now()-Date.parse(next.timestamp)>30000)throw Error(t('server.stale'));
  observeSession(next);state=next;render();
  if(manual){UX.feedback(t('feedback.refreshed'),t('feedback.libraryCount',{count:state.games.length}));toast(t('feedback.refreshed'));}
  return true;
 }catch(e){
  if(state){state.online=false;render();}
  UX.setConnection(false,e.message||t('server.help'));$('#live-label').textContent=t('server.disconnected');$('#live-label').previousElementSibling.style.background='#eab29d';
  if(!state)$('#logs').textContent=t('server.help');
  if(manual)UX.feedback(t('feedback.refreshFailed'),e.message||t('server.help'),'error');
  return false;
 }finally{if(manual){button.disabled=false;button.classList.remove('is-loading');button.removeAttribute('aria-busy');}}
}
async function action(path,data={}){
 if(pending||!state)return;pending=true;const token=UX.beginAction();
 const game=state.games.find(g=>g.id===data.id);
 UX.feedback(t('feedback.pending.'+path),game?.name||t('feedback.wait'),'pending');
 try{
  const res=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-Cache-Token':state.csrf},body:JSON.stringify(data)});
  const reply=await res.json();if(!res.ok){const key='error.'+reply.code;throw Error(reply.code&&t(key)!==key?t(key):res.status===403?t('feedback.reload'):res.status===409?t('feedback.busy'):t('feedback.error'));}
  const message=t(path==='schedule'?(data.enabled?'feedback.scheduleOn':'feedback.scheduleOff'):'feedback.'+path);
  toast(message);UX.feedback(message,game?.name||(path==='start'||path==='check'?t('feedback.watchLogs'):''),'success',path==='start'||path==='check');
  render.signature=null;await refresh();setTimeout(refresh,1500);
 }catch(e){toast(e.message,true);UX.feedback(t('feedback.actionFailed'),e.message,'error',true);render.signature=null;await refresh();}
 finally{pending=false;UX.endAction(token);render.signature=null;if(state)render();}
}
function render(){
 const busy=state.active.length>0,checking=busy&&state.jobMode==='check';
 UX.setActive(busy);UX.setConnection(state.online,t('server.offline'));
 const current=state.games.find(g=>g.status==='downloading'||g.status==='checking');
 $('#session-summary').textContent=!state.online?t('server.offline'):busy?(current?t('feedback.currentGame',{game:current.name}):t('feedback.sessionActive'))+(state.canStop===false?' · '+t('feedback.externalShort'):' · '+t('feedback.controlsBusy')):t('feedback.ready');
 $('#sync-summary').textContent=t('feedback.synced',{time:new Date(state.timestamp).toLocaleTimeString(I.locale,{hour:'2-digit',minute:'2-digit',second:'2-digit'})});
 document.querySelectorAll('[data-server-host]').forEach(el=>el.textContent=state.host||location.hostname);document.querySelectorAll('[data-cache-ip]').forEach(el=>el.textContent=state.cacheIp||'—');$('#dns-address').textContent=state.cacheIp||'—';$('#login-command').textContent=loginCommand();$('#login-instruction').textContent=t(cfg().sshHost?'dialog.ssh':'dialog.docker');$('.timezone').textContent=t('planning.timezone',{zone:cfg().timezone});const times=document.querySelectorAll('.time-window strong');times[0].textContent=cfg().nightStart;times[1].textContent=cfg().nightEnd;

 $('#live-label').textContent=state.online?t('server.connected'):t('server.offline');$('#live-label').previousElementSibling.style.background=state.online?'#66c0f4':'#eab29d';
 $('#engine-status').textContent=checking?t('engine.checking'):busy?t('engine.busy'):state.online?t('engine.ready'):t('engine.offline');
 $('#engine-detail').textContent=current?current.name:checking?t('engine.detailCheck'):busy?t('engine.detailBusy'):t('engine.detailIdle');
 $('#engine-schedule').innerHTML=state.nightEnabled?esc(cfg().nightStart)+' <em>→</em> '+esc(cfg().nightEnd):'<small>'+t('engine.paused')+'</small>';
 const featured=state.games.find(g=>g.id===526870);
 $('#feature-status').textContent=!featured?t('hero.unselected'):featured.filled?t('hero.filled',{host:state.host||location.hostname}):t('hero.prepare',{host:state.host||location.hostname});
 $('#feature-start').disabled=busy||pending||!state.online||!featured;
 $('#feature-start').textContent=featured?.filled?'↻ '+t('update'):'↧ '+t('hero.start');
 $('#hero-status').textContent=checking?t('hero.checking'):busy?t('hero.busy'):state.online?t('hero.online'):t('hero.offline');
 $('#cache-size').innerHTML=fmt(state.cacheBytes);$('#cache-meter').style.width=Math.min(100,state.cacheBytes/state.capacity*100)+'%';
 $('#cache-capacity').textContent=t('metric.capacity',{value:(state.capacity/1024**3).toLocaleString(I.locale)});
 const total=state.hitBytes+state.missBytes;$('#hit-rate').innerHTML=total?Math.round(state.hitBytes/total*100)+'<em>%</em>':'—';
 $('#hit-sample').textContent=state.sampleRequests?t('metric.requests',{value:state.sampleRequests.toLocaleString(I.locale)}):t('metric.awaiting');
 $('#speed').innerHTML=state.speed.toLocaleString(I.locale,{maximumFractionDigits:1})+'<em>Mbit/s</em>';
 $('#speed-state').textContent=checking?t('engine.checking'):busy?t('metric.busy'):t('metric.clients');
 $('#disk-free').innerHTML=fmt(state.disk.free);$('#disk-total').textContent=t('metric.total',{value:(state.disk.total/1024**3).toLocaleString(I.locale,{maximumFractionDigits:0})});
 $('#schedule-toggle').setAttribute('aria-checked',String(state.nightEnabled));$('#schedule-text').textContent=state.nightEnabled?t('planning.enabled'):t('planning.paused');
 $('#stop').disabled=!busy||pending||state.canStop===false;$('#check-steam').disabled=busy||pending||!state.games.length||!state.online;$('#schedule-toggle').disabled=pending;$('#job-label').textContent=checking?t('logs.checking'):busy?t('logs.busy',{jobs:state.active.join(', ')})+(state.canStop===false?' · '+t('logs.external'):''):t('logs.idle');
 const log=$('#logs'),bottom=log.scrollHeight-log.scrollTop-log.clientHeight<40;log.textContent=state.logs||t('logs.empty');if(bottom)log.scrollTop=log.scrollHeight;
 const signature=JSON.stringify([state.games,busy,pending,state.online,I.language]);
 if(render.signature!==signature){render.signature=signature;$('#games').innerHTML=state.games.map(g=>`<article class="game-card"><div class="game-art"><img src="https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/${g.id}/library_600x900.jpg" alt="${esc(g.name)}" loading="lazy"><span class="game-badge ${g.filled?'filled':''}">${esc(t('game.status.'+(g.status||'unknown')))}</span></div><div class="game-body"><span class="card-platform">STEAM / WINDOWS</span><h3>${esc(g.name)}</h3><div class="game-genre">${esc(t('genre.'+g.id)==='genre.'+g.id?('Steam #'+g.id):t('genre.'+g.id))}</div><div class="game-size"><span>${t('game.depots')}</span><strong>${g.observedDepots?g.completedDepots+' / '+g.observedDepots:'—'}</strong></div><label class="night-choice"><input type="checkbox" data-game="${g.id}" ${g.selected?'checked':''} ${pending||busy?'disabled':''}> ${t('game.night')}</label><button class="button" data-start="${g.id}" ${busy||pending||!state.online?'disabled':''}>↧ ${g.filled?t('update'):t('game.start')}</button></div></article>`).join('')||'<div class="empty">'+esc(t('games.empty'))+'</div>';}
 $('#requests').innerHTML=state.recent.length?state.recent.slice(0,4).map(r=>`<div class="request-row"><span class="cache-tag ${r.cache==='HIT'?'':'miss'}">${esc(r.cache||'—')}</span><code>depot ${esc(r.path.split('/')[2]||'')}</code><span>${esc(r.time.split(':').slice(1,3).join(':'))}</span><span class="request-size">${(r.bytes/1024**2).toLocaleString(I.locale,{maximumFractionDigits:2})} ${t('unit.mib')}</span></div>`).join(''):'<div class="empty">'+t('activity.empty')+'</div>';
 const h=state.history,max=Math.max(10,...h.map(p=>p.mbps));const points=h.map((p,i)=>`${i/Math.max(1,h.length-1)*640},${100-p.mbps/max*85}`);$('#chart-line').setAttribute('d',points.length?'M'+points.join(' L'):'');$('#chart-fill').setAttribute('d',points.length?'M0,110 L'+points.join(' L')+' L640,110 Z':'');$('#chart-start').textContent=h[0]?.time||t('activity.start');
 $('.feature-index').textContent=(featured?String(state.games.findIndex(g=>g.id===526870)+1).padStart(2,'0'):'—')+' / '+String(state.games.length).padStart(2,'0');$('.count').textContent=String(state.games.length).padStart(2,'0');$('.nav-item i').textContent=state.games.length;
}
function setView(next){view=next;document.body.dataset.view=next;const show={overview:['overview-area','games-area','activity-area','planning-area','logs-area'],games:['games-area'],activity:['activity-area','logs-area'],planning:['planning-area']}[next];for(const id of ['overview-area','games-area','activity-area','planning-area','logs-area'])$('#'+id).classList.toggle('hidden',!show.includes(id));$('.lower-grid').classList.toggle('hidden',!show.includes('activity-area')&&!show.includes('planning-area'));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('selected',b.dataset.view===next));$('#page-title').textContent=t('page.'+next+'.title');$('#page-description').textContent=t('page.'+next+'.description',{start:cfg().nightStart,end:cfg().nightEnd,zone:cfg().timezone});$('#breadcrumb').textContent=t('nav.'+next);window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
$('#hero-games').addEventListener('click',()=>setView('games'));$('#refresh').addEventListener('click',()=>refresh(true));
$('#games').addEventListener('click',e=>{const b=e.target.closest('[data-start]');if(b)action('start',{id:Number(b.dataset.start)})});
$('#games').addEventListener('change',e=>{if(e.target.dataset.game)action('selection',{id:Number(e.target.dataset.game),enabled:e.target.checked})});
$('#schedule-toggle').addEventListener('click',()=>{if(state)action('schedule',{enabled:!state.nightEnabled})});$('#stop').addEventListener('click',()=>action('stop'));
async function copy(text){try{await navigator.clipboard.writeText(text);toast(t('feedback.copied'))}catch{const a=document.createElement('textarea');a.value=text;a.style.position='fixed';a.style.opacity='0';document.body.append(a);a.select();const ok=document.execCommand('copy');a.remove();toast(ok?t('feedback.copied'):t('feedback.copyManual'),!ok)}}
$('#copy-logs').addEventListener('click',()=>copy(state?.logs||''));$('#add-help').addEventListener('click',()=>$('#info-dialog').showModal());$('#close-dialog').addEventListener('click',()=>$('#info-dialog').close());$('#copy-command').addEventListener('click',()=>copy(loginCommand()));
$('#feature-start').addEventListener('click',()=>action('start',{id:526870}));
$('#engine-activity').addEventListener('click',()=>setView('activity'));
document.addEventListener('error',e=>{if(e.target instanceof HTMLImageElement){if(!e.target.dataset.fallback){e.target.dataset.fallback='1';e.target.src=e.target.src.replace(/library_(600x900|hero)\.jpg/,'header.jpg')}else{e.target.style.visibility='hidden'}}},true);
document.addEventListener('cacheflow:language',()=>{render.signature=null;setView(view);if(state)render()});
I.init().then(()=>{refresh();setInterval(refresh,5000)}).catch(()=>toast('Translation files unavailable. Please reload.',true));

$('#check-steam').addEventListener('click',()=>action('check'));

$('#feedback-logs').addEventListener('click',()=>setView('activity'));
