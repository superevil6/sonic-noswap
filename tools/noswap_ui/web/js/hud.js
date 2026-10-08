// The HUD & ending tab: the six HUD pieces and Sonic 1's ending poses, each a frame or a rect on the sheet.
import {S, fill, h, api, set, del, get, edit, frameNames, toast, go} from "./core.js";

const UI = [
  ["life_icon", "Life icon", "16×16, the head on the lives counter", [16, 16]],
  ["life_name", "Life name tag", "the name next to the lives counter, typed (at most 72 px)", null],
  ["monitor_1up", "1-UP monitor", "16×14, the face on the 1-UP monitor", [16, 14]],
  ["sign_face", "Signpost face", "at most 48×32, the end-of-act signpost", [48, 32]],
  ["mini_1", "Mini icon 1", "the small icon (UI palette: remap +128)", null],
  ["mini_2", "Mini icon 2", "the second small icon frame", null],
];
const ENDING = [
  ["end_idle", "Ending idle", "standing"], ["end_pose_1", "Pose 1 (small)", ""], ["end_pose_2", "Pose 2 (medium)", "at most 71 px wide"],
  ["end_pose_3", "Pose 3 (large)", ""], ...[1, 2, 3, 4, 5, 6].map(n => [`good_${n}`, `Good ending ${n}`, ""]),
];

// The name tag is typed: {"text": "NAME"} (or left out: his "name"), drawn in the HUD's own letters (tools/hud_font.py),
// unless the creator picks "use my own graphic" (a frame or rect, like the other pieces).
let FONT = null;
function layTag(word) {  // hud_font.tag: each letter's pixels, then one blank column; a space is SPACE more
  const g = FONT.glyphs, letters = [...word].filter(c => c !== " ");
  if (!letters.length || letters.some(c => !g[c])) return null;
  const height = Math.max(...letters.map(c => g[c].length));
  let rows = Array(height).fill("");
  for (const c of word) {
    if (c === " ") { rows = rows.map(r => r + ".".repeat(FONT.space)); continue; }
    const gl = g[c], w = gl[0].length;
    rows = rows.map((r, i) => r + (i < gl.length ? gl[i] : ".".repeat(w)) + ".");
  }
  return rows.map(r => r.replace(/\.+$/, ""));
}

function drawTag(cv, rows, z = 4) {
  const w = Math.max(1, ...rows.map(r => r.length)), ht = rows.length;
  cv.width = w * z; cv.height = ht * z;
  const ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, cv.width, cv.height);
  rows.forEach((r, y) => [...r].forEach((ch, x) => {
    const col = FONT.colours[ch];
    if (col) { ctx.fillStyle = col; ctx.fillRect(x * z, y * z, z, z); }
  }));
}

function nameTagRow(label, hint) {
  const path = ["ui", "life_name"];
  const e = get(path);
  const name = (get(["name"]) || "").toUpperCase();
  const typed = !e || e.text !== undefined;
  if (!typed) return null;  // (own graphic: the usual row)
  const text = e ? e.text : name;
  const cv = h("canvas.pixel.tag-preview");
  const count = h("span.mono.small");
  const msg = h("div.small");
  const show = t => {
    if (!FONT) return;
    const [rw, rh] = FONT.room;
    const bad = [...new Set([...t].filter(c => c !== " " && !FONT.glyphs[c]))];
    const rows = bad.length ? null : layTag(t);
    if (!rows) {
      drawTag(cv, [""]);
      count.textContent = "";
      fill(msg, h("span.bad", t.trim() ? `not in the font: ${bad.map(c => JSON.stringify(c)).join(" ")} (it has A-Z, 0-9, space and · . , : ; ! ?)` : "empty"));
      return;
    }
    drawTag(cv, rows);
    const w = Math.max(...rows.map(r => r.length)), tall = rows.length > rh;
    count.textContent = `${w} px of ${rw}`;
    count.className = "mono small " + (w > rw ? "bad" : "ok");
    fill(msg, w > rw ? h("span.bad", `${w - rw} px too long: shorten it`) : tall ? h("span.bad", `${rows.length} px tall: Q , ; have tails below the ${rh}-px room`) : null);
  };
  const input = h("input.mono", {value: text, placeholder: name, "data-key": "ui/life_name/text", style: {width: "12em"}, spellcheck: "false",
    oninput: ev => { const p = ev.target.selectionStart; ev.target.value = ev.target.value.toUpperCase(); ev.target.setSelectionRange(p, p); show(ev.target.value); },
    onchange: ev => {
      const v = ev.target.value;
      // (his own name is the default: left out of the file then, so a renamed character's tag follows)
      if (v === name) return e ? del(path) : null;
      set(path, {...(e || {}), text: v});
    }});
  const load = FONT ? Promise.resolve() : api("name_font").then(f => { FONT = f; });
  load.then(() => show(text)).catch(err => fill(msg, h("span.bad", err.message)));
  return h("div.hud-row",
    h("div", h("b", label), h("div.hint", h("span.mono", "life_name"), " · ", hint)),
    h("span.thumb.checker.big", cv),
    h("div.hud-ctl",
      h("label.mini", h("span", "text"), input), count,
      h("button.small", {title: "draw it from your sheet instead (a frame or rect)",
        onclick: () => set(path, {frame: frameNames()[0] || ""})}, "use my own graphic"),
      msg,
      h("div.hint", e ? "Typed in the HUD's letters (Rayan C.'s Sonic 1 font)." : `Not set: his name, ${name || "?"}, in the HUD's letters (Rayan C.'s Sonic 1 font).`)));
}

// The signpost face: "head on the official sign" ({"head": FRAME_or_rect, "scale"?: "auto" | n}: the head goes on the
// game's own board, tools/sign_face.py) or "my own full sign graphic" ({"frame": ...}, a whole 48x32 sign drawn on the
// sheet, used as drawn). A plain {"frame": ...} that is clearly a head (smaller than the board) is built as a head too
// ("detected"), and with no sign_face at all the top of the Stopped frame is used ("default"): the backend's plan
// (character_json.sign_face_plan, the build's own) says which, so the row waits for it.
const SCALE_MIN = 1, SCALE_MAX = 2;
const SIGN_PATH = ["ui", "sign_face"];

function signModes(isHead, toHead, toOwn) {
  return h("div.sign-mode",
    h("label.check", {title: "a head from your sheet on the game's own signpost board (enlarged to fill it)"},
      h("input", {type: "radio", name: "sign-mode", checked: isHead, onchange: toHead}), h("span", "Head on the official sign (automatic)")),
    h("label.check", {title: "a whole 48×32 sign drawn on your sheet, used exactly as drawn"},
      h("input", {type: "radio", name: "sign-mode", checked: !isHead, onchange: toOwn}), h("span", "My own full sign graphic")));
}

function signRow(label, hint, rowFn) {
  const e = get(SIGN_PATH);
  if (e && e.head === undefined && (e.own || e.text !== undefined || e.remap || e.scale !== undefined || e.base)) return null;  // (own: the usual row)
  const slot = h("div.hud-row", h("div", h("b", label), h("div.hint", h("span.mono", "sign_face"), " · ", hint)), h("span.muted.small", "…"));
  api("sign_preview", {scale: 3}).then(p => {
    slot.replaceWith(p.mode === "head" ? headRow(label, hint, p) : rowFn(true));
  }).catch(err => fill(slot, h("b", label), h("span.bad.small", err.message)));
  return slot;
}

function headRow(label, hint, p) {
  const path = SIGN_PATH;
  const e = get(path);
  const names = frameNames();
  const head = e && e.head !== undefined ? e.head : e ? (e.frame !== undefined ? e.frame : e.rect) : p.head;
  const scale = e && e.head !== undefined && typeof e.scale === "number" ? e.scale : "auto";
  const writeHead = (hd, s) => set(path, {head: hd, ...(s === "auto" ? {} : {scale: s})});
  const ownSign = () => set(path, {...(typeof head === "string" ? {frame: head} : {rect: head || [0, 0, 48, 32]}), trim: false, own: true});
  const img = h("span.thumb.checker.big", p.board ? h("img.pixel", {src: p.board.png, width: p.board.w, height: p.board.h,
    title: "as S1 / S2 / CD / S3&K show it (Mania puts the same face on its own board)"}) : null);

  const picker = h("select", {onchange: ev => writeHead(ev.target.value === "(rect)" ? (typeof head === "string" ? get(["frames", head]) : head) || [0, 0, 24, 24] : ev.target.value, scale)},
    names.map(n => h("option", {value: n}, n)), h("option", {value: "(rect)"}, "a rect…"));
  picker.value = typeof head === "string" ? head : "(rect)";
  const rectIn = Array.isArray(head) ? h("span.xywh", ["x", "y", "w", "h"].map((l, i) => h("label.mini", h("span", l), h("input.mono", {value: head[i], style: {width: "3.6em"},
    onchange: ev => { const r = [...head]; r[i] = parseInt(ev.target.value, 10); if (!isNaN(r[i])) writeHead(r, scale); }})))) : null;

  const auto = scale === "auto";
  const value = h("span.mono.small", auto ? `auto: ${p.scale}×` : `${p.scale}×`);
  const slider = h("input", {type: "range", min: SCALE_MIN, max: SCALE_MAX, step: 0.05, value: p.scale, disabled: auto, style: {width: "9em"},
    oninput: ev => { value.textContent = `${(+ev.target.value).toFixed(2)}×`; },
    onchange: ev => writeHead(head, Math.round(+ev.target.value * 100) / 100)});
  const autoBox = h("label.check", {title: "fill the face area's 24-px height, as the hand-made characters do (tools/sign_face.auto_scale)"},
    h("input", {type: "checkbox", checked: auto, onchange: ev => writeHead(head, ev.target.checked ? "auto" : p.scale)}), h("span", "auto"));
  const [, , w, ht] = p.head || [0, 0, 0, 0];
  const note = h("div.hint",
    p.why === "detected" ? `Your frame is ${w}×${ht}: a head, not a whole 48×32 sign, so it goes on the official board. ` : null,
    p.why === "default" ? `No signpost face set: the top of the Stopped frame (${w}×${ht}) on the official board. Pick a head to choose your own. ` : null,
    `Shown at 3× as the game shows it: the head enlarged ${p.scale}× nearest-neighbour (the signpost exception), its top trimmed if it's too tall.`);
  return h("div.hud-row" + (e ? "" : ".missing"),
    h("div", h("b", label), h("div.hint", h("span.mono", "sign_face"), " · ", hint)),
    img,
    h("div.hud-ctl", signModes(true, null, ownSign),
      h("label.mini", h("span", "head"), picker),
      typeof head === "string" ? h("button.icon", {title: "show on the sheet", onclick: () => go("sheet", {frame: head, scrollTo: true})}, "⌖") : null,
      rectIn,
      h("label.mini", h("span", "scale"), slider), value, autoBox,
      note));
}

function row(sec, [key, label, hint, size], ownSign = false) {
  const path = [sec, key];
  const e = get(path);
  if (sec === "ui" && key === "life_name") {
    const typed = nameTagRow(label, hint);
    if (typed) return typed;
  }
  if (sec === "ui" && key === "sign_face" && !ownSign) {
    const signed = signRow(label, hint, own => row(sec, [key, label, hint, size], own));
    if (signed) return signed;
  }
  const names = frameNames();
  const img = h("span.thumb.checker.big");
  if (e && (e.frame || e.rect)) {
    api("frame_image", {ref: e.frame ? {frame: e.frame} : e.rect, raw: false, scale: sec === "ui" ? 3 : 1})
      .then(t => {
        fill(img, h("img.pixel", {src: t.png, width: t.w, height: t.h}));
        const real = sec === "ui" ? [t.w / 3, t.h / 3] : [t.w, t.h];
        if (size && (real[0] > size[0] || real[1] > size[1])) img.after(h("span.warn.small", ` ${real[0]}×${real[1]}: too big`));
      }).catch(err => fill(img, h("span.bad.small", err.message)));
  }
  const mode = e ? (e.frame !== undefined ? "frame" : "rect") : "none";
  const modeSel = h("select", {onchange: ev => {
    const m = ev.target.value;
    if (m === "none") return del(path);
    const keep = {...(e || {})};
    delete keep.frame; delete keep.rect;
    set(path, m === "frame" ? {frame: names[0] || "", ...keep} : {rect: (e && e.frame && (get(["frames", e.frame]) || [0, 0, 16, 16])) || [0, 0, 16, 16], ...keep});
  }}, ["none", "frame", "rect"].map(m => h("option", {value: m}, m)));
  modeSel.value = mode;
  let ctl = null;
  if (mode === "frame") {
    const s = h("select", {onchange: ev => set([...path, "frame"], ev.target.value)}, names.map(n => h("option", {value: n}, n)));
    s.value = e.frame;
    ctl = h("span", s, h("button.icon", {title: "show on the sheet", onclick: () => go("sheet", {frame: e.frame, scrollTo: true})}, "⌖"));
  } else if (mode === "rect") {
    ctl = h("span.xywh", ["x", "y", "w", "h"].map((l, i) => h("label.mini", h("span", l), h("input.mono", {value: e.rect[i], style: {width: "3.6em"},
      onchange: ev => { const r = [...e.rect]; r[i] = parseInt(ev.target.value, 10); if (!isNaN(r[i])) set([...path, "rect"], r); }}))));
  }
  const back = sec === "ui" && key === "life_name"
    ? h("button.small", {title: "type it instead (the HUD's letters)", onclick: () => del(path)}, "type it instead") : null;
  // (the signpost face drawn whole: the switch back to a head on the official sign; "own" is dropped then)
  const signSwitch = sec === "ui" && key === "sign_face" && e && (e.frame !== undefined || e.rect)
    ? signModes(false, () => set(path, {head: e.frame !== undefined ? e.frame : e.rect}), null) : null;
  return h("div.hud-row" + (e ? "" : ".missing"),
    h("div", h("b", label), h("div.hint", h("span.mono", key), hint ? " · " + hint : ""), back),
    img,
    h("div.hud-ctl", signSwitch, modeSel, ctl,
      e ? h("label.check", {title: "trim empty edges (off keeps the box as drawn)"}, h("input", {type: "checkbox", checked: e.trim !== false, onchange: ev => ev.target.checked ? del([...path, "trim"]) : set([...path, "trim"], false)}), h("span", "trim")) : null,
      e ? h("label.mini", {title: "colour remap: +128 moves colours 1-15 to the UI sheet's 129-143"}, h("span", "remap"),
        h("input.mono", {value: typeof e.remap === "string" ? e.remap : e.remap ? JSON.stringify(e.remap) : "", placeholder: "none", style: {width: "5em"},
          onchange: ev => { const v = ev.target.value.trim(); if (!v) return del([...path, "remap"]); if (/^\+\d+$/.test(v)) return set([...path, "remap"], v); try { set([...path, "remap"], JSON.parse(v)); } catch { toast("remap is +128 or a JSON object", "error"); } }})) : null));
}

export function renderHud(main) {
  main.append(h("div.page",
    h("h2", "HUD & ending"),
    h("p.hint", "The sheet's own HUD art and Sonic 1's ending poses. Each is a named frame or a rect; trimmed to the drawing unless trim is off."),
    h("div.cols.hud-cols",
      h("section.card.col", h("h3", "HUD", h("span.hint", " shown at 3×")), UI.map(u => row("ui", u))),
      h("section.card.col", h("h3", "Sonic 1 ending", h("span.hint", " shown at 1×")), ENDING.map(u => row("ending", u))))));
  if (S.sel.element) {
    S.sel.element = null;
  }
}

S.renderers.hud = renderHud;
