// The hit-box panel (Abilities tab): a per-frame group of fields (abilities_registry.PER_FRAME_GROUPS: the melee's
// reach / top / bottom on the ground and in the air, the Ear Grapple's tip) drawn on the frames of its animation slot,
// placed as the game places them (the backend's `animation`: sheet2ani.build_anims), with the box as each game
// computes it:
//   Sonic 1 / 2 (tools/abilities.py melee_function): player.hitbox* = -10 (behind), top, reach, bottom; facing left
//     mirrored; melee_radial: -reach, -reach, reach, reach;
//   Sonic 3&K and Mania (tools/build_s3k_art.py): the pose frame's box 0 = the same, the reach at least 10;
//   Sonic CD (backend.per_frame_info): his own box (plus build_soniccd.SHOT_OUT's reach for the extras that have one).
// Drag the front, top and bottom edges (or the point); whole px. A shape a new group needs is a registry entry.
import {S, fill, h, api, edit, get, toast, go} from "./core.js";

const ENGINES = {v4: "Sonic 1 / 2", s3k: "Sonic 3&K / Mania", cd: "Sonic CD"};
const M = {};          // per move: {group, frame, engine, zoom, playing, t, adv}
const anims = {};      // slot -> {key, data, loading}
let info = null, infoKey = null;
let drag = null;       // {move, gname, i, edge, vals, bb}

const groups = () => (S.registry && S.registry.per_frame_groups) || {};
export const groupsOf = move => Object.entries(groups()).filter(([, g]) => g.move === move).map(([n]) => n);
const st = move => M[move] || (M[move] = {group: null, frame: 0, engine: "v4", zoom: 4, playing: false, t: 0, adv: false});
const abEntry = () => get(["abilities"]) || {};

function slotN(slot) {
  const a = (get(["ability_animations"]) || {})[slot];
  if (!a || !Array.isArray(a.frames) || !a.frames.length) return 0;
  return a.frames.length * (Number.isInteger(a.hold) && a.hold > 1 ? a.hold : 1);
}
const num = (v, d) => typeof v === "number" && isFinite(v) ? v : d;

// The group's values, one per frame of its slot (a short list repeats its last value, as the builders do). A box group
// whose reach is left out and that has same_as uses that group's box: the game's own rule (melee_poses).
function lists(gname) {
  const g = groups()[gname], ab = abEntry(), n = slotN(g.slot);
  if (g.shape === "point") {
    const L = Array.isArray(ab[g.fields.point]) ? ab[g.fields.point] : [];
    return {own: L.length > 0, n, vals: Array.from({length: n}, (_, i) => {
      const p = L.length ? L[Math.min(i, L.length - 1)] : null;
      return {x: num(p && p[0], 0), y: num(p && p[1], 0)};
    })};
  }
  const own = Array.isArray(ab[g.fields.reach]) && ab[g.fields.reach].length > 0;
  if (!own && g.same_as) {
    const o = lists(g.same_as);
    const m = o.vals.length;
    return {own: false, borrowed: g.same_as, n, vals: Array.from({length: n}, (_, i) => m ? {...o.vals[Math.min(i, m - 1)]} : {reach: 10, top: g.defaults.top, bottom: g.defaults.bottom})};
  }
  const pick = (k, i, d) => { const L = ab[g.fields[k]]; return Array.isArray(L) && L.length ? num(L[Math.min(i, L.length - 1)], d) : d; };
  return {own, n, vals: Array.from({length: n}, (_, i) => ({reach: pick("reach", i, 10), top: pick("top", i, g.defaults.top), bottom: pick("bottom", i, g.defaults.bottom)}))};
}

// Write a group's values (one edit: every field of the group, full length). A top / bottom list that's left out and
// would be all its default stays left out (the minimal-text save keeps the file as it was).
function commit(gname, vals) {
  const g = groups()[gname], ab = abEntry();
  if (!slotN(g.slot)) { toast(`Slot ${g.slot} has no frames: draw it first.`, "error"); return; }
  const ops = [];
  const put = (field, arr, dflt) => {
    if (ab[field] === undefined && dflt !== undefined && arr.every(x => x === dflt)) return;
    if (JSON.stringify(ab[field]) === JSON.stringify(arr)) return;
    ops.push({op: "set", path: ["abilities", field], value: arr});
  };
  if (g.shape === "point") put(g.fields.point, vals.map(v => [v.x, v.y]));
  else for (const k of ["reach", "top", "bottom"]) put(g.fields[k], vals.map(v => v[k]), g.defaults[k]);
  if (ops.length) return edit(ops);
}

const radial = g => g.radial && !!abEntry()[g.radial];
const shotOnY = () => { const s = abEntry().shot; return s && typeof s === "object" && !["down", "slam", "up"].includes(s.input); };

// Which frames the engine shows for this group, and with which group's box: Sonic 3&K shows the ground move in the air
// when the air move has no reach of its own; Sonic CD has one pose (slot 46 there: the ground frames, in the air too).
function view(move, gname) {
  const g = groups()[gname], s = st(move);
  if (g.shape === "point") return {slot: g.slot, gname};
  const L = lists(gname);
  if (s.engine === "cd") return {slot: "43", gname: Object.keys(groups()).find(k => groups()[k].move === move && !groups()[k].same_as) || gname, cd: true};
  if (s.engine === "s3k" && L.borrowed) return {slot: groups()[L.borrowed].slot, gname: L.borrowed};
  return {slot: g.slot, gname};
}

// The box the engine uses on frame i (facing right): {l, t, r, b}
function boxOf(move, gname, v, i) {
  const g = groups()[gname], e = st(move).engine;
  if (e === "cd") return info && info.cd.boxes[i] ? (([l, t, r, b]) => ({l, t, r, b}))(info.cd.boxes[i]) : null;
  const reach = e === "s3k" ? Math.max(num(g.min_reach && g.min_reach.s3k, -1e9), v.reach) : v.reach;
  if (radial(g)) return {l: -reach, t: -reach, r: reach, b: reach};
  return {l: g.behind, t: v.top, r: reach, b: v.bottom};
}

function ticksOf(gname) {
  const g = groups()[gname];
  if (g.ticks) return g.ticks;
  const f = g.ticks_field, v = abEntry()[f];
  const d = (((S.registry.abilities[g.move] || {}).fields || {})[f] || {}).default;
  return Math.max(1, num(v, num(d, 4)));
}

// ---- loading the frames (the backend places them as the build does)
function animKey(slot) {
  const d = S.info.doc;
  return JSON.stringify([slot, (d.ability_animations || {})[slot], d.frames, d.sheet, d.palette, d.base]);
}
function loadAnim(slot) {
  const key = animKey(slot), a = anims[slot];
  if (a && a.key === key) return a.data;
  if (a && a.loading === key) return null;
  anims[slot] = {key: null, data: a ? a.data : null, loading: key};
  api("animation", {section: "ability_animations", name: slot})
    .catch(e => ({error: e.message, frames: []}))
    .then(data => {
      const before = anims[slot] && anims[slot].data;
      anims[slot] = {key, data, loading: null};
      if (!before || before.frames.length !== data.frames.length)  // (the strip needs its thumbnails)
        for (const m of Object.keys(M)) if (st(m).raw && st(m).group && view(m, st(m).group).slot === slot) rerenderPanel(m, st(m).raw);
      drawAll();
    });
  return null;
}
function loadInfo() {
  const key = JSON.stringify([S.info.folder, (S.info.doc.ability_animations || {})["43"], S.info.doc.base]);
  if (infoKey === key) return;
  infoKey = key;
  api("per_frame_info").then(r => { info = r; drawAll(); }).catch(() => { info = null; });
}

const imgs = new Map();
function img(png) {
  if (!imgs.has(png)) { const i = new Image(); i.onload = () => drawAll(); i.src = png; imgs.set(png, i); }
  return imgs.get(png);
}

// ---- drawing
function bounds(d, boxes, pts) {
  let l = 12, r = 12, t = 12, b = 12;
  for (const f of d.frames) { l = Math.max(l, -f.px); r = Math.max(r, f.px + f.w); t = Math.max(t, -f.py); b = Math.max(b, f.py + f.h); }
  for (const x of boxes) if (x) { l = Math.max(l, -x.l); r = Math.max(r, x.r); t = Math.max(t, -x.t); b = Math.max(b, x.b); }
  for (const p of pts) { r = Math.max(r, p.x); l = Math.max(l, -p.x); t = Math.max(t, -p.y); b = Math.max(b, p.y); }
  if (d.anchor === "feet") b = Math.max(b, d.feet_y + 4);
  return {l: l + 8, r: r + 28, t: t + 14, b: b + 8};
}

function paint(cv, move, gname, i, z, bb, {main = false, flash = null} = {}) {
  const s = st(move), vw = view(move, gname), g = groups()[gname], d = (anims[vw.slot] || {}).data;
  if (!cv || !d || !d.frames.length) return;
  const n = d.frames.length, f = d.frames[Math.min(i, n - 1)];
  cv.width = (bb.l + bb.r) * z; cv.height = (bb.t + bb.b) * z;
  const ctx = cv.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = "#0b0d12"; ctx.fillRect(0, 0, cv.width, cv.height);
  const ox = bb.l * z, oy = bb.t * z;
  if (d.anchor === "feet") {
    const gy = oy + d.feet_y * z;
    ctx.fillStyle = "#18241a"; ctx.fillRect(0, gy, cv.width, cv.height - gy);
    ctx.fillStyle = "#4f8f4f"; ctx.fillRect(0, gy, cv.width, Math.max(1, z / 2));
  }
  const im = img(f.png);
  if (im.complete) ctx.drawImage(im, ox + f.px * z, oy + f.py * z, f.w * z, f.h * z);
  const vals = drag && drag.move === move && drag.gname === vw.gname ? drag.vals : lists(vw.gname).vals;
  const v = vals[Math.min(i, vals.length - 1)];
  const lw = main ? 2 : 1;
  if (g.shape === "point" && v) {
    const px = ox + (v.x + 0.5) * z, py = oy + (v.y + 0.5) * z;
    ctx.strokeStyle = "rgba(127, 211, 255, .5)"; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(px, py); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = flash === false ? "rgba(255, 90, 90, .35)" : "#ff5a5a";
    ctx.beginPath(); ctx.arc(px, py, main ? Math.max(4, z * 1.2) : 2, 0, Math.PI * 2); ctx.fill();
    if (main) { ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.stroke(); }
  } else if (v) {
    const bx = boxOf(move, vw.gname, v, i);
    if (bx) {
      const x0 = ox + bx.l * z, y0 = oy + bx.t * z, w = (bx.r - bx.l) * z, hh = (bx.b - bx.t) * z;
      ctx.fillStyle = flash === null ? "rgba(255, 90, 90, .2)" : flash ? "rgba(255, 90, 90, .42)" : "rgba(255, 90, 90, .08)";
      ctx.fillRect(x0, y0, w, hh);
      ctx.strokeStyle = "#ff5a5a"; ctx.lineWidth = lw;
      ctx.strokeRect(x0 + lw / 2, y0 + lw / 2, Math.max(0, w - lw), Math.max(0, hh - lw));
      if (main && s.engine !== "cd") {  // the handles: front, top, bottom (radial: the front sets every side)
        ctx.fillStyle = "#ffd34d";
        const hs = 7, mx = x0 + w / 2, my = y0 + hh / 2;
        ctx.fillRect(x0 + w - hs / 2 - 1, my - hs / 2, hs, hs);
        if (!radial(g)) { ctx.fillRect(mx - hs / 2, y0 - hs / 2 + 1, hs, hs); ctx.fillRect(mx - hs / 2, y0 + hh - hs / 2 - 1, hs, hs); }
      }
    }
  }
  ctx.strokeStyle = "#7fd3ff"; ctx.lineWidth = 1;  // his centre (the object's position)
  const c = Math.max(3, z * 1.5);
  ctx.beginPath(); ctx.moveTo(ox - c, oy + 0.5); ctx.lineTo(ox + c + 1, oy + 0.5); ctx.moveTo(ox + 0.5, oy - c); ctx.lineTo(ox + 0.5, oy + c + 1); ctx.stroke();
}

function frameBounds(move, gname) {
  const vw = view(move, gname), d = (anims[vw.slot] || {}).data;
  if (!d) return null;
  const g = groups()[gname];
  const vals = drag && drag.move === move ? drag.vals : lists(vw.gname).vals;
  const boxes = g.shape === "point" ? [] : vals.map((v, i) => boxOf(move, vw.gname, v, i));
  return bounds(d, boxes, g.shape === "point" ? vals : []);
}

function drawAll() {
  for (const move of Object.keys(M)) {
    const s = st(move), gname = s.group;
    const cv = document.getElementById("hb-canvas-" + move);
    if (!cv || !gname || !groups()[gname]) continue;
    const vw = view(move, gname), d = (anims[vw.slot] || {}).data;
    if (!d) continue;
    const n = d.frames.length;
    if (!n) continue;
    s.frame = Math.min(s.frame, n - 1);
    const bb = drag && drag.move === move ? drag.bb : frameBounds(move, gname);
    const ticks = ticksOf(vw.gname);
    const flash = s.playing ? Math.floor(s.t / 2) % 2 === 0 : null;  // (every frame of the move hits: the box flashes)
    paint(cv, move, gname, s.frame, s.zoom, bb, {main: true, flash});
    const strip = document.getElementById("hb-strip-" + move);
    if (strip) {
      const tz = Math.max(1, Math.min(2, Math.floor(110 / Math.max(bb.l + bb.r, bb.t + bb.b))));
      strip.querySelectorAll("canvas").forEach((c, k) => paint(c, move, gname, k, tz, bb));
      strip.querySelectorAll(".hb-thumb").forEach((t, k) => t.classList.toggle("on", k === s.frame));
    }
    const say = document.getElementById("hb-say-" + move);
    if (say) say.textContent = describe(move, gname, s.frame, ticks, n);
  }
}

const above = t => t <= 0 ? `${-t} px above` : `${t} px below`;
const below = b => b >= 0 ? `${b} px below` : `${-b} px above`;
function describe(move, gname, i, ticks, n) {
  const g = groups()[gname], vw = view(move, gname), s = st(move);
  const vals = drag && drag.move === move ? drag.vals : lists(vw.gname).vals;
  const v = vals[Math.min(i, vals.length - 1)];
  const head = `Frame ${i + 1} of ${n} (${ticks} game frame${ticks === 1 ? "" : "s"}): `;
  if (!v) return head;
  if (g.shape === "point") return head + `the tip ${v.x} px ahead, ${v.y <= 0 ? `${-v.y} px above` : `${v.y} px below`} his centre`;
  const bx = boxOf(move, vw.gname, v, i);
  if (!bx) return head;
  if (s.engine === "cd") return head + `his box: ${-bx.l} px behind to ${bx.r} px ahead · ${above(bx.t)} to ${below(bx.b)} his centre`;
  if (radial(g)) return head + `reaches ${bx.r} px all round his centre`;
  return head + `reaches ${bx.r} px ahead · ${above(bx.t)} to ${below(bx.b)} his centre` + (bx.r !== v.reach ? ` (his reach ${v.reach} counts as ${bx.r} here)` : "");
}

// ---- playing: the move at game timing (each frame for melee_ticks game frames, 60 a second), then a short pause
let raf = null, last = 0, acc = 0;
function tick(t) {
  raf = requestAnimationFrame(tick);
  const dt = Math.min(100, t - (last || t)); last = t;
  const playing = Object.keys(M).filter(m => st(m).playing && document.getElementById("hb-canvas-" + m));
  if (!playing.length) { acc = 0; return; }
  acc += dt;
  let steps = 0;
  while (acc >= 1000 / 60) { acc -= 1000 / 60; steps++; }
  if (!steps) return;
  for (const move of playing) {
    const s = st(move), vw = view(move, s.group), d = (anims[vw.slot] || {}).data;
    if (!d || !d.frames.length) continue;
    const ticks = ticksOf(vw.gname), n = d.frames.length, pause = 24;
    s.t = (s.t + steps) % (n * ticks + pause);
    s.frame = Math.min(n - 1, Math.floor(s.t / ticks));
  }
  drawAll();
}
if (!raf) raf = requestAnimationFrame(tick);

// ---- dragging the edges (or the point): whole px; one edit when the mouse is let go
function wire(cv, move) {
  const at = e => {
    const s = st(move), bb = drag ? drag.bb : frameBounds(move, s.group);
    const r = cv.getBoundingClientRect(), k = cv.width / r.width;
    return {sx: (e.clientX - r.left) * k, sy: (e.clientY - r.top) * k, bb, z: s.zoom,
            gx: (e.clientX - r.left) * k / s.zoom - bb.l, gy: (e.clientY - r.top) * k / s.zoom - bb.t};
  };
  const edgeAt = p => {
    const s = st(move), g = groups()[s.group], vw = view(move, s.group);
    if (s.engine === "cd" && g.shape !== "point") return null;
    const v = lists(vw.gname).vals[s.frame];
    if (!v) return null;
    const tol = 6 / p.z;
    if (g.shape === "point") return "point";
    const bx = boxOf(move, vw.gname, v, s.frame);
    const inX = p.gx > bx.l - tol && p.gx < bx.r + tol, inY = p.gy > bx.t - tol && p.gy < bx.b + tol;
    if (Math.abs(p.gx - bx.r) < tol && inY) return "reach";
    if (radial(g)) return null;
    if (Math.abs(p.gy - bx.t) < tol && inX) return "top";
    if (Math.abs(p.gy - bx.b) < tol && inX) return "bottom";
    return null;
  };
  const apply = p => {
    const g = groups()[drag.gname], v = drag.vals[drag.i], x = Math.round(p.gx), y = Math.round(p.gy);
    if (drag.edge === "point") { v.x = Math.floor(p.gx); v.y = Math.floor(p.gy); }
    else if (drag.edge === "reach") v.reach = Math.max(radial(g) ? 1 : g.behind + 1, x);
    else if (drag.edge === "top") v.top = Math.min(v.bottom - 1, y);
    else if (drag.edge === "bottom") v.bottom = Math.max(v.top + 1, y);
    drawAll();
  };
  cv.addEventListener("mousemove", e => {
    if (drag) { apply(at(e)); return; }
    const ed = edgeAt(at(e));
    cv.style.cursor = ed === "reach" ? "ew-resize" : ed === "top" || ed === "bottom" ? "ns-resize" : ed === "point" ? "crosshair" : "default";
  });
  cv.addEventListener("mousedown", e => {
    const p = at(e), ed = edgeAt(p);
    if (!ed) return;
    const s = st(move), vw = view(move, s.group);
    s.playing = false;
    drag = {move, gname: vw.gname, i: s.frame, edge: ed, vals: lists(vw.gname).vals.map(v => ({...v})), bb: p.bb};
    apply(p);
    e.preventDefault();
  });
  const up = () => {
    if (!drag || drag.move !== move) return;
    const d = drag;
    drag = null;
    commit(d.gname, d.vals);
    drawAll();
  };
  window.addEventListener("mouseup", up);
}

// ---- the tools
function fitFrame(move, gname, vals, i) {
  const g = groups()[gname], vw = view(move, gname), d = (anims[vw.slot] || {}).data;
  const f = d && d.frames[i];
  if (!f || !f.drawn) return false;
  const [l, t, r, b] = f.drawn;
  if (g.shape === "point") { vals[i] = {x: f.diag[0], y: f.diag[1]}; return true; }
  if (radial(g)) { vals[i] = {...vals[i], reach: Math.max(1, -l, r, -t, b)}; return true; }
  vals[i] = {...vals[i], reach: Math.max(g.behind + 1, r), top: t, bottom: Math.max(t + 1, b)};
  return true;
}

function tools(move) {
  const s = st(move), gname = s.group, g = groups()[gname], L = lists(gname);
  const editable = s.engine !== "cd" || g.shape === "point";
  const vw = view(move, gname);
  const run = (fn, msg) => () => { const vals = lists(vw.gname).vals.map(v => ({...v})); if (fn(vals) !== false) { commit(vw.gname, vals); if (msg) toast(msg); } };
  const pair = groupsOf(move).filter(k => k !== gname && groups()[k].shape === g.shape);
  const copyTo = (src, dst) => () => {
    const from = lists(src).vals, n = slotN(groups()[dst].slot);
    if (!n) { toast(`Slot ${groups()[dst].slot} has no frames: draw it first.`, "error"); return; }
    commit(dst, Array.from({length: n}, (_, i) => ({...from[Math.min(i, from.length - 1)]})));
    toast(`Copied ${groups()[src].label.toLowerCase()} → ${groups()[dst].label.toLowerCase()} (frame by frame; a longer one repeats the last)`);
  };
  return h("div.hb-tools",
    h("div.row",
      h("button.small", {disabled: !editable, title: g.shape === "point" ? "the tip on the opaque pixel furthest up and forward" : "front edge on the furthest drawn pixel ahead of his centre, top and bottom on the drawing's",
        onclick: run(v => { if (fitFrame(move, vw.gname, v, s.frame)) return true; toast("Nothing drawn on this frame", "error"); return false; })}, "Fit to sprite"),
      h("button.small", {disabled: !editable, onclick: run(v => { v.forEach((_, i) => fitFrame(move, vw.gname, v, i)); }, "Fitted every frame to its drawing")}, "Fit all frames"),
      h("button.small", {disabled: !editable, title: "every frame gets this frame's " + (g.shape === "point" ? "point" : "box"),
        onclick: run(v => { const c = v[s.frame]; v.forEach((_, i) => v[i] = {...c}); }, "Same on every frame")}, g.shape === "point" ? "Same point on all frames" : "Same box on all frames")),
    pair.length ? h("div.row",
      pair.map(o => [
        h("button.small", {disabled: !slotN(groups()[o].slot), title: slotN(groups()[o].slot) ? "" : `slot ${groups()[o].slot} has no frames`, onclick: copyTo(gname, o)},
          `Copy ${shortLabel(gname)} → ${shortLabel(o)}`),
        h("button.small", {disabled: !slotN(g.slot) || (groups()[o].same_as && !lists(o).own), onclick: copyTo(o, gname)}, `Copy ${shortLabel(o)} → ${shortLabel(gname)}`)]),
      g.same_as && L.own ? h("button.small", {title: `remove ${Object.values(g.fields).join(", ")}: the game then uses the ${shortLabel(g.same_as)} box`,
        onclick: () => edit(Object.values(g.fields).filter(f => abEntry()[f] !== undefined).map(f => ({op: "del", path: ["abilities", f]})))}, `Use the ${shortLabel(g.same_as)} box`) : null) : null);
}
const shortLabel = gname => ({"On the ground": "ground", "In the air": "air"})[groups()[gname].label] || groups()[gname].label.toLowerCase();

function notes(move) {
  const s = st(move), gname = s.group, g = groups()[gname], L = lists(gname), out = [];
  if (g.shape === "point") {
    out.push("The ear goes out one frame per game frame; each frame's tip is tested against the terrain and hits enemies and monitors it touches (every game: Sonic CD and Sonic 3&K test the same point).");
    if (g.max_frames && L.n > g.max_frames) out.push(`Sonic 3&K has room for ${g.max_frames} frames: the rest are cut off there.`);
    return out.map(t => h("p.hint", t));
  }
  if (move === "melee" && shotOnY()) out.push(h("p.warn.small", "He throws a shot with Y: these frames are only its throw pose and the box isn't used (Sonic 3&K uses it only if its shot system is off)."));
  if (L.borrowed) out.push(h("p.hint", s.engine === "s3k" ? `No ${g.fields.reach}: in the air Sonic 3&K and Mania show the ground move (slot ${groups()[L.borrowed].slot}) and its box. Drag, fit or copy to give the air move its own.`
    : `No ${g.fields.reach}: the air move uses the ground move's box (Sonic 1/2 show slot ${g.slot}'s frames with it). Drag, fit or copy to give the air move its own.`));
  if (s.engine === "v4") out.push(h("p.hint", "Sonic 1 / 2 use exactly this box (mirrored when he faces left)."));
  if (s.engine === "s3k") out.push(h("p.hint", "Sonic 3&K and Mania: the same box, but the front edge never comes in closer than 10 px ahead of his centre (a smaller reach counts as 10)."));
  if (s.engine === "cd") out.push(h("p.hint", info && info.cd.rule === "reach"
    ? "Sonic CD doesn't read these numbers: its Y move (slot 46 there: the ground frames, in the air too) hits with his own box, plus the reach Sonic CD's builder gives this character (build_soniccd.py SHOT_OUT)."
    : "Sonic CD doesn't read these numbers: its Y move (slot 46 there: the ground frames, in the air too) hits with his own box, drawn here. Switch to Sonic 1 / 2 or 3&K to edit."));
  out.push(h("p.hint", h("b", "No \"no hit\" frame: "), "every frame of the move attacks (the games count the whole move as an attack), and the box always reaches back to 10 px behind his centre. For a frame that shouldn't reach out, pull the front edge back to his body."));
  return out;
}

// The numbers, in words: still editable (and the raw lists as saved, with "Fit to N frames" when one is out of step)
function advanced(move, rawEditor) {
  const s = st(move), gname = s.group, g = groups()[gname], L = lists(gname);
  const vw = view(move, gname);
  const cell = (i, k, shown, toVal, title) => h("input.mono", {value: shown, title, style: {width: "3.6em"}, "data-key": `hb/${gname}/${i}/${k}`,
    onchange: e => {
      const n = Number(e.target.value.trim());
      if (!Number.isInteger(n)) { toast(`${e.target.value} isn't a whole number`, "error"); return; }
      const vals = L.vals.map(v => ({...v}));
      vals[i] = {...vals[i], [k]: toVal(n)};
      if (g.shape === "box" && vals[i].top >= vals[i].bottom) { toast("the top has to be above the bottom", "error"); return; }
      commit(gname, vals);
    }});
  const rows = L.vals.map((v, i) => h("div.hb-adv-row" + (i === s.frame ? ".on" : ""), {onclick: () => { s.frame = i; s.playing = false; drawAll(); }},
    h("span.mono.muted", `${i + 1}`),
    g.shape === "point"
      ? h("span", "the tip ", cell(i, "x", v.x, n => n, "px ahead of his centre (negative: behind)"), " px ahead, ", cell(i, "y", -v.y, n => -n, "px above his centre (negative: below)"), " px above his centre")
      : radial(g) ? h("span", "reaches ", cell(i, "reach", v.reach, n => n), " px all round his centre")
        : h("span", "reaches ", cell(i, "reach", v.reach, n => n, "px ahead of his centre"), " px ahead · from ",
          cell(i, "top", -v.top, n => -n, "px above his centre (negative: below)"), " px above to ",
          cell(i, "bottom", v.bottom, n => n, "px below his centre (negative: above)"), " px below his centre")));
  const det = h("details.hb-adv", {open: s.adv ? "" : null, ontoggle: e => { s.adv = e.target.open; }},
    h("summary", "Advanced: the numbers"),
    L.borrowed ? h("p.hint", `(the ${shortLabel(L.borrowed)} move's, until the ${shortLabel(gname)} move has its own: editing one gives it its own)`) : null,
    L.n ? h("div.hb-adv-rows", rows) : null,
    h("div.label", "As saved"),
    h("div.ab-fields", Object.values(g.fields).map(f => rawEditor(f))));
  return det;
}

// The panel for a move's per-frame groups: a switch (Ground / Air), the frame with its box, the frame strip, the tools.
export function hitboxPanel(move, rawEditor) {
  const names = groupsOf(move);
  if (!names.length) return null;
  const s = st(move);
  s.raw = rawEditor;
  if (!names.includes(s.group)) s.group = names[0];
  const g = groups()[s.group];
  loadInfo();
  const vw = view(move, s.group);
  const d = loadAnim(vw.slot) || (anims[vw.slot] || {}).data;
  const n = slotN(vw.slot);
  const cv = h("canvas.pixel.hb-canvas", {id: "hb-canvas-" + move, tabindex: 0});
  wire(cv, move);
  const strip = h("div.hb-strip", {id: "hb-strip-" + move, "data-scroll": "hb-strip-" + move},
    Array.from({length: d ? d.frames.length : 0}, (_, i) => h("div.hb-thumb", {onclick: () => { s.frame = i; s.playing = false; drawAll(); rerenderPlay(move); }},
      h("canvas.pixel"), h("span.mono.small", String(i + 1)))));
  const panel = h("div.hb", {id: "hb-" + move},
    h("div.row.spread",
      h("div.row",
        names.length > 1 ? h("div.seg", names.map(k => h("button.small" + (k === s.group ? ".on" : ""), {onclick: () => { s.group = k; s.frame = 0; s.t = 0; drawAll(); rerenderPanel(move, rawEditor); }}, groups()[k].label))) : h("b", g.label),
        h("span.muted.small", `slot ${g.slot}`)),
      h("div.row",
        g.shape === "box" ? h("label.mini", {title: "draw the box as this game computes it"}, h("span", "as in"),
          h("select", {onchange: e => { s.engine = e.target.value; s.frame = 0; rerenderPanel(move, rawEditor); }},
            Object.entries(ENGINES).map(([k, t]) => h("option", {value: k, selected: k === s.engine ? "" : null}, t)))) : null,
        h("label.mini", h("span", "zoom"), h("select", {onchange: e => { s.zoom = +e.target.value; drawAll(); }},
          [2, 3, 4, 5, 6].map(z => h("option", {value: z, selected: z === s.zoom ? "" : null}, z + "×")))))),
    !n ? h("p.warn", `Slot ${vw.slot} has no frames yet: draw it first (`, h("a", {href: "#", onclick: e => { e.preventDefault(); go("anims", {section: "ability_animations", anim: vw.slot}); }}, "Animations tab"), ").")
      : h("div.hb-body",
        h("div.hb-stage", cv),
        h("div.hb-side",
          h("p.mono.small#hb-say-" + move),
          h("div.row.controls",
            h("button.small", {title: "previous frame", onclick: () => { s.playing = false; s.frame = (s.frame - 1 + n) % n; drawAll(); rerenderPlay(move); }}, "⏮"),
            h("button.small.primary", {id: "hb-play-" + move, onclick: () => { s.playing = !s.playing; s.t = s.frame * ticksOf(vw.gname); rerenderPlay(move); }}, s.playing ? "Pause" : "Play the move"),
            h("button.small", {title: "next frame", onclick: () => { s.playing = false; s.frame = (s.frame + 1) % n; drawAll(); rerenderPlay(move); }}, "⏭")),
          h("p.hint", `At game speed: ${ticksOf(vw.gname)} game frame${ticksOf(vw.gname) === 1 ? "" : "s"} a frame${g.ticks_field ? ` (${g.ticks_field})` : ""}; the ${g.shape === "point" ? "point" : "box"} flashes while it hits.`),
          (g.shape === "box" && s.engine === "cd") ? null : h("p.hint", g.shape === "point" ? "Drag the point (or click where the tip should be). He faces right here." : "Drag the yellow handles: the front edge (reach), the top and the bottom. Whole px; he faces right here."),
          tools(move),
          notes(move))),
    n ? strip : null,
    advanced(move, rawEditor));
  requestAnimationFrame(drawAll);
  return panel;
}

function rerenderPlay(move) {
  const b = document.getElementById("hb-play-" + move);
  if (b) b.textContent = st(move).playing ? "Pause" : "Play the move";
}
function rerenderPanel(move, rawEditor) {
  const old = document.getElementById("hb-" + move);
  const nu = hitboxPanel(move, rawEditor);
  if (old && nu) old.replaceWith(nu);
}

// (#abilities?hb=melee&group=melee air&engine=s3k&hbframe=2&adv=1: open the panel that way, for links and screenshots)
export function hitboxFromSel(sel) {
  if (!sel.hb) return;
  const s = st(sel.hb);
  if (sel.group) s.group = sel.group;
  if (sel.engine) s.engine = sel.engine;
  if (sel.hbframe !== undefined) s.frame = +sel.hbframe;
  if (sel.adv) s.adv = true;
  if (sel.zoom) s.zoom = +sel.zoom;
  for (const k of ["hb", "group", "engine", "hbframe", "adv", "zoom"]) delete sel[k];
}
// (for tests and screenshots: the boxes an engine uses, per frame of the frames it shows, and those frames' placement)
export function hbBoxes(move, gname, engine) {
  const s = st(move), keep = s.engine;
  s.engine = engine;
  const vw = view(move, gname), d = (anims[vw.slot] || {}).data;
  const out = {slot: vw.slot, boxes: lists(vw.gname).vals.map((v, i) => boxOf(move, vw.gname, v, i)),
               frames: d ? d.frames.map(f => [f.px, f.py, f.w, f.h]) : null};
  s.engine = keep;
  return out;
}
export {M as HB, lists as hbLists, commit as hbCommit, frameBounds as hbBounds};
