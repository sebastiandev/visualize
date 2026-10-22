// state-machine kind: columns by transition depth (ctx.layout.layers), boxes via ctx.components, colours via status.
export default function render(block, ctx) {
  const { d3 } = ctx;
  const W = 190, H = 46, GX = 120, GY = 40;
  const layer = ctx.layout.depth(block.states, block.transitions);
  const cols = d3.groups(block.states, (s) => layer[s.id]).sort((a, b) => a[0] - b[0]);
  const pos = {};
  cols.forEach(([c, states]) => states.forEach((s, r) => { pos[s.id] = { x: 20 + c * (W + GX), y: 20 + r * (H + GY) }; }));
  const width = 40 + cols.length * (W + GX) - GX;
  const height = 40 + d3.max(cols, ([, s]) => s.length) * (H + GY) - GY + 60;
  const svg = ctx.svg({ width, height, label: block.title });
  const g = svg.append("g");

  for (const t of block.transitions) {
    const a = pos[t.from], b = pos[t.to];
    if (!a || !b) continue;
    const st = t.status || "unchanged";
    const self = t.from === t.to;
    const same = a.x === b.x && !self;             // same column: straight vertical edge
    const back = b.x < a.x && !self;               // loop back: route below every box
    const floor = height - 30;
    const d = same
      ? (b.y > a.y ? `M${a.x + W / 2},${a.y + H} L${b.x + W / 2},${b.y}` : `M${a.x + W / 2},${a.y} L${b.x + W / 2},${b.y + H}`)
      : self
      ? `M${a.x + W - 30},${a.y} C${a.x + W - 10},${a.y - 34} ${a.x + W + 20},${a.y - 10} ${a.x + W},${a.y + 12}`
      : back
        ? `M${a.x + W / 2},${a.y + H} L${a.x + W / 2},${floor} L${b.x + W / 2},${floor} L${b.x + W / 2},${b.y + H}`
        : `M${a.x + W},${a.y + H / 2} C${a.x + W + GX / 2},${a.y + H / 2} ${b.x - GX / 2},${b.y + H / 2} ${b.x},${b.y + H / 2}`;
    const link = g.append("a").attr("href", null);
    link.append("path").attr("class", `sm-edge ${st}`).attr("d", d)
      .attr("stroke", ctx.status(st).color).attr("marker-end", ctx.components.marker(svg, st));
    if (t.label) {
      const mx = same ? a.x + W / 2 + 8 : self ? a.x + W + 14 : back ? (a.x + b.x) / 2 + W / 2 : (a.x + W + b.x) / 2;
      const my = same ? (Math.min(a.y, b.y) + H + Math.max(a.y, b.y)) / 2 + 4 : self ? a.y - 18 : back ? floor - 6 : (a.y + b.y) / 2 + H / 2 - 6;
      const anchor = same ? "start" : "middle";
      const text = link.append("text").attr("class", "sm-label").attr("x", mx).attr("y", my).attr("text-anchor", anchor).text(t.label);
      const bb = text.node().getBBox();
      link.insert("rect", "text").attr("class", "sm-label-bg").attr("x", bb.x - 3).attr("y", bb.y - 1).attr("width", bb.width + 6).attr("height", bb.height + 2).attr("rx", 3);
    }
    link.append("title").text(`${t.from} → ${t.to}${t.label ? ": " + t.label : ""} (${st})`);
  }

  for (const s of block.states) {
    const p = pos[s.id];
    const node = ctx.components.nodeBox(g, { x: p.x, y: p.y, w: W, h: H, label: s.label, sub: s.terminal ? "terminal" : ctx.status(s.status || "unchanged").label, status: s.status, rounded: true });
    if (s.terminal) node.classed("sm-terminal", true);
    node.append("title").text(`${s.label} (${s.status || "unchanged"})${s.ref ? "\n" + s.ref : ""}`);
  }

  d3.select(ctx.el).append("div").html(ctx.components.legend([["new", "new"], ["changed", "changed"], ["removed", "removed (dashed)"], ["unchanged", "unchanged"]]));
}
