"""Score our reviews on Greptile's benchmark metric: one injected bug per PR, caught = a line-level comment identifies it.
Uses hand-judge decisions (golden -> candidate) where the injected bug is a Martian golden, and a keyword match on inline
comment text where it is not. Prints caught/total per tool and the misses."""
import json, re, sys, glob
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("hj", "scripts/aether_hand_judge.py"); hj = importlib.util.module_from_spec(spec); spec.loader.exec_module(hj)
C = "https://github.com/calcom/cal.com/pull/"; D = "https://github.com/ai-code-review-evaluation/discourse-graphite/pull/"; G = "https://github.com/grafana/grafana/pull/"
SG = "https://github.com/ai-code-review-evaluation/sentry-greptile/pull/"; SS = "https://github.com/getsentry/sentry/pull/"; K = "https://github.com/keycloak/keycloak/pull/"; KG = "https://github.com/ai-code-review-evaluation/keycloak-greptile/pull/"
# injected bug per PR: goldens that describe it, and/or a regex over inline comment text
BUGS = {
  C+"8087": dict(g=["G2"], kw=r"forEach.*async|async.*forEach|unawaited|not awaited|discard.*promise"),
  C+"10600": dict(g=["G4"], kw=r"(reuse|more than once|twice|not invalidated|single.use|consum).*backup|backup code.*(reuse|twice|more than once|not invalidated|atomic)"),
  C+"10967": dict(g=["G1"]), C+"22345": dict(g=[], kw=r"NOTHING_CONDITION|invalid SQL|sql injection|injection"),  # strict: mentioning the 1=0 deny predicate alone is not the composition bug
  C+"7232": dict(g=["G2"], kw=r"(orphan|never deleted|not deleted|leaves the row|row remains).*(reminder|record)|WorkflowReminder.*(orphan|not deleted|never deleted)"),
  C+"8330": dict(g=["G1"]), C+"11059": dict(g=[], kw=r"timing attack|timing.safe|constant.time|timingSafeEqual"),
  C+"14943": dict(g=["G2"]), C+"14740": dict(g=["G1"]), C+"22532": dict(g=["G1"]),
  G+"79265": dict(g=["G1"]), G+"103633": dict(g=[], kw=r"(denial|denied|deny).{0,80}(TTL|expir|never expire|permanent|outlive|no expiry)|(TTL|expir).{0,80}(denial|denied)"),
  G+"76186": dict(g=["G1", "G3"]),  # Greptile graded 'undefined endpoint constants' as its catch; they are defined in utils.go
  G+"107534": dict(g=[], kw=r"interpolat.*(again|twice|second|re-?interpret|double)|double interpolation"),
  G+"106778": dict(g=["G1"]), G+"90045": dict(g=["G2"]), G+"80329": dict(g=["G1"]), G+"90939": dict(g=["G1", "G2"]), G+"94942": dict(g=["G1"]), G+"97529": dict(g=["G1", "G2"]),
  D+"1": dict(g=["G1"]), D+"2": dict(g=["G1"]), D+"3": dict(g=["G1"]), D+"4": dict(g=["G1"]), D+"5": dict(g=["G1"]),
  D+"6": dict(g=[], kw=r"<<|mutat|frozen|in.place|shared string"), D+"7": dict(g=["G1", "G2", "G3", "G4", "G5"]), D+"8": dict(g=["G1"]), D+"9": dict(g=["G1"]), D+"10": dict(g=["G1"]),
  SG+"1": dict(g=["G1"]), SG+"2": dict(g=["G1"]), SG+"3": dict(g=["G1"]), SS+"67876": dict(g=["G1"]), SG+"5": dict(g=["G2"], kw=r"detector_type"), SS+"93824": dict(g=["G1"]), SS+"77754": dict(g=["G1"]),
  SS+"80528": dict(g=["G1"]), SS+"95633": dict(g=[], kw=r"queue\.ShutDown|ShutDown"), SS+"80168": dict(g=["G1"]),
  KG+"1": dict(g=["G1"]), K+"32918": dict(g=["G1"]), K+"33832": dict(g=["G1"]), K+"36882": dict(g=["G1"]), K+"36880": dict(g=["G1"]), K+"37038": dict(g=["G1"]), K+"37429": dict(g=["G1"]), K+"37634": dict(g=["G1"]), K+"38446": dict(g=["G1"]), K+"40940": dict(g=["G1"]),
}
data = hj.load_data()
def score(tool, decision_files):
    dec = {}
    for f in decision_files: dec.update(json.load(open(f)))
    caught, judged, misses = 0, 0, []
    for url, spec_ in BUGS.items():
        if tool == "MULTI":
            review = None
            for t in ("aether-r1-deep-v14", "aether-r1-deep-v13", "aether-r1-deep-v12"):
                review = hj.review_for(data.get(url, {"reviews": []}), t) if url in data else None
                if review and any(c.get("path") for c in review["review_comments"]): break
        else:
            review = hj.review_for(data.get(url, {"reviews": []}), tool) if url in data else None
        has_review = review is not None and len(review["review_comments"]) > 0
        if not has_review: continue
        judged += 1
        hit = False
        if url in dec and any(g in dec[url]["matches"] for g in spec_["g"]): hit = True
        if not hit and url in dec and dec[url]["matches"].get("kw"):  # hand-judged keyword catch recorded in the handjudge file
            hit = True
        if not hit and spec_.get("kw"):
            text = " ".join((c.get("body") or "") for c in review["review_comments"] if c.get("path"))
            hit = re.search(spec_["kw"], text, re.I) is not None
        caught += hit
        if not hit: misses.append(url.rsplit("/", 2)[-3].split("/")[-1][:9] + "#" + url.rsplit("/", 1)[-1])
    return caught, judged, misses
tools = {"v3": ("aether-r1-deep-v3", ["handjudge/aether-r1-deep-v3.json"]),
         "v6fam": ("aether-r1-deep-v6", ["handjudge/aether-r1-deep-v6.json"]),
         "v11": ("aether-r1-deep-v11", ["handjudge/aether-r1-deep-v11.json"]),
         "opus": ("aether-r1-deep-v3-opus", ["handjudge/aether-r1-deep-v3-opus.json"]),
         "v12": ("aether-r1-deep-v12", ["handjudge/aether-r1-deep-v12.json"]),
         "v13": ("aether-r1-deep-v13", ["handjudge/aether-r1-deep-v13.json"]),
         "v14": ("aether-r1-deep-v14", ["handjudge/aether-r1-deep-v14.json"]),
         "v15": ("aether-r1-deep-v15", ["handjudge/aether-r1-deep-v15-lenient.json"]),  # owner 10-08: a comment on the injected line explaining the mechanism counts even with a 'safe' verdict
         "v15S": ("aether-r1-deep-v15", ["handjudge/aether-r1-deep-v15.json"]),
         "v16": ("aether-r1-deep-v16", ["handjudge/aether-r1-deep-v16-lenient.json"]),
         "v16S": ("aether-r1-deep-v16", ["handjudge/aether-r1-deep-v16.json"]),
         "final": ("aether-final", ["handjudge/aether-final-lenient.json"]),
         "finalS": ("aether-final", ["handjudge/aether-final.json"]),
         "opusF": ("aether-final-final-opus", ["handjudge/aether-final-final-opus-lenient.json"]),
         "opusFS": ("aether-final-final-opus", ["handjudge/aether-final-final-opus.json"]),
         "prod": ("aether-prod", ["handjudge/aether-prod-lenient.json"]),
         "prodS": ("aether-prod", ["handjudge/aether-prod.json"]),
    "abl": ("aether-ablate", ["handjudge/aether-ablate-lenient.json"]),
    "ablS": ("aether-ablate", ["handjudge/aether-ablate.json"]),
    "v18": ("aether-v18", ["handjudge/aether-v18-lenient.json"]),
    "v18S": ("aether-v18", ["handjudge/aether-v18.json"]),
    "v19": ("aether-v19", ["handjudge/aether-v19-lenient.json"]),
    "v19S": ("aether-v19", ["handjudge/aether-v19.json"]),
    "v20": ("aether-v20", ["handjudge/aether-v20-lenient.json"]),
    "v20S": ("aether-v20", ["handjudge/aether-v20.json"]),
    "v21": ("aether-v21", ["handjudge/aether-v21-lenient.json"]),
    "v21S": ("aether-v21", ["handjudge/aether-v21.json"]),
    "v22": ("aether-v22", ["handjudge/aether-v22-lenient.json"]),
    "v22S": ("aether-v22", ["handjudge/aether-v22.json"]),
         "v12-14": ("MULTI", ["handjudge/aether-r1-deep-v12.json", "handjudge/aether-r1-deep-v13.json", "handjudge/aether-r1-deep-v14.json"])}
for name, (tool, files) in tools.items():
    if not all(glob.glob(f) for f in files): continue
    c, j, m = score(tool, files)
    print(f"{name:6s} caught {c:2d}/{j:2d} reviewed PRs ({c/max(j,1):.0%})   misses: {', '.join(m)}")
if "--union" in sys.argv:
    print("\n== union across every judged variant (which variant caught each injected bug)")
    allvars = {"v1": "aether-r1-deep-v1", "v2": "aether-r1-deep-v2", "v3": "aether-r1-deep-v3", "v6": "aether-r1-deep-v6", "v7": "aether-r1-deep-v7",
               "v8": "aether-r1-deep-v8", "v9": "aether-r1-deep-v9", "v10": "aether-r1-deep-v10", "v11": "aether-r1-deep-v11", "v12": "aether-r1-deep-v12", "v13": "aether-r1-deep-v13", "v14": "aether-r1-deep-v14", "v15": "aether-r1-deep-v15", "v16": "aether-r1-deep-v16", "final": "aether-final", "opusF": "aether-final-final-opus", "opus": "aether-r1-deep-v3-opus"}
    decs = {n: json.load(open(f"handjudge/{t}.json")) for n, t in allvars.items() if glob.glob(f"handjudge/{t}.json")}
    never, reviewed_any = [], 0
    for url, spec_ in BUGS.items():
        who = []
        for n, t in allvars.items():
            if url not in data: continue
            review = hj.review_for(data[url], t)
            if not review or not any(c.get("path") for c in review["review_comments"]): continue
            hit = url in decs.get(n, {}) and any(g in decs[n][url]["matches"] for g in spec_["g"])
            if not hit and spec_.get("kw"):
                text = " ".join((c.get("body") or "") for c in review["review_comments"] if c.get("path"))
                hit = re.search(spec_["kw"], text, re.I) is not None
            who.append(n + ("+" if hit else "-"))
        if who: reviewed_any += 1
        if who and not any(w.endswith("+") for w in who): never.append(url.split("/")[-3][:9] + "#" + url.rsplit("/", 1)[-1] + " [" + " ".join(who) + "]")
    print(f"PRs reviewed by at least one variant: {reviewed_any}/50; caught by at least one: {reviewed_any - len(never)}")
    print("never caught:", "; ".join(never) or "none")
print("Greptile: 41/50 (82%), Bugbot 58%, Copilot 54%, CodeRabbit 44%")
