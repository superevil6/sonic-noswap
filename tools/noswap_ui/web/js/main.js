// Start-up, the top bar (open, new, save, revert), tabs and keyboard shortcuts.
import {S, fill, h, api, rerender, updateTop, toast, modal, closeModal, go} from "./core.js";
import "./character.js";
import "./sheet.js";
import "./anims.js";
import "./abilities.js";
import "./palette.js";
import "./hud.js";
import "./build.js";
import "./settings.js";
import {runCheck, scheduleCheck, renderCheck} from "./check.js";

async function openFolder(folder) {
  try {
    S.info = await api("open", {folder});
    S.check = null;
    S.sel = {frame: null, section: "animations", anim: "Stopped"};
    updateTop(); rerender(); closeModal();
    runCheck();
    const rn = S.info.renamed || [];  // (older names, migrated on open: popgun_reach is now melee_reach...)
    if (rn.length) toast(`Renamed: ${rn.map(r => `${r.old} is now ${r.new}`).join(", ")}. Save writes the new names.`);
    try { localStorage.setItem("noswap.last", folder); } catch { /* */ }
  } catch (e) { toast(e.message, "error"); }
}

async function save(force = false) {
  if (!S.info) return;
  try {
    const r = await api("save", {force});
    S.info = r;
    updateTop(); rerender();
    toast(r.saved ? `Saved ${r.path}${r.backup ? ` (the old file is backed up in ${r.backup})` : ""}` : "Nothing to save.");
    scheduleCheck(300);
  } catch (e) {
    if (!force && e.message.includes("changed on disk") && confirm(e.message + "\n\nOverwrite it with your version?")) return save(true);
    toast(e.message, "error");
  }
}

async function revert() {
  if (!S.info || !S.info.dirty) return;
  if (!confirm("Throw away your unsaved changes?")) return;
  try { S.info = await api("revert"); updateTop(); rerender(); toast("Back to the saved file."); } catch (e) { toast(e.message, "error"); }
}

// A small file browser (browser mode has no native dialogs).
function browser(start, {pickFile = false, onPick}) {
  const box = h("div.browser");
  const load = async path => {
    let r;
    try { r = await api("ls", {path}); } catch (e) { toast(e.message, "error"); return; }
    fill(box, 
      h("div.row", h("button.small", {onclick: () => load(r.parent)}, "↑ up"), h("input.mono", {value: r.path, style: {flex: 1},
        onkeydown: e => { if (e.key === "Enter") load(e.target.value); }})),
      h("div.list.browse", r.dirs.map(d => h("div.item", {ondblclick: () => d.character && !pickFile ? onPick(d.path) : load(d.path), onclick: () => load(d.path)},
          h("span", "📁 " + d.name), d.character ? h("span.badge.yes", "character") : null,
          d.character && !pickFile ? h("button.small", {onclick: e => { e.stopPropagation(); onPick(d.path); }}, "Open") : null)),
        pickFile ? r.files.map(f => h("div.item", {onclick: () => onPick(f.path)}, h("span", "🖼 " + f.name))) : null),
      !pickFile ? h("div.row", h("button", {onclick: () => onPick(r.path)}, "Use this folder")) : null);
  };
  load(start);
  return box;
}

async function openDialog() {
  let chars = [];
  try { chars = (await api("characters")).characters; } catch (e) { toast(e.message, "error"); }
  let q = "";
  const list = h("div.list.chars");
  const refresh = () => fill(list, ...chars.filter(c => !q || (c.id + c.name + c.full_name + c.key).toLowerCase().includes(q))
    .map(c => h("div.item", {onclick: () => openFolder(c.folder)}, h("b", c.full_name || c.name), h("span.muted.mono.small", c.key), h("span.muted.small", c.folder))));
  refresh();
  let last = null;
  try { last = localStorage.getItem("noswap.last"); } catch { /* */ }
  modal(h("div",
    h("div.row.spread", h("h2", "Open a character"), h("button", {onclick: closeModal}, "Close")),
    h("input", {placeholder: "filter…", oninput: e => { q = e.target.value.toLowerCase(); refresh(); }}),
    h("p.hint", "Characters the build finds (testmods/*/character.json and $NOSWAP_CHARACTER_DIRS):"),
    list,
    h("details", h("summary", "Another folder…"), browser(last || S.info?.folder || null, {onPick: openFolder}))), {wide: true});
}

function newDialog() {
  const f = {sheet: "", parent: "", key: "", id: "", name: "", full_name: "", artists: "", base: "sonic"};
  let idTouched = false;
  const input = (k, attrs = {}) => h("input" + (attrs.mono ? ".mono" : ""), {value: f[k], placeholder: attrs.placeholder, "data-f": k,
    oninput: e => {
      f[k] = e.target.value;
      if (k === "id") idTouched = true;
      if (k === "key" && !idTouched) {
        const [creator, ch] = f.key.split(".");
        f.id = (ch ? `${creator}-${ch}` : creator || "").toLowerCase().replace(/[^a-z0-9-]/g, "-");
        document.querySelector('[data-f="id"]').value = f.id;
      }
    }});
  const sheetBox = h("div");
  const parentBox = h("div");
  const sheetLabel = h("span.mono.small", "(none yet)"), parentLabel = h("span.mono.small", "testmods/ (found by the build automatically)");
  modal(h("div.newchar",
    h("div.row.spread", h("h2", "New character from a sheet"), h("button", {onclick: closeModal}, "Close")),
    h("p.hint", "This makes a folder with a copy of your sheet (unchanged) and a character.json to fill in. The Check panel then lists what's left: frames, animations, HUD art."),
    h("div.form",
      h("label.field", h("span.label", "sprite sheet"), h("div.row", sheetLabel, h("button.small", {onclick: () => fill(sheetBox, browser(null, {pickFile: true, onPick: p => { f.sheet = p; sheetLabel.textContent = p; sheetBox.replaceChildren(); }}))}, "Choose…"), sheetBox)),
      h("label.field", h("span.label", "key"), input("key", {mono: true, placeholder: "creator.character, e.g. someone.newchar"}), h("span.hint", "Permanent: saves hang on it.")),
      h("label.field", h("span.label", "id (folder)"), input("id", {mono: true, placeholder: "creator-character"}), h("span.hint", "Lower case; pick something distinctive (Mania keys saves by folder).")),
      h("label.field", h("span.label", "in-game name"), input("name", {placeholder: "BEAN"}), h("span.hint", "Capitals, up to 16.")),
      h("label.field", h("span.label", "full name"), input("full_name", {placeholder: "Bean the Dynamite"})),
      h("label.field", h("span.label", "artists"), input("artists", {placeholder: "comma-separated"}), h("span.hint", "Whoever drew the sheet: credit them as they ask.")),
      h("label.field", h("span.label", "base"), h("select", {onchange: e => f.base = e.target.value}, ["sonic", "tails", "knuckles"].map(b => h("option", {value: b}, b))), h("span.hint", "Whose moveset and animation list he plays on.")),
      h("label.field", h("span.label", "where"), h("div.row", parentLabel, h("button.small", {onclick: () => fill(parentBox, browser(null, {onPick: p => { f.parent = p; parentLabel.textContent = p; parentBox.replaceChildren(); }}))}, "Choose…"), parentBox))),
    h("div.row", h("button.primary", {onclick: async () => {
      try {
        S.info = await api("new_character", f);
        S.check = null; S.sel = {frame: null, section: "animations", anim: "Stopped"};
        closeModal(); updateTop(); go("sheet"); runCheck();
        toast("Made it. Start by drawing frames on the sheet (Draw frame, R).");
      } catch (e) { toast(e.message, "error"); }
    }}, "Make it"))), {wide: true});
}

document.getElementById("btn-open").onclick = openDialog;
document.getElementById("btn-new").onclick = newDialog;
document.getElementById("btn-save").onclick = () => save();
document.getElementById("btn-revert").onclick = revert;
document.getElementById("btn-check").onclick = runCheck;
document.getElementById("check-notes").onchange = renderCheck;
document.getElementById("btn-fold").onclick = () => {
  document.body.classList.toggle("folded");
  try { localStorage.setItem("noswap.folded", document.body.classList.contains("folded") ? "1" : ""); } catch { /* */ }
};
try { if (localStorage.getItem("noswap.folded")) document.body.classList.add("folded"); } catch { /* */ }
window.addEventListener("noswap-open", openDialog);
window.addEventListener("noswap-new", newDialog);
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => go(b.dataset.tab));
document.getElementById("modal").addEventListener("mousedown", e => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); save(); }
  else if (e.key === "Escape" && !document.getElementById("modal").hidden) closeModal();
  else if (e.altKey && /^[1-8]$/.test(e.key)) { const tabs = [...document.querySelectorAll("#tabs button")]; go(tabs[+e.key - 1].dataset.tab); e.preventDefault(); }
});
window.addEventListener("beforeunload", e => { if (S.info && S.info.dirty) { e.preventDefault(); e.returnValue = ""; } });

clearTimeout(window.__noswapBoot);  // (index.html's "scripts blocked?" note: the modules did load)
(async () => {
  try {
    const [st, schema] = await Promise.all([api("state"), api("schema")]);
    S.schema = schema;
    S.lock = st.build_lock;
    S.kit = st.kit;  // (the Creator Kit's setup; null in the repo)
    S.info = st.open;
    if (S.kit && !S.kit.ready_origins && !S.kit.ready_mania && !location.hash) S.tab = "settings";
    // #tab or #tab?frame=NAME&section=...&anim=... (handy for links and screenshots)
    const [tab, q] = location.hash.slice(1).split("?");
    if (tab) S.tab = tab;
    if (q) for (const [k, v] of new URLSearchParams(q)) S.sel[k] = v;
    if (S.sel.frame) S.sel.scrollTo = true;
  } catch (e) { toast(e.message, "error"); }
  updateTop();
  rerender();
  if (S.info) runCheck();
  if (S.sel.dialog === "open") openDialog();
  if (S.sel.dialog === "new") newDialog();
})();
