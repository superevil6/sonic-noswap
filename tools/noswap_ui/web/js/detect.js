// Frame detection on the Sheet tab: finds the sprites (noswap_cli/detect.py, via the backend's detect_frames) and
// shows them as dashed proposals to accept. Nothing changes until a proposal is accepted; accepting adds named
// frames in one edit, and "Remove the frames just added" takes a batch back out.
import {S, h, api, edit, toast, fill, frameNames} from "./core.js";

const store = {
  get(k, d) { try { const v = localStorage.getItem("noswap.detect." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  put(k, v) { try { localStorage.setItem("noswap.detect." + k, JSON.stringify(v)); } catch { /* private mode */ } },
};

export const DT = {
  on: false, res: null, busy: false, seq: 0, drag: null, region: null,
  merge: store.get("merge", 3), minSize: store.get("minSize", 3),
  showHidden: false, showExisting: false,
  sel: new Set(),       // keys (rect "x,y,w,h") of selected proposals
  rejected: new Set(),  // keys of rejected ones (kept across re-detects)
  extraBg: [], prefix: "", lastAdded: [],
};

const COL = {sprite: "#ff4fd8", small: "#ff9f43", text: "#4dd0e1", line: "#4dd0e1", tiny: "#c0ca33"};
const FRAMEISH = ["sprite", "small"];
let C = null;  // {V, draw, renderInspector, renderToolbar, scrollTo}: hooks from sheet.js

export function initDetect(ctx) { C = ctx; }

const key = p => p.rect.join(",");
const props = () => (DT.res && DT.res.proposals) || [];

function visible(p) {
  if (DT.rejected.has(key(p))) return false;
  if (p.existing && !DT.showExisting) return false;
  if (!FRAMEISH.includes(p.kind) && !DT.showHidden) return false;
  return true;
}
const shown = () => props().filter(visible);
const selected = () => props().filter(p => DT.sel.has(key(p)) && visible(p));

export function toggleDetect(on = !DT.on) {
  DT.on = on;
  if (on && !DT.res) runDetect();
  C.renderToolbar(); C.renderInspector(); C.draw();
}

let timer = null;
function redetectSoon() { clearTimeout(timer); timer = setTimeout(runDetect, 160); }

export async function runDetect() {
  const seq = ++DT.seq;
  DT.busy = true;
  renderCounts();
  try {
    const res = await api("detect_frames", {merge: DT.merge, min_size: DT.minSize, region: DT.region, extra_background: DT.extraBg});
    if (seq !== DT.seq) return;
    DT.res = res;
    const keys = new Set(res.proposals.map(key));
    for (const k of [...DT.sel]) if (!keys.has(k)) DT.sel.delete(k);
  } catch (e) { toast(e.message, "error"); }
  if (seq !== DT.seq) return;
  DT.busy = false;
  C.draw(); C.renderInspector();
}

// ------------------------------------------------------------------ drawing

export function drawDetect(ctx, z) {
  if (!DT.on) return;
  if (DT.region) dashed(ctx, DT.region, z, "#ffffff", 1, [6, 4]);
  if (DT.drag && DT.drag.rect) dashed(ctx, DT.drag.rect, z, "#ffffff", 2, [6, 4]);
  ctx.font = "10px system-ui, sans-serif";
  ctx.textBaseline = "bottom";
  for (const p of shown()) {
    const colour = p.existing ? "#9aa3b5" : COL[p.kind] || COL.sprite, on = DT.sel.has(key(p));
    const [x, y, w, hh] = p.rect;
    if (on) {
      ctx.fillStyle = "rgba(255, 79, 216, 0.18)";
      ctx.fillRect(x * z, y * z, w * z, hh * z);
    }
    dashed(ctx, p.rect, z, colour, on ? 2 : 1, on ? [] : [4, 3]);
    if (C.V.names && z >= 2 && (on || p.kind === "sprite")) {
      const text = p.existing ? "= " + p.existing : (p.name || p.kind);
      ctx.fillStyle = "rgba(14, 17, 23, 0.75)";
      const tw = ctx.measureText(text).width + 4;
      ctx.fillRect(x * z, (y + hh) * z + 1, tw, 12);
      ctx.fillStyle = colour;
      ctx.fillText(text, x * z + 2, (y + hh) * z + 12);
    }
  }
}

function dashed(ctx, r, z, colour, w, dash) {
  ctx.save();
  ctx.strokeStyle = colour; ctx.lineWidth = w; ctx.setLineDash(dash);
  ctx.strokeRect(r[0] * z - w / 2 - 1, r[1] * z - w / 2 - 1, r[2] * z + w + 2, r[3] * z + w + 2);
  ctx.restore();
}

// ------------------------------------------------------------------ mouse and keys (sheet.js calls these while on)

function hit(x, y) {
  let best = null, area = Infinity;
  for (const p of shown()) {
    const [rx, ry, rw, rh] = p.rect;
    if (x >= rx - 1 && y >= ry - 1 && x <= rx + rw && y <= ry + rh && rw * rh < area) { best = p; area = rw * rh; }
  }
  return best;
}

export function detectDown(e, x, y) {
  const p = hit(x, y);
  if (p) {
    const k = key(p);
    if (!e.shiftKey && !e.ctrlKey && !e.metaKey && !DT.sel.has(k)) DT.sel.clear();
    if (DT.sel.has(k)) DT.sel.delete(k); else DT.sel.add(k);
    C.draw(); C.renderInspector();
    return;
  }
  DT.drag = {start: [x, y], rect: null, add: e.shiftKey};
}

export function detectMove(x, y) {
  const d = DT.drag;
  if (!d) return false;
  const [sx, sy] = d.start;
  d.rect = [Math.min(sx, x), Math.min(sy, y), Math.abs(x - sx) + 1, Math.abs(y - sy) + 1];
  C.draw();
  return true;
}

export function detectUp() {
  const d = DT.drag;
  DT.drag = null;
  if (!d) return;
  if (!d.rect || d.rect[2] < 4 || d.rect[3] < 4) {  // a click on empty sheet: clear the selection
    if (!d.add) DT.sel.clear();
    C.draw(); C.renderInspector();
    return;
  }
  DT.region = d.rect;
  DT.sel.clear();
  runDetect();
}

export function detectDbl(x, y) {
  const p = hit(x, y);
  if (p && !p.existing) accept([p]);
}

export async function detectAltClick(colour) {
  if (!colour || DT.extraBg.includes(colour) || (DT.res && DT.res.background.includes(colour))) return;
  DT.extraBg.push(colour);
  toast(`${colour} counts as background for detection (not saved: "Add to the sheet's background" keeps it).`);
  runDetect();
}

export function detectKey(e) {
  const k = e.key;
  if (k === "Enter") accept(selected().filter(p => !p.existing));
  else if (k === "Delete" || k === "Backspace" || k === "x") reject();
  else if ((k === "a" || k === "A") && (e.ctrlKey || e.metaKey)) { for (const p of shown()) DT.sel.add(key(p)); C.draw(); C.renderInspector(); }
  else if (k === "Escape") { if (DT.sel.size) DT.sel.clear(); else if (DT.region) { DT.region = null; runDetect(); } else toggleDetect(false); C.draw(); C.renderInspector(); }
  else if (k === "s" && selected().length === 1) splitSel();
  else if (k === "m" && selected().length > 1) mergeSel();
  else return false;
  return true;
}

// ------------------------------------------------------------------ actions

function freeName(base, taken) {
  let n = base, i = 2;
  while (taken.has(n)) n = `${base}_${i++}`;
  taken.add(n);
  return n;
}

// sheet.background plus the cell fills detection found behind these rects (default: every proposal and frame), the
// guessed corner colours too when the file lists none. A fill elsewhere (a title panel) is left alone.
function boxColourOps(rects) {
  rects = rects || [...((DT.res && DT.res.proposals) || []).map(p => p.rect), ...Object.values(S.info.doc.frames || {}).filter(Array.isArray)];
  const meets = (a, b) => a[0] < b[0] + b[2] && b[0] < a[0] + a[2] && a[1] < b[1] + b[3] && b[1] < a[1] + a[3];
  const fills = Object.entries((DT.res && DT.res.fills) || {})
    .filter(([, boxes]) => boxes.length >= 3 && boxes.some(b => rects.some(r => meets(r, b)))).map(([c]) => c.toLowerCase());  // (cells come in numbers: one or two boxes are more likely scenery)
  const cur = ((S.info.doc.sheet && S.info.doc.sheet.background) || []).map(c => c.toLowerCase());
  const base = cur.length ? cur : ((DT.res && DT.res.background) || []).map(c => c.toLowerCase());
  const added = fills.filter(c => !base.includes(c));
  if (!added.length) return {ops: [], added: []};
  return {ops: [{op: "set", path: ["sheet", "background"], value: [...base, ...added]}], added};
}

async function addBoxColours() {
  const {ops, added} = boxColourOps();
  if (!ops.length) { toast("The cell-box colours are in the sheet's background already."); return; }
  if (await edit(ops, {render: false})) { toast(`Added to the sheet's background: ${added.join(", ")}.`); runDetect(); }
}

async function accept(list) {
  list = list.filter(p => !p.existing);
  if (!list.length) { toast("Nothing to accept: select proposals first (click; shift-click adds)."); return; }
  const taken = new Set(frameNames());
  const prefix = DT.prefix.trim().toUpperCase().replace(/[^A-Z0-9_]/g, "_");
  let n = 1;
  const names = list.map(p => {
    if (prefix) { while (taken.has(prefix + n)) n++; const nm = prefix + n; taken.add(nm); return nm; }
    return freeName(p.name || (p.kind === "text" ? "TEXT" : "FRAME"), taken);
  });
  // The cell-box colours detection counted as background go into sheet.background with the frames: else the build
  // (and Fill from sheet) would draw each box behind his sprite
  const bgOps = boxColourOps(list.map(p => p.rect));
  const ok = await edit([...list.map((p, i) => ({op: "set", path: ["frames", names[i]], value: p.rect})), ...bgOps.ops], {render: false});
  if (!ok) return;
  list.forEach((p, i) => { p.existing = names[i]; DT.sel.delete(key(p)); });
  DT.lastAdded = names;
  toast(`Added ${names.length} frame${names.length > 1 ? "s" : ""}: ${names.slice(0, 6).join(", ")}${names.length > 6 ? " …" : ""}. Rename them in the frame inspector (every use follows).`
    + (bgOps.added.length ? ` The cell-box colour${bgOps.added.length > 1 ? "s" : ""} ${bgOps.added.join(", ")} went into the sheet's background (the boxes aren't drawn in game).` : ""));
  (await import("./core.js")).rerender();
}

async function removeLast() {
  const doc = S.info.doc.frames || {};
  const gone = DT.lastAdded.filter(n => doc[n]);
  if (!gone.length) { DT.lastAdded = []; C.renderInspector(); return; }
  let used = [];
  try {
    const info = await api("frames_info");
    used = gone.filter(n => info.frames[n] && info.frames[n].used_by.length);
  } catch { /* the edit below still runs */ }
  let drop = gone;
  if (used.length && !confirm(`${used.length} of them are used already (${used.slice(0, 4).join(", ")}). Remove those too?`)) {
    drop = gone.filter(n => !used.includes(n));
  }
  if (!drop.length) return;
  if (!(await edit(drop.map(n => ({op: "del", path: ["frames", n]}), {render: false})))) return;
  for (const p of props()) if (drop.includes(p.existing)) p.existing = null;
  DT.lastAdded = DT.lastAdded.filter(n => !drop.includes(n));
  toast(`Removed ${drop.length} frame${drop.length > 1 ? "s" : ""}.`);
  (await import("./core.js")).rerender();
}

function reject() {
  const sel = selected();
  if (!sel.length) return;
  for (const p of sel) { DT.rejected.add(key(p)); DT.sel.delete(key(p)); }
  C.draw(); C.renderInspector();
}

async function splitSel() {
  const [p] = selected();
  if (!p) return;
  let rects;
  try { rects = (await api("detect_frames", {split: p.rect, extra_background: DT.extraBg})).rects; } catch (e) { toast(e.message, "error"); return; }
  if (rects.length < 2) { toast("It's one piece: nothing to split (merge 0 doesn't separate it)."); return; }
  const list = DT.res.proposals, i = list.indexOf(p);
  const taken = new Set([...frameNames(), ...list.map(q => q.name).filter(Boolean)]);
  const parts = rects.map((r, j) => ({rect: r, kind: r[2] * r[3] >= 64 ? "sprite" : "small", confidence: 0.5, parts: 1, px: 0,
    name: freeName(`${p.name || "FRAME"}_${String.fromCharCode(97 + j)}`, taken), existing: null}));
  list.splice(i, 1, ...parts);
  DT.sel.clear();
  parts.forEach(q => DT.sel.add(key(q)));
  C.draw(); C.renderInspector();
}

async function mergeSel() {
  const sel = selected();
  if (sel.length < 2) return;
  const x0 = Math.min(...sel.map(p => p.rect[0])), y0 = Math.min(...sel.map(p => p.rect[1]));
  const x1 = Math.max(...sel.map(p => p.rect[0] + p.rect[2])), y1 = Math.max(...sel.map(p => p.rect[1] + p.rect[3]));
  let rect = [x0, y0, x1 - x0, y1 - y0];
  try { rect = (await api("fit_rect", {rect})).rect; } catch { /* keep the union */ }
  const list = DT.res.proposals;
  const first = sel.find(p => p.name) || sel[0];
  const merged = {rect, kind: "sprite", confidence: 0.6, parts: sel.reduce((a, p) => a + (p.parts || 1), 0), px: 0,
    name: first.name, existing: null};
  list.splice(list.indexOf(sel[0]), 0, merged);
  for (const p of sel) list.splice(list.indexOf(p), 1);
  DT.sel = new Set([key(merged)]);
  C.draw(); C.renderInspector();
}

// ------------------------------------------------------------------ the panel (in the inspector's place)

function renderCounts() {
  const el = document.getElementById("detect-counts");
  if (el) fill(el, countsText());
}

function countsText() {
  if (DT.busy && !DT.res) return "looking…";
  if (!DT.res) return "";
  const all = props(), vis = shown();
  const hidden = {existing: 0, other: 0, rejected: 0};
  for (const p of all) {
    if (DT.rejected.has(key(p))) hidden.rejected++;
    else if (p.existing && !DT.showExisting) hidden.existing++;
    else if (!FRAMEISH.includes(p.kind) && !DT.showHidden) hidden.other++;
  }
  const parts = [`${vis.filter(p => !p.existing).length} new`];
  if (hidden.existing) parts.push(`${hidden.existing} on frames you have`);
  if (hidden.other) parts.push(`${hidden.other} text / lines / specks`);
  if (hidden.rejected) parts.push(`${hidden.rejected} rejected`);
  return parts.join(" · ") + (DT.busy ? " …" : "");
}

export function renderDetectPanel(box) {
  const slider = (label, k, min, max, hint) => h("label.detect-slider", {title: hint},
    h("span", label), h("input", {type: "range", min, max, value: DT[k], "data-key": "detect-" + k,
      oninput: e => { DT[k] = +e.target.value; store.put(k, DT[k]); e.target.nextSibling.textContent = DT[k] + " px"; redetectSoon(); }}),
    h("span.mono", DT[k] + " px"));
  const check = (label, k) => h("label.check", h("input", {type: "checkbox", checked: DT[k],
    onchange: e => { DT[k] = e.target.checked; C.draw(); C.renderInspector(); }}), h("span", label));
  const sel = selected(), vis = shown().filter(p => !p.existing);
  const fresh = DT.lastAdded.filter(n => (S.info.doc.frames || {})[n]);
  const bg = DT.res ? DT.res.background : [];
  fill(box,
    h("section.card.detect",
      h("div.row.spread", h("h3", "Detect frames"), h("button.small", {onclick: () => toggleDetect(false), title: "back to editing frames (D)"}, "Done")),
      h("p.hint", "Dashed boxes are proposals, trimmed to the drawing. Click to select (shift-click adds), double-click accepts one, drag on an empty spot to look only inside that area. Your frames aren't touched."),
      slider("merge", "merge", 0, 12, "small bits (sparks, drops, a detached hand) this close to a bigger body join it"),
      slider("min size", "minSize", 1, 10, "lone pieces smaller than this both ways are specks (hidden)"),
      h("div.checks", check("text, lines, specks", "showHidden"), check("on existing frames", "showExisting")),
      DT.region ? h("div.row", h("span.hint", `Area: ${DT.region.join(", ")}`), h("button.small", {onclick: () => { DT.region = null; runDetect(); }}, "Whole sheet")) : null,
      h("div.detect-bg",
        h("span.hint", DT.res && DT.res.guessed_background ? "background (guessed from the corners):" : "background:"),
        bg.map(c => h("span.swatch", {style: {background: c}, title: c})),
        Object.keys((DT.res && DT.res.fills) || {}).map(c => h("span.swatch", {style: {background: c}, title: `${c}: a cell-box fill, counted as background`})),
        boxColourOps().added.length ? h("button.small", {onclick: addBoxColours,
          title: "the boxes' colour isn't part of the sprites: save it in sheet.background so the build and Fill from sheet leave it out (accepting frames does this too)"},
          "Add the box colour to the background") : null,
        DT.extraBg.map(c => h("span.tag", h("span.swatch", {style: {background: c}}), h("span.mono", c),
          h("button.x", {title: "stop treating it as background", onclick: () => { DT.extraBg = DT.extraBg.filter(x => x !== c); runDetect(); }}, "×"))),
        h("span.hint", "alt-click the sheet: one more background colour"),
        DT.extraBg.length ? h("button.small", {title: "save these colours in sheet.background (the build ignores them too)",
          onclick: async () => {
            const cur = (S.info.doc.sheet && S.info.doc.sheet.background) || [];
            if (await edit([{op: "set", path: ["sheet", "background"], value: [...cur, ...DT.extraBg.filter(c => !cur.includes(c))]}], {render: false})) {
              DT.extraBg = []; toast("Added to the sheet's background."); runDetect();
            }
          }}, "Add to the sheet's background") : null),
      h("p.mono.small#detect-counts", countsText()),
      h("label.mini", h("span", "names"), h("input.mono", {value: DT.prefix, placeholder: "ROW<row>_<n>", "data-key": "detect-prefix", style: {width: "130px"},
        title: "a prefix such as WALK names them WALK1, WALK2, ... in reading order", oninput: e => { DT.prefix = e.target.value; }})),
      h("div.row.detect-actions",
        h("button.small.primary", {disabled: !sel.filter(p => !p.existing).length, onclick: () => accept(sel), title: "Enter"}, `Accept selected (${sel.filter(p => !p.existing).length})`),
        h("button.small", {disabled: !vis.length, onclick: () => { if (vis.length < 20 || confirm(`Add all ${vis.length} proposals as frames?`)) accept(vis); }}, `Accept all (${vis.length})`)),
      h("div.row.detect-actions",
        h("button.small", {disabled: !sel.length, onclick: reject, title: "Delete / X"}, "Reject"),
        h("button.small", {disabled: sel.length !== 1, onclick: splitSel, title: "cut it into its separate pieces (S)"}, "Split"),
        h("button.small", {disabled: sel.length < 2, onclick: mergeSel, title: "one box around the selected ones (M)"}, "Merge"),
        DT.rejected.size ? h("button.small", {onclick: () => { DT.rejected.clear(); C.draw(); C.renderInspector(); }}, "Unreject all") : null),
      fresh.length ? h("div.row.detect-undo", h("span.hint", `Just added ${fresh.length}.`),
        h("button.small.danger", {onclick: removeLast, title: "take the last accepted batch back out (Revert throws away every unsaved edit)"}, `Remove the ${fresh.length} just added`)) : null),
    h("section.card.grow",
      h("div.list#detect-list", {"data-scroll": "detect"}, shown().map(p => h("div.item" + (DT.sel.has(key(p)) ? ".on" : ""), {
        onclick: e => { const k = key(p); if (!e.shiftKey) DT.sel.clear(); DT.sel.add(k); C.draw(); C.renderInspector(); C.scrollTo(p.rect); },
        ondblclick: () => accept([p])},
        h("span.mono", p.existing ? `= ${p.existing}` : p.name || p.kind), h("span.muted.mono", `${p.rect[2]}×${p.rect[3]}`),
        h("span.badge" + (p.kind === "sprite" ? ".yes" : p.kind === "small" ? ".partial" : ".plain"), {title: p.parts > 1 ? `${p.parts} pieces merged` : ""}, p.kind + (p.parts > 1 ? ` +${p.parts - 1}` : "")))))));
}
