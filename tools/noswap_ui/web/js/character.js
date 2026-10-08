// The Character tab: identity, credits, the sheet, flags, games and physics, as forms made from the JSON Schema
// (docs/character.schema.json): each property's type picks its control, its description becomes the hint.
import {S, h, get, set, del, edit, field, textInput, numInput, checkbox, select, swatch, toast, api, go} from "./core.js";

let schema = null;

const OVERRIDES = {   // extra words and controls where the schema alone isn't enough
  "id": {hint: "The folder's name and the package folder. Never rename it once released.", readonly: true},
  "key": {hint: "<creator>.<character>, e.g. someone.newchar. Saves hang on it: never change it once released.", placeholder: "left out: noswap.<id> (NoSwap's own)"},
  "name": {hint: "In capitals, up to 16 characters: the act results and HUD tag.", transform: v => v.toUpperCase()},
  "full_name": {hint: "A human-readable name (the release title)."},
  "base": {hint: "Whose moveset, physics and animation list he plays on."},
  "credits/short": {hint: "The line under the Origins select card: about 32 characters."},
  "credits/full": {multiline: true, hint: "The full credit, as the sheet asks."},
  "credits/terms": {multiline: true, hint: "The sheet's own terms, copied word for word."},
  "credits/url": {hint: "Where the sheet comes from."},
  "sheet/file": {hint: "The sprite sheet, relative to this folder."},
  "sheet/feet_y": {hint: "Where the feet sit (Sonic's ground line is 20)."},
  "sheet/angled_halves": {label: "angled halves", hint: "Walk and run lists are upright frames, then the 45° ones (S3&K splits them)."},
  "flags/super": {hint: "Uses Sonic's own Super palette."},
  "flags/drop_dash": {hint: "Has Sonic's Drop Dash."},
  "flags/roll": {hint: "Has a rolling animation of his own (ability slot 49)."},
  "flags/no_roll": {hint: "Can't roll."},
  "flags/private": {hint: "Not in public builds."},
  "flags/crossover": {hint: "A separate download, never in the all-in-one."},
};

function resolve(node) {
  while (node && node.$ref) node = schema.$defs[node.$ref.split("/").pop()];
  return node || {};
}

function control(path, node) {
  const key = path.join("/");
  const o = OVERRIDES[key] || {};
  node = resolve(node);
  if (o.readonly) return h("input.mono", {value: get(path) ?? "", readonly: true});
  if (node.enum) return select(path, node.enum);
  if (node.type === "boolean") return checkbox(path, o.label || path[path.length - 1]);
  if (node.type === "integer" || (node.anyOf && node.anyOf.some(a => resolve(a).type === "integer"))) return numInput(path, {width: "7em"});
  if (node.type === "array" && resolve(node.items).pattern === "^#[0-9a-fA-F]{6}$") return colourList(path);
  if (node.type === "array" && resolve(node.items).type === "string") return tagList(path);
  if (node.type === "string" || !node.type) return textInput(path, {multiline: o.multiline, transform: o.transform, placeholder: o.placeholder});
  return h("span.muted", "(edit in the file)");
}

function schemaForm(path, node, keys) {
  node = resolve(node);
  const props = node.properties || {};
  return h("div.form", (keys || Object.keys(props)).map(k => {
    const p = resolve(props[k]);
    const kpath = [...path, k];
    const o = OVERRIDES[kpath.join("/")] || {};
    const c = control(kpath, p);
    if (p.type === "boolean") return h("div.field.bool", c, h("span.hint", o.hint || p.description || ""));
    return field(o.label || k.replace(/_/g, " "), c, o.hint || p.description, {wide: !!o.multiline});
  }));
}

function tagList(path) {
  const items = get(path) || [];
  const input = h("input", {placeholder: "add…", "data-key": path.join("/") + "/+",
    onkeydown: e => { if (e.key === "Enter" && e.target.value.trim()) { set(path, [...items, e.target.value.trim()]); } }});
  return h("div.tags", items.map((t, i) => h("span.tag", t,
    h("button.x", {title: "remove", onclick: () => set(path, items.filter((_, j) => j !== i))}, "×"))), input);
}

function colourList(path) {
  const items = get(path) || [];
  return h("div.tags", items.map((c, i) => h("span.tag.colour", swatch(c), h("span.mono", c),
      h("button.x", {title: "remove", onclick: () => set(path, items.filter((_, j) => j !== i))}, "×"))),
    h("input.mono", {placeholder: "#rrggbb", style: {width: "7em"}, "data-key": path.join("/") + "/+",
      onkeydown: e => {
        const v = e.target.value.trim().toLowerCase();
        if (e.key === "Enter") {
          if (!/^#[0-9a-f]{6}$/.test(v)) return toast("a colour is #rrggbb", "error");
          set(path, [...items, v]);
        }
      }}),
    h("span.hint", "Tip: alt-click the sheet (Sheet tab) to pick a colour."));
}

// Physics: the "physics" passive (multipliers on Sonic's): writes abilities.physics and lists it in abilities.
const PHYS = [
  ["top_speed", "Top speed"], ["acceleration", "Acceleration"], ["air_acceleration", "Air acceleration"], ["jump", "Jump"],
];
const PHYS_V4 = [["air_deceleration", "Air deceleration"], ["skid_speed", "Skid speed"], ["rolling_friction", "Rolling friction"], ["jump_cap", "Jump cap"]];

function physics() {
  const ab = get(["abilities"]) || {};
  const on = (ab.abilities || []).includes("physics");
  const ph = ab.physics || {};
  const row = ([k, label], note) => {
    const v = ph[k] ?? 1;
    const commit = val => {
      const ops = [];
      if (!on) ops.push({op: "set", path: ["abilities", "abilities"], value: [...(ab.abilities || []), "physics"]});
      if (Math.abs(val - 1) < 1e-9) ops.push({op: "del", path: ["abilities", "physics", k]});
      else ops.push({op: "set", path: ["abilities", "physics", k], value: Math.round(val * 100) / 100});
      edit(ops);
    };
    return h("div.phys",
      h("span.label", label),
      h("input", {type: "range", min: 0.5, max: 1.5, step: 0.05, value: v, "data-key": "phys/" + k,
        oninput: e => e.target.nextSibling.value = (+e.target.value).toFixed(2), onchange: e => commit(+e.target.value)}),
      h("input.mono", {value: (+v).toFixed(2), style: {width: "4.5em"}, onchange: e => { const n = parseFloat(e.target.value); if (!isNaN(n)) commit(n); }}),
      h("span.hint", v === 1 ? "Sonic's" : `${Math.round(v * 100)}% of Sonic's`, note ? " · " + note : ""));
  };
  return h("section.card",
    h("h3", "Physics", h("span.hint", " multipliers on Sonic's (1.00 = Sonic's)")),
    h("p.hint", "Heavy characters: a lower top speed and slower acceleration; racers the opposite. Keep the jump at 1.00 or above unless you've tested the levels: a lower jump can make some gaps impossible."),
    PHYS.map(p => row(p, p[0] === "jump" && (ph.jump ?? 1) < 1 ? "below Sonic's: test the levels" : "")),
    h("details", h("summary", "Sonic 1 / 2 only"), PHYS_V4.map(p => row(p))),
    on ? h("button.small", {onclick: () => edit([
      {op: "set", path: ["abilities", "abilities"], value: (ab.abilities || []).filter(m => m !== "physics")},
      {op: "del", path: ["abilities", "physics"]}])}, "Reset to Sonic's") : null);
}

export function renderCharacter(main) {
  schema = S.schema;
  const d = get([]);
  const sheet = S.info.sheet;
  main.append(h("div.page",
    h("div.cols",
      h("div.col",
        h("section.card", h("h3", "Identity"), schemaForm([], schema, ["id", "key", "name", "full_name", "base"])),
        h("section.card", h("h3", "Credits & terms"),
          h("p.hint", "The art stays the artist's: crops, mirroring, 90° turns and whole-number enlargements only, and their terms as written."),
          schemaForm(["credits"], schema.properties.credits)),
      ),
      h("div.col",
        h("section.card", h("h3", "Sprite sheet"),
          sheet.exists ? h("div.sheet-thumb", {onclick: () => go("sheet")},
            h("img", {src: `/sheet?t=${new URLSearchParams(location.search).get("t")}&v=${sheet.version}`, alt: "sheet"}),
            h("span.hint", `${sheet.size[0]}×${sheet.size[1]} · click to open the sheet`))
            : h("p.bad", `The sheet ${sheet.path} doesn't exist.`),
          schemaForm(["sheet"], schema.properties.sheet)),
        physics(),
        h("section.card", h("h3", "Games"),
          h("p.hint", "The Origins games (S1, S2, CD, S3&K) are always built together; Mania is optional."),
          h("div.checks", ["sonic1", "sonic2", "soniccd", "s3k", "mania"].map(g =>
            checkbox(["games", g], {sonic1: "Sonic 1", sonic2: "Sonic 2", soniccd: "Sonic CD", s3k: "Sonic 3&K", mania: "Sonic Mania"}[g], {dflt: true})))),
        h("section.card", h("h3", "Flags"), schemaForm(["flags"], schema.properties.flags)),
        h("section.card", h("h3", "Select card"),
          d.card == null ? h("p.hint", "None: the Origins select card is his Stopped frame at 8×.")
            : h("pre.mono.small", JSON.stringify(d.card, null, 1)),
          h("p.hint", "Edit a custom card in character.json for now (docs/character-json.md).")),
      )),
  ));
  focusField();
}

function focusField() {
  const f = S.sel.field;
  if (!f) return;
  S.sel.field = null;
  const key = f.replace(/\./g, "/");
  const el = document.querySelector(`[data-key^="${CSS.escape(key)}"]`);
  if (el) { el.focus(); el.scrollIntoView({block: "center"}); el.classList.add("flash"); }
}

S.renderers.character = renderCharacter;
