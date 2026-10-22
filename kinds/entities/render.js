export default function render(g, ctx) {
  // Shared helpers from the render API (see SKILL.md): no page globals.
  const { d3, esc, ref } = ctx;
  const statusColour = new Proxy({}, { get: (_, k) => ctx.status(String(k)).color });
  const svgHref = ctx.href;
  const el = '#' + ctx.el.id;
const E=g.entities,R=g.relations||[];const layer={};E.forEach(e=>{layer[e.id]=0;});
 for(let pass=0;pass<E.length;pass++)for(const r of R)if(layer[r.to]!==undefined&&layer[r.from]!==undefined&&layer[r.to]<=layer[r.from])layer[r.to]=layer[r.from]+1;
 const nCols=Math.max(...Object.values(layer))+1;const wrap=d3.select(el).append('div').attr('class','ent-wrap');
 const grid=wrap.append('div').attr('class','ent-grid').style('grid-template-columns',`repeat(${nCols},minmax(220px,1fr))`);
 const cols=d3.range(nCols).map(c=>grid.append('div').style('display','grid').style('gap','24px'));
 const mark={new:'+',removed:'−',changed:'~',unchanged:' '};
 E.forEach(e=>{cols[layer[e.id]].append('div').attr('class','ent '+(e.status||'unchanged')).attr('id','ent-'+e.id).html(
  `<div class="eh"><b>${esc(e.label)}</b><span class="k">${esc(e.kind)}</span>${e.status&&e.status!=='unchanged'?` <span class="badge ${e.status==='changed'?'chg':''}">${esc(e.status)}</span>`:''}${e.file?`<span class="ep">${esc(e.file)}</span>`:''}${ref(e.ref)}</div>
   <ul>${(e.fields||[]).map(f=>`<li class="${f.status||'unchanged'}"><span class="m">${mark[f.status||'unchanged']}</span><span>${esc(f.name)}${f.note?`<span class="nt">${esc(f.note)}</span>`:''}</span><span class="t">${esc(f.type||'')}</span></li>`).join('')}</ul>`);});
 const svg=wrap.append('svg').attr('class','edges');const mid='ent-ar-'+el.slice(1);
 svg.append('defs').append('marker').attr('id',mid).attr('viewBox','0 0 10 10').attr('refX',9).attr('refY',5).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto').append('path').attr('d','M0,0L10,5L0,10z').attr('fill','var(--faint)');
 const layerG=svg.append('g');
 const draw=()=>{layerG.selectAll('*').remove();const box=wrap.node().getBoundingClientRect();
  for(const r of R){const a=document.getElementById('ent-'+r.from),b=document.getElementById('ent-'+r.to);if(!a||!b)continue;const A=a.getBoundingClientRect(),B=b.getBoundingClientRect();
   const ax=A.right-box.left,ay=A.top-box.top+18,bx=B.left-box.left,by=B.top-box.top+18;
   const p=B.left>=A.right?`M${ax},${ay} C${ax+40},${ay} ${bx-40},${by} ${bx},${by}`:`M${A.left-box.left+A.width/2},${A.bottom-box.top} L${B.left-box.left+B.width/2},${B.top-box.top}`;
   layerG.append('path').attr('d',p).attr('marker-end',`url(#${mid})`);
   if(r.label){const lbl=r.label.length>16?r.label.slice(0,15)+'…':r.label,mx=B.left>=A.right?(A.right+B.left)/2-box.left:(A.left+A.width/2-box.left)+8,my=B.left>=A.right?(ay+by)/2:(A.bottom+B.top)/2-box.top;
    const t=layerG.append('text').attr('x',mx).attr('y',my+4).attr('text-anchor',B.left>=A.right?'middle':'start').text(lbl);t.append('title').text(r.label);const bb=t.node().getBBox();
    layerG.insert('rect','text').attr('x',bb.x-4).attr('y',bb.y-2).attr('width',bb.width+8).attr('height',bb.height+4).attr('rx',4).attr('fill','var(--card)').attr('stroke','var(--line)');}}};
 ctx.onResize(draw);
}
