// The Palette tab: his own colours in the free slots 74-95, sheet colours that match the base's, and every colour his
// frames use with what the game draws it as (so a merged colour shows before the build).
import {S, fill, h, api, edit, set, del, get, toast, swatch, select, checkbox, modal, closeModal} from "./core.js";

const FIRST = 74, LAST = 95;

function ownGrid() {
  const own = get(["palette", "own"]) || {};
  const cells = [];
  for (let s = FIRST; s <= LAST; s++) {
    const c = own[String(s)];
    cells.push(h("div.slot-cell" + (c ? "" : ".empty"),
      h("span.mono.small", s),
      c ? h("input", {type: "color", value: c, title: `slot ${s}: ${c}`, onchange: e => set(["palette", "own", String(s)], e.target.value)}) : h("span.swatch.none"),
      h("input.mono", {value: c || "", placeholder: "#rrggbb", "data-key": `own/${s}`, onchange: e => {
        const v = e.target.value.trim().toLowerCase();
        if (!v) return del(["palette", "own", String(s)]);
        if (!/^#[0-9a-f]{6}$/.test(v)) return toast("a colour is #rrggbb", "error");
        set(["palette", "own", String(s)], v);
      }})));
  }
  return h("div.slot-grid", cells);
}

function sharedList() {
  const sh = get(["palette", "shared"]) || {};
  const rows = Object.entries(sh).filter(([k]) => !k.startsWith("_"));
  return h("div",
    rows.map(([c, s]) => h("div.row", swatch(c), h("span.mono", c), h("span", "→ slot"), h("input.mono", {value: s, style: {width: "4em"},
      onchange: e => { const n = parseInt(e.target.value, 10); if (n >= 1 && n <= 255) set(["palette", "shared", c], n); }}),
      h("button.icon.danger", {title: "remove", onclick: () => del(["palette", "shared", c])}, "×"))),
    h("p.hint", "A sheet colour that already matches one of the base character's slots 1-15 (black outlines: slot 1)."));
}

async function coloursTable(box) {
  let data;
  try { data = await api("sheet_colours"); } catch (e) { fill(box, h("p.bad", e.message)); return; }
  const own = get(["palette", "own"]) || {};
  const free = () => { for (let s = FIRST; s <= LAST; s++) if (!own[String(s)]) return s; return null; };
  const total = data.colours.reduce((a, c) => a + c.count, 0) || 1;
  const drawnSet = new Set(data.colours.map(c => c.drawn_as).filter(Boolean));
  const collapse = data.colours.length >= 4 && drawnSet.size <= 2;
  fill(box,
    collapse ? h("div.alert", h("b", `His ${data.colours.length} colours are drawn as only ${drawnSet.size}: in game he'd be a flat silhouette. `),
      "Every colour without a slot goes to the nearest listed one. ", h("button.primary.small", {onclick: fillFromSheet}, "Fill from sheet…")) : null,
    h("p.hint", `${data.colours.length} colours on his frames (background ${data.background.join(", ")} left out). "Drawn as" is what the game shows, through the same mapping as the build.`),
    h("table.colours",
      h("tr", h("th", "sheet"), h("th", "pixels"), h("th", "slot"), h("th", "drawn as"), h("th", "")),
      data.colours.map(c => {
        const exact = c.drawn_as && close(c.drawn_as, c.colour);
        const merged = c.drawn_as && !exact;
        return h("tr" + (merged ? ".merged" : ""),
          h("td", swatch(c.colour), " ", h("span.mono", c.colour)),
          h("td.mono.small", `${c.count} (${(100 * c.count / total).toFixed(1)}%)`),
          h("td.mono", c.slot ?? (c.drawn_slot != null ? h("span.muted", `→ ${c.drawn_slot}`) : "–")),
          h("td", c.drawn_as ? [swatch(c.drawn_as), " ", h("span.mono.small", c.drawn_as === c.colour ? "exact" : exact ? `${c.drawn_as} (same to the eye)` : c.drawn_as)] : h("span.muted", "?")),
          h("td", c.slot == null ? h("button.small", {title: "give it one of his own slots (74-95)", onclick: () => {
            const s = free();
            if (s === null) return toast("all 22 own slots are taken", "error");
            set(["palette", "own", String(s)], c.colour);
          }}, "Own slot") : null));
      })),
    data.colours.filter(c => c.drawn_as)
      .filter(c => !close(c.drawn_as, c.colour)).length ? h("p.warn", "Highlighted colours are drawn as a different colour (merged into a nearby one). The faithful art rule allows no recolours: give them own slots, unless it's only labels or cameos on the sheet.") : h("p.ok", "Every colour is drawn exactly."));
}

// "Fill from sheet": the backend proposes a slot for every colour on his frames (backend.palette_fill); this shows the
// proposal and lets the user change it before anything is written. Exact colours only: a colour that gets no slot is
// merged into another only when the user picks which (the faithful art rule: no recolouring behind anyone's back).
async function fillFromSheet() {
  let p;
  try { p = await api("palette_fill"); } catch (e) { toast(e.message, "error"); return; }
  const own = get(["palette", "own"]) || {};
  let freeUnused = false;  // (also give out the own slots no frame uses)
  const unusedSlots = new Set(p.unused_own.map(u => u.slot));
  let freeSlots = [];
  const slotsNow = () => { freeSlots = []; for (let s = p.first; s <= p.last; s++) if (!own[String(s)] || (freeUnused && unusedSlots.has(s))) freeSlots.push(s); };
  slotsNow();
  const choice = new Map();  // colour -> {own: bool, into: colour or ""}
  for (const r of p.rows) if (r.kind === "own" || r.kind === "over") choice.set(r.colour, {own: r.kind === "own", into: ""});
  const total = p.total || 1;
  const box = h("div.fill");
  const dist = (a, b) => { const n = x => [1, 3, 5].map(i => parseInt(x.slice(i, i + 2), 16)); const [u, v] = [n(a), n(b)]; return u.reduce((t, x, i) => t + (x - v[i]) ** 2, 0); };

  function plan() {
    const slots = [...freeSlots];
    const out = [];
    for (const r of p.rows) {
      const c = choice.get(r.colour);
      if (!c) out.push({...r, final: r.kind === "kept" ? "kept" : "shared", fslot: r.slot});
      else if (c.own) out.push({...r, final: "own", fslot: slots.shift() ?? null});
      else out.push({...r, final: "merge", into: c.into});
    }
    const slotted = out.filter(r => r.final !== "merge" && r.fslot != null);
    for (const r of out) if (r.final === "merge") {
      const t = slotted.find(x => x.colour === r.into);
      r.fslot = t ? t.fslot : null;
      r.near = slotted.length ? slotted.reduce((a, b) => dist(a.colour, r.colour) <= dist(b.colour, r.colour) ? a : b) : null;
    }
    return out;
  }

  function render() {
    const rows = plan();
    const nOwn = rows.filter(r => r.final === "own").length;
    const pending = rows.filter(r => r.final === "merge" && r.fslot == null);
    const merged = rows.filter(r => r.final === "merge" && r.fslot != null);
    const maniaOwn = rows.filter(r => (r.final === "own" || r.via === "own") && r.mania_global === false).length;
    const mergedPx = merged.reduce((a, r) => a + r.count, 0);
    const pct = n => `${(100 * n / total).toFixed(n * 1000 < total ? 2 : 1)}%`;
    const merge = r => {
      const sel = h("select", {onchange: e => { choice.get(r.colour).into = e.target.value; render(); }},
        h("option", {value: ""}, "merge into… (choose)"),
        rows.filter(x => x.final !== "merge" && x.fslot != null).map(x => h("option", {value: x.colour}, `${x.colour} (slot ${x.fslot})${r.near && x.colour === r.near.colour ? "  nearest" : ""}`)));
      sel.value = r.into || "";
      return sel;
    };
    fill(box,
      h("h3", "Fill the palette from the sheet"),
      h("p.hint", `Every colour on his frames, most pixels first. Exact colours only: the same colour as one of the base's slots 1-15 is shared, every other colour gets one of his own slots (${p.first}-${p.last}; ${freeSlots.length} free). Nothing is recoloured: a colour with no slot is merged only into a colour you pick.`),
      h("p", `${rows.length} colours: ${rows.filter(r => r.final === "kept").length} already listed, ${rows.filter(r => r.final === "shared").length} shared with the base, ${nOwn} own of ${freeSlots.length} free, ${merged.length} merged (${pct(mergedPx)} of his pixels)` + (pending.length ? `, ${pending.length} still to choose` : "")),
      (p.box_colours || []).length ? h("p.warn", `Left out: ${p.box_colours.map(b => `${b.colour} (${b.boxes} cell box${b.boxes > 1 ? "es" : ""} behind his frames)`).join(", ")}. A cell-box colour isn't part of the sprites: Apply puts it in the sheet's background${p.box_colours.some(b => b.listed) ? " and takes it out of his palette" : ""}, so the game doesn't draw a box behind every frame.`) : null,
      nOwn > freeSlots.length ? h("p.bad", "More own colours than free slots.") : null,
      p.mania && S.info.doc.games && S.info.doc.games.mania && maniaOwn > p.mania.slots
        ? h("p.warn", `Mania: ${maniaOwn} of these own colours aren't in Mania's global palette, which has only ${p.mania.slots} free slots: there the ${maniaOwn - p.mania.slots} rarest go to the nearest Mania colour (the approved Mania exception; the build reports it). Origins draws them all exactly.`)
        : p.mania ? h("p.hint", `Mania: ${maniaOwn} of its ${p.mania.slots} free slots.`) : null,
      p.unused_own.length ? h("p.hint", `Own slots not used by any frame: ${p.unused_own.map(u => `${u.slot} ${u.colour}`).join(", ")}. `,
        h("label.check", h("input", {type: "checkbox", checked: freeUnused, onchange: e => { freeUnused = e.target.checked; slotsNow(); render(); }}),
          h("span", "free them for these colours"))) : null,
      h("div.fill-table", h("table.colours",
        h("tr", h("th", "sheet colour"), h("th", "pixels"), h("th", "own slot"), h("th", "becomes")),
        rows.map(r => h("tr" + (r.final === "merge" ? ".merged" : ""),
          h("td", swatch(r.colour), " ", h("span.mono", r.colour)),
          h("td.mono.small", `${r.count} (${pct(r.count)})`),
          h("td", choice.has(r.colour) ? h("input", {type: "checkbox", checked: r.final === "own", title: "give it one of his own slots",
            onchange: e => { choice.get(r.colour).own = e.target.checked; render(); }}) : null),
          h("td",
            r.final === "kept" ? h("span.muted", `already: ${r.via} slot ${r.slot}`)
            : r.final === "shared" ? h("span", `base slot ${r.fslot} (the same colour)`)
            : r.final === "own" ? (r.fslot == null ? h("span.bad", "no free slot: untick some") : h("span", `own slot ${r.fslot}`))
            : [merge(r), r.fslot != null ? [" ", swatch(r.into), h("span.small.muted", ` drawn as ${r.into}`)] : null]))))),
      h("div.row",
        pending.length ? h("button", {title: "pick the nearest slotted colour for each one still to choose (you can change any of them)",
          onclick: () => { for (const r of pending) if (r.near) choice.get(r.colour).into = r.near.colour; render(); }}, "Suggest nearest for the rest") : null,
        h("span.grow"),
        h("button", {onclick: closeModal}, "Cancel"),
        h("button.primary", {disabled: pending.length || nOwn > freeSlots.length ? true : null, title: pending.length ? "choose what each colour without a slot merges into first" : "",
          onclick: async () => {
            const o = {...(get(["palette", "own"]) || {})};
            if (freeUnused) for (const sl of unusedSlots) delete o[String(sl)];
            const sh = {...(get(["palette", "shared"]) || {})};
            for (const r of rows) {
              if (r.final === "own") o[String(r.fslot)] = r.colour;
              else if (r.final === "shared" || r.final === "merge") sh[r.colour] = r.fslot;
            }
            const boxCols = (p.box_colours || []).map(b => b.colour);
            for (const [k, v] of Object.entries(o)) if (boxCols.includes(String(v).toLowerCase())) delete o[k];
            for (const c of Object.keys(sh)) if (boxCols.includes(c.toLowerCase())) delete sh[c];
            const sorted = Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a.startsWith("_") - b.startsWith("_")) || (+a - +b)));
            const ops = [{op: "set", path: ["palette", "own"], value: sorted}, {op: "set", path: ["palette", "shared"], value: sh}];
            const bgNow = (get(["sheet", "background"]) || []).map(c => c.toLowerCase());
            const bgAdd = boxCols.filter(c => !bgNow.includes(c));
            if (bgAdd.length) ops.push({op: "set", path: ["sheet", "background"], value: [...bgNow, ...bgAdd]});
            closeModal();
            if (await edit(ops))
              toast("Palette filled from the sheet (not saved yet)" + (bgAdd.length ? `; ${bgAdd.join(", ")} added to the sheet's background (cell boxes)` : ""));
          }}, "Apply")));
  }
  modal(box, {wide: true});
  render();
}

// the same colour to the eye: within 4 per channel (noswap check's tolerance)
function close(a, b) {
  const n = x => [1, 3, 5].map(i => parseInt(x.slice(i, i + 2), 16));
  const [p, q] = [n(a), n(b)];
  return p.every((v, i) => Math.abs(v - q[i]) <= 4);
}

export function renderPalette(main) {
  const p = get(["palette"]) || {};
  const tableBox = h("div", h("p.muted", "Reading his colours…"));
  main.append(h("div.page",
    h("h2", "Palette"),
    h("div.cols",
      h("div.col",
        h("section.card", h("div.row.spread", h("h3", "His own colours", h("span.hint", ` slots ${FIRST}-${LAST}`)),
          h("button.primary.small", {title: "propose a slot for every colour on his frames (shown before anything changes)", onclick: fillFromSheet}, "Fill from sheet…")),
          h("p.hint", "Origins S1/S2/CD and S3&K draw these slots in his colours; Mania has 13 free slots (the rarest share the nearest colour past that, the approved exception)."),
          ownGrid()),
        h("section.card", h("h3", "Shared with the base"), sharedList()),
        h("section.card", h("h3", "Other colours"),
          h("label.field", h("span.label", "other colours"), select(["palette", "other_colours"], [["nearest", "nearest: go to the nearest listed colour"], ["guess", "guess: sheet2ani's nearest of slots 1-15 and the listed ones"]])),
          h("div.field.bool", checkbox(["palette", "strict"], "strict"), h("span.hint", "Stop the build if a used frame has a colour with no slot (for sheets that say do not edit).")))),
      h("div.col", h("section.card", h("h3", "Colours on his frames"), tableBox)))));
  coloursTable(tableBox);
  if (S.sel.dialog === "fill") { delete S.sel.dialog; fillFromSheet(); }  // (#palette?dialog=fill: for links and screenshots)
}

S.renderers.palette = renderPalette;
