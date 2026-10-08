// The Settings tab: where `noswap deploy` copies to (Origins' mods folder, the Mania decomp's play folder). Each is
// detected (Steam's libraries, the usual folders), editable and checked as you type. They're saved in the user's own
// settings file (never the repo); clearing one goes back to detection.
import {S, fill, h, api, toast, badge} from "./core.js";

export const D = {data: null, loading: null, draft: {}, checks: {}};

export async function loadDeploy(force = false) {
  if (D.data && !force) return D.data;
  if (!D.loading) D.loading = api("deploy_settings").then(r => { D.data = r; return r; }).finally(() => { D.loading = null; });
  return D.loading;
}

const TITLE = {origins: "Sonic Origins: HedgeModManager's mods folder", mania: "Sonic Mania: the decomp's play folder"};
const WHAT = {
  origins: "Every mod in mods/ except NoSwapMania is mirrored here (deploy.sh). It's <Sonic Origins>/build/main/projects/exec/mods, next to SonicOrigins.exe; HedgeModManager keeps ModsDB.ini in it. Logs, cache/ and the player's NoSwapS3K.ini are kept.",
  mania: "mods/NoSwapMania is symlinked into its mods/ and enabled in mods/modconfig.ini (deploy_mania.sh). It's the folder with the decompilation's RSDKv5U and the game's Data.rsdk, not Steam's SonicMania.exe.",
};

// The Creator Kit's Set up (tools/noswap_cli/kit.py): the game files the build reads, taken from the player's own
// games into the kit's data folder. Shown only in the kit.
const K = {draft: {}, checks: {}, job: null, lines: [], done: true, code: null, next: 0, timer: null};
const KIT_WHAT = {
  origins: "Sonic Origins' folder (the Steam one, with image/ and build/ in it). The kit reads its classic games' data packs and the decompiled scripts HedgeModManager installs there (install HedgeModManager and the NoSwap mod, and start the game once with NoSwap enabled, first). Needed to build for Origins.",
  mania: "Optional: a folder with Sonic Mania's Data.rsdk (Steam's Sonic Mania, or your decompilation's play folder). Needed to build for Mania, and for the generic spin ball.",
};

async function kitPoll() {
  clearTimeout(K.timer);
  if (!K.job) return;
  try {
    const r = await api("build_log", {job: K.job, since: K.next});
    K.lines.push(...r.lines); K.next = r.next; K.done = r.done; K.code = r.code;
  } catch (e) { K.done = true; K.lines.push(String(e.message)); }
  const log = document.getElementById("kit-log");
  if (log) log.textContent = K.lines.join("\n");
  if (!K.done) K.timer = setTimeout(kitPoll, 400);
  else {
    toast(K.code === 0 ? "Set up: done" : "Set up stopped: see its log", K.code === 0 ? "info" : "error");
    await loadDeploy(true);
    render();
  }
}

function kitCard() {
  const k = D.data.kit;
  const field = game => {
    const v = K.draft[game] ?? (k[game] || k.found[game] || "");
    const verdict = h("div");
    const check = async val => {
      try { K.checks[game] = await api("kit_check", {game, path: val}); } catch (e) { K.checks[game] = {ok: false, problems: [e.message], notes: []}; }
      fill(verdict, status(K.checks[game]));
    };
    let timer;
    const input = h("input.mono.path", {value: v, spellcheck: "false", "data-key": "kit-" + game, placeholder: game === "mania" ? "(optional)" : "",
      oninput: e => { K.draft[game] = e.target.value; clearTimeout(timer); timer = setTimeout(() => check(e.target.value), 250); }});
    if (v) check(v);
    const ready = game === "origins" ? k.ready_origins : k.ready_mania;
    return h("div.kitfield",
      h("div.row.spread", h("h4", game === "origins" ? "Sonic Origins" : "Sonic Mania"),
        badge(ready ? "set up" : "not set up", ready ? "yes" : "no", ready ? (k[game] || "") : "")),
      h("p.hint", KIT_WHAT[game]), input, verdict);
  };
  const go = async () => {
    const o = (K.draft.origins ?? (k.origins || k.found.origins || "")).trim();
    const m = (K.draft.mania ?? (k.mania || k.found.mania || "")).trim();
    try {
      const r = await api("kit_setup", {origins: o || null, mania: m || null});
      Object.assign(K, {job: r.job, lines: [], done: false, code: null, next: 0});
      kitPoll();
      render();
    } catch (e) { toast(e.message, "error"); }
  };
  return h("section.card.kit",
    h("h3", "Set up the Creator Kit"),
    h("p.hint", "First time only (and after a game update): the kit takes the game files its build needs from your own games, into its data folder ",
      h("span.mono", k.root), ". Your games are only read, never changed. The kit ships none of SEGA's files."),
    h("p.hint", "Characters you build here are for the NoSwap core ", h("b", (k.core.origins || {}).version || "?"),
      " (Origins) and the NoSwap Mania mod ", h("b", (k.core.mania || {}).version || "?"), ": players need those installed. Your characters are in ",
      h("span.mono", k.characters), "; what Build makes to install, in ", h("span.mono", k.output), "."),
    h("div.cols", field("origins"), field("mania")),
    h("div.row", h("button.primary", {onclick: go, disabled: !K.done}, K.done ? "Set up" : "Setting up…"),
      h("span.hint", "About 10 seconds; it extracts about 100 MB.")),
    K.job ? h("pre.log#kit-log", K.lines.join("\n")) : null);
}

function status(c) {
  if (!c) return null;
  return h("div.verdict",
    c.ok ? h("p.ok", "✓ looks right") : c.problems.map(p => h("p.bad", "✗ " + p)),
    (c.notes || []).map(n => h("p.hint", "· " + n)));
}

const KIT_TITLE = {origins: "Install into Sonic Origins: HedgeModManager's mods folder", mania: "Install into Sonic Mania: the decomp's play folder"};
const KIT_DEPLOY = {
  origins: "Deploy copies each character you build into this folder as its own mod (NoSwap-<Name>), beside the NoSwap core mod; then enable it in HedgeModManager. Nothing to set: it's the mods folder of the Sonic Origins you set up above (<Sonic Origins>/build/main/projects/exec/mods). Save a folder here only to install somewhere else; the game's own folder works too (its mods folder is used).",
  mania: "Deploy copies each character you build into its mods/ folder as its own mod and enables it in mods/modconfig.ini (the NoSwap Mania mod must be there too). Nothing to set if the Sonic Mania folder you set up above is the decompilation's play folder (with RSDKv5U and Data.rsdk); if you set up from Steam's Sonic Mania, save the decompilation's play folder here.",
};

function folderCard(game) {
  const t = D.data.targets[game];
  const isKit = !!D.data.kit;
  const key = game;
  const draft = D.draft[key] ?? t.path;
  const verdict = h("div");
  const check = async v => {
    try { D.checks[key] = await api("check_folder", {game, path: v}); } catch (e) { D.checks[key] = {ok: false, problems: [e.message], notes: []}; }
    fill(verdict, status(D.checks[key]));
  };
  let timer;
  const input = h("input.mono.path", {value: draft, spellcheck: "false", "data-key": "deploy-" + game,
    oninput: e => { D.draft[key] = e.target.value; clearTimeout(timer); timer = setTimeout(() => check(e.target.value), 250); }});
  fill(verdict, status(D.draft[key] !== undefined && D.checks[key] ? D.checks[key] : t));
  const save = async v => {
    try {
      D.data = await api("set_deploy_settings", {[game]: v});
      delete D.draft[key]; delete D.checks[key];
      toast(v ? `Saved: ${game === "origins" ? "Origins" : "Mania"} deploys to ${v}` : "Cleared: detection picks the folder");
      render();
    } catch (e) { toast(e.message, "error"); }
  };
  const fromSettings = t.source === "settings";
  return h("section.card.folder",
    h("div.row.spread", h("h3", (isKit ? KIT_TITLE : TITLE)[game]), badge(fromSettings ? "set" : "detected", fromSettings ? "yes" : "plain", t.source)),
    h("p.hint", (isKit ? KIT_DEPLOY : WHAT)[game]),
    h("div.row", input,
      h("button.primary", {onclick: () => save(input.value.trim()), title: "Save this folder (empty: back to detection)"}, "Save"),
      fromSettings ? h("button", {onclick: () => save(""), title: "Forget the setting: detection picks the folder again"}, "Use detected") : null),
    h("p.hint", "Now: ", h("span.mono", t.path), " (", t.source, ")"),
    verdict,
    h("details", {open: true}, h("summary", "Detected on this machine"),
      h("div.cands", t.candidates.map(c => h("div.cand",
        h("span.badge." + (c.ok ? "yes" : "no"), c.ok ? "ok" : "no"),
        h("span.mono.small", c.path),
        h("span.hint", c.source + (c.ok ? "" : ": " + c.problems.join("; "))),
        c.path !== t.path ? h("button.small", {onclick: () => save(c.path)}, "Use") : h("span.hint", "(in use)"))))));
}

export function runningBanner(games = ["origins", "mania"]) {
  if (!D.data) return null;
  const run = D.data.running.filter(p => games.includes(p.game));
  if (!run.length) return null;
  return h("p.warn.banner", "⚠ Running now: ", run.map(p => `${p.name} (pid ${p.pid})`).join(", "),
    `. A deploy still goes ahead, but ${D.data.restart}.`);
}

function render() {
  if (S.tab !== "settings") return;
  const main = document.getElementById("main");
  main.replaceChildren();
  renderSettings(main);
}

export function renderSettings(main) {
  const page = h("div.page.settings", h("h2", "Settings"));
  main.append(page);
  if (!D.data) {
    page.append(h("p.muted", "Looking for the games…"));
    loadDeploy().then(render, e => toast(e.message, "error"));
    return;
  }
  fill(page, h("h2", "Settings"),
    D.data.kit ? kitCard() : null,
    D.data.kit ? h("h3", "Where Deploy installs") : null,
    h("p.hint", "Where Deploy (Build tab, or the deploy command) copies the built mods. Saved in ",
      h("span.mono", D.data.file), D.data.file_exists ? "" : " (not made yet: both folders are detected)", D.data.kit ? "." : ", outside the repo."),
    runningBanner(),
    h("div.cols", folderCard("origins"), folderCard("mania")),
    h("div.row", h("button", {onclick: async () => { await loadDeploy(true); D.draft = {}; D.checks = {}; render(); }}, "Detect again")));
}

S.renderers.settings = renderSettings;
