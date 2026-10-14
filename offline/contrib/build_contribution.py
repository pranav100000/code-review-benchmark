#!/usr/bin/env python3
"""Turn contrib/proposed_goldens.json into reviewable upstream PR material.

For each proposed golden: find the public review comment on our aether-bench fork that states it
(by file and line), note whether that review reproduced it, and list the published tools whose
unmatched candidates describe the same issue (word-overlap against results/<judge>/evaluations.json).
Writes contrib/out/<repo>.md (PR body), contrib/out/golden_comments/<repo>.json (patched file) and
contrib/out/<repo>.diff.
"""

import difflib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "contrib" / "out"
ORG = "aether-bench"
REPO_FILE = {"calcom/cal.com": "cal_dot_com", "ai-code-review-evaluation/discourse-graphite": "discourse", "grafana/grafana": "grafana"}
STOP = set(["the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "be", "was", "were", "it", "its", "this", "that", "with", "from", "by", "as", "at", "not", "no", "can", "when", "then", "than", "into", "also", "only", "each", "any", "all", "which", "while", "because", "before", "after", "over", "under", "both", "same", "such", "more", "most", "less", "very", "just", "does", "do", "did", "have", "has", "had", "will", "would", "should", "could", "may", "might", "must", "use", "used", "using", "if", "else", "so", "there", "their", "they", "them", "these", "those", "now", "new"])


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9_.]{2,}", text.lower()) if w not in STOP}


def candidate_text(fp) -> str:
    return fp if isinstance(fp, str) else (fp.get("candidate") or json.dumps(fp))


def fork_repo_for(url: str) -> str:
    owner, repo, _, number = url.split("github.com/")[1].split("/")
    prefix = REPO_FILE[f"{owner}/{repo}"]
    names = subprocess.run(["gh", "repo", "list", ORG, "--limit", "1000", "--json", "name", "--jq", ".[].name"], capture_output=True, text=True, check=True).stdout.split()
    matches = [n for n in names if n.startswith(f"{prefix}__{repo}__aether-r1__PR{number}__")]
    if len(matches) != 1:
        raise RuntimeError(f"expected one fork for {url}, found {matches}")
    return matches[0]


def fork_comments(fork: str) -> list[dict]:
    out = []
    for pr in subprocess.run(["gh", "pr", "list", "--repo", f"{ORG}/{fork}", "--state", "all", "--limit", "50", "--json", "number", "--jq", ".[].number"], capture_output=True, text=True, check=True).stdout.split():
        comments = json.loads(subprocess.run(["gh", "api", f"repos/{ORG}/{fork}/pulls/{pr}/comments"], capture_output=True, text=True, check=True).stdout)
        out += [c for c in comments if c["user"]["login"] == "aether-agent[bot]"]
    return out


def main() -> None:
    proposed = json.load(open(ROOT / "contrib" / "proposed_goldens.json"))
    evaluations = json.load(open(ROOT / "results" / "anthropic_claude-opus-4-5-20251101" / "evaluations.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "golden_comments").mkdir(exist_ok=True)
    by_repo: dict[str, list[dict]] = {}
    fork_cache: dict[str, list[dict]] = {}
    for entry in proposed:
        url = entry["url"]
        fork = fork_repo_for(url)
        if fork not in fork_cache:
            fork_cache[fork] = fork_comments(fork)
        near = [c for c in fork_cache[fork] if c["path"].endswith(entry["path"]) and c.get("line") and abs(c["line"] - entry["line"]) <= 8]
        if not near:
            raise RuntimeError(f"no review comment near {entry['path']}:{entry['line']} on {fork}")
        best = max(near, key=lambda c: len(words(c["body"]) & words(entry["comment"])))
        reproduced = bool(re.search(r"reproduc", best["body"], re.I))
        ours = words(re.sub(r"<sub>.*?</sub>", "", best["body"]))
        corroborating = []
        pattern = re.compile(entry["corroboration_pattern"], re.I) if entry.get("corroboration_pattern") else None
        for tool, result in evaluations.get(url, {}).items():
            if result.get("skipped") or tool.startswith("mra-"):
                continue
            for fp in result.get("false_positives", []):
                text = candidate_text(fp)
                theirs = words(text)
                overlap = len(ours & theirs) >= 6 and len(ours & theirs) / len(ours | theirs) >= 0.12
                if overlap or (pattern and pattern.search(text)):
                    corroborating.append(tool)
                    break
        entry.update({"evidence_url": best["html_url"], "reproduced": reproduced, "corroborated_by": sorted(set(corroborating))})
        by_repo.setdefault(url.rsplit("/", 2)[0], []).append(entry)

    for repo_url, entries in by_repo.items():
        owner_repo = repo_url.split("github.com/")[1]
        stem = REPO_FILE[owner_repo]
        golden_path = ROOT / "golden_comments" / f"{stem}.json"
        golden = json.load(open(golden_path))
        by_url = {e["url"]: e for e in golden}
        for entry in entries:
            by_url[entry["url"]]["comments"].append({"comment": entry["comment"], "severity": entry["severity"], "category": entry["category"]})
        patched = json.dumps(golden, indent=2, ensure_ascii=False) + "\n"
        (OUT / "golden_comments" / f"{stem}.json").write_text(patched)
        original = golden_path.read_text()
        diff = difflib.unified_diff(original.splitlines(True), patched.splitlines(True), f"a/offline/golden_comments/{stem}.json", f"b/offline/golden_comments/{stem}.json")
        (OUT / f"{stem}.diff").write_text("".join(diff))

        lines = [f"# Golden set: {len(entries)} additional issues on the {owner_repo} PRs", "",
                 "Each entry below is an issue that a review of the benchmark PR surfaced, that the current gold set does not contain, "
                 "and that is corroborated by at least one of: a recorded reproduction in the review, or the same finding appearing among "
                 "other published tools' unmatched candidates in `results/anthropic_claude-opus-4-5-20251101/evaluations.json` "
                 "(the methodology's \"multiple strong tools agree against the gold set\" signal).", "",
                 "Disclosure: these were found by Aether Review, a vendor tool, on public forks in the `aether-bench` GitHub org. "
                 "Every linked review comment is public and states the trigger; the entries stand or fall on that evidence.", "",
                 "Adding them changes the gold set for every tool, so this is a new golden-set version in the sense of #52; "
                 "re-running step 3 against stored candidates re-scores existing tools without re-running them.", "",
                 "| PR | proposed golden comment | severity / category | corroborated by | reproduced | evidence |", "|---|---|---|---|---|---|"]
        for e in sorted(entries, key=lambda e: int(e["url"].rsplit("/", 1)[1])):
            tools = ", ".join(e["corroborated_by"]) or "—"
            lines.append(f"| #{e['url'].rsplit('/', 1)[1]} | {e['comment']} | {e['severity']} / {e['category']} | {tools} | {'yes' if e['reproduced'] else 'no'} | [review comment]({e['evidence_url']}) |")
        (OUT / f"{stem}.md").write_text("\n".join(lines) + "\n")
        n_corr = sum(1 for e in entries if e["corroborated_by"])
        n_repro = sum(1 for e in entries if e["reproduced"])
        print(f"{stem:12} {len(entries):2} entries | corroborated by another tool: {n_corr:2} | reproduced in review: {n_repro:2} | neither: {sum(1 for e in entries if not e['corroborated_by'] and not e['reproduced'])}")
    json.dump(proposed, open(OUT / "proposed_goldens_with_evidence.json", "w"), indent=1)


if __name__ == "__main__":
    main()
