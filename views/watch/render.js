export default function render(block, ctx) {
  const { d3, esc, ref } = ctx, P = ctx.page, el = ctx.el;
  ctx.title(block.title || "Worth a reviewer's look");
  el.innerHTML = `<ul class="watch">${(block.items||[]).map(w=>`<li>${esc(w.text)}${ref(w.ref)}</li>`).join('')}</ul>`;
}
