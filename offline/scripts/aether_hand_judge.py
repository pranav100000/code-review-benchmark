#!/usr/bin/env python3
"""Hand-judging worksheet and scorer for reviews collected in results/benchmark_data.json.

`worksheet` prints, per PR, the golden comments (G1..) and the tool's candidates (A1..) so a human
judge can decide matches. Decisions live in handjudge/<tool>.json as
  {"<golden url>": {"matches": {"G2": "A1", "G5": "A1"}, "candidates": 4}}
where a golden maps to the candidate that describes the same underlying issue (several goldens may
map to one candidate), and `candidates` is the number of distinct candidates after merging duplicates.
`score` computes Core/Strict/All precision, recall, F1 and F2 from those decisions, overall and per repo.

Usage:
  uv run python scripts/aether_hand_judge.py worksheet --tool aether-r1 [--repo discourse]
  uv run python scripts/aether_hand_judge.py score --tool aether-r1 [--tool aether-r1-deep-v1 ...]
"""

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "results" / "benchmark_data.json"
JUDGE_DIR = ROOT / "handjudge"
PROFILES = {
    "strict": {"bug", "security", "concurrency", "data", "api"},
    "core": {"bug", "security", "concurrency", "data", "api", "perf", "test_gap", "doc_defect"},
    "all": {"bug", "security", "concurrency", "data", "api", "perf", "test_gap", "doc_defect", "style", "speculative"},
}
SUB = re.compile(r"<sub>.*?</sub>\s*", re.S)


def load_data() -> dict:
    with open(DATA) as f:
        return json.load(f)


def review_for(entry: dict, tool: str) -> dict | None:
    return next((r for r in entry["reviews"] if r["tool"] == tool), None)


def candidates(review: dict) -> list[str]:
    """Inline comments first, then general comments, each stripped of the attribution header."""
    inline = [c for c in review["review_comments"] if c.get("path")]
    general = [c for c in review["review_comments"] if not c.get("path")]
    texts = []
    for c in inline + general:
        where = f"{c['path'].split('/')[-1]}:{c.get('line')} " if c.get("path") else "(summary) "
        texts.append(where + SUB.sub("", c["body"] or "").strip().replace("\n", " "))
    return texts


def worksheet(args: argparse.Namespace) -> None:
    data = load_data()
    for url, entry in sorted(data.items(), key=lambda kv: (kv[1]["source_repo"], kv[0])):
        if args.repo and args.repo not in entry["golden_source_file"]:
            continue
        review = review_for(entry, args.tool)
        if review is None:
            continue
        print(f"\n######## {url}")
        for i, g in enumerate(entry["golden_comments"], 1):
            print(f"  G{i} [{g.get('severity')}/{g.get('category')}] {g['comment'][:240]}")
        for j, text in enumerate(candidates(review), 1):
            print(f"  A{j} {text[:320]}")


def score(args: argparse.Namespace) -> None:
    data = load_data()
    for tool in args.tool:
        path = JUDGE_DIR / f"{tool}.json"
        with open(path) as f:
            decisions = json.load(f)
        print(f"\n=== {tool}  ({len(decisions)} PRs judged, {path.relative_to(ROOT)})")
        for profile in ("core", "strict", "all"):
            cats = PROFILES[profile]
            totals: dict[str, dict[str, int]] = {}
            for url, d in decisions.items():
                entry = data[url]
                repo = entry["source_repo"]
                t = totals.setdefault(repo, {"tp": 0, "fp": 0, "fn": 0, "prs": 0})
                t["prs"] += 1
                matched_cands = set()
                for i, g in enumerate(entry["golden_comments"], 1):
                    cand = d["matches"].get(f"G{i}")
                    if g.get("category") not in cats:
                        continue  # excluded from this profile: neither reward nor penalty
                    if cand:
                        t["tp"] += 1
                    else:
                        t["fn"] += 1
                matched_cands = {c for gi, c in d["matches"].items()}
                t["fp"] += d["candidates"] - len(matched_cands)
            grand = {"tp": 0, "fp": 0, "fn": 0, "prs": 0}
            for t in totals.values():
                for k in grand:
                    grand[k] += t[k]
            rows = [*sorted(totals.items()), ("ALL", grand)]
            header = f"{'PRs':>3} {'TP':>3} {'FP':>3} {'FN':>3} {'prec':>5} {'rec':>5} {'F1':>5} {'F2':>5}"
            print(f"  {profile:6} {'repo':12} {header}")
            for repo, t in rows:
                p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
                r = t["tp"] / (t["tp"] + t["fn"]) if t["tp"] + t["fn"] else 0.0
                f1 = 2 * p * r / (p + r) if p + r else 0.0
                f2 = 5 * p * r / (4 * p + r) if 4 * p + r else 0.0
                counts = f"{t['prs']:3} {t['tp']:3} {t['fp']:3} {t['fn']:3}"
                print(f"  {'':6} {repo:12} {counts} {p:5.2f} {r:5.2f} {f1:5.2f} {f2:5.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("worksheet")
    w.add_argument("--tool", required=True)
    w.add_argument("--repo")
    s = sub.add_parser("score")
    s.add_argument("--tool", action="append", required=True)
    args = parser.parse_args()
    worksheet(args) if args.command == "worksheet" else score(args)


if __name__ == "__main__":
    main()
