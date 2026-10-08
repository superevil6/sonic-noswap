// The Sheet tab: the sprite sheet at a whole-number zoom with crisp pixels, every frame's rectangle, the selected
// frame's drawn part and pivot, and an inspector to edit it. Drag to move, drag an edge to resize, the Draw tool (R)
// to add a frame, alt-click to read a colour.
import {S, fill, h, api, edit, set, toast, status, sheetUrl, go, frameNames, field} from "./core.js";
import {DT, initDetect, toggleDetect, drawDetect, detectDown, detectMove, detectUp, detectDbl, detectAltClick, detectKey,
  renderDetectPanel} from "./detect.js";

const store = {
  get(k, d) { try { const v = localStorage.getItem("noswap." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  put(k, v) { try { localStorage.setItem("noswap." + k, JSON.stringify(v)); } catch { /* private mode */ } },
};

const V = {
  zoom: store.get("zoom", 2), tool: "select", names: store.get("names", true), raw: store.get("raw", false), filter: "",
  info: null, infoKey: null, img: null, imgVersion: null, pixels: null, drag: null, canvas: null,
};

const COL = {sel: "#ffd34d", used: "#4fc3f7", unused: "#8a93a6", bad: "#ff5d5d", trim: "#ffffff", ground: "#7ddc7d", pivot: "#ff6b6b"};

async function loadInfo(force) {
  const key = JSON.stringify([S.info.doc.frames, S.info.doc.sheet, S.info.doc.animations, S.info.doc.ability_animations]);
  if (!force && V.infoKey === key && V.info) return V.info;
  try { V.info = await api("frames_info"); } catch (e) { toast(e.message, "error"); V.info = {frames: {}, sheet_size: [0, 0]}; }
  V.infoKey = key;
  return V.info;
}

function loadImage() {
  return new Promise(res => {
    if (V.img && V.imgVersion === S.info.sheet.version) return res(V.img);
    const img = new Image();
    img.onload = () => {
      V.img = img; V.imgVersion = S.info.sheet.version;
      const c = document.createElement("canvas");
      c.width = img.width; c.height = img.height;
      const cx = c.getContext("2d");
      cx.drawImage(img, 0, 0);
      V.pixels = cx.getImageData(0, 0, img.width, img.height);
      res(img);
    };
    img.onerror = () => res(null);
    img.src = sheetUrl();
  });
}

function rectOf(name) {
  if (V.drag && V.drag.name === name && V.drag.rect) return V.drag.rect;
  const r = (S.info.doc.frames || {})[name];
  return Array.isArray(r) ? r : null;
}

function draw() {
  const c = V.canvas;
  if (!c || !V.img) return;
  const z = V.zoom;
  const ctx = c.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, c.width, c.height);
  ctx.drawImage(V.img, 0, 0, V.img.width * z, V.img.height * z);
  const frames = (V.info && V.info.frames) || {};
  const sel = S.sel.frame;
  ctx.font = "11px system-ui, sans-serif";
  ctx.textBaseline = "bottom";
  const names = frameNames();
  for (const name of names) {
    const r = rectOf(name);
    if (!r || name === sel) continue;
    const fi = frames[name] || {};
    const colour = fi.empty || fi.outside ? COL.bad : (fi.used_by && fi.used_by.length ? COL.used : COL.unused);
    strokeRect(ctx, r, z, colour, 1);
    if (V.names && z >= 2) label(ctx, name, r, z, colour);
  }
  if (V.drag && V.drag.mode === "draw" && V.drag.rect) strokeRect(ctx, V.drag.rect, z, COL.sel, 2, [4, 3]);
  const r = sel && rectOf(sel);
  if (r) {
    const fi = frames[sel] || {};
    ctx.fillStyle = "rgba(255, 211, 77, 0.08)";
    ctx.fillRect(r[0] * z, r[1] * z, r[2] * z, r[3] * z);
    strokeRect(ctx, r, z, COL.sel, 2);
    label(ctx, sel, r, z, COL.sel, true);
    // the drawn part (what the build keeps after trimming) and where the game puts the object's position
    const t = (!V.drag || V.drag.name !== sel) && fi.trim;
    if (t) {
      strokeRect(ctx, t, z, COL.trim, 1, [2, 2]);
      const cx = (t[0] + Math.floor(t[2] / 2)) * z;
      const anchors = fi.anchors && fi.anchors.length ? fi.anchors : ["feet"];
      if (anchors.includes("feet")) {
        const gy = (t[1] + t[3]) * z;
        ctx.strokeStyle = COL.ground; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(t[0] * z - 6, gy + 0.5); ctx.lineTo((t[0] + t[2]) * z + 6, gy + 0.5); ctx.stroke();
        cross(ctx, cx, gy - (S.info.doc.sheet.feet_y ?? 20) * z, COL.pivot);
      }
      if (anchors.includes("center")) cross(ctx, cx, (t[1] + Math.floor(t[3] / 2)) * z, "#d18cff");
    }
  }
  drawDetect(ctx, z);
}

function strokeRect(ctx, r, z, colour, w, dash) {
  ctx.save();
  ctx.strokeStyle = colour; ctx.lineWidth = w; ctx.setLineDash(dash || []);
  ctx.strokeRect(r[0] * z - w / 2, r[1] * z - w / 2, r[2] * z + w, r[3] * z + w);
  ctx.restore();
}

function label(ctx, text, r, z, colour, bold) {
  const x = r[0] * z, y = r[1] * z - 2;
  ctx.font = (bold ? "600 " : "") + "11px system-ui, sans-serif";
  const w = ctx.measureText(text).width + 6;
  ctx.fillStyle = "rgba(14, 17, 23, 0.82)";
  ctx.fillRect(x - 1, y - 13, w, 14);
  ctx.fillStyle = colour;
  ctx.fillText(text, x + 2, y);
}

function cross(ctx, x, y, colour) {
  ctx.strokeStyle = colour; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x + 6, y); ctx.moveTo(x, y - 6); ctx.lineTo(x, y + 6); ctx.stroke();
}

function sheetPos(e) {
  const b = V.canvas.getBoundingClientRect();
  return [Math.floor((e.clientX - b.left) / V.zoom), Math.floor((e.clientY - b.top) / V.zoom)];
}

function hitFrame(x, y) {
  let best = null, area = Infinity;
  for (const n of frameNames()) {
    const r = rectOf(n);
    if (r && x >= r[0] && y >= r[1] && x < r[0] + r[2] && y < r[1] + r[3] && r[2] * r[3] < area) { best = n; area = r[2] * r[3]; }
  }
  return best;
}

function edgeAt(e, r) {
  if (!r) return null;
  const b = V.canvas.getBoundingClientRect();
  const mx = e.clientX - b.left, my = e.clientY - b.top, z = V.zoom, tol = 5;
  const [x0, y0, x1, y1] = [r[0] * z, r[1] * z, (r[0] + r[2]) * z, (r[1] + r[3]) * z];
  if (mx < x0 - tol || mx > x1 + tol || my < y0 - tol || my > y1 + tol) return null;
  let s = "";
  if (Math.abs(my - y0) <= tol) s += "n"; else if (Math.abs(my - y1) <= tol) s += "s";
  if (Math.abs(mx - x0) <= tol) s += "w"; else if (Math.abs(mx - x1) <= tol) s += "e";
  return s || null;
}

function colourAt(x, y) {
  if (!V.pixels || x < 0 || y < 0 || x >= V.pixels.width || y >= V.pixels.height) return null;
  const i = (y * V.pixels.width + x) * 4, p = V.pixels.data;
  return "#" + [p[i], p[i + 1], p[i + 2]].map(v => v.toString(16).padStart(2, "0")).join("");
}

function onDown(e) {
  if (e.button !== 0) return;
  const [x, y] = sheetPos(e);
  if (e.altKey) {
    const c = colourAt(x, y);
    if (c && DT.on) { detectAltClick(c); return; }
    if (c) {
      navigator.clipboard && navigator.clipboard.writeText(c).catch(() => {});
      toast(`${c} at ${x}, ${y} (copied)`);
    }
    return;
  }
  if (DT.on) { detectDown(e, x, y); return; }
  if (V.tool === "draw") {
    V.drag = {mode: "draw", start: [x, y], rect: [x, y, 1, 1]};
    return;
  }
  const sel = S.sel.frame;
  const edge = sel && edgeAt(e, rectOf(sel));
  if (edge) { V.drag = {mode: "resize", edge, name: sel, start: [x, y], orig: [...rectOf(sel)], rect: [...rectOf(sel)]}; return; }
  const hit = hitFrame(x, y);
  if (hit !== sel) { selectFrame(hit); }
  if (hit) V.drag = {mode: "move", name: hit, start: [x, y], orig: [...rectOf(hit)], rect: null};
}

function onMove(e) {
  const [x, y] = sheetPos(e);
  const c = colourAt(x, y);
  status(`x ${x}  y ${y}${c ? "  " + c : ""}${V.drag && V.drag.rect ? `   ·   [${V.drag.rect.join(", ")}]` : ""}`);
  if (DT.on) { V.canvas.style.cursor = "crosshair"; detectMove(x, y); return; }
  if (!V.drag) {
    const edge = V.tool === "select" && S.sel.frame && edgeAt(e, rectOf(S.sel.frame));
    V.canvas.style.cursor = V.tool === "draw" ? "crosshair" : edge ? ({n: "ns", s: "ns", e: "ew", w: "ew", ne: "nesw", sw: "nesw", nw: "nwse", se: "nwse"}[edge] + "-resize") : "default";
    return;
  }
  const d = V.drag, [sx, sy] = d.start;
  if (d.mode === "draw") {
    d.rect = [Math.min(sx, x), Math.min(sy, y), Math.abs(x - sx) + 1, Math.abs(y - sy) + 1];
  } else if (d.mode === "move") {
    if (x === sx && y === sy && !d.rect) return;
    d.rect = [d.orig[0] + x - sx, d.orig[1] + y - sy, d.orig[2], d.orig[3]];
    d.rect[0] = Math.max(0, d.rect[0]); d.rect[1] = Math.max(0, d.rect[1]);
  } else if (d.mode === "resize") {
    let [rx, ry, rw, rh] = d.orig;
    const dx = x - sx, dy = y - sy;
    if (d.edge.includes("e")) rw = Math.max(1, rw + dx);
    if (d.edge.includes("s")) rh = Math.max(1, rh + dy);
    if (d.edge.includes("w")) { const nx = Math.min(rx + rw - 1, rx + dx); rw += rx - nx; rx = nx; }
    if (d.edge.includes("n")) { const ny = Math.min(ry + rh - 1, ry + dy); rh += ry - ny; ry = ny; }
    d.rect = [rx, ry, rw, rh];
  }
  draw();
}

async function onUp() {
  const d = V.drag;
  V.drag = null;
  if (!d) return;
  if (d.mode === "draw") {
    if (d.rect[2] < 2 || d.rect[3] < 2) { draw(); return; }
    let rect = d.rect;
    try { rect = (await api("fit_rect", {rect})).rect; } catch (e) { toast(e.message, "error"); draw(); return; }
    const name = nextName();
    S.sel.frame = name;
    await set(["frames", name], rect);
    toast(`Added ${name} [${rect.join(", ")}], fitted to the drawing. Rename it in the inspector.`);
    const n = document.querySelector('[data-key="frame-name"]');
    if (n) { n.focus(); n.select(); }
    return;
  }
  if (d.rect && JSON.stringify(d.rect) !== JSON.stringify(d.orig)) await set(["frames", d.name], d.rect);
  else draw();
}

function nextName() {
  const names = new Set(frameNames());
  let i = names.size + 1;
  while (names.has("FRAME" + i)) i++;
  return "FRAME" + i;
}

function selectFrame(name, scroll) {
  S.sel.frame = name;
  renderInspector();
  draw();
  if (scroll && name) {
    const r = rectOf(name), wrap = document.querySelector('[data-scroll="sheet"]');
    if (r && wrap) {
      wrap.scrollTo({left: Math.max(0, r[0] * V.zoom - wrap.clientWidth / 2 + r[2] * V.zoom / 2),
        top: Math.max(0, r[1] * V.zoom - wrap.clientHeight / 2 + r[3] * V.zoom / 2), behavior: "smooth"});
    }
  }
}

function setRect(name, rect) { return set(["frames", name], rect.map(v => Math.max(0, Math.round(v)))); }

function onKey(e) {
  if (S.tab !== "sheet" || !S.info) return;
  if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
  const sel = S.sel.frame, r = sel && rectOf(sel);
  const k = e.key;
  if (k === "d" || k === "D") { toggleDetect(); e.preventDefault(); return; }
  if (DT.on) { if (detectKey(e) || ["+", "=", "-"].includes(k)) { if (k === "+" || k === "=") zoom(1); if (k === "-") zoom(-1); e.preventDefault(); } return; }
  if (k === "v" || k === "V") { V.tool = "select"; renderToolbar(); }
  else if (k === "r" || k === "R" || k === "b") { V.tool = "draw"; renderToolbar(); }
  else if (k === "+" || k === "=") zoom(1);
  else if (k === "-") zoom(-1);
  else if (k === "[" || k === "]") {
    const names = frameNames(), i = names.indexOf(sel);
    selectFrame(names[(i + (k === "]" ? 1 : -1) + names.length) % names.length], true);
  } else if (r && k.startsWith("Arrow")) {
    const step = 1, nr = [...r];
    const dx = k === "ArrowLeft" ? -step : k === "ArrowRight" ? step : 0, dy = k === "ArrowUp" ? -step : k === "ArrowDown" ? step : 0;
    if (e.shiftKey) { nr[2] = Math.max(1, nr[2] + dx); nr[3] = Math.max(1, nr[3] + dy); } else { nr[0] += dx; nr[1] += dy; }
    setRect(sel, nr);
  } else if (r && (k === "f" || k === "F")) fit(sel);
  else if (r && (k === "Delete" || k === "Backspace")) removeFrame(sel);
  else if (k === "Escape") selectFrame(null);
  else return;
  e.preventDefault();
}
document.addEventListener("keydown", onKey);

function zoom(d) {
  V.zoom = Math.max(1, Math.min(10, V.zoom + d));
  store.put("zoom", V.zoom);
  sizeCanvas(); draw(); renderToolbar();
}

function sizeCanvas() {
  if (!V.canvas || !V.img) return;
  V.canvas.width = V.img.width * V.zoom;
  V.canvas.height = V.img.height * V.zoom;
}

async function fit(name) {
  try { const {rect} = await api("fit_rect", {rect: rectOf(name)}); await setRect(name, rect); toast(`${name} fitted: [${rect.join(", ")}]`); }
  catch (e) { toast(e.message, "error"); }
}

async function removeFrame(name) {
  const fi = (V.info.frames || {})[name] || {};
  if (fi.used_by && fi.used_by.length && !confirm(`${name} is used by ${fi.used_by.length} place(s): ${fi.used_by.slice(0, 4).join(", ")}. Delete it anyway?`)) return;
  S.sel.frame = null;
  await edit([{op: "del", path: ["frames", name]}]);
}

function renderToolbar() {
  const bar = document.getElementById("sheet-toolbar");
  if (!bar) return;
  const tool = (id, text, key) => h("button" + (V.tool === id ? ".on" : ""), {title: `${text} (${key})`, onclick: () => { V.tool = id; renderToolbar(); }}, text);
  fill(bar, 
    h("div.group", tool("select", "Select", "V"), tool("draw", "Draw frame", "R")),
    h("button" + (DT.on ? ".on" : ""), {title: "Find the sprites on the sheet and propose frames (D)", onclick: () => toggleDetect()}, "Detect frames"),
    h("div.group", h("button", {title: "Zoom out (-)", onclick: () => zoom(-1)}, "−"), h("span.mono.zoom", `${V.zoom}×`),
      h("button", {title: "Zoom in (+)", onclick: () => zoom(1)}, "+")),
    h("label.check", h("input", {type: "checkbox", checked: V.names, onchange: e => { V.names = e.target.checked; store.put("names", V.names); draw(); }}), h("span", "names")),
    h("span.legend", h("i", {style: {background: COL.used}}), "used", h("i", {style: {background: COL.unused}}), "unused",
      h("i", {style: {background: COL.bad}}), "empty / outside", h("i", {style: {background: COL.ground}}), "ground", h("i", {style: {background: COL.pivot}}), "position"),
    h("span.hint", "drag to move · drag an edge to resize · arrows nudge (shift: resize) · F fit · [ ] next · alt-click: colour"));
}

let inspectorSeq = 0;
async function renderInspector() {
  const box = document.getElementById("inspector");
  if (!box) return;
  if (DT.on) { renderDetectPanel(box); return; }
  const name = S.sel.frame, r = name && rectOf(name);
  const fi = (V.info && V.info.frames[name]) || {};
  const list = frameList();
  if (!r) {
    fill(box, h("section.card", h("h3", "Frames"),
      h("p.hint", "Click a rectangle to edit it, or use Draw frame (R) and drag around a sprite: the box is fitted to the drawing for you."),
      h("p.hint", `${frameNames().length} frames on a ${V.info ? V.info.sheet_size.join("×") : "?"} sheet.`)), list);
    return;
  }
  const num = (i, label) => h("label.mini", h("span", label), h("input.mono", {value: r[i], "data-key": `frame-${label}`, inputmode: "numeric",
    onchange: e => { const nr = [...r]; nr[i] = parseInt(e.target.value, 10); if (!isNaN(nr[i])) setRect(name, nr); }}));
  const preview = h("div.frame-preview.checker", h("span.muted", "…"));
  fill(box, 
    h("section.card",
      h("div.row", h("input.mono.name", {value: name, "data-key": "frame-name", title: "rename (every use follows)",
        onchange: async e => {
          const to = e.target.value.trim();
          if (!to || to === name) return;
          try { S.info = await api("rename_frame", {old: name, new: to}); S.sel.frame = to; (await import("./core.js")).rerender(); }
          catch (err) { toast(err.message, "error"); e.target.value = name; }
        }})),
      h("div.xywh", num(0, "x"), num(1, "y"), num(2, "w"), num(3, "h")),
      fi.empty ? h("p.bad", "Empty: only background colours inside.") : null,
      fi.outside ? h("p.bad", "Reaches past the sheet's edge.") : null,
      fi.trim && JSON.stringify(fi.trim) !== JSON.stringify(r) ? h("p.hint", `Drawn part: [${fi.trim.join(", ")}] (the build trims to it)`) : null,
      h("div.row",
        h("button.small", {onclick: () => fit(name), title: "shrink to the drawn pixels (F)"}, "Fit to drawing"),
        h("button.small", {onclick: async () => { const n = nextName(); S.sel.frame = n; await set(["frames", n], [r[0] + r[2] + 2, r[1], r[2], r[3]]); }}, "Duplicate"),
        h("button.small.danger", {onclick: () => removeFrame(name)}, "Delete")),
      preview,
      h("label.check", h("input", {type: "checkbox", checked: V.raw, onchange: e => { V.raw = e.target.checked; store.put("raw", V.raw); renderInspector(); }}),
        h("span", "sheet colours (off: as the game draws it)")),
      h("div.used", h("span.label", fi.used_by && fi.used_by.length ? "Used by" : "Not used yet"),
        (fi.used_by || []).map(w => {
          const [sec, ...rest] = w.split(" ");
          const anim = rest.join(" ");
          return h("a.chip", {href: "#", onclick: ev => { ev.preventDefault(); sec === "ui" || sec === "ending" ? go("hud") : go("anims", {section: sec, anim: sec === "s3k_victory" ? null : anim}); }}, w);
        }))),
    list);
  const seq = ++inspectorSeq;
  try {
    const img = await api("frame_image", {ref: name, raw: V.raw, scale: 4});
    if (seq !== inspectorSeq) return;
    fill(preview, h("img.pixel", {src: img.png, width: img.w, height: img.h}), h("span.hint", `${img.w / 4}×${img.h / 4} after trimming`));
  } catch (e) { fill(preview, h("span.bad", e.message)); }
}

function frameList() {
  const names = frameNames().filter(n => !V.filter || n.toLowerCase().includes(V.filter.toLowerCase()));
  const frames = (V.info && V.info.frames) || {};
  return h("section.card.grow",
    h("input", {placeholder: "filter frames…", value: V.filter, "data-key": "frame-filter",
      oninput: e => { V.filter = e.target.value; const l = document.getElementById("frame-list"); if (l) l.replaceWith(frameList().querySelector("#frame-list")); }}),
    h("div.list#frame-list", {"data-scroll": "frames"}, names.map(n => {
      const fi = frames[n] || {}, r = (S.info.doc.frames || {})[n] || [];
      return h("div.item" + (n === S.sel.frame ? ".on" : ""), {onclick: () => selectFrame(n, true)},
        h("span.mono", n), h("span.muted.mono", `${r[2]}×${r[3]}`),
        fi.empty || fi.outside ? h("span.badge.no", "!") : fi.used_by && fi.used_by.length ? h("span.badge.yes", fi.used_by.length) : h("span.badge.plain", "unused"));
    })));
}

export async function renderSheet(main) {
  const wrap = h("div.sheet-wrap", {"data-scroll": "sheet"});
  const page = h("div.sheet-page", h("div.toolbar#sheet-toolbar"), h("div.sheet-body", wrap, h("div.inspector#inspector")));
  main.append(page);
  renderToolbar();
  if (!S.info.sheet.exists) { wrap.append(h("p.bad", `The sheet ${S.info.sheet.path} doesn't exist: set sheet.file on the Character tab.`)); return; }
  const [img] = await Promise.all([loadImage(), loadInfo()]);
  if (!img) { wrap.append(h("p.bad", "The sheet couldn't be loaded.")); return; }
  const canvas = h("canvas.sheet", {onmousedown: onDown, onmousemove: onMove, onmouseleave: () => status(""),
    ondblclick: e => { if (DT.on) detectDbl(...sheetPos(e)); }});
  V.canvas = canvas;
  wrap.append(canvas);
  sizeCanvas();
  draw();
  renderInspector();
  if (S.sel.scrollTo) { selectFrame(S.sel.frame, true); S.sel.scrollTo = false; }
  if (S.sel.detect) { delete S.sel.detect; toggleDetect(true); }
}
window.addEventListener("mouseup", () => { if (V.drag) onUp(); if (DT.drag) detectUp(); });
initDetect({V, draw, renderInspector: () => renderInspector(), renderToolbar: () => renderToolbar(),
  scrollTo: r => { const wrap = document.querySelector('[data-scroll="sheet"]');
    if (wrap) wrap.scrollTo({left: Math.max(0, (r[0] + r[2] / 2) * V.zoom - wrap.clientWidth / 2), top: Math.max(0, (r[1] + r[3] / 2) * V.zoom - wrap.clientHeight / 2), behavior: "smooth"}); }});

S.renderers.sheet = renderSheet;
