// The Build tab: runs `noswap build` (check first, then the pipeline under the build lock), `noswap deploy` (copy the
// built mods into Origins and/or the Mania decomp: the folders are on the Settings tab), or both in a row (the deploy
// runs only if the build succeeded). The output is streamed.
import {S, fill, h, api, toast, go, GAME_NAMES} from "./core.js";
import {D, loadDeploy, runningBanner} from "./settings.js";

const B = {games: {s1: true, s2: true, cd: true, s3k: true, mania: true}, dry: true, job: null, kind: "", lines: [], done: true, code: null, next: 0, timer: null, cmd: "",
  targets: {origins: true, mania: true}, ddry: false};

async function start(method, args) {
  try {
    const r = await api(method, args);
    Object.assign(B, {job: r.job, kind: method, lines: [], done: false, code: null, next: 0, cmd: r.cmd});
    if (r.dirty && method !== "deploy") toast("Unsaved changes aren't in this build: it reads the saved character.json.", "error");
    poll();
  } catch (e) { toast(e.message, "error"); }
  render();
}

const targets = () => Object.keys(B.targets).filter(t => B.targets[t]);

async function poll() {
  clearTimeout(B.timer);
  if (!B.job) return;
  try {
    const r = await api("build_log", {job: B.job, since: B.next});
    B.lines.push(...r.lines); B.next = r.next; B.done = r.done; B.code = r.code; B.seconds = r.seconds; B.step = r.step; B.steps = r.steps;
  } catch (e) { B.done = true; B.lines.push(String(e.message)); }
  const log = document.getElementById("build-log");
  if (log) {
    const atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
    log.textContent = B.lines.join("\n");
    if (atEnd) log.scrollTop = log.scrollHeight;
    renderState();
  }
  if (!B.done) B.timer = setTimeout(poll, 400);
  else if (B.kind !== "build") loadDeploy(true).then(() => S.tab === "build" && renderTargets());
}

const WHY = {
  build: {1: "the check found errors", 2: "bad usage", 3: "a build step failed"},
  deploy: {1: "a folder isn't set up (Settings tab)", 2: "bad usage", 3: "copying failed"},
};

function renderState() {
  const s = document.getElementById("build-state");
  if (!s) return;
  const what = B.kind === "deploy" ? "Deploy" : B.kind === "build_deploy" ? "Build & deploy" : "Build";
  const why = (B.kind === "deploy" || (B.kind === "build_deploy" && B.step === 1) ? WHY.deploy : WHY.build)[B.code];
  const failedBuild = B.kind === "build_deploy" && B.step === 0 && B.code;
  fill(s, !B.job ? h("span.muted", "Not run yet.")
    : !B.done ? h("span.running", `${what}: running${B.steps > 1 ? ` (step ${B.step + 1} of ${B.steps}: ${B.step ? "deploy" : "build"})` : ""}… ${B.seconds || 0} s`)
    : B.code === 0 ? h("span.ok", `${what}: finished OK`)
    : h("span.bad", `${what}: stopped, exit ${B.code}${why ? ` (${why})` : ""}${failedBuild ? ": nothing was deployed" : ""}`));
  const busy = !B.done;
  for (const id of ["build-go", "deploy-go", "build-deploy-go"]) {
    const b = document.getElementById(id);
    if (b) b.disabled = busy || (id !== "deploy-go" && !S.info) || (id !== "build-go" && !targets().length);
  }
  const stop = document.getElementById("build-stop");
  if (stop) stop.disabled = B.done;
}

function render() {
  const main = document.getElementById("main");
  if (S.tab !== "build") return;
  main.replaceChildren();
  renderBuild(main);
}

function targetLine(game) {
  const t = D.data && D.data.targets[game];
  return h("label.check.target", h("input", {type: "checkbox", checked: B.targets[game], onchange: e => { B.targets[game] = e.target.checked; renderState(); }}),
    h("span", game === "origins" ? "Sonic Origins" : "Sonic Mania"),
    !t ? h("span.hint", "…")
      : h("span.small", h("span.mono", t.path), " ", t.ok ? h("span.ok", "✓") : h("span.bad", "✗ " + t.problems.join("; ")), h("span.hint", ` (${t.source})`)));
}

function renderTargets() {
  const box = document.getElementById("deploy-targets");
  if (!box) return;
  fill(box, targetLine("origins"), targetLine("mania"), runningBanner(targets()));
}

export function renderBuild(main) {
  if (S.kit && !B.kitDefaults) { B.dry = false; B.kitDefaults = true; }  // (the kit: a real build by default)
  const buildCard = !S.info
    ? h("section.card", h("h3", "Build a character"), h("p.muted", "Open a character to build it. Deploy (below) works without one: it copies what's already built in mods/."))
    : h("section.card",
      h("h3", "Build ", h("span.hint", S.info.doc.full_name || S.info.doc.name || S.info.id)),
      S.kit
        ? h("p.hint", "The check first (stops on errors), then the art and the scripts for the Origins games (always all four together) and the Mania package. What to install lands in ",
            h("span.mono", S.kit.output + "/" + S.info.id), ": a mod for each game, as a folder and a zip to share. Build alone copies nothing into the games.",
            !S.kit.ready_origins ? h("span.bad", " Origins isn't set up yet (Settings tab).") : null,
            !S.kit.ready_mania ? h("span.hint", " Mania isn't set up (Settings tab): untick Mania, or set it up.") : null)
        : h("p.hint", "Runs the same pipeline as python3 tools/noswap.py build: the check first (stops on errors), then the art and the game scripts for the Origins games (always all four together, under the build lock), and the Mania package. The output lands in mods/; Build alone copies nothing into the game."),
      h("div.checks", Object.keys(B.games).map(g => h("label.check", h("input", {type: "checkbox", checked: B.games[g], onchange: e => { B.games[g] = e.target.checked; }}), h("span", GAME_NAMES[g])))),
      h("label.check", h("input", {type: "checkbox", checked: B.dry, onchange: e => { B.dry = e.target.checked; }}), h("span", "dry run (only print the steps)")),
      h("div.row", h("button.primary#build-go", {onclick: () => start("build", {games: Object.keys(B.games).filter(g => B.games[g]), dry_run: B.dry})}, "Build")),
      h("p.hint", "Build lock: ", h("span.mono", S.lock || "")),
      S.info.dirty ? h("p.warn", "You have unsaved changes: save first, the build reads the saved file.") : null);
  const deployCard = h("section.card",
    h("h3", "Deploy to the games"),
    h("p.hint", S.kit
      ? "Installs the open character's built mods into the games, each as its own mod beside the NoSwap core (Origins: then enable it in HedgeModManager; Mania: enabled in mods/modconfig.ini). The folders are on the "
      : "Copies what's built in mods/ into the games, as python3 tools/noswap.py deploy: Origins gets mods/NoSwap mirrored into HedgeModManager's mods folder; Mania gets mods/NoSwapMania symlinked and enabled. The folders are on the ",
      h("a", {href: "#settings", onclick: e => { e.preventDefault(); go("settings"); }}, "Settings tab"), ". Both games load the DLL and scripts at startup: restart a running game afterwards."),
    h("div.targets#deploy-targets"),
    h("label.check", h("input", {type: "checkbox", checked: B.ddry, onchange: e => { B.ddry = e.target.checked; }}), h("span", "dry run (say what would change; write nothing)")),
    h("div.row",
      h("button.primary#deploy-go", {onclick: () => start("deploy", {targets: targets(), dry_run: B.ddry})}, "Deploy"),
      h("button#build-deploy-go", {title: S.info ? "Build the open character for the ticked games, then deploy them: only if the build succeeded" : "Open a character first",
        onclick: () => start("build_deploy", {targets: targets(), dry_run: B.ddry})}, "Build & deploy"),
      h("span.hint", S.info ? "Build & deploy builds the open character for the ticked games, then deploys; a failed build deploys nothing." : "Build & deploy needs an open character.")));
  main.append(h("div.page.build",
    h("h2", "Build & deploy"),
    h("div.cols", buildCard, deployCard),
    h("div.row.logbar", h("button#build-stop", {onclick: async () => { await api("build_stop", {job: B.job}); }}, "Stop"), h("span#build-state"),
      h("span.hint.mono", B.cmd ? "$ " + B.cmd : "")),
    h("pre.log#build-log", {"data-scroll": "log"}, B.lines.join("\n"))));
  renderState();
  renderTargets();
  if (!D.data) loadDeploy().then(renderTargets, e => toast(e.message, "error"));
}

S.renderers.build = renderBuild;
