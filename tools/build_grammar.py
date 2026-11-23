#!/usr/bin/env python3
"""Builds grammar.json (Mode 8, Business Grammar) from the adapted textbook in markdown.

    python3 tools/build_grammar.py SOURCE.md [UNIT ...]     # default: units already present in grammar.json, else 1

The rules are turned into a small, safe HTML subset (everything is escaped first). Exercises are parsed into typed items and the
keys are matched to them, so a unit that does not parse cleanly stops the build with a clear message instead of shipping a
broken key. Item types: choose, type, place, fix, rewrite. Other exercise kinds raise NotImplementedError for now.
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

CYR = re.compile(r"[А-Яа-яЁё]")

def clean_key(s):
    s = s.strip()
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    return s

def strip_comments(s):
    """Drops remarks in brackets: Russian text, '(state verb)'. Latin words in brackets are alternatives and stay."""
    def keep(m):
        t = m.group(1)
        if re.match(r"^(или|or)\s", t.strip()): return m.group(0)          # '(или other wording)' is an alternative, not a remark
        return "" if CYR.search(t) or re.match(r"^(state|state verb|formal|informal)\b", t.strip()) else m.group(0)
    return re.sub(r"\s*\(([^()]*)\)", keep, s).strip()

OPT_PREP = {"for", "of", "some"}                  # '(for)', '(of)', '(some)': may be left out
REL = {"that", "who", "whom", "which"}            # '(who) I spoke to': may be left out; 'who (that)': a replacement

def expand_parens(s):
    """Latin words in brackets, by meaning: a replacement ('who (that)', 'have (get) the model'), a word that may be left out
    ('The person (who) I spoke to', 'All (of) the banks'), an optional addition ('reviewed (by the agency)') or a remark
    ('*He probably won't agree.*', 'of (the company's strategy)'). Returns the accepted wordings, the main one first."""
    m = re.search(r"\(([^()]+)\)", s)
    if not m: return [s]
    pre, p, post = s[:m.start()].rstrip(), m.group(1).strip(), s[m.end():].lstrip()
    pw = pre.split()
    join = lambda *xs: re.sub(r"\s+", " ", " ".join(x for x in xs if x)).strip().replace(" .", ".").replace(" ,", ",")
    if p.startswith("*") or CYR.search(p): variants = [join(pre, post)]
    elif len(pw) == 1 and len(pw[0]) <= 2 and len(p.split()) >= 2: variants = [join(pre, post)]          # "of (the company's strategy)"
    elif not post and re.search(r"[.?!]$", pre): variants = [pre, join(pre[:-1], p) + pre[-1]]          # "reviewed. (by the agency)"
    elif p in OPT_PREP or (p in REL and post) or (len(p.split()) >= 2 and re.fullmatch(r"[.?!,;]*", post or "") and pw and p.split()[0] in ("by", "from", "with", "to", "for")):
        variants = [join(pre, p, post), join(pre, post)]
    else:
        alts = [x.strip() for x in p.split(",")]
        variants = [join(pre, post)] if False else []
        whole = not post and len(pw) <= 3
        for k, a in enumerate([None] + alts):
            if a is None: variants.append(join(pre, post)); continue
            cut = len(pw) if whole else min(len(a.split()), len(pw))
            variants.append(join(" ".join(pw[:len(pw) - cut]), a, post))
    out = []
    for v in variants:
        for w in expand_parens(v):
            if w not in out: out.append(w)
    return out

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
    """'main. (или *other*)' -> [main, other]; remarks in brackets are dropped; (w) inside the key is an alternative."""
    key = strip_comments(key)
    m = re.match(r"^(.*?)\s*\((?:или|or)\s+(.+)\)\s*$", key)
    mains = [clean_key(m.group(1))] + [clean_key(x) for x in re.split(r"\s+/\s+|\s+или\s+", m.group(2))] if m else [clean_key(key)]
    out = []
    for x in mains:
        for y in expand_parens(x):
            if y not in out: out.append(y)
    return out

def edit_dist(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (x != y))
    return d[-1]

# ---------- exercises ----------
START_OK = {"usually", "normally", "often", "sometimes", "occasionally", "generally", "frequently", "regularly"}
END_OK = {"sometimes", "occasionally"}

def parse_exercises(block):
    exs, cur = [], None
    for ln in block.split("\n"):
        m = re.match(r"^\*\*Exercise (\d+)\.\*\*\s*(.*)$", ln)
        if m:
            cur = {"n": int(m.group(1)), "h": clean_key(m.group(2)), "raw": []}; exs.append(cur)
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", ln)
        if m and cur is not None:
            cur["raw"].append([int(m.group(1)), m.group(2).strip()])
        elif ln.startswith("   ") and ln.strip() and cur is not None and cur["raw"]:
            cur["raw"][-1][1] += " " + ln.strip()      # continuation line of the previous item
    for e in exs: e["raw"] = [tuple(x) for x in e["raw"]]
    return exs

# label exercises: the answer is a short code taken from the instruction
LABEL_OVERRIDES = {"Which sentence describes a fixed future arrangement, a timetable, or a complaint? Write A, B or C.":
                   [("A", "fixed future arrangement"), ("B", "timetable"), ("C", "complaint")]}
def label_opts(h):
    if h in LABEL_OVERRIDES: return LABEL_OVERRIDES[h]
    m = re.findall(r"([A-D])\)\s*([^,.]+)", h)
    if len(m) >= 2 and h.startswith("Match"): return [(a, t.strip()) for a, t in m]
    m = re.findall(r"([A-Za-z]+)\s+\(([A-Z])\)", h)
    if len(m) >= 2 and "Write" not in h or (len(m) >= 2 and re.search(r"\([A-Z]\) or", h)): return [(c, w.lower()) for w, c in m]
    if re.search(r"Write Y or N", h): return [("Y", "yes"), ("N", "no")]
    return None

VERBS = r"(Complete|Choose|Put|Find|Rewrite|Make|Write|Match|Which|Does|Can|Add|Join|Correct|Combine|Shorten|Report|Replace|Disagree|Third|Perception|Passive|Comparative|Past|Transitive|Countable)"
def or_opts(h):
    """'On time or in time?' -> ['on time', 'in time']"""
    t = h.strip().rstrip("?.")
    if re.match(VERBS, t) or " or " not in t or len(t.split()) > 9: return None
    return [x.strip() for x in re.split(r",\s*|\s+or\s+", t) if x.strip()]

EXACT = re.compile(r"(commas|punctuation|capitalisation|semicolon or colon|quotation marks)", re.I)
REWRITE = re.compile(r"^(Rewrite|Make the|Make questions|Report the|Shorten|Join with|Disagree|Write a reply|Write the|Write in words|Replace|Correct the|Combine|Add commas|Add the necessary|Put the adjectives)")

def kind_of(h):
    if label_opts(h): return "label"
    if h.startswith("Choose"): return "choose"
    if h.startswith("Put the adverb"): return "place"
    if h.startswith("Find and correct"): return "fix"
    if REWRITE.match(h): return "rewrite"
    if or_opts(h): return "or"
    return "default"

LETTERED = re.compile(r"(?:^|\s)(?=[a-d]\)\s)")

def pick(opts, alts):
    k = [norm(x) for x in alts]
    return [i for i, o in enumerate(opts) if norm(o) in k]

def build_item(unit, ex, n, q, key, overrides):
    h, kind = ex["h"], kind_of(ex["h"])
    if (unit, n) in overrides: return {"n": n, **overrides[(unit, n)]}
    alts = alts_of(key)
    # 1. label exercises (T/I, C/U, A/B/C, Y/N)
    if kind == "label":
        opts = label_opts(h)
        hit = [i for i, (c, _) in enumerate(opts) if c.lower() == alts[0].lower()]
        if len(hit) != 1: raise ValueError(f"item {n}: label {key!r} not in {opts}")
        return {"n": n, "t": "choose", "q": q, "opts": [f"{c} · {w}" for c, w in opts], "ans": hit[0], "label": True}
    # 2. lettered sentences: 'a) ... b) ... c) ...'
    parts = [p.strip() for p in LETTERED.split(q) if p.strip()]
    lett = [p for p in parts if re.match(r"^[a-d]\)\s", p)]
    if len(lett) >= 2 and re.fullmatch(r"[a-d]", alts[0].strip().lower()):
        lead = " ".join(p for p in parts if p not in lett) or h
        lead = re.sub(r"\s*Write [a-d](?:, [a-d])* or [a-d]\.?$", "", lead).strip()          # the options are buttons, no need to 'write' a letter
        opts = [re.sub(r"^[a-d]\)\s*", "", p) for p in lett]
        idx = ord(alts[0].strip().lower()) - ord("a")
        if idx >= len(opts): raise ValueError(f"item {n}: letter {key!r} out of range")
        return {"n": n, "t": "choose", "q": lead, "opts": opts, "ans": idx, "lettered": True}
    # 3. adverb placement
    if kind == "place":
        m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", q)
        if not m: raise ValueError(f"item {n}: no (adverb)")
        base, adv = m.group(1).strip(), m.group(2).strip()
        if " / " in adv:                                      # several adverbials: write the whole sentence
            return {"n": n, "t": "rewrite", "q": f"{base} ({adv})", "ans": alts}
        punct = re.search(r"[.?!]$", base)
        words = base[:-1].split() if punct else base.split()
        end = punct.group(0) if punct else ""
        pos = set()
        for sentence in alts:
            sentence = re.sub(r"\.{3}|…", "", sentence).strip()
            toks = re.sub(r"[.?!]+$", "", sentence).split()
            a = adv.lower().split()
            idx = [i for i in range(len(toks) - len(a) + 1) if [t.lower() for t in toks[i:i + len(a)]] == a]
            if len(idx) != 1: raise ValueError(f"item {n}: adverb {adv!r} not found once in {sentence!r}")
            pos.add(idx[0])
        order = sorted(pos)
        low = adv.lower()                                     # single frequency adverbs may also open the sentence
        if low in START_OK and 0 not in order: order.append(0)
        if low in END_OK and len(words) not in order: order.append(len(words))
        return {"n": n, "t": "place", "adv": adv, "words": words, "end": end, "ans": order}
    # 4. (a / b) inside the sentence
    if kind in ("choose", "default", "label"):
        g = re.search(r"\(([^()]*\s/\s[^()]*)\)", q)
        if g and not re.search(r"\(\s*\d", g.group(0)):
            opts = [o.strip() for o in g.group(1).split(" / ")]
            hit = pick(opts, alts)
            if not hit: raise ValueError(f"item {n}: key {key!r} does not match one of {opts}")
            rest = q[:g.start()].rstrip() + (" " if q[g.end():].strip() else "") + q[g.end():].lstrip()
            qq = re.sub(r"_{3,}", "___", rest) if re.search(r"_{3,}", rest) else q[:g.start()] + "___" + q[g.end():]
            return {"n": n, "t": "choose", "q": qq.strip(), "opts": opts, "ans": hit[0] if len(hit) == 1 else hit}
    # 5. options named in the instruction ('On time or in time?')
    if kind == "or":
        opts = or_opts(h)
        hit = pick(opts, alts)
        if not hit: raise ValueError(f"item {n}: key {key!r} not among {opts}")
        return {"n": n, "t": "choose", "q": re.sub(r"_{3,}", "___", q), "opts": opts, "ans": hit[0] if len(hit) == 1 else hit}
    # 6. correct / rewrite
    if kind == "fix":
        full = alts
        words = q.split()
        if len(full[0].split()) < max(3, len(words) - 3):
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
    if not re.search(r"_{3,}", q):                 # no gap in the text: the learner types the whole answer
        ans = alts
        if alts[0].lower() in ("no commas", "no comma", "no change"): ans = [q, alts[0]]
        item = {"n": n, "t": "rewrite", "q": q, "ans": ans}
        if EXACT.search(h): item["exact"] = True
        return item
    # 7. gaps
    gaps = len(re.findall(r"_{3,}", q))
    if gaps == 1 and re.search(r"Complete with the or –", h) and alts[0].strip() in ("the", "–"):
        return {"n": n, "t": "choose", "q": re.sub(r"_{3,}", "___", q), "opts": ["the", "– (no article)"], "ans": 0 if alts[0].strip() == "the" else 1}
    sets = [[p.strip() for p in re.split(r"\s+(?:\.\.\.|→)\s+", a)] for a in alts]
    if len(sets[0]) != gaps:
        words = alts[0].split()
        if len(sets[0]) == 1 and gaps == 2 and len(words) >= 2:
            sets = [[" ".join(w.split()[:-1]), w.split()[-1]] for w in alts if len(w.split()) >= 2]
        else:
            raise ValueError(f"item {n}: {gaps} gaps but key {key!r}")
    ans = [[s[g] for s in sets if len(s) == gaps] for g in range(gaps)]
    ans = [list(dict.fromkeys(a)) for a in ans]
    return {"n": n, "t": "type", "q": re.sub(r"_{3,}", "___", q), "ans": ans}

# Items whose key cannot be matched mechanically are written out here: (unit, item) -> item fields
OVERRIDES = {
    (10, 9): {"t": "type", "q": "We are going to ___ the model ___ (audit) next month.", "ans": [["have", "get"], ["audited"]]},
    (21, 5): {"t": "rewrite", "q": "'We issued the notes last year,' she said.", "ans": ["She said they had issued the notes the year before.", "She said they issued the notes the year before."]},
    (7, 12): {"t": "fix", "q": "It's hot here. – Wait, I'm going to open the window.", "ans": ["It's hot here. – Wait, I'll open the window.", "I'll open the window."]},
}

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

def check_item(n, it):
    """Invariants every shipped item must satisfy; a violation stops the build."""
    t, bad = it["t"], None
    texts = []
    if t == "choose":
        idx = it["ans"] if isinstance(it["ans"], list) else [it["ans"]]
        if not it["opts"] or any(not (0 <= i < len(it["opts"])) for i in idx): bad = "answer index out of range"
        texts = it["opts"] + [it["q"]]
    elif t == "type":
        if not it["ans"] or any(not a or any(not x.strip() for x in a) for a in it["ans"]): bad = "empty answer"
        if it["q"].count("___") != len(it["ans"]): bad = "gaps and answers differ"
        texts = [x for a in it["ans"] for x in a] + [it["q"]]
    elif t == "place":
        if not it["ans"] or any(not (0 <= p <= len(it["words"])) for p in it["ans"]): bad = "position out of range"
        texts = it["words"]
    else:
        if not it["ans"] or any(not x.strip() for x in it["ans"]): bad = "empty answer"
        texts = it["ans"] + [it["q"]]
    if any("  " in x or x != x.strip() for x in texts): bad = bad or "stray spaces"
    if bad: raise ValueError(f"unit {n} item {it['n']}: {bad}: {it}")

def build_unit(n, body):
    title = body.split("\n", 1)[0].strip()
    m = re.search(r"### Правила\n(.*?)\n### Упражнения\n(.*?)\n### Ключи\n(.*?)(?:\n---|\Z)", body, flags=re.S)
    if not m: raise ValueError(f"unit {n}: sections not found")
    rules, ex_block, key_block = m.groups()
    keys = split_keys(key_block.strip().split("\n\n")[0] if "·" in key_block else key_block)
    exs = []
    for e in parse_exercises(ex_block):
        items = []
        for num, q in e["raw"]:
            if num not in keys: raise ValueError(f"unit {n}: no key for item {num}")
            try:
                items.append(build_item(n, e, num, q, keys[num], OVERRIDES))
            except Exception as ex:
                raise ValueError(f"unit {n}, exercise {e['n']} [{e['h'][:50]}]: {ex}")
        exs.append({"id": f"e{e['n']}", "h": e["h"], "kind": kind_of(e["h"]), "items": items})
    for e in exs:
        for it in e["items"]: check_item(n, it)
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
