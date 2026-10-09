/* Sampled cache throughput: true values and timestamps, no synthetic traffic. */
window.CacheflowChart=(()=>{
 const geometry=(samples)=>{
  const values=samples.map(p=>Math.max(0,Number(p.mbps)||0));
  const peak=Math.max(0,...values),raw=Math.max(10,peak*1.15),power=10**Math.floor(Math.log10(raw));
  const maximum=Math.ceil(raw/power/2)*2*power;
  const stamps=samples.map((p,i)=>Date.parse(p.timestamp)||i*5000);
  const span=stamps.at(-1)-stamps[0];
  const points=values.map((value,i)=>({x:span>0?(stamps[i]-stamps[0])/span*900:450,y:190-value/maximum*180,value,time:samples[i].time}));
  return {points,maximum,peak,average:values.length?values.reduce((a,b)=>a+b,0)/values.length:0};
 };
 let samples=[],model={points:[]},windowSize=60,hover=-1;
 const $=id=>document.getElementById(id),number=n=>n.toLocaleString(window.CacheflowI18n.locale,{maximumFractionDigits:1});
 function inspect(index){
  if(!model.points.length)return;hover=Math.max(0,Math.min(index,model.points.length-1));
  const point=model.points[hover];$('chart-tooltip').hidden=false;
  $('chart-tooltip').textContent=point.time+' · '+number(point.value)+' Mbit/s';
  $('chart-tooltip').style.left=Math.max(12,Math.min(88,point.x/9))+'%';
  $('chart-cursor').setAttribute('d',`M${point.x},10 V190`);
  $('chart-dot').setAttribute('cx',point.x);$('chart-dot').setAttribute('cy',point.y);$('chart-dot').style.visibility='visible';
 }
 function hide(){hover=-1;$('chart-tooltip').hidden=true;$('chart-cursor').setAttribute('d','');$('chart-dot').style.visibility='hidden';}
 function render(history){
  const latest=Date.parse(history.at(-1)?.timestamp);
  samples=latest?history.filter(p=>Date.parse(p.timestamp)>=latest-windowSize*5000):history.slice(-windowSize);model=geometry(samples);
  const points=model.points.map(p=>`${p.x},${p.y}`),path=points.length?'M'+points.join(' L'):'';
  $('chart-line').setAttribute('d',path);
  $('chart-fill').setAttribute('d',points.length?`M${model.points[0].x},190 L${points.join(' L')} L${model.points.at(-1).x},190 Z`:'');
  document.querySelectorAll('[data-chart-tick]').forEach((el,i)=>el.textContent=number(model.maximum*(1-i/4)));
  const labels=document.querySelectorAll('[data-chart-time]');
  labels.forEach((el,i)=>el.textContent=samples.length?samples[Math.round(i*(samples.length-1)/4)].time:'—');
  $('chart-current').textContent=number(model.points.at(-1)?.value||0);
  $('chart-peak').textContent=number(model.peak);$('chart-average').textContent=number(model.average);
  $('chart-empty').hidden=model.peak>0;
  if(hover>=0)inspect(hover);
 }
 function init(){
  const plot=$('chart');
  plot.addEventListener('pointermove',e=>{const bounds=plot.getBoundingClientRect();const x=(e.clientX-bounds.left)/bounds.width*900;
   if(model.points.length)inspect(model.points.reduce((best,p,i)=>Math.abs(p.x-x)<Math.abs(model.points[best].x-x)?i:best,0));
  });
  plot.addEventListener('pointerleave',hide);
  plot.addEventListener('focus',()=>inspect(model.points.length-1));plot.addEventListener('blur',hide);
  plot.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End','Escape'].includes(e.key))e.preventDefault();
   if(e.key==='ArrowLeft')inspect((hover<0?model.points.length:hover)-1);
   if(e.key==='ArrowRight')inspect(hover+1);if(e.key==='Home')inspect(0);if(e.key==='End')inspect(model.points.length-1);if(e.key==='Escape')hide();
  });
  document.querySelectorAll('[data-chart-window]').forEach(button=>button.addEventListener('click',()=>{
   windowSize=Number(button.dataset.chartWindow);document.querySelectorAll('[data-chart-window]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
   hide();render(window.CacheflowChart.history||[]);
  }));
 }
 return {geometry,init,render(history){this.history=history;render(history);}};
})();
window.CacheflowChart.init();
