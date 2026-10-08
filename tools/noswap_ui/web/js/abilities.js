// The Abilities tab: the character's moves from the ability registry (docs/abilities.json): what each does, the games
// it works in, its fields with their units, the animation slots it draws, and the rules on combining moves.
import {S, fill, h, api, edit, set, del, get, toast, go, modal, closeModal, gameBadges, badge, numValue, parseNum, rerender} from "./core.js";
import {hitboxPanel, groupsOf, hitboxFromSel} from "./hitbox.js";

const KIND_TEXT = {move: "move", passive: "passive", setting: "setting"};

function reg() { return S.registry; }
function entry() { return get(["abilities"]) || {}; }
function moves() { return entry().abilities || []; }

// Settings in use: a setting's own field is in the entry (shot, float_lean, ability_cycle, ...)
function settingsInUse() {
  const e = entry();
  return Object.values(reg().abilities).filter(a => a.kind === "setting" && Object.keys(a.fields).some(f => f in e)).map(a => a.id);
}

function speedText(v, unit) {
  const n = numValue(v);
  if (n === null) return "";
  const px = n / 65536;
  return unit === "accel" ? `= ${+px.toFixed(4)} px a frame, each frame` : `= ${+px.toFixed(3)} px a frame`;
}

function fieldEditor(name, d) {
  const path = ["abilities", name];
  const v = get(path);
  const unit = d.unit;
  const placeholder = d.default !== null && d.default !== undefined && typeof d.default !== "object" ? String(d.default) : d.no_default ? "required" : "";
  let control, after = null;
  if (d.per_frame) return perFrameEditor(name, d);
  if (unit === "bool") {
    control = h("input", {type: "checkbox", checked: v === undefined ? !!d.default : !!v, "data-key": path.join("/"), onchange: e => set(path, e.target.checked)});
  } else if (["list", "frame list", "px list", "object"].includes(unit) || (v !== undefined && typeof v === "object")) {
    control = h("textarea.mono", {rows: unit === "object" ? 4 : 1, "data-key": path.join("/"), spellcheck: "false",
      value: v === undefined ? "" : JSON.stringify(v, null, unit === "object" && JSON.stringify(v).length > 70 ? 1 : 0), placeholder: d.example_text || "",
      onchange: e => {
        const t = e.target.value.trim();
        if (!t) return del(path);
        try { set(path, JSON.parse(t)); } catch (err) { toast(`${name}: not valid JSON (${err.message})`, "error"); e.target.classList.add("bad"); }
      }});
  } else if (unit === "sound") {
    // S3&K / Mania sound fields also take the character's own sounds (character.json "sounds": "own:<name>"), offered
    // in the field's list (tools/own_sounds.py)
    const own = name.endsWith("_s3k") ? Object.keys(get(["sounds"]) || {}).filter(k => !k.startsWith("_")) : [];
    const listId = own.length ? `own-sounds-${name}` : null;
    control = h("span", h("input", {value: v ?? "", placeholder: d.example_text ? d.example_text.replace(/^"|"$/g, "") : "", "data-key": path.join("/"),
      ...(listId ? {list: listId} : {}),
      onchange: e => e.target.value.trim() ? set(path, e.target.value.trim()) : del(path)}),
      listId ? h("datalist", {id: listId}, own.map(k => h("option", {value: `own:${k}`}))) : null);
  } else {
    const hex = unit === "speed" || unit === "accel";
    control = h("input.mono", {value: v ?? "", placeholder, "data-key": path.join("/"), style: {width: hex ? "9em" : "6em"},
      onchange: e => {
        const t = e.target.value.trim();
        if (!t) return del(path);
        const n = parseNum(t, hex);
        if (n === null) { toast(`${name}: ${t} isn't a number${hex ? " or a hex string like 0x60000" : ""}`, "error"); return; }
        set(path, n);
      }});
    if (hex) after = h("span.mono.small.muted", speedText(v ?? d.default, unit));
    if (unit === "frames" && typeof v === "number") after = h("span.mono.small.muted", `= ${(v / 60).toFixed(2)} s`);
  }
  return h("div.ab-field",
    h("div.ab-field-head", h("span.mono", name), h("span.unit", {title: d.unit_text}, unit + (d.range ? `, ${d.range}` : "")),
      v === undefined ? h("span.muted.small", d.no_default ? " not set (needed)" : " not set: its default") : h("button.icon", {title: "remove (use the default)", onclick: () => del(path)}, "×")),
    h("div.ab-field-ctl", control, after),
    h("div.hint", d.what, d.example_text && v === undefined ? h("span.muted", ` e.g. ${d.example_text}`) : null));
}

// A per-frame list (registry per_frame: melee_reach, melee_top...): one box per frame of its slot, so it can't be a
// different length from the animation. Frames added or removed on the Animations tab grow or shrink it (backend.edit).
function slotFrames(slot) {
  const a = (get(["ability_animations"]) || {})[slot];
  if (!a || !a.frames || !a.frames.length) return 0;
  return a.frames.length * (Number.isInteger(a.hold) && a.hold > 1 ? a.hold : 1);
}

// what a frame's box is without the list (tools/abilities.py melee_poses: 20 px above and below his centre)
const PF_DEFAULT = {melee_top: -20, melee_bottom: 20, melee_air_top: -20, melee_air_bottom: 20};

function perFrameEditor(name, d) {
  const path = ["abilities", name];
  const v = get(path);
  const n = slotFrames(d.per_frame);
  const list = Array.isArray(v) ? v : null;
  const vals = n ? Array.from({length: n}, (_, i) => list && list.length ? (i < list.length ? list[i] : list[list.length - 1]) : undefined) : (list || []);
  const fit = list && n && list.length !== n;
  const commit = (i, raw) => {
    const t = String(raw).trim();
    let val;
    if (d.unit === "px list") { val = parseNum(t); if (val === null) { toast(`${name} frame ${i + 1}: ${t} isn't a number`, "error"); return; } }
    else { try { val = JSON.parse(t); } catch { toast(`${name} frame ${i + 1}: not valid JSON`, "error"); return; } }
    const filled = vals.map((x, j) => j === i ? val : x === undefined ? (PF_DEFAULT[name] ?? val) : x);
    set(path, filled);
  };
  const boxes = vals.map((x, i) => h("label.pf", h("span.mono.small.muted", String(i + 1)),  // (frames counted from 1, as the hit-box panel's)
    h("input.mono", {value: x === undefined ? "" : (typeof x === "object" ? JSON.stringify(x) : x), placeholder: PF_DEFAULT[name] !== undefined ? String(PF_DEFAULT[name]) : "",
      "data-key": `${path.join("/")}/${i}`, style: {width: d.unit === "px list" ? "4em" : "7em"}, onchange: e => commit(i, e.target.value)})));
  return h("div.ab-field",
    h("div.ab-field-head", h("span.mono", name), h("span.unit", {title: d.unit_text}, `${d.unit}, one per frame of slot ${d.per_frame}`),
      v === undefined ? h("span.muted.small", d.no_default ? " not set (needed)" : " not set: its default") : h("button.icon", {title: "remove (use the default)", onclick: () => del(path)}, "×")),
    n ? h("div.ab-field-ctl.pf-row", boxes) : h("p.warn.small", `Slot ${d.per_frame} has no frames yet: draw it first (one value per frame).`),
    fit ? h("p.bad.small", `${list.length} values for ${n} frames: the build needs one per frame. `,
      h("button.small", {onclick: () => set(path, (list.concat(Array(n).fill(list[list.length - 1]))).slice(0, n))}, `Fit to ${n} frames`)) : null,
    h("div.hint", d.what));
}

function slotRow(slot, d) {
  const anim = (get(["ability_animations"]) || {})[slot];
  const n = anim && anim.frames ? anim.frames.length : 0;
  return h("div.slot",
    h("span.mono.slotno", slot),
    h("span", d.what, d.required ? null : h("span.muted", " (optional)")),
    n ? badge(`${n} frame${n === 1 ? "" : "s"}`, "yes") : badge(d.required ? "no frames" : "none", d.required ? "no" : "plain"),
    h("button.small", {onclick: () => go("anims", {section: "ability_animations", anim: slot})}, n ? "Edit" : "Draw it"),
    h("span.muted.small", {title: "its number in Sonic CD and Sonic 3&K"}, `CD ${d.per_game.cd || "–"} · 3K ${d.per_game.s3k || "–"}`));
}

function moveCard(id, rulesNow) {
  const a = reg().abilities[id];
  if (!a) {
    return h("section.card.ab", h("div.row.spread", h("h3.bad", id), h("button.small.danger", {onclick: () => remove(id)}, "Remove")),
      h("p.bad", "Not a move NoSwap has: pick one from Add a move."));
  }
  const builtFor = gamesBuilt();
  const missing = builtFor.filter(g => (a.games[g] || {}).support === "no");
  const broken = rulesNow.filter(r => (r.bad || []).some(b => b.includes(id)) || (reg().rules.find(x => x.id === r.id) || {moves: []}).moves.includes(id));
  return h("section.card.ab" + (S.sel.move === id ? ".flash" : ""), {id: "ab-" + id},
    h("div.row.spread",
      h("div", h("h3", a.name, " ", h("span.muted.small.mono", id)), h("div.small", badge(KIND_TEXT[a.kind], "plain"), " ", h("span.muted", a.input))),
      h("div.row", gameBadges(a.games), id === "physics" ? h("button.small", {onclick: () => go("character")}, "Edit physics")
        : h("button.small.danger", {onclick: () => remove(id)}, "Remove"))),
    h("p.desc", a.description || h("span.muted", "(no description yet)")),
    missing.length ? h("p.warn", `Not in ${missing.map(g => ({s1: "Sonic 1", s2: "Sonic 2", cd: "Sonic CD", s3k: "Sonic 3&K", mania: "Sonic Mania"})[g]).join(", ")} yet: skipped there.`) : null,
    broken.map(r => h("p." + (r.level === "error" ? "bad" : "warn"), r.text)),
    a.needs && a.needs.length ? h("ul.needs", a.needs.map(n => h("li", n))) : null,
    Object.keys(a.slots).length ? h("div.slots", h("div.label", "Animation slots"), Object.entries(a.slots).map(([s, d]) => slotRow(s, d))) : null,
    hitboxPanel(id, f => perFrameEditor(f, a.fields[f])),  // (the per-frame groups: drawn on the frames, hitbox.js)
    id !== "physics" && Object.keys(a.fields).length ? h("div.ab-fields", Object.entries(a.fields)
      .filter(([f]) => !grouped(id).has(f)).map(([f, d]) => fieldEditor(f, d))) : null);
}

// The fields a move's hit-box panel edits (abilities_registry.PER_FRAME_GROUPS of that move): not listed again.
function grouped(id) {
  const g = (S.registry && S.registry.per_frame_groups) || {};
  return new Set(groupsOf(id).flatMap(n => Object.values(g[n].fields)));
}

function gamesBuilt() {
  const g = get(["games"]) || {};
  return ["s1", "s2", "cd", "s3k", ...(g.mania ? ["mania"] : [])];
}

async function remove(id) {
  try { S.info = await api("remove_ability", {mid: id}); rerender(); toast(`Removed ${id}`); }
  catch (e) { toast(e.message, "error"); }
}

function otherFields() {
  const e = entry(), r = reg().abilities;
  const owned = new Set(["abilities"]);
  for (const id of [...moves(), ...settingsInUse()]) for (const f of Object.keys((r[id] || {}).fields || {})) owned.add(f);
  const rest = Object.keys(e).filter(k => !owned.has(k) && !k.startsWith("_"));
  if (!rest.length) return null;
  const owners = {};
  for (const [id, a] of Object.entries(r)) for (const f of Object.keys(a.fields)) (owners[f] = owners[f] || []).push(id);
  return h("section.card", h("h3", "Other fields"),
    h("p.hint", "Fields in the file that none of his moves read: they do nothing unless their move is added."),
    rest.map(k => h("div.row", h("span.mono", k), h("span.muted.small", owners[k] ? `belongs to ${owners[k].join(" / ")}` : "no move reads it"),
      h("code.small", JSON.stringify(e[k]).slice(0, 60)), h("button.small.danger", {onclick: () => del(["abilities", k])}, "Remove"))));
}

// The picker: every move with its games, a search, and what adding it would break.
function picker() {
  const all = Object.values(reg().abilities).filter(a => a.id !== "physics");
  const have = new Set([...moves(), ...settingsInUse()]);
  let q = "", kind = "", onlyAll = false, chosen = null;
  const listEl = h("div.pick-list"), detail = h("div.pick-detail", h("p.muted", "Pick a move to see what it does."));
  const refresh = () => {
    const built = gamesBuilt();
    const rows = all.filter(a => (!kind || a.kind === kind)
      && (!q || (a.name + " " + a.id + " " + a.description).toLowerCase().includes(q))
      && (!onlyAll || built.every(g => (a.games[g] || {}).support !== "no")))
      .sort((a, b) => (a.kind > b.kind) - (a.kind < b.kind) || a.name.localeCompare(b.name));
    fill(listEl, ...rows.map(a => h("div.item" + (chosen === a.id ? ".on" : "") + (have.has(a.id) ? ".have" : ""), {onclick: () => { chosen = a.id; refresh(); show(a); }},
      h("span", a.name), h("span.muted.small", a.kind), gameBadges(a.games))));
  };
  const show = async a => {
    fill(detail, h("h3", a.name, " ", h("span.muted.small.mono", a.id)), h("div", badge(a.kind, "plain"), " ", h("span.muted", a.input), " ", gameBadges(a.games)),
      h("p", a.description), h("div#pick-rules", h("p.muted.small", "checking the rules on combining moves…")),
      a.needs.length ? h("ul.needs", a.needs.map(n => h("li", n))) : null,
      Object.keys(a.slots).length ? h("div", h("div.label", "Draws"), Object.entries(a.slots).map(([s, d]) => h("div.small", h("span.mono", s), " ", d.what, d.required ? "" : " (optional)"))) : null,
      Object.keys(a.fields).length ? h("div#pick-fields", h("p.muted.small", "…")) : null,
      a.example_from ? h("p.hint", `Values come from ${a.example_from.replace(/\b(\w)(\w*)/g, (m, x, y) => x + y.toLowerCase())}'s own entry, which works: tune them after adding. Options start off: switch them on in the Abilities tab.`) : null,
      a.id === "shot" ? h("p.warn", "The shot's art points at another character's sheet: change shot.art to your own drawing.") : null,
      h("div.row", have.has(a.id) ? h("span.muted", "He has it already.")
        : h("button.primary", {onclick: async () => {
          try { S.info = await api("add_ability", {mid: a.id}); closeModal(); S.sel.move = a.id; rerender(); toast(`Added ${a.name}`); }
          catch (e) { toast(e.message, "error"); }
        }}, `Add ${a.name}`)));
    try {
      const start = await api("starting_fields", {mid: a.id});
      const box = document.getElementById("pick-fields");
      if (box) fill(box, h("table.fields", h("tr", h("th", "field"), h("th", "unit"), h("th", "filled with")),
        Object.entries(a.fields).map(([f, d]) => h("tr", {title: d.what}, h("td.mono", f), h("td", d.unit),
          h("td.mono.small", f in start ? JSON.stringify(start[f]).slice(0, 60) : h("span.muted", d.unit === "bool" ? "off" : "left out (its default)"))))));
    } catch (e) { /* ignore */ }
    try {
      const r = await api("ability_rules", {add: a.id});
      const box = document.getElementById("pick-rules");
      if (box) fill(box, r.new.length ? h("div", r.new.map(x => h("p." + (x.level === "error" ? "bad" : "warn"), "⚠ ", x.text))) : h("p.ok.small", "No clash with his other moves."));
    } catch (e) { /* ignore */ }
  };
  modal(h("div.picker",
    h("div.row.spread", h("h2", "Add a move"), h("button", {onclick: closeModal}, "Close")),
    h("div.row",
      h("input", {placeholder: "search moves…", oninput: e => { q = e.target.value.toLowerCase(); refresh(); }, style: {flex: 1}}),
      h("select", {onchange: e => { kind = e.target.value; refresh(); }}, h("option", {value: ""}, "all kinds"), ["move", "passive", "setting"].map(k => h("option", {value: k}, k + "s"))),
      h("label.check", h("input", {type: "checkbox", onchange: e => { onlyAll = e.target.checked; refresh(); }}), h("span", "works in all his games"))),
    h("p.hint", "Badges: S1 Sonic 1, S2 Sonic 2, CD, 3K Sonic 3&K, MA Mania. Green works, amber partly, grey not there yet. New moves are core work; these are the ones NoSwap has."),
    h("div.pick-body", listEl, detail)), {wide: true});
  refresh();
}

export async function renderAbilities(main) {
  if (!S.registry) {
    main.append(h("p.muted", "Loading the ability registry…"));
    try { S.registry = await api("registry"); } catch (e) { fill(main, h("p.bad", e.message)); return; }
    main.replaceChildren();
  }
  let rules = {now: []};
  try { rules = await api("ability_rules", {}); } catch { /* shown by check */ }
  if (S.sel.hb) { S.sel.move = S.sel.move || S.sel.hb; hitboxFromSel(S.sel); }  // (#abilities?hb=melee&group=...)
  const ms = moves(), sets = settingsInUse();
  main.append(h("div.page",
    h("div.row.spread", h("div", h("h2", "Abilities"), h("p.hint", "His moves, from the registry NoSwap's builders read (docs/abilities.md). Values are 16.16 fixed point where the unit says speed: 0x10000 is 1 px a frame.")),
      h("button.primary", {onclick: picker}, "Add a move…")),
    rules.now.filter(r => !ms.some(m => (reg().rules.find(x => x.id === r.id) || {moves: []}).moves.includes(m))).map(r => h("p." + (r.level === "error" ? "bad" : "warn"), r.text)),
    ms.length || sets.length ? null : h("section.card", h("p", "No moves yet: he plays like his base character. Add one!")),
    ms.map(m => moveCard(m, rules.now)),
    sets.map(m => moveCard(m, rules.now)),
    otherFields()));
  if (S.sel.dialog === "add") { S.sel.dialog = null; picker(); }
  if (S.sel.move) {
    const el = document.getElementById("ab-" + S.sel.move);
    if (el) el.scrollIntoView({block: "start"});
    S.sel.move = null;
  }
}

S.renderers.abilities = renderAbilities;
window.addEventListener("noswap-add-move", () => { if (S.registry && S.info) picker(); });
