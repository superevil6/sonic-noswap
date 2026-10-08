// The Ball panel (Animations tab): character.json "ball", the generic spin ball (tools/generic_ball.py: Sonic Mania's
// plain spin ball in five of his own colours). Size buttons, the colours (auto, or picked from his palette), a live
// preview in the game's colours (backend.ball_preview), and which animations it is used for.
import {S, h, api, set, del, get, fill, go, toast} from "./core.js";

export const SIZES = [["small", 24, "Bomb's size"], ["medium", 30, "the ball as ripped"], ["large", 40, "Big's size"]];
export const ROLES = [["outline", "the shadow crescent and rim"], ["dark", "the shading band"], ["mid", "the main fill"],
  ["light", "the lit edge"], ["shine", "the sparkle"]];
export const USE_FOR = [
  ["Spin Dash", "charging and releasing the Spin Dash (the default)"],
  ["Jumping", "his jump, which is his attack: it looks like a spin ball, not his own jump pose (also the S2 / CD / S3&K special stages)"],
  ["Rolling", "rolling on the ground (ability slot 49, turns \"roll\" on; also the S2 / CD / S3&K special stages); his jump keeps its pose"],
  ["Special Stage", "Sonic 1's special stage"]];
export const DEFAULT_USE_FOR = ["Spin Dash"];

let timer = null;
const cache = new Map();

export function ballUse() {
  const b = S.info && S.info.doc.ball;
  if (!b || typeof b !== "object") return [];
  return Array.isArray(b.use_for) ? b.use_for : DEFAULT_USE_FOR;
}

export async function ballPreview(b) {
  const args = {size: b.size || "medium", colours: b.colours || "auto", scale: 3};
  const key = JSON.stringify([args, S.info.doc.palette, S.info.doc.sheet, S.info.doc.frames]);
  if (!cache.has(key)) cache.set(key, api("ball_preview", args).catch(e => ({error: e.message})));
  return cache.get(key);
}

function playBall(el, frames) {
  // each of the 2 frames twice, as the build does; about the game's ball speed for a look
  clearInterval(timer);
  let i = 0;
  const seq = [0, 0, 1, 1];
  const img = h("img.pixel", {src: frames[0].png, width: frames[0].w, height: frames[0].h});
  fill(el, img);
  timer = setInterval(() => {
    if (!document.body.contains(img)) { clearInterval(timer); return; }
    i = (i + 1) % seq.length;
    img.src = frames[seq[i]].png;
  }, 70);
}

// A small "generic ball" picture for a slot the ball fills.
export function ballBadge() {
  const b = S.info.doc.ball;
  const el = h("span.ball-mini.checker");
  if (b) ballPreview(b).then(p => { if (p && p.frames) fill(el, h("img.pixel", {src: p.frames[0].png, width: p.frames[0].w / 1.5, height: p.frames[0].h / 1.5})); });
  return el;
}

export function ballPanel() {
  const b = S.info.doc.ball;
  if (!b || typeof b !== "object") {
    return h("section.card.ball-panel",
      h("h3", "Generic spin ball"),
      h("p", "For a sheet with no spin ball: Sonic Mania's plain spin ball (SEGA's frames), in five of his own colours. "
        + "It is built exactly as Bomb's and Chaos's are, in every game (S1, S2, CD, S3&K and Mania)."),
      h("button.primary", {onclick: () => set(["ball"], {size: "medium", colours: "auto", use_for: [...DEFAULT_USE_FOR]})}, "Add a ball"));
  }
  const size = b.size || "medium";
  const cols = b.colours || "auto";
  const use = ballUse();
  const stage = h("div.ball-stage.checker", h("span.muted", "…"));
  const still = h("div.ball-still");
  const picks = h("div.ball-colours");
  const card = h("section.card.ball-panel",
    h("div.row.spread", h("h3", "Generic spin ball"),
      h("button.small.danger", {onclick: () => { if (confirm("Remove the ball? The animations it fills go back to his own frames (or their fallbacks).")) del(["ball"]); }}, "Remove")),
    h("div.ball-grid",
      h("div",
        h("div.label", "Size"),
        h("div.seg", SIZES.map(([k, px, what]) => h("button" + (k === size ? ".on" : ""), {title: what, onclick: () => set(["ball", "size"], k)}, `${k} · ${px} px`))),
        h("div.label", "Colours"),
        h("div.seg",
          h("button" + (cols === "auto" ? ".on" : ""), {title: "picked from his palette: his most used colour's shades", onclick: () => set(["ball", "colours"], "auto")}, "auto"),
          h("button" + (cols !== "auto" ? ".on" : ""), {title: "choose each of the five from his palette", onclick: async () => {
            if (cols !== "auto") return;
            const p = await ballPreview(b);
            if (p.error) return toast(p.error, "error");
            set(["ball", "colours"], {...p.colours});
          }}, "pick my own")),
        picks,
        h("div.label", "Use it for"),
        h("div.ball-use", USE_FOR.map(([k, what]) => h("label.check", {title: what},
          h("input", {type: "checkbox", checked: use.includes(k), onchange: e => {
            const next = USE_FOR.map(([n]) => n).filter(n => n === k ? e.target.checked : use.includes(n));
            if (!next.length) { toast("use it for at least one (or remove the ball)", "error"); e.target.checked = true; return; }
            set(["ball", "use_for"], next);
          }}), h("span", k), h("span.hint", " " + what)))),
        h("p.hint", "Spin Dash only is the usual choice. A ball in Jumping changes how his attack looks.")),
      h("div",
        h("div.label", "Preview (game colours)"),
        stage, still)),
    h("p.hint", "The ball's frames go under a working copy of the sheet (build/<id>_ball.png); the sheet itself is never changed. "
      + "Small and large are nearest-neighbour resizes of the same pixels."));
  ballPreview(b).then(p => {
    if (!p || p.error) { fill(stage, h("p.bad", p ? p.error : "no preview")); return; }
    playBall(stage, p.frames);
    fill(still, p.frames.map(f => h("span.checker", h("img.pixel", {src: f.png, width: f.w, height: f.h}))),
      h("div.mono.small", `${p.size} px`), p.source_exists ? null : h("p.bad", `the ball's frames (${p.source}) aren't there`));
    fill(picks, ROLES.map(([role, what]) => {
      const cur = cols === "auto" ? p.colours[role] : (cols[role] || p.colours[role]);
      return h("div.ball-role",
        h("span.role", {title: what}, role),
        h("span.swatch", {style: {background: p.game[role]}, title: `${cur} (game: ${p.game[role]})`}),
        h("span.mono.small", cur),
        cols === "auto" ? null : h("span.pal", p.palette.map(({colour, slot}) => h("button.sw" + (colour === (cols[role] || "").toLowerCase() ? ".on" : ""),
          {title: `${colour} (slot ${slot})`, style: {background: colour}, onclick: () => set(["ball", "colours", role], colour)}))));
    }));
  });
  return card;
}
