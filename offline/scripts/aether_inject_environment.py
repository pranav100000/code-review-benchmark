#!/usr/bin/env python3
"""Add .aether/environment.json to benchmark forks without re-forking, keeping each PR's diff unchanged.

For each fork of the tool slug: commit the file onto the PR's base branch through the GitHub contents
API, then merge the base branch into the PR branch through the merges API. The PR's three-dot diff is
still exactly the upstream change; the checkout the reviewer gets now carries the file.

Usage:
  uv run python scripts/aether_inject_environment.py --tool aether-r1 --env-dir contrib/env [--only 10600 4] [--dry-run]
"""

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess

ORG = "aether-bench"
PATH = ".aether/environment.json"


def gh_json(*args: str):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--env-dir", type=Path, required=True, help="dir with <prefix>/environment.json per project")
    parser.add_argument("--only", nargs="*", default=None, help="restrict to forks: PR numbers or prefix:number")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    listing = gh_json("repo", "list", ORG, "--limit", "1000", "--json", "name")
    names = [r["name"] for r in listing if f"__{args.tool}__" in r["name"]]
    for name in sorted(names):
        match = re.match(r"^(.+?)__(.+?)__.+?__PR(\d+)__", name)
        prefix, number = match.group(1), match.group(3)
        if args.only and number not in set(args.only) and f"{prefix}:{number}" not in set(args.only):
            continue
        env_path = args.env_dir / prefix / "environment.json"
        if not env_path.exists():
            raise RuntimeError(f"no environment file for {prefix} at {env_path}")
        try:
            pr = gh_json("api", f"repos/{ORG}/{name}/pulls/1")
        except RuntimeError:
            print(f"  {name}: no PR #1, skipped")
            continue
        if not pr["head"]["ref"].startswith("pr-"):
            print(f"  ERROR {name}: PR #1 head is {pr['head']['ref']!r}, not the benchmark branch; skipped")
            continue
        base, head = pr["base"]["ref"], pr["head"]["ref"]
        existing = subprocess.run(
            ["gh", "api", f"repos/{ORG}/{name}/contents/{PATH}?ref={base}", "--jq", ".sha"],
            capture_output=True, text=True,
        )
        if args.dry_run:
            verb = "update" if existing.returncode == 0 else "add"
            print(f"  {name}: would {verb} {PATH} on {base} and merge {base} into {head}")
            continue
        body = {"message": "Add .aether/environment.json for benchmark reviews", "branch": base,
                "content": base64.b64encode(env_path.read_bytes()).decode()}
        if existing.returncode == 0:
            body["sha"] = existing.stdout.strip()
        subprocess.run(
            ["gh", "api", "-X", "PUT", f"repos/{ORG}/{name}/contents/{PATH}", "--input", "-"],
            input=json.dumps(body), capture_output=True, text=True, check=True,
        )
        merge = subprocess.run(
            ["gh", "api", "-X", "POST", f"repos/{ORG}/{name}/merges", "-f", f"base={head}", "-f", f"head={base}",
             "-f", "commit_message=Merge base with .aether/environment.json into the PR branch"],
            capture_output=True, text=True,
        )
        if merge.returncode != 0 and "Nothing to merge" not in merge.stderr and "already" not in merge.stderr:
            raise RuntimeError(f"{name}: merge {base} -> {head} failed:\n{merge.stderr.strip()}")
        print(f"  {name}: {PATH} on {base}; {base} merged into {head}")


if __name__ == "__main__":
    main()
