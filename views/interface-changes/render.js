export default function render(block, ctx) {
  const { d3, esc, ref } = ctx, P = ctx.page, el = ctx.el;
const C=block.cards_built||P.contract_cards||[];if(!C.length){el.innerHTML='<p class="q">No interface changes detected.</p>';return;}
 const body=c=>c.generated?`<p class="gh-note">${c.members} generated entries mirror the schema changes above.<br>${esc(c.file)}</p>`:c.change==='added'&&c.code?`<table class="gh"><colgroup><col style="width:44px"><col></colgroup><tbody>${ctx.code.rows(c.code,ctx.code.langOf(c.file))}</tbody></table>`
  :(ctx.code.diffTable(c.file,c.range?[c.range]:null)||'<p class="gh-note">Change detected but not visible in the diff hunks.</p>');
 const badge=c=>c.breaking===true?'<span class="badge brk">breaking</span>':c.breaking==='review'?'<span class="badge chg">review</span>':c.change==='added'?'<span class="badge">new</span>':'<span class="badge chg">changed</span>';
 const proposed=P.mode==='proposal'||!!block.cards_built;ctx.title(proposed?'Proposed model':'Interface changes');
 el.innerHTML = `<p class="q">${proposed?'Proposed definitions (not code yet). New types show their definition; changed ones a diff against today.':'Detected from the code (base vs head). New types show their definition; changed ones their diff.'}</p>
 ${C.map((c,i)=>`<details class="gh card" ${i<4&&!c.generated?'open':''}><summary><span class="chev">▸</span>${badge(c)}<span class="surf">${esc(c.surface)}</span><b>${esc(c.name)}</b>${c.members&&c.change!=='added'?`<span class="surf">${c.members} member change(s)</span>`:''}<span class="fp" style="flex:1;text-align:right">${c.generated?'':esc(c.file)+(c.range?':'+c.range[0]:'')}</span>${c.ref?ref(c.ref):''}</summary>${body(c)}</details>`).join('')}`;
}
