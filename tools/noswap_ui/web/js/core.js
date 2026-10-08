// Shared bits: the API, the app state, a tiny element builder, edits, toasts and dialogs.

const token = new URLSearchParams(location.search).get("t") || "";

export const S = {
  info: null,        // the open character (backend._info): folder, id, doc, dirty, sheet, templates, speeds
  tab: "character",
  check: null,
  registry: null,
  sel: {frame: null, section: "animations", anim: "Stopped"},
  renderers: {},     // tab -> function(main)
};

export async function api(method, args = {}) {
  const r = await fetch("/api/" + method, {
    method: "POST", headers: {"Content-Type": "application/json", "X-Noswap-Token": token},
    body: JSON.stringify(args),
  });
  let data;
  try { data = await r.json(); } catch { throw new Error(`${method}: the editor's server didn't answer`); }
  if (!r.ok || data.error) throw new Error(data.error || `${method} failed`);
  return data.result;
}

export function sheetUrl() {
  return `/sheet?t=${encodeURIComponent(token)}&v=${S.info ? S.info.sheet.version : 0}`;
}

// h("div.card#id", {attrs / on*: handlers}, ...children)
export function h(tag, attrs, ...kids) {
  const m = tag.match(/^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i);
  const el = document.createElement(m[1] || "div");
  for (const part of (m[2] || "").match(/[.#][\w-]+/g) || []) {
    if (part[0] === ".") el.classList.add(part.slice(1)); else el.id = part.slice(1);
  }
  if (attrs && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k === "value") el.value = v;
    else if (k === "checked") el.checked = !!v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

export const doc = () => S.info && S.info.doc;

export function get(path, d = doc()) {
  let cur = d;
  for (const k of path) { if (cur == null) return undefined; cur = cur[k]; }
  return cur;
}

// Apply edits on the backend (it keeps key order, comments and unknown keys), then re-render.
export async function edit(ops, {render = true} = {}) {
  try {
    S.info = await api("edit", {ops});
  } catch (e) { toast(e.message, "error"); return false; }
  updateTop();
  if (render) rerender();
  return true;
}
export const set = (path, value, opts) => edit([{op: "set", path, value}], opts);
export const del = (path, opts) => edit([{op: "del", path}], opts);

export function rerender() {
  const main = document.getElementById("main");
  const focusKey = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.key : null;
  const scrolls = [...main.querySelectorAll("[data-scroll]")].map(e => [e.dataset.scroll, e.scrollTop, e.scrollLeft]);
  const top = main.scrollTop;
  main.replaceChildren();
  let done;
  if (!S.info && S.tab !== "build" && S.tab !== "settings") {
    main.append(welcome());
  } else {
    done = (S.renderers[S.tab] || (() => {}))(main);
  }
  const restore = () => {
    main.scrollTop = top;
    for (const [k, t, l] of scrolls) {
      const e = main.querySelector(`[data-scroll="${k}"]`);
      if (e) { e.scrollTop = t; e.scrollLeft = l; }
    }
    if (focusKey) {
      const e = main.querySelector(`[data-key="${CSS.escape(focusKey)}"]`);
      if (e) e.focus();
    }
  };
  restore();
  if (done && done.then) done.then(restore);
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === S.tab));
}

function welcome() {
  return h("div.welcome",
    h("h1", "Make a character"),
    h("p", "Open a character folder (one with a character.json), or start a new one from your sprite sheet."),
    h("div.row", h("button.primary", {onclick: () => window.dispatchEvent(new Event("noswap-open"))}, "Open a character…"),
      h("button", {onclick: () => window.dispatchEvent(new Event("noswap-new"))}, "New from a sheet…")),
    S.kit && !S.kit.ready_origins && !S.kit.ready_mania
      ? h("p.warn", "First set up the kit: Settings tab, Set up (it takes the game files the build needs from your own games).") : null,
    S.kit ? h("p.muted", "New characters go in ", h("span.mono", S.kit.characters), ". Start from the example in the kit's example/ folder, or New from your own sheet. The guide: docs/character-json.md and docs/abilities.md in the kit folder.") : null,
    h("p.muted", "Everything here edits character.json and runs the same tools as the command line. Nothing goes into the games until you press Deploy (Build & deploy tab)."));
}

export function updateTop() {
  const who = document.getElementById("who");
  const save = document.getElementById("btn-save");
  if (!S.info) { who.textContent = "no character open"; save.disabled = true; return; }
  const d = S.info.doc;
  fill(who, h("b", d.full_name || d.name || S.info.id), h("span.muted", ` ${d.key || "noswap." + S.info.id}`),
    S.info.dirty ? h("span.dirty", {title: "unsaved changes"}, "● unsaved") : h("span.saved", "saved"));
  save.disabled = !S.info.dirty;
  document.title = `${S.info.dirty ? "• " : ""}${d.name || S.info.id} - NoSwap Character Editor`;
}

let toastTimer;
export function toast(msg, kind = "info") {
  const t = document.getElementById("toast");
  t.className = "show " + kind;
  t.textContent = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = "", kind === "error" ? 7000 : 3000);
}

export function status(msg) { document.getElementById("status").textContent = msg || ""; }

export function modal(content, {wide = false} = {}) {
  const m = document.getElementById("modal");
  const box = document.getElementById("modal-box");
  box.className = "modal-box" + (wide ? " wide" : "");
  box.replaceChildren(content);
  m.hidden = false;
  const first = box.querySelector("input, select, textarea, button");
  if (first) first.focus();
}
export function closeModal() { document.getElementById("modal").hidden = true; }

// A labelled form row: label, control, optional hint.
export function field(label, control, hint, {wide = false} = {}) {
  return h("label.field" + (wide ? ".wide" : ""), h("span.label", label), control, hint ? h("span.hint", hint) : null);
}

// Inputs bound to a path in the document; they commit on change (Enter / leaving the field).
export function textInput(path, {placeholder, mono = false, multiline = false, transform, list} = {}) {
  const v = get(path);
  const el = h(multiline ? "textarea" : "input", {
    value: v == null ? "" : String(v), placeholder, "data-key": path.join("/"), class: mono ? "mono" : null,
    list, rows: multiline ? 3 : null, spellcheck: multiline ? "true" : "false",
    onchange: e => {
      let val = e.target.value;
      if (transform) val = transform(val);
      if (val === "" && v === undefined) return;
      set(path, val);
    },
  });
  return el;
}

// A number (or a "0x..." hex string where hex is allowed): numbers stay numbers, hex stays hex.
export function numInput(path, {min, max, step, placeholder, hex = false, width} = {}) {
  const v = get(path);
  return h("input.mono", {
    value: v == null ? "" : String(v), placeholder, "data-key": path.join("/"), inputmode: "numeric",
    style: width ? {width} : null,
    onchange: e => {
      const t = e.target.value.trim();
      if (t === "") { del(path); return; }
      const val = parseNum(t, hex);
      if (val === null) { toast(`${t} isn't a number${hex ? " (or a hex string like 0x30000)" : ""}`, "error"); e.target.value = v ?? ""; return; }
      if (typeof val === "number" && ((min !== undefined && val < min) || (max !== undefined && val > max))) {
        toast(`keep it between ${min} and ${max}`, "error"); e.target.value = v ?? ""; return;
      }
      set(path, val);
    },
    onkeydown: e => {
      if ((e.key === "ArrowUp" || e.key === "ArrowDown") && !e.target.value.startsWith("0x") && !e.target.value.startsWith("-0x")) {
        const n = Number(e.target.value || 0);
        if (!isNaN(n)) {
          const st = step || 1;
          e.target.value = +(n + (e.key === "ArrowUp" ? st : -st) * (e.shiftKey ? 10 : 1)).toFixed(4);
          e.preventDefault();
          e.target.dispatchEvent(new Event("change"));
        }
      }
    },
  });
}

export function parseNum(t, hex = false) {
  t = String(t).trim();
  if (hex && /^-?0x[0-9a-f]+$/i.test(t)) return t;
  if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t);
  if (!hex && /^-?0x[0-9a-f]+$/i.test(t)) return parseInt(t, 16);
  return null;
}

export function numValue(v) {
  if (typeof v === "string" && /^-?0x[0-9a-f]+$/i.test(v)) return (v.startsWith("-") ? -1 : 1) * parseInt(v.replace("-", ""), 16);
  return typeof v === "number" ? v : null;
}

export function checkbox(path, label, {title, dflt = false} = {}) {
  const v = get(path);
  return h("label.check", {title},
    h("input", {type: "checkbox", checked: v === undefined ? dflt : !!v, "data-key": path.join("/"),
      onchange: e => set(path, e.target.checked)}), h("span", label));
}

export function select(path, options, {dflt, allowNone = false} = {}) {
  const v = get(path);
  const s = h("select", {"data-key": path.join("/"), onchange: e => e.target.value === "" ? del(path) : set(path, e.target.value)},
    allowNone ? h("option", {value: ""}, "(default)") : null,
    options.map(o => {
      const [val, text] = Array.isArray(o) ? o : [o, o];
      return h("option", {value: val}, text);
    }));
  s.value = v === undefined ? (allowNone ? "" : (dflt ?? "")) : v;
  return s;
}

// A JSON editor for a value of any shape (lists, objects): commits valid JSON only.
export function jsonInput(path, {rows = 3} = {}) {
  const v = get(path);
  const text = v === undefined ? "" : JSON.stringify(v);
  return h("textarea.mono", {
    rows, "data-key": path.join("/"), spellcheck: "false", value: text,
    onchange: e => {
      const t = e.target.value.trim();
      if (!t) { del(path); return; }
      try { set(path, JSON.parse(t)); }
      catch (err) { toast(`not valid JSON: ${err.message}`, "error"); e.target.classList.add("bad"); }
    },
  });
}

export function swatch(colour, title) {
  return h("span.swatch", {style: {background: colour || "transparent"}, title: title || colour || "none"});
}

export function badge(text, kind, title) { return h("span.badge." + (kind || "plain"), {title}, text); }

export const GAME_SHORT = {s1: "S1", s2: "S2", cd: "CD", s3k: "3K", mania: "MA"};
export const GAME_NAMES = {s1: "Sonic 1", s2: "Sonic 2", cd: "Sonic CD", s3k: "Sonic 3&K", mania: "Sonic Mania"};

export function gameBadges(games) {
  return h("span.games", Object.keys(GAME_SHORT).map(g => {
    const s = (games[g] || {}).support || "no";
    return badge(GAME_SHORT[g], s === "yes" ? "yes" : s === "partial" ? "partial" : "no",
      `${GAME_NAMES[g]}: ${s === "no" ? "not there yet" : s}${games[g] && games[g].note ? " (" + games[g].note + ")" : ""}`);
  }));
}

export function go(tab, sel = {}) {
  S.tab = tab;
  Object.assign(S.sel, sel);
  rerender();
}

// Frame names in the open document, in file order.
export function frameNames() {
  return Object.keys(get(["frames"]) || {}).filter(k => !k.startsWith("_"));
}

// replaceChildren that skips null / false (conditional children) and flattens arrays.
export function fill(el, ...kids) {
  el.replaceChildren(...kids.flat(Infinity).filter(k => k !== null && k !== undefined && k !== false));
}
