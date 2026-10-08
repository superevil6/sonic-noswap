"""Save a JSON document by editing its file's text as little as possible.

Hand-written character.json files (Bean's) have a layout of their own: several frames to a line, blank lines between
sections. Re-serialising the whole file would reformat all of it. Instead, update() walks the old and new documents
together and changes only the text of what changed:

  - a changed value (a number, a rect, a list) is replaced where it stands;
  - a new key is added after the object's last entry, in the same layout as that entry (same line or a new one);
  - a removed key is cut out with its comma;
  - a renamed key keeps its place;
  - anything else (a reordered object, a list that changed length) re-writes just that object or list with
    noswap_cli.convert.pretty, NoSwap's style for generated files.

The result is parsed again and must equal the new document exactly, key order included; if it doesn't (a case this
module doesn't know), the whole file is written with pretty() instead.
"""
import json
import re

from noswap_cli.convert import pretty

_WS = re.compile(r"[ \t\n\r]*")
_STR = re.compile(r'"(?:[^"\\]|\\.)*"')
_NUM = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")


class Node:
    __slots__ = ("start", "end", "kind", "items")

    def __init__(self, start, end, kind, items=None):
        self.start, self.end, self.kind, self.items = start, end, kind, items
        # items: object -> [(key, key_start, key_end, Node)], array -> [Node]


def parse(text):
    """The document's layout: a Node per value with its span in the text."""
    pos = _WS.match(text, 0).end()
    node, pos = _value(text, pos)
    return node


def _value(t, i):
    c = t[i]
    if c == "{":
        start, items, i = i, [], _WS.match(t, i + 1).end()
        if t[i] == "}":
            return Node(start, i + 1, "object", items), i + 1
        while True:
            m = _STR.match(t, i)
            key = json.loads(m.group())
            i = _WS.match(t, m.end()).end()
            assert t[i] == ":"
            i = _WS.match(t, i + 1).end()
            v, i = _value(t, i)
            items.append((key, m.start(), m.end(), v))
            i = _WS.match(t, i).end()
            if t[i] == ",":
                i = _WS.match(t, i + 1).end()
                continue
            assert t[i] == "}"
            return Node(start, i + 1, "object", items), i + 1
    if c == "[":
        start, items, i = i, [], _WS.match(t, i + 1).end()
        if t[i] == "]":
            return Node(start, i + 1, "array", items), i + 1
        while True:
            v, i = _value(t, i)
            items.append(v)
            i = _WS.match(t, i).end()
            if t[i] == ",":
                i = _WS.match(t, i + 1).end()
                continue
            assert t[i] == "]"
            return Node(start, i + 1, "array", items), i + 1
    if c == '"':
        m = _STR.match(t, i)
        return Node(i, m.end(), "scalar"), m.end()
    for word in ("true", "false", "null"):
        if t.startswith(word, i):
            return Node(i, i + len(word), "scalar"), i + len(word)
    m = _NUM.match(t, i)
    return Node(i, m.end(), "scalar"), m.end()


def _indent(t, pos):
    line = t.rfind("\n", 0, pos) + 1
    return len(t[line:pos]) - len(t[line:pos].lstrip(" "))


def _dump(v, t, pos, width=118):
    """pretty() at the value's place; a list of plain values too long for one line wraps with its items aligned
    under the first (as hand-written frame lists are)."""
    flat = json.dumps(v, ensure_ascii=False, separators=(", ", ": "))
    col = pos - (t.rfind("\n", 0, pos) + 1)
    if isinstance(v, list) and v and all(not isinstance(x, (dict, list)) for x in v) and col + len(flat) > width:
        lines, line = [], ""
        for x in v:
            item = json.dumps(x, ensure_ascii=False)
            if line and col + 1 + len(line) + len(item) + 2 > width:
                lines.append(line.rstrip())
                line = ""
            line += item + ", "
        lines.append(line.rstrip().rstrip(","))
        return "[" + ("\n" + " " * (col + 1)).join(lines) + "]"
    return pretty(v, _indent(t, pos))


def _edits(t, node, old, new, out):
    """Text edits [(start, end, replacement)] turning old (laid out as node) into new."""
    if old == new and type(old) is type(new) and json.dumps(old) == json.dumps(new):
        return
    if node.kind == "object" and isinstance(old, dict) and isinstance(new, dict) and node.items:
        ok, nk = list(old), list(new)
        kept = [k for k in ok if k in new]
        if sorted(ok) != sorted(nk) and len(ok) == len(nk):  # (a key renamed in place?)
            gone = [k for k in ok if k not in new]
            came = [k for k in nk if k not in old]
            if len(gone) == 1 and len(came) == 1 and [came[0] if k == gone[0] else k for k in ok] == nk:
                for k, ks, ke, child in node.items:
                    if k == gone[0]:
                        out.append((ks, ke, json.dumps(came[0], ensure_ascii=False)))
                        _edits(t, child, old[k], new[came[0]], out)
                    else:
                        _edits(t, child, old[k], new[k], out)
                return
        if [k for k in nk if k in old] == kept and kept:  # (same order for the keys both have: edit in place)
            added = [k for k in nk if k not in old]
            if added and added != nk[len(nk) - len(added):]:  # (inserted in the middle: re-write the object)
                out.append((node.start, node.end, _dump(new, t, node.start)))
                return
            local = []
            for idx, (k, ks, ke, child) in enumerate(node.items):
                if k not in new:
                    if idx > 0:  # from the end of the entry before it
                        local.append((node.items[idx - 1][3].end, child.end, ""))
                    else:  # the first entry: up to the next one's key
                        local.append((ks, node.items[idx + 1][1], ""))
                else:
                    _edits(t, child, old[k], new[k], local)
            if added:
                last = max((it for it in node.items if it[0] in new), key=lambda it: it[3].end)
                ks0 = last[1]
                line_start = t.rfind("\n", 0, ks0) + 1
                own_line = t[line_start:ks0].strip() == ""
                sep = ",\n" + " " * _indent(t, ks0) if own_line else ", "
                text = "".join(f"{sep}{json.dumps(k, ensure_ascii=False)}: {pretty(new[k], _indent(t, ks0))}" for k in added)
                local.append((last[3].end, last[3].end, text))
            out.extend(local)
            return
    if node.kind == "array" and isinstance(old, list) and isinstance(new, list) and len(old) == len(new) and node.items:
        for child, a, b in zip(node.items, old, new):
            _edits(t, child, a, b, out)
        return
    out.append((node.start, node.end, _dump(new, t, node.start)))


def update(text, new):
    """The file's text with `new` written into it, changing as little of the text as possible."""
    try:
        old = json.loads(text)
        node = parse(text)
        out = []
        _edits(text, node, old, new, out)
        for start, end, rep in sorted(out, key=lambda e: e[0], reverse=True):
            text = text[:start] + rep + text[end:]
        if json.dumps(json.loads(text)) == json.dumps(new):
            return text
    except (AssertionError, IndexError, ValueError, AttributeError):
        pass
    return pretty(new) + "\n"
