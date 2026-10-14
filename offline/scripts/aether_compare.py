#!/usr/bin/env python3
"""Compare tools on the offline benchmark by scoring profile, with per-repo and tune/holdout splits.

Reads results/<judge model>/evaluations.json plus golden_comments/*.json. The holdout split is
every second PR within each golden file, so each repo contributes equally to both halves.

Usage:
  uv run python scripts/aether_compare.py --tools aether-r1 aether-r1-v2 claude augment --profile core
"""

import argparse
import glob
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {
    "strict": {"bug", "security", "concurrency", "data", "api"},
    "core": {"bug", "security", "concurrency", "data", "api", "perf", "test_gap", "doc_defect"},
    "all": {"bug", "security", "concurrency", "data", "api", "perf", "test_gap", "doc_defect", "style", "speculative"},
}


def model_dir() -> Path:
    model = os.environ.get("MARTIAN_MODEL")
    if not model:
        raise SystemExit("set MARTIAN_MODEL to the judge model whose results/ folder to read")
    return ROOT / "results" / model.strip().replace("/", "_")


def load_golden() -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, str]]:
    categories: dict[str, dict[str, str]] = {}
    repo_of: dict[str, str] = {}
    split_of: dict[str, str] = {}
    for path in sorted(glob.glob(str(ROOT / "golden_comments" / "*.json"))):
        repo = Path(path).stem
        with open(path) as f:
            entries = json.load(f)
        for index, entry in enumerate(entries):
            url = entry["url"]
            categories[url] = {c["comment"]: c.get("category") for c in entry["comments"]}
            repo_of[url] = repo
            split_of[url] = "tune" if index % 2 == 0 else "holdout"
    return categories, repo_of, split_of


def score(evals: dict, tool: str, urls: list[str], categories: dict, profile: set[str]) -> dict:
    tp = fp = fn = 0
    covered = 0
    for url in urls:
        result = evals.get(url, {}).get(tool)
        if result is None or result.get("skipped"):
            continue
        covered += 1
        gold = categories[url]
        tp += sum(1 for t in result.get("true_positives", []) if gold.get(t["golden_comment"]) in profile)
        fn += sum(1 for f in result.get("false_negatives", []) if gold.get(f["golden_comment"]) in profile)
        fp += result.get("fp", 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"prs": covered, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def print_table(title: str, rows: list[tuple[str, dict]]) -> None:
    print(f"\n{title}")
    print(f"{'tool':24} {'PRs':>3} {'TP':>3} {'FP':>3} {'FN':>3} {'prec':>5} {'rec':>5} {'F1':>5}")
    for name, s in rows:
        print(
            f"{name:24} {s['prs']:3} {s['tp']:3} {s['fp']:3} {s['fn']:3} "
            f"{s['precision']:5.2f} {s['recall']:5.2f} {s['f1']:5.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tools", nargs="+", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="core")
    parser.add_argument("--by-repo", action="store_true", help="also print one table per source repo")
    args = parser.parse_args()

    evals_path = model_dir() / "evaluations.json"
    with open(evals_path) as f:
        evals = json.load(f)
    categories, repo_of, split_of = load_golden()
    profile = PROFILES[args.profile]
    urls = sorted(categories)
    missing = [t for t in args.tools if not any(t in evals.get(u, {}) for u in urls)]
    if missing:
        raise SystemExit(f"no evaluations for {missing} in {evals_path}")

    print(f"judge results: {evals_path}\nprofile: {args.profile} ({', '.join(sorted(profile))})")
    print_table("ALL 50 PRs", [(t, score(evals, t, urls, categories, profile)) for t in args.tools])
    for split in ("tune", "holdout"):
        split_urls = [u for u in urls if split_of[u] == split]
        rows = [(t, score(evals, t, split_urls, categories, profile)) for t in args.tools]
        print_table(f"{split.upper()} ({len(split_urls)} PRs)", rows)
    if args.by_repo:
        for repo in sorted(set(repo_of.values())):
            repo_urls = [u for u in urls if repo_of[u] == repo]
            print_table(f"REPO {repo}", [(t, score(evals, t, repo_urls, categories, profile)) for t in args.tools])


if __name__ == "__main__":
    main()
