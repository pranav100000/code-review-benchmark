"""Focused judging sheet for the Opus run: per PR, the injected-bug golden(s) (or keyword rule), the production catch for reference
(which comment matched, its path:line), and every Opus inline comment. Usage: ablate_sheet.py <substring filter on repo>."""
import json, re, sys, importlib.util
sys.path.insert(0, "scripts")
spec = importlib.util.spec_from_file_location("hj", "scripts/aether_hand_judge.py"); hj = importlib.util.module_from_spec(spec); spec.loader.exec_module(hj)
src = open("scripts/aether_greptile_score.py").read()
ns = {}; exec(src.split("data = hj.load_data()")[0].split("BUGS = {")[0].replace("import json, re, sys, glob", "import json, re, sys, glob"), ns)
exec("BUGS = {" + src.split("BUGS = {", 1)[1].split("\n}\n", 1)[0] + "\n}", ns); BUGS = ns["BUGS"]
data = hj.load_data()
golden = {}
for f in ("cal_dot_com", "discourse", "grafana", "keycloak", "sentry"):
    for e in json.load(open(f"golden_comments/{f}.json")): golden[e["url"].rstrip("/")] = e
prodS = json.load(open("handjudge/aether-prod.json")); prodL = json.load(open("handjudge/aether-prod-lenient.json"))
flts = sys.argv[1].split(",") if len(sys.argv) > 1 else [""]
def comments(review):
    cs = [c for c in review["review_comments"] if c.get("path")]
    return cs
for url, rule in BUGS.items():
    if not any(f in url for f in flts): continue
    if url not in data: print("######", url, "NOT IN DATA"); continue
    opus = hj.review_for(data[url], "aether-final-final-opus"); prod = hj.review_for(data[url], "aether-prod")
    print(f"\n######## {url.split('/')[-3]}#{url.rsplit('/',1)[-1]}   rule g={rule['g']} kw={rule.get('kw','')!r}")
    g = golden.get(url.rstrip("/"))
    for i, c in enumerate(g["comments"], 1):
        if f"G{i}" in rule["g"]: print(f"  G{i} [{c['severity']}/{c['category']}] {c['comment'][:420]}")
    # production reference
    pm = (prodL.get(url) or {}).get("matches", {}); strict = url in prodS and any(x in prodS[url]["matches"] for x in rule["g"] + ["kw"])
    if prod:
        pcs = comments(prod)
        refs = []
        for gk, ak in pm.items():
            m = re.match(r"A(\d+)", ak or "")
            if m and int(m.group(1)) <= len(pcs):
                c = pcs[int(m.group(1)) - 1]; refs.append(f"{gk}->{ak} {c['path'].split('/')[-1]}:{c.get('line') or c.get('original_line')} :: {(c.get('body') or '')[:200]}")
        print(f"  PROD: {'strict' if strict else ('lenient' if pm else 'MISS')} | " + (" || ".join(refs) if refs else f"matches={pm}"))
    if not opus: print("  OPUS: NO REVIEW"); continue
    acs = comments(opus)
    for i, c in enumerate(acs, 1):
        b = re.sub(r"<sub>.*?</sub>", "", c.get("body") or "").strip().replace("\n", " ")
        sev = re.search(r"\[(P1|P2|NIT)\]", b, re.I); b = re.sub(r"\[(P1|P2|NIT)\]\s*", "", b, flags=re.I)
        fb = re.search(r"found by (\d+) of 9", b); b = re.sub(r"\(found by \d+ of 9 reviewers\)\s*$", "", b).strip()
        print(f"  A{i} {c['path'].split('/')[-1]}:{c.get('line') or c.get('original_line')} [{sev.group(1).lower() if sev else '?'}|{fb.group(1) if fb else '-'}] {b[:330]}")
