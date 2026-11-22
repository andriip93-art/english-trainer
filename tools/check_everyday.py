"""Checks everyday.json before a commit: python3 tools/check_everyday.py [path].
Errors (exit 1): broken ** markers, item/dialogue mismatch, malformed traps, empty fields, duplicate topics.
Warnings: unbalanced roles, collocation not found among dialogue marks (short idioms can be false alarms), few traps."""
import re, sys, json

def stem(w):
    w = w.lower().strip("'.,!?-")
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w

def marks(t):
    return re.findall(r"\*\*(.+?)\*\*", t)

def check(topics):
    ids, warns, errs = set(), [], []
    for T in topics:
        tid = T["id"]
        if tid in ids:
            errs.append(f"dup topic {tid}")
        ids.add(tid)
        items = T["items"]
        spans = [(L["w"], m) for L in T["dialogue"] for m in marks(L["t"])]
        for L in T["dialogue"]:
            if L["t"].count("**") % 2 or not L["ru"].strip():
                errs.append(f"{tid}: bad dialogue line {L['t'][:40]}")
            if L["w"] not in ("B", "Y"):
                errs.append(f"{tid}: bad role")
        if len(spans) != len(items):
            errs.append(f"{tid}: {len(items)} items but {len(spans)} marks")
        nb = sum(1 for w, _ in spans if w == "B"); ny = len(spans) - nb
        if min(nb, ny) < 2:
            warns.append(f"{tid}: role balance B{nb}/Y{ny}")
        for it in items:
            if it["ex"].count("**") != 2:
                errs.append(f"{it['id']}: ex markers")
            if not all(it.get(k) for k in ("en", "ru", "def", "ex_ru")):
                errs.append(f"{it['id']}: empty field")
            tg = marks(it["ex"])
            if len(tg) != 1:
                errs.append(f"{it['id']}: ex marks {len(tg)}")
            words = {stem(w) for w in re.findall(r"[A-Za-z']+", it["en"]) if len(w) > 3}
            if not any(words & {stem(w) for w in re.findall(r"[A-Za-z']+", m)} for _, m in spans):
                warns.append(f"{it['id']}: '{it['en']}' not found in dialogue marks")
            if "trap" in it:
                tr = it["trap"]
                if "___" not in tr["s"] or tr["ok"] in tr["bad"] or len(set(tr["bad"])) != 2 or not tr["why_ru"]:
                    errs.append(f"{it['id']}: bad trap")
        if len(T["talk"]["targets"]) < 3:
            warns.append(f"{tid}: few talk targets")
        for g in T["talk"]["targets"]:
            pass
        if sum(1 for it in items if "trap" in it) < 2:
            warns.append(f"{tid}: only {sum(1 for it in items if 'trap' in it)} traps")
    for w in warns: print("WARN", w)
    for e in errs: print("ERR ", e)
    print(f"{len(topics)} topics, {sum(len(T['items']) for T in topics)} items, {sum(1 for T in topics for it in T['items'] if 'trap' in it)} traps, {len(errs)} errors, {len(warns)} warnings")
    return not errs

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "everyday.json"
    sys.exit(0 if check(json.load(open(path, encoding="utf-8"))["topics"]) else 1)
