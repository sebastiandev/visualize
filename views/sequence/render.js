export default function render(g, ctx) {
  // Shared helpers from the render API (see SKILL.md): no page globals.
  const { d3, esc, ref } = ctx;
  const statusColour = new Proxy({}, { get: (_, k) => ctx.status(String(k)).color });
  const svgHref = ctx.href;
  const el = '#' + ctx.el.id;
const A=g.actors,S=g.steps,idx=Object.fromEntries(A.map((a,i)=>[a.id,i]));
 const colW=Math.max(170,Math.min(240,1100/A.length)),W=colW*A.length+40,top=64,rowH=46,FH=22;const x=i=>20+colW*i+colW/2;
 /* Row positions: each frame start adds FH so the frame label gets its own line. */
 const Y=[];let acc=top;S.forEach((s,n)=>{if(s.branch&&(n===0||S[n-1].branch!==s.branch))acc+=FH;Y.push(acc);acc+=rowH;});const H=acc+30;
 const svg=d3.select(el).append('svg').attr('viewBox',`0 0 ${W} ${H}`).attr('role','img').attr('aria-label',g.title);
 const defs=svg.append('defs');for(const [k,c] of ['new','changed','unchanged','removed','moved'].map(k=>[k,statusColour[k]]))defs.append('marker').attr('id','sq-'+el.slice(1)+'-'+k).attr('viewBox','0 0 10 10').attr('refX',9).attr('refY',5).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto-start-reverse').append('path').attr('d','M0,0L10,5L0,10z').attr('fill',c);
 // branch frames
 let k=0;while(k<S.length){const b=S[k].branch;if(!b){k++;continue;}let j=k;while(j+1<S.length&&S[j+1].branch===b)j++;
  const cols=S.slice(k,j+1).flatMap(s=>[idx[s.from],idx[s.to]]),c0=Math.min(...cols),c1=Math.max(...cols);
  svg.append('rect').attr('class','frame').attr('x',x(c0)-colW/2+8).attr('y',Y[k]-FH-6).attr('width',(c1-c0+1)*colW-16).attr('height',Y[j]-Y[k]+rowH+FH+2).attr('rx',8);
  svg.append('text').attr('class','ft').attr('x',x(c0)-colW/2+18).attr('y',Y[k]-FH+9).text(b);k=j+1;}
 A.forEach((a,i)=>{svg.append('line').attr('class','life').attr('x1',x(i)).attr('x2',x(i)).attr('y1',46).attr('y2',H-10);
  const gA=svg.append('g').attr('class','actor');gA.append('title').text(a.file||'');gA.append('rect').attr('x',x(i)-colW/2+10).attr('y',4).attr('width',colW-20).attr('height',42).attr('rx',8);
  gA.append('text').attr('class','al').attr('x',x(i)).attr('y',22).attr('text-anchor','middle').text(a.label.length>Math.floor((colW-30)/7.4)?a.label.slice(0,Math.floor((colW-30)/7.4)-1)+'…':a.label);gA.select('title').text(a.label+(a.file?'\n'+a.file:''));
  if(a.file)gA.append('text').attr('class','af').attr('x',x(i)).attr('y',37).attr('text-anchor','middle').text(a.file.split('/').pop());});
 S.forEach((s,n)=>{const y=Y[n]+18,a=idx[s.from],b=idx[s.to],c=statusColour[s.status]||statusColour.unchanged;
  const gS=svg.append('a').attr('href',svgHref(s.ref)).attr('target','_blank');
  if(a===b){gS.append('path').attr('class','msg '+s.kind).attr('stroke',c).attr('d',`M${x(a)},${y-6} h34 v14 h-30`).attr('marker-end',`url(#sq-${el.slice(1)}-${s.status||'unchanged'})`);
   gS.append('text').attr('class','ml').attr('x',x(a)+40).attr('y',y+2).text(s.label);}
  else{const x1=x(a)+(b>a?6:-6),x2=x(b)+(b>a?-6:6);gS.append('line').attr('class','msg '+s.kind).attr('stroke',c).attr('x1',x1).attr('x2',x2).attr('y1',y).attr('y2',y).attr('marker-end',`url(#sq-${el.slice(1)}-${s.status||'unchanged'})`);
   gS.append('text').attr('class','ml').attr('x',(x1+x2)/2+10).attr('y',y-7).attr('text-anchor','middle').text(s.label);}
  const lb=gS.select('text.ml').node().getBBox();const nx=lb.x-12,ny=lb.y+lb.height/2;gS.append('circle').attr('cx',nx).attr('cy',ny).attr('r',8).attr('fill',c);gS.append('text').attr('class','num').attr('x',nx).attr('y',ny+3.5).attr('text-anchor','middle').text(n+1);
  gS.append('title').text(`${n+1}. ${s.label} (${s.kind}, ${s.status})`);});
 d3.select(el).append('ul').attr('class','steps-list').html(S.map((s,n)=>`<li><span class="n" style="background:${statusColour[s.status]||statusColour.unchanged}">${n+1}</span><span>${esc(s.label)} <span style="color:var(--faint)">· ${esc(s.kind)}${s.branch?' · '+esc(s.branch):''}</span>${ref(s.ref)}</span></li>`).join(''));
 d3.select(el).append('div').attr('class','legend').html(`<span><i class="sw" style="border-color:var(--sage)"></i>new</span><span><i class="sw" style="border-color:var(--clay)"></i>changed</span><span><i class="sw" style="border-color:var(--stone)"></i>unchanged</span><span>— call · - - return · ··· event</span>`);
}
