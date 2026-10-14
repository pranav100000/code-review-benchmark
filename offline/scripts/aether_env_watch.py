#!/usr/bin/env python3
"""Print one status line per fork for a variant: review posted, or the latest task status and message.

Exit code 10 when every fork has posted or its task has ended without posting.
"""

import argparse
import json
import subprocess
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants-file", required=True)
    args = parser.parse_args()
    v = json.load(open(args.variants_file))
    projects = json.loads(subprocess.run(["aether", "project", "list", "--json"], capture_output=True, text=True).stdout)
    by_repo = {p["repo_url"].lower().rsplit("/", 1)[-1].removesuffix(".git"): p["id"] for p in projects if p.get("repo_url")}
    settled = 0
    print(time.strftime("%H:%M:%S", time.gmtime()))
    for repo, info in sorted(v["repos"].items()):
        n = subprocess.run(["gh", "api", f"repos/aether-bench/{repo}/pulls/{info['pr_number']}/reviews", "--jq",
                            '[.[] | select(.user.login=="aether-agent[bot]")] | length'], capture_output=True, text=True).stdout.strip()
        if n not in ("", "0"):
            settled += 1
            print(f"  {repo.split('__')[0]:12} POSTED")
            continue
        tasks = json.loads(subprocess.run(["aether", "task", "list", "--project", by_repo[repo.lower()], "--json"],
                                          capture_output=True, text=True).stdout)["tasks"]
        t = sorted(tasks, key=lambda t: t["created_at"])[-1]
        status = t["display_status"]
        if status not in ("running", "queued", "starting"):
            settled += 1
        print(f"  {repo.split('__')[0]:12} {status:10} {(t.get('latest_status_message') or '').replace(chr(10), ' ')[:100]}")
    if settled == len(v["repos"]):
        print("SETTLED")
        sys.exit(10)


if __name__ == "__main__":
    main()
