// Headless Chrome check of a built explain page. Usage: node check.js <page.html> <screenshot-dir>
// Prints one JSON line: errors, overflow, per-node explanations, diff text integrity, diagram errors, overlaps.
const {spawn}=require('child_process'),fs=require('fs'),path=require('path');
const CHROME=process.env.CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
(async()=>{const [file,shots]=process.argv.slice(2);fs.mkdirSync(shots,{recursive:true});
 const prof=fs.mkdtempSync(path.join(require('os').tmpdir(),'visualize-check-'));
 const child=spawn(CHROME,['--headless','--no-first-run','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+prof,'about:blank'],{stdio:'ignore'});let ws;
 try{let port;for(let i=0;i<150&&!port;i++){try{port=fs.readFileSync(prof+'/DevToolsActivePort','utf8').split('\n')[0]}catch{await new Promise(r=>setTimeout(r,100))}}
  if(!port)throw Error('Chrome did not start: '+CHROME);
  const pages=await(await fetch('http://127.0.0.1:'+port+'/json')).json();ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
  let seq=0;const pend=new Map(),errors=[];ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description?.split('\n')[0]||m.params.exceptionDetails.text);if(m.id){pend.get(m.id)(m);pend.delete(m.id)}};
  const call=(method,params={})=>new Promise(r=>{const id=++seq;pend.set(id,r);ws.send(JSON.stringify({id,method,params}))});
  const ev=async x=>{const r=(await call('Runtime.evaluate',{expression:x,returnByValue:true,awaitPromise:true})).result;if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description);return r.result.value};
  await call('Runtime.enable');await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:'file://'+path.resolve(file)});await new Promise(r=>setTimeout(r,1500));
  await ev("localStorage.clear();document.documentElement.dataset.theme='light';1");
  const report=await ev(`(()=>{const P=JSON.parse(document.getElementById('page').textContent);const raw=new Set(P.mode==='code'?Object.values(P.sources||{}).flat().concat(['⋯']):Object.values(P.diff).flat().flatMap(h=>h.lines.map(l=>l.s)));
   let mismatch=0,nodes=0;const noExplain=[],noDiff=[];for(const v of document.querySelectorAll('[data-view="call-path"]'))for(const g of v.querySelectorAll('svg.loc g.node')){nodes++;g.dispatchEvent(new MouseEvent('click',{bubbles:true}));const st=g.getAttribute('aria-label');const det=v.querySelector('.detail');
    if(!/unchanged/.test(st)&&!det.querySelector('.explain'))noExplain.push(st.split(',')[0]);
    const tds=[...det.querySelectorAll('table.gh td:not(.num):not(.sign)')].filter(td=>!td.closest('tr.hunk'));if(!/unchanged/.test(st)&&!tds.length)noDiff.push(st.split(',')[0]);
    for(const td of tds)if(td.textContent&&!raw.has(td.textContent))mismatch++;}
   let overlaps=0;for(const a of document.querySelectorAll('.view svg a')){const c=a.querySelector('circle'),t=a.querySelector('text.ml');if(c&&t){const cb=c.getBBox(),tb=t.getBBox();if(cb.x+cb.width>tb.x+1)overlaps++;}}
   for(const n of document.querySelectorAll('.dnode')){const r=n.querySelector('rect').getBBox();for(const t of n.querySelectorAll('text')){const b=t.getBBox();if(b.x<r.x-1||b.x+b.width>r.x+r.width+1)overlaps++;}}
   for(const w of document.querySelectorAll('.ent-wrap')){const W=w.getBoundingClientRect();const cards=[...w.querySelectorAll('.ent')].map(c=>{const r=c.getBoundingClientRect();return {x:r.left-W.left+3,y:r.top-W.top+3,r:r.right-W.left-3,b:r.bottom-W.top-3};});
    const inside=(x,y)=>cards.some(c=>x>c.x&&x<c.r&&y>c.y&&y<c.b);
    for(const path of w.querySelectorAll('svg.edges path:not([d^="M0,0"])')){const L=path.getTotalLength();let hit=false;for(let t=10;t<L-10;t+=6){const pt=path.getPointAtLength(t);if(inside(pt.x,pt.y)){hit=true;break;}}if(hit)overlaps++;}
    for(const r of w.querySelectorAll('svg.edges rect')){const b=r.getBBox();if(cards.some(c=>b.x<c.r&&b.x+b.width>c.x&&b.y<c.b&&b.y+b.height>c.y))overlaps++;}}
   const long=[...document.querySelectorAll('.detail .explain li, ul.watch li')].filter(li=>li.firstChild&&li.firstChild.textContent.trim().split(/\\s+/).length>18).length;
   const views=[...document.querySelectorAll('.view[data-view]')].map(el=>{const hard=[...el.querySelectorAll('[fill],[stroke]')].flatMap(n=>['fill','stroke'].map(k=>n.getAttribute(k))).filter(v=>v&&/^#|^rgb/i.test(v));
     return {view:el.dataset.view,drawn:el.children.length>0,error:/^View error/.test(el.textContent)?el.textContent.slice(0,120):null,hardcodedColours:hard.length};});
   const viewProblems=views.filter(k=>!k.drawn||k.error||k.hardcodedColours);
   return {nodes,noExplain,noDiff,diffTextMismatch:mismatch,
     viewErrors:views.some(v=>v.error),overlaps,longItems:long,matrixRows:document.querySelectorAll('table.matrix tbody tr').length,
     cards:document.querySelectorAll('details.card').length,views,viewProblems:viewProblems.length,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}})()`);
  const s=await call('Page.captureScreenshot');fs.writeFileSync(path.join(shots,'desktop.png'),Buffer.from(s.result.data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,400));
  report.mobileOverflow=await ev('document.documentElement.scrollWidth>innerWidth');report.consoleErrors=errors;
  report.ok=!errors.length&&!report.viewErrors&&!report.horizontalOverflow&&!report.mobileOverflow&&!report.diffTextMismatch&&!report.noExplain.length&&!report.overlaps&&!report.viewProblems;
  console.log(JSON.stringify(report));process.exitCode=report.ok?0:3;
 }catch(e){console.log(JSON.stringify({ok:false,error:String(e)}));process.exitCode=1}finally{ws?.close();child.kill()}})();
