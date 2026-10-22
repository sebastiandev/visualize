export default function render(block, ctx) {
  const { d3, esc, ref } = ctx, P = ctx.page, el = ctx.el;
const E=block;const rs=E.rows,t=c=>(typeof c==='string'?c:c.text)!=='untested';
 const both=rs.filter(r=>r.cells.every(t)).length,some=rs.filter(r=>r.cells.some(t)&&!r.cells.every(t)).length;
 const cover=E.columns.length>1?`<span><b>${both}/${rs.length}</b> cases tested on every path</span><span><b>${some}</b> only on some paths</span><span><span class="v untested">untested</span> no test covers that path</span>`:`<span><b>${both}/${rs.length}</b> cases asserted by tests</span>`;
 const cell=c=>{const tx=typeof c==='string'?c:c.text,tone=typeof c==='string'?(/^yes/.test(c)?'yes':/^no$/.test(c)?'no':/error/.test(c)?'err':c==='untested'?'untested':c==='n/a'?'na':'plain'):c.tone;return `<td><span class="v ${tone}">${esc(tx)}</span></td>`;};
 el.innerHTML = `${E.no_coverage?'':`<div class="coverage">${cover}</div>`}
 <table class="matrix"><thead><tr><th>${esc(E.case_header||'When…')}</th>${E.columns.map(c=>`<th>${esc(c)}</th>`).join('')}<th class="t">${P.mode==='proposal'?'Source':'Test'}</th></tr></thead><tbody>
 ${rs.map(r=>`<tr class="${r.new?'new':''}"><td class="case">${esc(r.case)}${r.new&&E.new_label?`<span class="tag">${esc(E.new_label)}</span>`:''}</td>${r.cells.map(cell).join('')}<td class="t">${ref(r.ref)}</td></tr>`).join('')}
 </tbody></table>${E.footnote?`<p class="foot">${esc(E.footnote.text)}${ref(E.footnote.ref)}</p>`:''}`;
}
