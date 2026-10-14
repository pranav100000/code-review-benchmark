#!/usr/bin/env python3
"""Print one progress line for a benchmark run: forks, repos, triggers, posted reviews.

Exit code 10 means the run is complete (fork loop done, link loop done, every repo reviewed).

Usage:
  uv run python scripts/aether_run_progress.py --tool aether-r1 --fork-log fork_r1.log --link-log link_r1.log
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def gh_json(*args: str):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout)


def pr_reviews(org: str, repo: str) -> list | None:
    """None when PR #1 does not exist yet (the repo is still being pushed)."""
    result = subprocess.run(["gh", "api", f"repos/{org}/{repo}/pulls/1/reviews"], capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "404" in result.stderr:
        return None
    raise RuntimeError(f"gh api pulls/1/reviews failed for {org}/{repo}:\n{result.stderr.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", default="aether-bench")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--fork-log", type=Path, required=True)
    parser.add_argument("--link-log", type=Path, required=True)
    parser.add_argument("--bot", default="aether-agent[bot]")
    args = parser.parse_args()

    fork_log = args.fork_log.read_text() if args.fork_log.exists() else ""
    link_log = args.link_log.read_text() if args.link_log.exists() else ""
    forks_ok = fork_log.count("SUCCESS!")
    fork_errors = [line for line in fork_log.splitlines() if line.startswith("Error processing")]
    forks_done = "=== ALL DONE" in fork_log
    link_done = "=== LINK LOOP DONE" in link_log
    triggered = sum(1 for line in link_log.splitlines() if "), commented" in line or "already commented" in line)

    marker = f"__{args.tool}__"
    all_repos = gh_json("repo", "list", args.org, "--limit", "1000", "--json", "name")
    repos = sorted(r["name"] for r in all_repos if marker in r["name"])
    reviewed = []
    prs_open = 0
    for repo in repos:
        reviews = pr_reviews(args.org, repo)
        if reviews is None:
            continue
        prs_open += 1
        if any(r["user"]["login"] == args.bot for r in reviews):
            reviewed.append(repo)

    stamp = time.strftime("%H:%M:%S", time.gmtime())
    print(
        f"{stamp} forks_ok={forks_ok} fork_errors={len(fork_errors)} repos={len(repos)} prs_open={prs_open} "
        f"triggered={triggered} reviews={len(reviewed)} forks_done={forks_done} link_done={link_done}"
    )
    for line in fork_errors[-3:]:
        print("  " + line[:200])
    if forks_done and link_done and repos and len(reviewed) == len(repos):
        print("RUN COMPLETE")
        sys.exit(10)


if __name__ == "__main__":
    main()
