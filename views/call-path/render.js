export default function render(block, ctx) {
  const { d3, esc, ref } = ctx, P = ctx.page, el = ctx.el;
  const L = block, F = block.fork;
  el.innerHTML = `<div class="locator"><div><svg class="loc" role="group" aria-label="Call path with the changed components"></svg>
  <div class="legend"><span><i class="sw" style="border-color:var(--clay)"></i>changed</span><span><i class="sw" style="border-color:var(--sage)"></i>${P.mode==='code'?'focus':'new'}</span><span ${P.mode==='code'?'hidden':''}><i class="sw" style="border-color:var(--lav)"></i>moved</span><span><i class="sw" style="border-color:var(--stone);border-style:dashed"></i>unchanged</span><span>select a box →</span></div></div>
  <div class="detail" aria-live="polite"></div></div>`;
let items=[];
const colour={changed:'var(--clay)',new:'var(--sage)',unchanged:'var(--stone)',moved:'var(--lav)'};
const fileOf=d=>(d.defs||[]).map(n=>ctx.defs[n]&&ctx.defs[n].file).find(Boolean)||(/^(?:test:\s*)?((?:[\w.\-]+\/)+[\w.\-]+):\d+$/.exec(d.ref||'')||[])[1]||null;
function drawLocator(){
 const W=520,NW=440,FW=252,GAP=30,cx=W/2,LH=17,PH=13;
 const chars=(w,px)=>Math.max(8,Math.floor((w-24)/px));
 /** Wrap text into lines of ≤ n chars, breaking at spaces, dots, slashes and underscores; never truncates. */
 const wrap=(s,n)=>{const out=[];let rest=s||'';while(rest.length>n){let cut=-1;for(const c of [' ','.','/','_','→','(']){const i=rest.lastIndexOf(c,n);if(i>cut)cut=i;}
   if(cut<n*0.4)cut=n;else cut+=1;out.push(rest.slice(0,cut).trimEnd());rest=rest.slice(cut).trimStart();}if(rest)out.push(rest);return out;};
 const lay=d=>{d.lbl=wrap(d.label,chars(d.w,7.6));d.pth=d.file?wrap(d.file,chars(d.w,6.3)):[];d.h=24+d.lbl.length*LH+(d.pth.length?6+d.pth.length*PH:0)+8;};
 items=L.nodes.map(n=>({...n,x:cx-NW/2,w:NW}));items.forEach(d=>{d.file=fileOf(d);lay(d);});
 let y=16;items.forEach(d=>{d.y=y;y+=d.h+GAP;});const last=items[items.length-1];let H=last.y+last.h+20;
 const links=items.slice(0,-1).map((n,i)=>[n,items[i+1]]);
 if(F){const fy=last.y+last.h+GAP+12;const off={...F.off,id:'off',layer:F.off.layer||'flag off',x:cx-FW-4,y:fy,w:FW},on={...F.on,id:'on',layer:F.on.layer||'flag on',x:cx+4,y:fy,w:FW};
  [off,on].forEach(d=>{d.file=fileOf(d);lay(d);});const fh=Math.max(off.h,on.h);off.h=on.h=fh;items.push(off,on);links.push([last,off],[last,on]);H=fy+fh+20;}
 const svg=d3.select(el).select('svg.loc').attr('viewBox',`0 0 ${W} ${H}`);svg.selectAll('*').remove();
 svg.selectAll('path').data(links).join('path').attr('class','link').attr('d',([a,b])=>`M${a.x+a.w/2},${a.y+a.h} C${a.x+a.w/2},${a.y+a.h+GAP/2} ${b.x+b.w/2},${b.y-GAP/2} ${b.x+b.w/2},${b.y}`);
 const g=svg.selectAll('g.node').data(items).join('g').attr('class','node').attr('tabindex',0).attr('role','button')
  .attr('aria-label',d=>`${d.layer}: ${d.label}, ${d.status}${d.file?', '+d.file:''}`).attr('transform',d=>`translate(${d.x},${d.y})`);
 g.append('rect').attr('width',d=>d.w).attr('height',d=>d.h).attr('rx',10).attr('stroke',d=>colour[d.status]).attr('stroke-dasharray',d=>d.status==='unchanged'?'5 4':null);
 g.append('text').attr('class','ly').attr('x',12).attr('y',16).text(d=>`${d.layer} · ${P.mode==='code'&&d.status==='new'?'focus':P.mode==='code'&&d.status==='unchanged'?'context':d.status}`);
 g.each(function(d){const t=d3.select(this);
  const lb=t.append('text').attr('class','lb');d.lbl.forEach((l,i)=>lb.append('tspan').attr('x',12).attr('y',36+i*LH).text(l));
  if(d.pth.length){const pt=t.append('text').attr('class','pth');const y0=36+(d.lbl.length-1)*LH+6+PH+2;d.pth.forEach((l,i)=>pt.append('tspan').attr('x',12).attr('y',y0+i*PH).text(l));}});
 g.append('title').text(d=>d.file||'');
 g.on('click',(e,d)=>select(d)).on('keydown',(e,d)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(d);}});
 select(items.find(i=>i.id===ctx.state.sel)||items.find(n=>n.status!=='unchanged')||items[0]);}
/** Signature only: GraphQL operation line, else the Python signature. */
function signature(d){const inp=(d.defs||[]).map(n=>P.inputs&&P.inputs[n]).find(Boolean);if(!inp)return'';
 const text=inp.sdl?inp.sdl.split('\n')[0]:inp.signature;
 const hl=ctx.code.highlight(text.split('\n'),inp.sdl?'graphql':'python').join('\n');
 return `<div class="sig"><h4>${inp.sdl?'GraphQL operation':'Signature'}</h4><pre class="code">${hl}</pre></div>`;}
/** Files the node touches, in order, each with its own head line ranges (definitions in that file, else the ref line). */
function filesOf(d){const by=new Map();
 for(const e of (d.defs||[]).map(n=>ctx.defs[n]).filter(Boolean)){if(!by.has(e.file))by.set(e.file,[]);if(e.after&&e.after.end)by.get(e.file).push([e.after.line,e.after.end]);}
 const m=/^(?:test:\s*)?((?:[\w.\-]+\/)+[\w.\-]+):(\d+)$/.exec(d.ref||'');
 if(m){if(!by.has(m[1]))by.set(m[1],[]);if(!by.get(m[1]).length)by.get(m[1]).push([+m[2]-3,+m[2]+12]);}
 if(!by.size&&d.file)by.set(d.file,[]);return [...by.entries()];}
/** Behaviour explanation: what it does (new), before → after (changed/moved), and impact. */
function explainHtml(d){const x=d.explain;if(!x)return'';const li=xs=>(xs||[]).map(i=>`<li>${esc(i.text)}${ref(i.ref)}</li>`).join('');let h='';
 if(x.what&&x.what.length)h+=`<div><h4>What it does</h4><ul>${li(x.what)}</ul></div>`;
 if((x.before&&x.before.length)||(x.after&&x.after.length))h+=`<div class="ba"><div class="b"><h4>${d.status==='moved'?'Before (where it lived)':'Before'}</h4><ul>${li(x.before)}</ul></div><div class="a"><h4>After</h4><ul>${li(x.after)}</ul></div></div>`;
 if(x.impact&&x.impact.length)h+=`<div class="imp"><h4>${P.mode==='code'?'Side effects':'Impact'}</h4><ul>${li(x.impact)}</ul></div>`;
 return h?`<div class="explain">${h}</div>`:'';}
function select(d){if(!d)return;ctx.state.sel=d.id;d3.select(el).selectAll('svg.loc g.node').classed('sel',x=>x===d);
 d3.select(el).select('.detail').html(`<h3>${esc(d.label)}</h3>${d.file?`<div class="path">${esc(d.file)}</div>`:''}<p class="what">${esc(d.summary||(P.mode==='code'?'':'Unchanged by this PR'))}${ref(d.ref)}</p>${explainHtml(d)}${signature(d)}${(()=>{const fs=filesOf(d);return fs.length?fs.map(([f,rs],i)=>ctx.code.fileDiff(f,rs,i<2)).join(''):(P.mode==='proposal'||P.mode==='code'?'':'<p class="what">Not part of this PR’s diff.</p>');})()}`);}
  drawLocator();
}
