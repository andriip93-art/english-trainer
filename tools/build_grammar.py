#!/usr/bin/env python3
"""Builds grammar.json (Mode 8, Business Grammar) from the adapted textbook in markdown.

    python3 tools/build_grammar.py SOURCE.md [UNIT ...]     # default: units already present in grammar.json, else 1

The rules are turned into a small, safe HTML subset (everything is escaped first). Exercises are parsed into typed items and the
keys are matched to them, so a unit that does not parse cleanly stops the build with a clear message instead of shipping a
broken key. Item types: choose, type, place, fix. Other exercise kinds raise NotImplementedError for now.
"""
import html, json, re, sys, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grammar.json")

# ---------- rules: markdown subset -> HTML ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r'<i class="ex">\1</i>', s)
    return s

def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[2:]]
    t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
    for r in body:
        t += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
    return t + "</tbody></table>"

def md_html(lines):
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            out.append(table(lines[i:j])); i = j
        elif re.match(r"\s*[-*] ", ln):
            items = []
            while i < len(lines) and re.match(r"\s*[-*] ", lines[i]):
                items.append(re.sub(r"^\s*[-*] ", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
        elif re.match(r"\s*\d+\. ", ln):
            items = []
            while i < len(lines) and re.match(r"\s*\d+\. ", lines[i]):
                items.append(re.sub(r"^\s*\d+\. ", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
        elif ln.startswith(">"):
            out.append(f"<p class=\"note\">{inline(ln.lstrip('> '))}</p>"); i += 1
        else:
            out.append(f"<p>{inline(ln)}</p>"); i += 1
    return "".join(out)

def rule_sections(block):
    """Sections start with a bold lead like **A. Present Simple: форма**."""
    lines, secs, cur = block.split("\n"), [], None
    for ln in lines:
        m = re.match(r"^\*\*([A-Z]\.\s.+?)\*\*\s*$", ln)
        if m:
            cur = {"h": m.group(1), "lines": []}; secs.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
        elif ln.strip():
            cur = {"h": "", "lines": [ln]}; secs.append(cur)
    return [{"h": s["h"], "html": md_html(s["lines"])} for s in secs if "".join(s["lines"]).strip() or s["h"]]

# ---------- answers ----------
def norm(s):
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^\w' ]+", " ", s, flags=re.U)
    return re.sub(r"\s+", " ", s).strip()

def clean_key(s):
    s = s.strip()
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    return s

def split_keys(text):
    parts = [p.strip() for p in re.split(r"\s·\s", text.strip())]
    keys = {}
    for p in parts:
        m = re.match(r"^(\d+)\s+(.*)$", p, flags=re.S)
        if not m:
            raise ValueError(f"key not numbered: {p[:50]}")
        keys[int(m.group(1))] = m.group(2).strip()
    return keys

def alts_of(key):
    """'main sentence. (или *other*)' -> [main, other...]"""
    m = re.match(r"^(.*?)\s*\((?:или|or)\s+(.+)\)\s*$", key)
    if m:
        return [clean_key(m.group(1))] + [clean_key(x) for x in re.split(r"\s+/\s+|\s+или\s+", m.group(2))]
    return [clean_key(key)]

def edit_dist(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (x != y))
    return d[-1]

# ---------- exercises ----------
def parse_exercises(block):
    exs, cur = [], None
    for ln in block.split("\n"):
        m = re.match(r"^\*\*Exercise (\d+)\.\*\*\s*(.*)$", ln)
        if m:
            cur = {"n": int(m.group(1)), "h": clean_key(m.group(2)), "raw": []}; exs.append(cur)
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", ln)
        if m and cur is not None:
            cur["raw"].append((int(m.group(1)), m.group(2).strip()))
    return exs

def kind_of(h):
    if h.startswith("Choose the correct form"): return "choose"
    if h.startswith("Put the adverb"): return "place"
    if h.startswith("Find and correct"): return "fix"
    if h.startswith("Put the verb in brackets") or h.startswith("Complete"): return "type"
    raise NotImplementedError(f"exercise kind not supported yet: {h!r}")

def build_item(kind, n, q, key):
    if kind == "choose":
        m = re.search(r"\(([^()]*\s/\s[^()]*)\)", q)
        if not m: raise ValueError(f"item {n}: no (a / b) group")
        opts = [o.strip() for o in m.group(1).split(" / ")]
        k = [norm(x) for x in alts_of(key)]
        hit = [i for i, o in enumerate(opts) if norm(o) in k]
        if len(hit) != 1: raise ValueError(f"item {n}: key {key!r} does not match one of {opts}")
        return {"n": n, "t": "choose", "q": q[:m.start()] + "___" + q[m.end():], "opts": opts, "ans": hit[0]}
    if kind == "type":
        gaps = len(re.findall(r"_{3,}", q))
        parts = [p.strip() for p in alts_of(key)[0].split(" ... ")]
        if gaps == 0 or len(parts) != gaps: raise ValueError(f"item {n}: {gaps} gaps but key {key!r}")
        ans = [[p] + [] for p in parts]
        for extra in alts_of(key)[1:]:
            xs = [p.strip() for p in extra.split(" ... ")]
            if len(xs) == gaps:
                for g, x in enumerate(xs): ans[g].append(x)
        return {"n": n, "t": "type", "q": re.sub(r"_{3,}", "___", q), "ans": ans}
    if kind == "place":
        m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", q)
        if not m: raise ValueError(f"item {n}: no (adverb)")
        base, adv = m.group(1).strip(), m.group(2).strip()
        punct = re.search(r"[.?!]$", base)
        words = base[:-1].split() if punct else base.split()
        end = punct.group(0) if punct else ""
        pos = set()
        for sentence in alts_of(key):
            sentence = re.sub(r"\.{3}|…", "", sentence).strip()
            toks = re.sub(r"[.?!]+$", "", sentence).split()
            a = adv.lower().split()
            idx = [i for i in range(len(toks) - len(a) + 1) if [t.lower() for t in toks[i:i + len(a)]] == a]
            if len(idx) != 1: raise ValueError(f"item {n}: adverb {adv!r} not found once in {sentence!r}")
            pos.add(idx[0])
        return {"n": n, "t": "place", "adv": adv, "words": words, "end": end, "ans": sorted(pos)}
    if kind == "fix":
        full = alts_of(key)
        words = q.split()
        if len(full[0].split()) < max(3, len(words) - 3):          # key is only the corrected word(s)
            frag = full[0].split()
            best = None
            for i in range(len(words) - len(frag) + 1):
                seg = words[i:i + len(frag)]
                dist = sum(edit_dist(norm(a), norm(b)) for a, b in zip(seg, frag))
                if best is None or dist < best[0]: best = (dist, i)
            if best is None or best[0] > 4 * len(frag): raise ValueError(f"item {n}: cannot place fragment {key!r} into {q!r}")
            i = best[1]
            full = [" ".join(words[:i] + frag + words[i + len(frag):])] + full[1:]
        return {"n": n, "t": "fix", "q": q, "ans": full}
    raise AssertionError

# ---------- the book ----------
def parse_book(text):
    parts, index, cur_part = [], [], None
    for ln in text.split("\n"):
        m = re.match(r"^# Часть ([IVXL]+)\.\s*(.+)$", ln)
        if m:
            cur_part = m.group(1); parts.append({"id": cur_part, "t": m.group(2).strip()})
        m = re.match(r"^## Unit (\d+)\.\s*(.+)$", ln)
        if m:
            index.append({"n": int(m.group(1)), "part": cur_part, "t": m.group(2).strip()})
    return parts, index

def unit_blocks(text):
    chunks = re.split(r"^## Unit (\d+)\.", text, flags=re.M)
    return {int(chunks[i]): chunks[i + 1] for i in range(1, len(chunks), 2)}

def build_unit(n, body):
    title = body.split("\n", 1)[0].strip()
    m = re.search(r"### Правила\n(.*?)\n### Упражнения\n(.*?)\n### Ключи\n(.*?)(?:\n---|\Z)", body, flags=re.S)
    if not m: raise ValueError(f"unit {n}: sections not found")
    rules, ex_block, key_block = m.groups()
    keys = split_keys(key_block.strip().split("\n\n")[0] if "·" in key_block else key_block)
    exs = []
    for e in parse_exercises(ex_block):
        k = kind_of(e["h"])
        items = []
        for num, q in e["raw"]:
            if num not in keys: raise ValueError(f"unit {n}: no key for item {num}")
            items.append(build_item(k, num, q, keys[num]))
        exs.append({"id": f"e{e['n']}", "h": e["h"], "kind": k, "items": items})
    used = {it["n"] for e in exs for it in e["items"]}
    if used != set(keys): raise ValueError(f"unit {n}: keys without items {sorted(set(keys) - used)}")
    return {"n": n, "t": title, "rules": rule_sections(rules.strip()), "ex": exs}

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    text = open(sys.argv[1], encoding="utf-8").read()
    parts, index = parse_book(text)
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"units": {}}
    want = [int(x) for x in sys.argv[2:]] or [int(k) for k in old["units"]] or [1]
    blocks, units = unit_blocks(text), dict(old.get("units", {}))
    for n in want:
        units[str(n)] = build_unit(n, blocks[n])
    out = {"v": 1, "parts": parts, "index": index, "units": dict(sorted(units.items(), key=lambda kv: int(kv[0])))}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = sum(len(e["items"]) for u in out["units"].values() for e in u["ex"])
    print(f"grammar.json: {len(index)} units listed, {len(out['units'])} built ({', '.join(units)}), {total} items")

if __name__ == "__main__":
    main()
