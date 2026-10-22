export default function render(g, ctx) {
  // Shared helpers from the render API (see SKILL.md): no page globals.
  const { d3, esc, ref } = ctx;
  const statusColour = new Proxy({}, { get: (_, k) => ctx.status(String(k)).color });
  const svgHref = ctx.href;
  const el = '#' + ctx.el.id;
const root=d3.hierarchy(g.root,d=>d.children);const NW=236,NH=64;d3.tree().nodeSize([NW+24,NH+56])(root);
 const ds=root.descendants(),[x0,x1]=d3.extent(ds,d=>d.x),depth=d3.max(ds,d=>d.y);const W=x1-x0+NW+40,H=depth+NH+40;
 const svg=d3.select(el).append('svg').attr('viewBox',`0 0 ${W} ${H}`).attr('role','img').attr('aria-label',g.title);const G=svg.append('g').attr('transform',`translate(${20+NW/2-x0},20)`);
 G.selectAll('path').data(root.links()).join('path').attr('class','dlink').attr('d',l=>`M${l.source.x},${l.source.y+NH} C${l.source.x},${l.source.y+NH+28} ${l.target.x},${l.target.y-28} ${l.target.x},${l.target.y}`);
 const lbl=G.selectAll('g.el').data(root.links().filter(l=>l.target.data.edge)).join('g');
 lbl.each(function(l){const t=d3.select(this),mx=(l.source.x+l.target.x)/2,my=(l.source.y+NH+l.target.y)/2;const txt=t.append('text').attr('class','el').attr('x',mx).attr('y',my+4).attr('text-anchor','middle').text(l.target.data.edge);
  const bb=txt.node().getBBox();t.insert('rect','text').attr('class','elbg').attr('x',bb.x-4).attr('y',bb.y-2).attr('width',bb.width+8).attr('height',bb.height+4).attr('rx',4);});
 const tone={ok:['var(--sage-soft)','var(--sage)'],err:['var(--bad-soft)','var(--bad)'],plain:['var(--soft)','var(--stone)']};
 const n=G.selectAll('a.dnode').data(ds).join('a').attr('class','dnode').attr('href',d=>svgHref(d.data.ref)).attr('target','_blank').attr('transform',d=>`translate(${d.x-NW/2},${d.y})`);
 n.append('rect').attr('width',NW).attr('height',NH).attr('rx',d=>d.data.outcome?NH/2:8).attr('fill',d=>d.data.outcome?(tone[d.data.tone]||tone.plain)[0]:'var(--card)').attr('stroke',d=>d.data.outcome?(tone[d.data.tone]||tone.plain)[1]:'var(--amber-ink)');
 const fit=(s,n)=>s.length>n?s.slice(0,n-1)+'…':s;
 /** Wrap a label into ≤ 2 lines of ~n chars at word boundaries. */
 const wrap2=(s,n)=>{const w=s.split(/\s+/);let a='',b='';for(const x of w){if(!b&&(a+' '+x).trim().length<=n)a=(a+' '+x).trim();else b=(b+' '+x).trim();}return [a,b.length>n?b.slice(0,n-1)+'…':b];};
 n.each(function(d){const t=d3.select(this),mono=d.data.outcome&&d.data.tone==='plain',[l1,l2]=wrap2(d.data.outcome||d.data.label,mono?24:30);
  const tx=t.append('text').attr('class','dl').attr('x',NW/2).attr('text-anchor','middle').style('font-family',mono?'ui-monospace,monospace':null).style('font-size',mono?'11.5px':null);
  tx.append('tspan').attr('x',NW/2).attr('y',l2?20:27).text(l1);if(l2)tx.append('tspan').attr('x',NW/2).attr('y',35).text(l2);
  const m=/((?:[\w.\-]+\/)*([\w.\-]+)):(\d+)$/.exec(d.data.ref||'');if(m){const r=`${m[2]}:${m[3]}`;t.append('text').attr('class','dr').attr('x',NW/2).attr('y',53).attr('text-anchor','middle').text(r.length>34?'…'+r.slice(r.length-33):r);}});
 n.append('title').text(d=>(d.data.outcome||d.data.label)+(d.data.ref?'\n'+d.data.ref:''));
}
