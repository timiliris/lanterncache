// Exercise frontend feedback without a server, Steam account or downloads.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const calls=[];
const element={disabled:false,textContent:'',style:{},previousElementSibling:{style:{}},classList:{add(){},remove(){}},addEventListener(){},setAttribute(){},removeAttribute(){}};
const context=vm.createContext({
 window:{CacheflowI18n:{t:key=>key,init:()=>new Promise(()=>{})},CacheflowUX:{feedback:(...args)=>calls.push(args),toast(){},setConnection(){}}},
 document:{querySelector:()=>element,querySelectorAll:()=>[],addEventListener(){}},
 setTimeout(){},setInterval(){},Date,console,
 fetch:async()=>({ok:false})
});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8'),context);
vm.runInContext("observeSession({active:[]});observeSession({active:['job']});",context);
assert.equal(calls.length,0,'Initial state must not invent a completion');
vm.runInContext("observeSession({active:[]});observeSession({active:[]});",context);
assert.equal(calls.length,1,'Only one notice when a session ends');
assert.equal(calls[0][0],'feedback.sessionEnded');
assert.equal(calls[0][2],'info','An ended session is not proof of success');
vm.runInContext("observeSession({active:['job']});observeSession({active:[],jobStatus:'failed'});",context);
assert.equal(calls[1][0],'feedback.sessionFailed');
assert.equal(calls[1][2],'error');
(async()=>{
 calls.length=0;
 const ok=await vm.runInContext('refresh(true)',context);
 assert.equal(ok,false);
 assert.equal(calls[0][0],'feedback.refreshFailed');
 assert.ok(!calls.some(call=>call[0]==='feedback.refreshed'),'Failed fetch must not claim fresh data');
 assert.equal(element.disabled,false,'Refresh control must unlock after failure');
 console.log('Session notices, failure feedback and refresh recovery passed.');
})().catch(error=>{console.error(error);process.exit(1)});
