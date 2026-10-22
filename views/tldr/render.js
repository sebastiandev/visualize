export default function render(block, ctx) {
  const { d3, esc, ref } = ctx, P = ctx.page, el = ctx.el;
  el.innerHTML = `<p class="tldr">${esc(block.text)}${ref(block.ref)}</p>`;
}
