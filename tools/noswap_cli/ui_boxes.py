"""`noswap check`: does a character's built UI art grow a shared UI box? (noswap_common.UiSheets: each box is the union of
every extra's art for that element, so one larger mini / ending pose / icon grows every package's UI sheets and the
shared UI scripts' frames.) Reads the art the last build_art wrote (the Extra<n>_ui.json / _ending.json manifests);
skipped before the first build."""


def growth(extra):
    """[(game, sheet, element, the box without him, his span)] for each element of his that reaches past the box the
    other extras make (UI_RESERVE included)."""
    import build_sonic1
    import build_sonic2
    import build_soniccd
    from extras import EXTRAS
    from noswap_common import UI_RESERVE
    cases = [("Sonic 1", build_sonic1.UI_SHEETS, build_sonic1.element_image, build_sonic1.element_pivot),
             ("Sonic 2", build_sonic2.UI_SHEETS, build_sonic2.s2_element, build_sonic2.element_pivot),
             ("Sonic CD", {build_soniccd.SCORE_SHEETS[0]: build_soniccd.MINI_KEYS}, build_soniccd.mini_art,
              build_soniccd.mini_pivot)]
    out = []
    for game, sheets, art, pivot in cases:
        for sheet, keys in sheets.items():
            for k in keys:
                spans = []
                for e in EXTRAS:
                    if e["n"] == extra["n"]:
                        continue
                    try:
                        im = art(k, e)
                    except (OSError, SystemExit, KeyError, ValueError):
                        continue  # (a character not built yet: left out)
                    spans.append((pivot(k, im), im.size))
                if k in UI_RESERVE:
                    rl, rt, rr, rb = UI_RESERVE[k]
                    spans.append(((rl, rt), (rr - rl, rb - rt)))
                if not spans:
                    continue
                box = (min(p[0] for p, _ in spans), min(p[1] for p, _ in spans),
                       max(p[0] + s[0] for p, s in spans), max(p[1] + s[1] for p, s in spans))
                im = art(k, extra)
                (x, y), (w, h) = pivot(k, im), im.size
                if x < box[0] or y < box[1] or x + w > box[2] or y + h > box[3]:
                    out.append((game, sheet, k, (box[2] - box[0], box[3] - box[1]), (w, h)))
    return out


def check(ch, r):
    e = ch.extra
    if e is None or not (e["art"] / f"{e['file']}_ui.json").exists():
        return
    for game, sheet, k, (bw, bh), (w, h) in growth(e):
        r.warn(f"ui {k}", f"{game} {sheet}: his {w}x{h} art reaches past the shared {bw}x{bh} box: it grows every "
               "package's UI sheets and the shared UI scripts",
               "pick or crop a smaller frame for it (one that fits the box; tools/noswap_common.py UiSheets)")
