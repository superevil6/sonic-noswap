// The Check panel: `noswap check` on the saved file, after each save (debounced) or on demand. Each finding links to
// the place it's about.
import {S, fill, h, api, go} from "./core.js";

let timer = null, running = false, again = false;

export function scheduleCheck(delay = 600) {
  clearTimeout(timer);
  timer = setTimeout(runCheck, delay);
}

export async function runCheck() {
  if (!S.info) return;
  if (running) { again = true; return; }
  running = true;
  fill(document.getElementById("check-counts"), h("span.muted.small", "checking…"));
  try { S.check = await api("check"); }
  catch (e) { S.check = {items: [{level: "error", where: "check", msg: e.message}], counts: {error: 1, warning: 0, note: 0}}; }
  running = false;
  renderCheck();
  if (again) { again = false; runCheck(); }
}

export function renderCheck() {
  const body = document.getElementById("check-body"), counts = document.getElementById("check-counts");
  const c = S.check;
  if (!c) return;
  const notes = document.getElementById("check-notes").checked;
  fill(counts, 
    h("span.badge." + (c.counts.error ? "no" : "plain"), {title: "errors"}, `${c.counts.error} ✖`),
    h("span.badge." + (c.counts.warning ? "partial" : "plain"), {title: "warnings"}, `${c.counts.warning} ⚠`),
    h("span.badge.plain", {title: "notes"}, `${c.counts.note} i`));
  const items = c.items.filter(i => notes || i.level !== "note");
  fill(body, 
    c.dirty ? h("p.warn.small", "Checked the saved file: save to check your latest changes.") : null,
    !items.length ? h("p.ok", c.counts.error + c.counts.warning ? "" : "All clear: no errors or warnings.") : null,
    items.map(i => h("div.finding." + i.level + (i.target ? ".link" : ""), {
      title: i.target ? "show it" : "", onclick: () => { if (i.target) { const {tab, ...sel} = i.target; if (sel.frame) sel.scrollTo = true; go(tab, sel); } }},
      h("div.where", h("span.lvl", i.level), " ", i.where),
      h("div.msg", i.msg),
      i.fix ? h("div.fix", "fix: ", i.fix) : null)));
}
