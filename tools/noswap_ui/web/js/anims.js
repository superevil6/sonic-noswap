// The Animations tab: every animation slot the base character has (and NoSwap's ability slots), each one's frames
// and options, and a preview that plays it with the frames placed as the game places them (sheet2ani.build_anims,
// through the backend): feet on the ground line, or centred.
import {S, fill, h, api, set, del, get, go, frameNames, numInput, select, checkbox, textInput, rerender} from "./core.js";
import {ballPanel, ballUse, ballBadge} from "./ball.js";

// tools/noswap_cli/abilities_info.py SLOT_MEANING
const SLOTS = {"41": "the jump ability (an attack)", "42": "hover / glide", "43": "the Y move on the ground",
  "44": "the Y move in the air", "45": "aimed up", "46": "aimed down", "47": "glide up / cling / swim",
  "48": "glide down", "49": "rolling", "50": "Power Surge idle", "51": "Power Surge walk", "52": "Power Surge run"};

const P = {playing: true, frame: 0, ticks: null, onion: false, zoom: 3, data: null, key: null, raf: null, last: 0, acc: 0,
  raw: false, all: false, delta: null, drag: null, timer: null};

// A frame entry's own offset ({"frame": NAME, "offset": [dx, dy]}: px, +x right, +y down, as drawn in the preview, a
// mirrored frame too), and the entry with another offset: [0, 0] goes back to the plain name (or rect).
const refOffset = ref => ref && typeof ref === "object" && !Array.isArray(ref) && Array.isArray(ref.offset) ? ref.offset : [0, 0];
function withOffset(ref, off) {
  const zero = !off[0] && !off[1];
  if (typeof ref === "string") return zero ? ref : {frame: ref, offset: off};
  if (Array.isArray(ref)) return zero ? ref : {rect: ref, offset: off};
  if (!ref || typeof ref !== "object") return ref;
  if (!zero) return {...ref, offset: off};  // (an existing "offset" keeps its place)
  const {offset, ...rest} = ref;
  const keys = Object.keys(rest);
  if (keys.length === 1 && keys[0] === "frame") return rest.frame;
  if (keys.length === 1 && keys[0] === "rect") return rest.rect;
  return rest;
}
const thumbs = new Map();

// What fills a slot he left out (backend._fallbacks: tools/anim_fallbacks.plan): {source} borrowed frames, {ball} the
// generic ball, {empty} null on purpose.
export function standIn(sec, name) {
  const fb = S.info.fallbacks || {}, d = S.info.doc, use = ballUse();
  if (sec === "ability_animations") return name === "49" && use.includes("Rolling") ? {ball: true} : null;
  if (sec === "special_stage") {
    if (use.includes("Special Stage")) return {ball: true};
    if ((d.special_stage || {})[name] === null) return {empty: true};
    const src = ((fb.special || {}).used || {})[name];
    return src ? {source: src} : null;
  }
  if (["Jumping", "Spin Dash"].includes(name) && use.includes(name)) return {ball: true};
  if ((d.animations || {})[name] === null || (d.animations_sonic2 || {})[name] === null) return {empty: true};
  const src = ((fb.Sonic2 || {}).used || {})[name] || ((fb.Sonic1 || {}).used || {})[name];
  return src ? {source: src} : null;
}

// The source animation a fallback borrows: {anim, path} ("Rolling" is ability slot 49), or {ball} when that is the ball.
function sourceOf(src) {
  const d = S.info.doc;
  if (src === "Rolling") return ballUse().includes("Rolling") ? {ball: true} : {anim: (d.ability_animations || {})["49"], path: ["ability_animations", "49"]};
  if (["Jumping", "Spin Dash"].includes(src) && ballUse().includes(src)) return {ball: true};
  for (const sec of ["animations", "animations_sonic2"]) {
    const a = (d[sec] || {})[src];
    if (a && typeof a === "object") return {anim: a, path: [sec, src]};
  }
  return {};
}

function entries() {
  const d = S.info.doc, t = S.info.templates;
  const s1 = t.Sonic1.all, s2 = t.Sonic2.all;
  const filled = new Set([...t.Sonic1.filled, ...t.Sonic2.filled]);
  const names = [...s2, ...s1.filter(n => !s2.includes(n))];
  const out = [{group: "Generic spin ball", name: "ball", section: "ball", title: d.ball ? `Ball: ${ballUse().join(", ")}` : "Ball (none)", defined: !!d.ball, frames: 0, isBall: true}];
  const anim = (sec, n) => (d[sec] || {})[n];
  for (const n of names) {
    const sec = anim("animations", n) ? "animations" : anim("animations_sonic2", n) ? "animations_sonic2" : null;
    const section = sec || (s1.includes(n) ? "animations" : "animations_sonic2");
    out.push({group: "Base animations", name: n, section,
      defined: !!sec, frames: sec ? (anim(sec, n).frames || []).length : 0, needed: filled.has(n),
      only: !s1.includes(n) ? "S2/CD/3K" : !s2.includes(n) ? "S1" : null, stand: standIn(section, n)});
  }
  for (const sec of ["animations", "animations_sonic2"]) {
    for (const n of Object.keys(d[sec] || {})) {
      if (!n.startsWith("_") && !names.includes(n)) out.push({group: "Other (Sonic CD names…)", name: n, section: sec, defined: true, frames: (d[sec][n].frames || []).length});
    }
  }
  const ab = d.ability_animations || {};
  const slots = new Set([...Object.keys(SLOTS), ...Object.keys(ab).filter(k => !k.startsWith("_"))]);
  for (const s of [...slots].sort((a, b) => a - b)) {
    out.push({group: "Ability slots", name: s, section: "ability_animations", defined: !!ab[s], frames: ab[s] ? (ab[s].frames || []).length : 0,
      title: ab[s] && ab[s].name ? `${s} ${ab[s].name}` : `${s} (${SLOTS[s] || "slot"})`, needed: neededSlots().has(s), stand: standIn("ability_animations", s)});
  }
  const ss = d.special_stage || {};
  out.push({group: "Sonic 1 special stage", name: "Special Stage", section: "special_stage", defined: !!ss["Special Stage"],
    frames: ss["Special Stage"] ? (ss["Special Stage"].frames || []).length : 0, needed: true, stand: standIn("special_stage", "Special Stage")});
  out.push({group: "Sonic 3&K act clear", name: "s3k_victory", title: "Act clear pose", section: "s3k_victory", defined: !!d.s3k_victory,
    frames: d.s3k_victory ? (d.s3k_victory.frames || []).length : 0});
  return out;
}

function neededSlots() {
  const reg = S.registry, moves = ((S.info.doc.abilities || {}).abilities) || [];
  const out = new Set();
  if (!reg) return out;
  for (const m of moves) for (const [s, d] of Object.entries((reg.abilities[m] || {}).slots || {})) if (d.required) out.add(s);
  if (S.info.doc.flags && S.info.doc.flags.roll) out.add("49");
  return out;
}

function current() {
  let sec = S.sel.section;
  const name = S.sel.anim;
  const d = S.info.doc;
  if (sec === "animations" && !(d.animations || {})[name] && (d.animations_sonic2 || {})[name]) sec = S.sel.section = "animations_sonic2";
  if (sec === "animations_sonic2" && !(d.animations_sonic2 || {})[name] && (d.animations || {})[name]) sec = S.sel.section = "animations";
  if (sec === "s3k_victory") return {path: ["s3k_victory"], anim: S.info.doc.s3k_victory, sec, name: "s3k_victory"};
  if (sec === "ball") return {path: ["ball"], anim: S.info.doc.ball, sec, name: "ball"};
  return {path: [sec, name], anim: get([sec, name]), sec, name};
}

function list() {
  const es = entries();
  let group = null;
  const items = [];
  for (const e of es) {
    if (e.group !== group) { group = e.group; items.push(h("div.group-title", group)); }
    const on = e.section === S.sel.section && (e.section === "s3k_victory" || e.name === S.sel.anim);
    const st = e.stand;
    const state = st && st.ball ? h("span.badge.ball", {title: "the generic ball (Ball panel)"}, "generic ball")
      : e.isBall ? (e.defined ? h("span.badge.yes", "on") : h("span.badge.plain", "–"))
      : e.defined && e.frames ? h("span.badge.yes", e.frames)
      : st && st.source ? h("span.badge.fallback", {title: `no frames of his own: uses ${st.source}'s (fallback)`}, `↳ ${st.source}`)
      : st && st.empty ? h("span.badge.plain", {title: "null: deliberately empty"}, "null")
      : e.needed ? h("span.badge.no", {title: "the game shows nothing here"}, "empty") : h("span.badge.plain", "–");
    items.push(h("div.item" + (on ? ".on" : "") + (e.defined ? "" : ".undef"), {onclick: () => go("anims", {section: e.section, anim: e.section === "s3k_victory" ? null : e.name})},
      h("span", e.title || e.name), e.only ? h("span.muted.small", e.only) : null, state));
  }
  return h("div.anim-list", {"data-scroll": "animlist"}, items);
}

async function thumb(ref) {
  const key = JSON.stringify([ref, typeof ref === "string" ? (S.info.doc.frames || {})[ref] : (S.info.doc.frames || {})[ref.frame]]);
  if (!thumbs.has(key)) thumbs.set(key, api("frame_image", {ref, raw: false, scale: 2}).catch(() => null));
  return thumbs.get(key);
}

function frameChips(c) {
  const refs = (c.anim && c.anim.frames) || [];
  const path = [...c.path, "frames"];
  const names = new Set(frameNames());
  const chips = refs.map((ref, i) => {
    const off = refOffset(ref);
    const label = (typeof ref === "string" ? ref : ref && ref.frame ? ref.frame + (ref.flip ? " ⇋" : "") + (ref.rotate ? ` ⟳${ref.rotate}` : "") : Array.isArray(ref) ? `[${ref.join(",")}]` : ref && ref.rect ? `[${ref.rect.join(",")}]` : "layered")
      + (off[0] || off[1] ? ` ✥${off[0]},${off[1]}` : "");
    const bad = typeof ref === "string" ? !names.has(ref) : ref && ref.frame ? !names.has(ref.frame) : false;
    const img = h("span.thumb.checker");
    if (!bad) thumb(ref).then(t => { if (t) fill(img, h("img.pixel", {src: t.png, width: t.w, height: t.h})); });
    const move = d => {
      const j = i + d;
      if (j < 0 || j >= refs.length) return;
      const nr = [...refs];
      [nr[i], nr[j]] = [nr[j], nr[i]];
      set(path, nr);
    };
    const flip = () => {
      const nr = [...refs];
      if (typeof ref === "string") nr[i] = {frame: ref, flip: true};
      else if (ref && ref.frame) { const {flip: f, ...rest} = ref; nr[i] = f ? (Object.keys(rest).length === 1 ? rest.frame : rest) : {...ref, flip: true}; }
      else return;
      set(path, nr);
    };
    return h("div.chip-frame" + (bad ? ".bad" : "") + (P.frame === i ? ".on" : ""), {title: bad ? `${label}: no such frame` : label,
      onclick: () => { P.playing = false; P.frame = i; drawPreview(); markChips(); }},
      h("span.n", String(i)), img, h("span.lbl.mono", label),
      h("div.chip-actions",
        h("button.icon", {title: "earlier", onclick: e => { e.stopPropagation(); move(-1); }}, "‹"),
        h("button.icon", {title: "mirror left-right", onclick: e => { e.stopPropagation(); flip(); }}, "⇋"),
        h("button.icon", {title: "show on the sheet", onclick: e => { e.stopPropagation(); go("sheet", {frame: typeof ref === "string" ? ref : ref.frame, scrollTo: true}); }}, "⌖"),
        h("button.icon", {title: "later", onclick: e => { e.stopPropagation(); move(1); }}, "›"),
        h("button.icon.danger", {title: "remove", onclick: e => { e.stopPropagation(); set(path, refs.filter((_, j) => j !== i)); }}, "×")));
  });
  const pick = h("select", {"data-key": "add-frame"}, h("option", {value: ""}, "add a frame…"), [...names].map(n => h("option", {value: n}, n)));
  pick.onchange = () => { if (pick.value) set(path, [...refs, pick.value]); };
  const fromSheet = S.sel.frame && names.has(S.sel.frame)
    ? h("button.small", {title: "the frame selected on the Sheet tab", onclick: () => set(path, [...refs, S.sel.frame])}, `+ ${S.sel.frame}`) : null;
  return h("div.chips", chips, h("div.chip-add", pick, fromSheet));
}

function markChips() {
  document.querySelectorAll(".chip-frame").forEach((el, i) => el.classList.toggle("on", i === P.frame));
}

function options(c) {
  const a = c.anim, p = c.path, isAbility = c.sec === "ability_animations";
  const tplSpeed = S.info.speeds[c.name];
  return h("div.anim-opts",
    isAbility ? h("label.mini", h("span", "name"), textInput([...p, "name"])) : null,
    c.sec !== "s3k_victory" ? h("label.mini", h("span", "anchor"), select([...p, "anchor"], [["feet", "feet (on the ground)"], ["center", "center (balls, falls)"]], {allowNone: true})) : null,
    c.sec !== "s3k_victory" ? h("label.mini", {title: "frame number to loop back to (from 0)"}, h("span", "loop"), numInput([...p, "loop"], {min: 0, width: "4em"})) : null,
    c.sec !== "s3k_victory" ? h("label.mini", {title: "the .ani speed (240 = a new frame every game frame)"}, h("span", "speed"), numInput([...p, "speed"], {min: 0, max: 255, width: "4.5em", placeholder: tplSpeed !== undefined ? String(tplSpeed) : isAbility ? "60" : ""})) : null,
    c.sec !== "s3k_victory" ? h("label.mini", {title: "rotation mode (0 none, 1 full, 2 45° steps…)"}, h("span", "rot"), numInput([...p, "rot"], {min: 0, max: 4, width: "3.5em"})) : null,
    c.sec !== "s3k_victory" ? h("label.mini", {title: "show each frame this many times (for speeds the game sets)"}, h("span", "hold"), numInput([...p, "hold"], {min: 1, width: "3.5em"})) : null,
    c.sec !== "s3k_victory" ? h("label.mini", {title: "override the template's hitbox number"}, h("span", "hitbox"), numInput([...p, "hitbox"], {min: 0, width: "3.5em"})) : null,
    c.sec === "s3k_victory" ? h("label.mini", {title: "which frame is held at the end"}, h("span", "pose"), numInput(["s3k_victory", "pose"], {min: 0, width: "3.5em"})) : null,
    checkbox([...p, "align"], "align", {title: "nudge frames sideways to overlap the first (keeps the body still)"}));
}

async function loadPreview(c) {
  const key = JSON.stringify([c.sec, c.name, c.anim, S.info.doc.frames, S.info.doc.palette, S.info.doc.sheet, S.info.doc.base, P.raw]);
  if (P.key === key && P.data) return P.data;
  P.key = key;
  try { P.data = await api("animation", {section: c.sec, name: c.name, raw: P.raw}); }
  catch (e) { P.data = {error: e.message, frames: []}; }
  if (P.frame >= P.data.frames.length) P.frame = 0;
  return P.data;
}

function bounds(d) {
  let l = 8, r = 8, t = 8, b = 8;
  for (const f of d.frames) {
    l = Math.max(l, -f.px); r = Math.max(r, f.px + f.w); t = Math.max(t, -f.py); b = Math.max(b, f.py + f.h);
  }
  if (d.anchor === "feet") b = Math.max(b, d.feet_y + 6);
  return {l: l + 6, r: r + 6, t: t + 6, b: b + 6};
}

const imgCache = new Map();
function imgOf(png) {
  if (!imgCache.has(png)) {
    const i = new Image();
    i.onload = () => drawPreview();
    i.src = png;
    imgCache.set(png, i);
  }
  return imgCache.get(png);
}

function drawPreview() {
  const c = document.getElementById("anim-canvas");
  const d = P.data;
  if (!c || !d) return;
  const z = P.zoom, bb = P.drag ? P.drag.bb : bounds(d);
  c.width = (bb.l + bb.r) * z; c.height = (bb.t + bb.b) * z;
  const ctx = c.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = "#1a1f2b"; ctx.fillRect(0, 0, c.width, c.height);
  const ox = bb.l * z, oy = bb.t * z;
  if (d.anchor === "feet") {
    const gy = oy + d.feet_y * z;
    ctx.fillStyle = "#22301f"; ctx.fillRect(0, gy, c.width, c.height - gy);
    ctx.fillStyle = "#7ddc7d"; ctx.fillRect(0, gy, c.width, 1);
  }
  const n = d.frames.length;
  const cur = n ? d.frames[P.frame % n] : null;
  const paint = (f, alpha) => {
    const im = imgOf(f.png);
    if (!im.complete) return;
    ctx.globalAlpha = alpha;
    // (an offset being dragged or nudged and not saved yet: this frame, or every frame with "move all frames")
    const moved = P.delta && (P.all || f.index === cur.index);
    const fx = f.px + (moved ? P.delta.dx : 0), fy = f.py + (moved ? P.delta.dy : 0);
    ctx.drawImage(im, ox + fx * z, oy + fy * z, f.w * z, f.h * z);
    ctx.globalAlpha = 1;
  };
  if (n) {
    if (P.onion && n > 1) paint(d.frames[(P.frame - 1 + n) % n], 0.3);
    paint(d.frames[P.frame % n], 1);
  }
  ctx.strokeStyle = "#ff6b6b"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(ox - 4, oy + 0.5); ctx.lineTo(ox + 5, oy + 0.5); ctx.moveTo(ox + 0.5, oy - 4); ctx.lineTo(ox + 0.5, oy + 5); ctx.stroke();
  const info = document.getElementById("anim-info");
  if (info && n) {
    const f = d.frames[P.frame % n];
    const dd = P.delta || {dx: 0, dy: 0};
    info.textContent = `frame ${P.frame % n + 1}/${n} · ${f.label} · ${f.w}×${f.h} · pivot ${f.px + dd.dx}, ${f.py + dd.dy}`;
  }
  const ox_ = document.getElementById("off-x"), oy_ = document.getElementById("off-y");
  if (ox_ && n && document.activeElement !== ox_ && document.activeElement !== oy_) {
    const f = d.frames[P.frame % n], dd = P.delta || {dx: 0, dy: 0};
    ox_.value = f.offset[0] + dd.dx; oy_.value = f.offset[1] + dd.dy;
  }
}

function tick(t) {
  P.raf = requestAnimationFrame(tick);
  if (!P.data || !P.data.frames.length || !document.getElementById("anim-canvas")) return;
  const dt = Math.min(100, t - (P.last || t));
  P.last = t;
  if (!P.playing) return;
  const per = ticksPer() * 1000 / 60;
  P.acc += dt;
  if (P.acc >= per) {
    P.acc %= per;
    const n = P.data.frames.length;
    P.frame = P.frame + 1 >= n ? Math.min(P.data.loop || 0, n - 1) : P.frame + 1;
    drawPreview(); markChips();
  }
}
const ticksPer = () => P.ticks || (P.data && P.data.ticks) || 6;
if (!P.raf) P.raf = requestAnimationFrame(tick);

// ---- moving a frame: drag it in the preview, or arrow keys with the preview focused (shift: 8 px). The move is the
// frame entry's "offset" (sheet2ani.frame_offset), saved after a short pause so a held key is one edit.
function curFrame() {
  const d = P.data;
  return d && d.frames.length ? d.frames[P.frame % d.frames.length] : null;
}

function commitDelta() {
  clearTimeout(P.timer);
  const dl = P.delta;
  P.delta = null;
  if (!dl || (!dl.dx && !dl.dy)) { drawPreview(); return; }
  const f = curFrame();
  if (!f) return;
  for (const g of P.data.frames) if (P.all || g.index === f.index) {  // (shown where it will be while the edit runs)
    g.px += dl.dx; g.py += dl.dy; g.offset = [g.offset[0] + dl.dx, g.offset[1] + dl.dy];
  }
  shiftOffsets(P.all ? null : f.index, dl.dx, dl.dy);
}

function shiftOffsets(index, dx, dy) {
  const c = current();
  const refs = (c.anim && c.anim.frames) || [];
  const nr = refs.map((r, i) => index === null || i === index ? withOffset(r, [refOffset(r)[0] + dx, refOffset(r)[1] + dy]) : r);
  return set([...c.path, "frames"], nr);
}

function setOffset(index, off) {
  const c = current();
  const refs = (c.anim && c.anim.frames) || [];
  return set([...c.path, "frames"], refs.map((r, i) => i === index ? withOffset(r, off) : r));
}

function nudge(dx, dy) {
  if (!curFrame()) return;
  P.playing = false; renderControls();
  P.delta = {dx: (P.delta ? P.delta.dx : 0) + dx, dy: (P.delta ? P.delta.dy : 0) + dy};
  drawPreview();
  clearTimeout(P.timer);
  P.timer = setTimeout(commitDelta, 400);
}

function wireCanvas(cv) {
  cv.addEventListener("mousedown", e => {
    if (!curFrame() || e.button !== 0) return;
    commitDelta();
    P.playing = false; renderControls();
    cv.focus();
    const r = cv.getBoundingClientRect();
    P.drag = {x: e.clientX, y: e.clientY, sx: cv.width / r.width, sy: cv.height / r.height, bb: bounds(P.data)};
    P.delta = {dx: 0, dy: 0};
    cv.classList.add("dragging");
    e.preventDefault();
  });
}
window.addEventListener("mousemove", e => {
  if (!P.drag) return;
  P.delta = {dx: Math.round((e.clientX - P.drag.x) * P.drag.sx / P.zoom), dy: Math.round((e.clientY - P.drag.y) * P.drag.sy / P.zoom)};
  drawPreview();
});
window.addEventListener("mouseup", () => {
  if (!P.drag) return;
  P.drag = null;
  const cv = document.getElementById("anim-canvas");
  if (cv) cv.classList.remove("dragging");
  commitDelta();
});

function offsetPanel(c) {
  const f = curFrame();
  const refs = (c.anim && c.anim.frames) || [];
  const any = refs.some(r => { const o = refOffset(r); return o[0] || o[1]; });
  const num = (id, k) => h("input.mono#" + id, {type: "number", step: 1, value: f ? f.offset[k] : 0, disabled: f ? null : true,
    title: k ? "dy: px, + is down" : "dx: px, + is right (as drawn here, a mirrored frame too)",
    onchange: e => { const g = curFrame(); if (!g) return; const o = [...g.offset]; o[k] = Math.round(+e.target.value || 0); setOffset(g.index, o); }});
  return h("div.offset-box",
    h("div.offset-row",
      h("span.label", "move frame"), h("span.small", "dx"), num("off-x", 0), h("span.small", "dy"), num("off-y", 1),
      h("button.small", {title: "back to where the build puts it", disabled: f && (f.offset[0] || f.offset[1]) ? null : true,
        onclick: () => setOffset(curFrame().index, [0, 0])}, "Reset"),
      h("label.check", {title: "drag / arrow keys / the inputs' change moves every frame of this animation by the same amount"},
        h("input", {type: "checkbox", checked: P.all, onchange: e => { P.all = e.target.checked; }}), h("span", "move all frames together")),
      any ? h("button.small", {title: "reset every frame's offset in this animation", onclick: () => set([...c.path, "frames"], refs.map(r => withOffset(r, [0, 0])))}, "Reset all") : null),
    h("p.hint", "Drag the sprite, or click the preview and use the arrow keys (shift: 8 px; , and . step frames then). "
      + "Onion skin shows the previous frame to line it up against. Saved in the frame's entry as \"offset\": [dx, dy] "
      + "(+ right / down, as drawn here, a mirrored frame too), after the anchor, align and the ball's ground line."));
}

function previewPanel(c) {
  const d = P.data;
  const cv = h("canvas#anim-canvas.pixel", {tabindex: 0, "data-key": "anim-canvas", title: "drag to move this frame; arrow keys nudge it (shift: 8 px)"});
  wireCanvas(cv);
  const col = d && d.colours === "sheet" ? "sheet" : "game";
  return h("div.anim-preview",
    h("div.row.spread",
      h("span.colour-tag." + col, {title: col === "game" ? "as the game draws him: Sonic 1/2's player palette with his own slots (palette tab)" : "the sheet's own colours, not what the game draws"},
        col === "game" ? "game colours" : "sheet colours"),
      h("label.check", {title: "show the sheet's own colours instead of the game's"},
        h("input", {type: "checkbox", checked: P.raw, onchange: e => { P.raw = e.target.checked; rerender(); }}), h("span", "sheet colours"))),
    d && d.colours === "game" && d.collapse && d.collapse.bad ? h("div.alert",
      h("b", `In the game's colours these frames' ${d.collapse.sheet} sheet colours become ${d.collapse.game}: a flat silhouette. `),
      "His palette lists too few colours (the rest go to the nearest listed one). ",
      h("button.small.primary", {onclick: () => go("palette")}, "Fix it on the Palette tab")) : null,
    h("div.preview-stage", cv),
    h("div.mono.small#anim-info"),
    d && d.error ? h("p.bad", d.error) : null,
    d && d.missing && d.missing.length ? h("p.bad", `Can't cut: ${d.missing.join(", ")}`) : null,
    h("div.row.controls",
      h("button", {title: "previous frame", onclick: () => { P.playing = false; P.frame = (P.frame - 1 + P.data.frames.length) % Math.max(1, P.data.frames.length); drawPreview(); markChips(); renderControls(); }}, "⏮"),
      h("button#play.primary", {title: "play / pause (space)", onclick: () => { P.playing = !P.playing; renderControls(); }}, P.playing ? "Pause" : "Play"),
      h("button", {title: "next frame", onclick: () => { P.playing = false; P.frame = (P.frame + 1) % Math.max(1, P.data.frames.length); drawPreview(); markChips(); renderControls(); }}, "⏭"),
      h("label.check", h("input", {type: "checkbox", checked: P.onion, onchange: e => { P.onion = e.target.checked; drawPreview(); }}), h("span", "onion skin")),
      h("label.mini", h("span", "zoom"), h("select", {onchange: e => { P.zoom = +e.target.value; drawPreview(); }},
        [1, 2, 3, 4, 6].map(z => h("option", {value: z, selected: z === P.zoom ? "" : null}, z + "×"))))),
    h("div.row.controls",
      h("label.mini", {title: "game frames per animation frame (60 a second)"}, h("span", "ticks"),
        h("input", {type: "range", min: 1, max: 30, value: ticksPer(), oninput: e => { P.ticks = +e.target.value; e.target.nextSibling.textContent = `${P.ticks} (${(60 / P.ticks).toFixed(1)} fps)`; }}),
        h("span.mono.small", `${ticksPer()} (${(60 / ticksPer()).toFixed(1)} fps)`)),
      h("button.small", {title: "back to the animation's own speed", onclick: () => { P.ticks = null; rerender(); }}, "game speed")),
    offsetPanel(c),
    h("p.hint", d && d.ticks ? `Its .ani speed ${d.speed}: a new frame every ${d.ticks} game frame(s).`
      : "Speed 0: the game sets this animation's speed as he moves (walking, running); the slider picks one to look at."),
    h("p.hint", d && d.anchor === "feet" ? "Green: the ground line. Red cross: the object's position." : "Centred on the object's position (red cross)."));
}

function renderControls() {
  const b = document.getElementById("play");
  if (b) b.textContent = P.playing ? "Pause" : "Play";
}

document.addEventListener("keydown", e => {
  if (S.tab !== "anims" || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
  const arrows = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]};
  if (document.activeElement.id === "anim-canvas" && arrows[e.key] && !e.altKey && !e.ctrlKey && !e.metaKey) {
    const k = e.shiftKey ? 8 : 1;
    nudge(arrows[e.key][0] * k, arrows[e.key][1] * k);
    e.preventDefault();
    return;
  }
  if (e.key === " ") { P.playing = !P.playing; renderControls(); e.preventDefault(); }
  else if (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "." || e.key === ",") {
    P.playing = false;
    const n = Math.max(1, P.data ? P.data.frames.length : 1);
    commitDelta();
    P.frame = (P.frame + (e.key === "ArrowRight" || e.key === "." ? 1 : -1) + n) % n;
    drawPreview(); markChips(); renderControls(); e.preventDefault();
  }
});

export async function renderAnims(main) {
  if (S.sel.pframe !== undefined) {  // (#anims?...&pframe=N&onion=1: open paused on a frame, for links and screenshots)
    P.frame = +S.sel.pframe; P.playing = false; P.onion = !!S.sel.onion; delete S.sel.pframe;
  }
  if (!S.registry) { try { S.registry = await api("registry"); } catch { /* slots unknown */ } }
  const c = current();
  const editor = h("div.anim-editor");
  main.append(h("div.anim-page", list(), editor));
  if (c.sec === "ball") { editor.append(ballPanel()); return; }
  const title = c.sec === "ability_animations" ? `Ability slot ${c.name}: ${SLOTS[c.name] || ""}` : c.sec === "s3k_victory" ? "Sonic 3&K act clear" : c.name;
  const stand = c.sec === "s3k_victory" ? null : standIn(c.sec, c.name);
  if (stand && stand.ball) {  // the generic ball fills it (over his own frames, if any)
    editor.append(h("section.card", h("div.row.spread", h("h3", title), h("span.badge.ball", "generic ball")),
      h("div.row", ballBadge(), h("p.hint", "The generic spin ball fills this slot in every game (the Ball panel's \"use it for\").",
        c.anim && (c.anim.frames || []).length ? " His own frames here are kept in the file but not used while the ball is." : "")),
      h("button.primary", {onclick: () => go("anims", {section: "ball", anim: null})}, "Open the Ball panel")));
    if (!c.anim) return;
  }
  if (!c.anim && stand && stand.source) {
    const src = sourceOf(stand.source);
    const own = () => set(c.path, {frames: [...src.anim.frames], ...(src.anim.anchor ? {anchor: src.anim.anchor} : {}), ...(src.anim.align ? {align: true} : {})});
    editor.append(h("section.card.fallback",
      h("div.row.spread", h("h3", title, h("span.muted.small", ` uses ${stand.source} (fallback)`)), h("span.badge.fallback", "fallback")),
      h("p.hint", `He has no frames of his own here, so every game shows his ${stand.source} frames (and its anchor); `
        + "the speed, loop and hitbox stay this animation's own. Chains: tools/anim_fallbacks.py."),
      src.ball ? h("div.row", ballBadge(), h("span.hint", `${stand.source} is the generic ball.`))
        : h("div.chips.ghost", ((src.anim && src.anim.frames) || []).map((ref, i) => {
          const img = h("span.thumb.checker");
          thumb(ref).then(t => { if (t) fill(img, h("img.pixel", {src: t.png, width: t.w, height: t.h})); });
          return h("div.chip-frame", {title: `${stand.source}'s frame (borrowed)`}, h("span.n", String(i)), img,
            h("span.lbl.mono", typeof ref === "string" ? ref : ref && ref.frame ? ref.frame : "frame"));
        })),
      h("div.row",
        src.anim ? h("button.primary", {title: "copy these frames in as his own, to edit", onclick: own}, "Make my own") : h("button.primary", {onclick: () => set(c.path, {frames: []})}, "Make my own"),
        src.path ? h("button", {onclick: () => go("anims", {section: src.path[0], anim: src.path[1]})}, `Go to ${stand.source}`) : null,
        h("button", {title: "write null: the game shows nothing here (S3&K and Mania still show his standing frame)", onclick: () => set(c.path, null)}, "Leave it empty"))));
    return;
  }
  if (!c.anim && stand && stand.empty) {
    editor.append(h("section.card", h("h3", title, h("span.muted.small", " null")),
      h("p.hint", "Deliberately empty (null): no fallback, the game shows nothing here in Sonic 1, 2 and CD."),
      h("div.row", h("button.primary", {onclick: () => del(c.path)}, "Use the fallback again"),
        h("button", {onclick: () => set(c.path, {frames: [], ...(c.sec === "special_stage" ? {anchor: "center"} : {})})}, "Create it"))));
    return;
  }
  if (!c.anim) {
    const create = () => {
      if (c.sec === "s3k_victory") return set(["s3k_victory"], {frames: []});
      const v = {frames: []};
      if (c.sec === "ability_animations") v.name = (SLOTS[c.name] || "Ability").replace(/^the /, "").replace(/\b\w/g, m => m.toUpperCase()).slice(0, 24);
      if (c.sec === "special_stage") v.anchor = "center";
      return set(c.path, v);
    };
    editor.append(h("section.card", h("h3", title), h("p.hint", c.sec === "animations_sonic2" ? "Only on Sonic 2's list (Sonic 2, CD and S3&K use it)." : "Not defined yet."),
      h("button.primary", {onclick: create}, "Create it")));
    return;
  }
  editor.append(h("div.anim-grid",
    h("section.card",
      h("div.row.spread", h("h3", title, h("span.muted.small", ` ${c.sec}`)),
        h("button.small.danger", {onclick: () => { if (confirm(`Remove ${title}?`)) (c.sec === "s3k_victory" ? del(["s3k_victory"]) : del(c.path)); }}, "Remove")),
      options(c),
      frameChips(c)),
    h("section.card", h("h3", "Preview"), h("div#preview-slot", h("p.muted", "…")))));
  await loadPreview(c);
  const slot = document.getElementById("preview-slot");
  if (slot) { slot.replaceWith(previewPanel(c)); drawPreview(); markChips(); }
}

S.renderers.anims = renderAnims;
