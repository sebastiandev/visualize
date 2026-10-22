export default function render(g, ctx) {
  // Shared helpers from the render API (see SKILL.md): no page globals.
  const { d3, esc, ref } = ctx;
  const statusColour = new Proxy({}, { get: (_, k) => ctx.status(String(k)).color });
  const svgHref = ctx.href;
  const el = '#' + ctx.el.id;
const E=g.entities,R=g.relations||[];const layer={};E.forEach(e=>{layer[e.id]=0;});
 for(let pass=0;pass<E.length;pass++)for(const r of R)if(layer[r.to]!==undefined&&layer[r.from]!==undefined&&layer[r.to]<=layer[r.from])layer[r.to]=layer[r.from]+1;
 const nCols=Math.max(...Object.values(layer))+1;const wrap=d3.select(el).append('div').attr('class','ent-wrap');
 const grid=wrap.append('div').attr('class','ent-grid');
 const cols=d3.range(nCols).map(c=>grid.append('div').style('display','grid').style('gap','24px').style('align-content','start'));
 /* Depth levels that do not fit the width continue on the next row (re-laid out on resize). */
 const COL=220,GAP=72;let fit=0;
 const layout=()=>{const w=ctx.el.clientWidth||1200,f=Math.max(1,Math.min(nCols,Math.floor((w+GAP)/(COL+GAP))));if(f===fit)return;fit=f;
  grid.style('grid-template-columns',`repeat(${f},minmax(0,1fr))`).style('column-gap',GAP+'px');
  cols.forEach((c,i)=>c.style('grid-column',(i%f)+1).style('grid-row',Math.floor(i/f)+1));};
 layout();
 const mark={new:'+',removed:'−',changed:'~',unchanged:' '};
 E.forEach(e=>{cols[layer[e.id]].append('div').attr('class','ent '+(e.status||'unchanged')).attr('id','ent-'+e.id).html(
  `<div class="eh"><b>${esc(e.label)}</b><span class="k">${esc(e.kind)}</span>${e.status&&e.status!=='unchanged'?` <span class="badge ${e.status==='changed'?'chg':''}">${esc(e.status)}</span>`:''}${e.file?`<span class="ep">${esc(e.file)}</span>`:''}${ref(e.ref)}</div>
   <ul>${(e.fields||[]).map(f=>`<li class="${f.status||'unchanged'}"><span class="m">${mark[f.status||'unchanged']}</span><span>${esc(f.name)}${f.note?`<span class="nt">${esc(f.note)}</span>`:''}</span><span class="t">${esc(f.type||'')}</span></li>`).join('')}</ul>`);});
 const svg=wrap.append('svg').attr('class','edges');const mid='ent-ar-'+el.slice(1);
 svg.append('defs').append('marker').attr('id',mid).attr('viewBox','0 0 10 10').attr('refX',9).attr('refY',5).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto').append('path').attr('d','M0,0L10,5L0,10z').attr('fill','var(--faint)');
 const layerG=svg.append('g');
 const notes=wrap.append('ol').attr('class','ent-notes');
 /* Edges: same row and target to the right → curve through the column gap; otherwise (wrapped to a later row)
    route right of the source, along the gap above the target's row, then in from the target's left. Labels
    never truncate: one that does not fit its gap becomes a numbered marker explained in the list below. */
 const draw=()=>{layerG.selectAll('*').remove();notes.selectAll('*').remove();const box=wrap.node().getBoundingClientRect();let n=0;
  const rowTop=i=>Math.min(...cols.filter((c,k)=>Math.floor(k/fit)===Math.floor(i/fit)).map(c=>c.node().getBoundingClientRect().top))-box.top;
  const label=(text,x,y,room,anchor)=>{const t=layerG.append('text').attr('x',x).attr('y',y+4).attr('text-anchor',anchor).text(text);let bb=t.node().getBBox();
   if(bb.width>room){n+=1;t.text(String(n)).attr('class','num');bb=t.node().getBBox();notes.append('li').attr('value',n).text(text);}
   layerG.insert('rect','text').attr('x',bb.x-4).attr('y',bb.y-2).attr('width',bb.width+8).attr('height',bb.height+4).attr('rx',4).attr('fill','var(--card)').attr('stroke','var(--line)');};
  for(const r of R){const a=document.getElementById('ent-'+r.from),b=document.getElementById('ent-'+r.to);if(!a||!b)continue;const A=a.getBoundingClientRect(),B=b.getBoundingClientRect();
   const ax=A.right-box.left,ay=A.top-box.top+18,bx=B.left-box.left,by=B.top-box.top+18;
   const sameRow=Math.floor(layer[r.from]/fit)===Math.floor(layer[r.to]/fit);
   if(sameRow&&B.left>=A.right){
    layerG.append('path').attr('d',`M${ax},${ay} C${ax+40},${ay} ${bx-40},${by} ${bx},${by}`).attr('marker-end',`url(#${mid})`);
    if(r.label)label(r.label,(ax+bx)/2,(ay+by)/2,bx-ax-10,'middle');
   }else{
    const xr=Math.min(ax+GAP/2,box.width+12),xl=Math.max(bx-GAP/2,-12),yg=rowTop(layer[r.to])-20;
    layerG.append('path').attr('d',`M${ax},${ay} H${xr} V${yg} H${xl} V${by} H${bx}`).attr('marker-end',`url(#${mid})`);
    if(r.label)label(r.label,(xr+xl)/2,yg,Math.abs(xr-xl)-10,'middle');}}};
 ctx.onResize(()=>{layout();draw();});
}
