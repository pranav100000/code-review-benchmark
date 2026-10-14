#!/usr/bin/env python3
"""Run one prompt/config variant of Aether Review over the existing benchmark forks.

For every fork of the given tool slug:
  1. set the project's review prompt (and optionally reasoning effort / agent / model),
  2. close the open PR and open a fresh one from the same branches, so the reviewer
     sees no earlier bot comments,
  3. post `aether review` on the new PR,
  4. record the PR number in variants/<variant>.json for step1 --variants-file.

Idempotent per repo: a repo already recorded for this variant is skipped. Any failure aborts.

Usage:
  uv run python scripts/aether_variant_run.py --tool aether-r1 --variant v2 --prompt-file prompts/v2-coverage.md
  uv run python scripts/aether_variant_run.py --tool aether-r1 --variant v3 --prompt-file prompts/v2-coverage.md \
    --reasoning-effort max
"""

import argparse
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import time

from aether_link_and_trigger import TRIGGER_COMMENT
from aether_link_and_trigger import CorruptForkError
from aether_link_and_trigger import bench_repos
from aether_link_and_trigger import projects_by_repo
from aether_link_and_trigger import run
from aether_link_and_trigger import run_json

VARIANTS_DIR = Path(__file__).resolve().parent.parent / "variants"


def load_variant(path: Path, args: argparse.Namespace, prompt: str | None) -> dict:
    if path.exists():
        variant = json.loads(path.read_text())
        if variant["tool_slug"] != args.tool:
            raise RuntimeError(f"{path} belongs to tool slug {variant['tool_slug']!r}, not {args.tool!r}")
        return variant
    return {
        "variant": args.variant,
        "tool_name": f"{args.tool}-{args.variant}",
        "tool_slug": args.tool,
        "prompt_file": str(args.prompt_file) if args.prompt_file else None,
        "prompt": prompt,
        "reasoning_effort": args.reasoning_effort,
        "agent_type": args.agent_type,
        "model": args.model,
        "vm_size": args.vm_size,
        "repos": {},
    }


def configure_project(project_id: str, prompt: str | None, args: argparse.Namespace) -> None:
    cmd = ["aether", "project", "update", project_id, "--json"]
    if prompt is not None:
        cmd += ["--pr-review-prompt", prompt]
    if args.reasoning_effort:
        cmd += ["--reasoning-effort", args.reasoning_effort]
    if args.agent_type:
        cmd += ["--agent-type", args.agent_type]
    if args.model:
        cmd += ["--model", args.model]
    if args.vm_size:
        cmd += ["--default-size", args.vm_size]
    if len(cmd) == 5:
        raise RuntimeError(
            "nothing to configure: pass --prompt-file, --default-prompt, --reasoning-effort, "
            "--agent-type, --model or --vm-size"
        )
    run(*cmd)



def run_retrying(*cmd: str) -> str:
    """GitHub's GraphQL API fails transiently ("Something went wrong while executing your query");
    one retry after a pause is enough and keeps a 49-fork launch from dying on fork 17."""
    try:
        return run(*cmd)
    except RuntimeError as exc:
        transient = ("Something went wrong", "502", "503", "HTTP 401", "Requires authentication")
        if not any(s in str(exc) for s in transient) and "timeout" not in str(exc).lower():
            raise
        print(f"  transient GitHub error, retrying once: {str(exc).splitlines()[-1][:120]}")
        time.sleep(20)
        return run(*cmd)

def open_fresh_pr(org: str, repo: str, sibling_branch: str | None = None) -> int | None:
    """None when the repo has no PR #1 (a fork that was interrupted before its PR was opened)."""
    full = f"{org}/{repo}"
    prs = run_json("gh", "pr", "list", "--repo", full, "--state", "open", "--limit", "200", "--json", "number,state")
    probe = subprocess.run(["gh", "api", f"repos/{full}/pulls/1"], capture_output=True, text=True)
    if probe.returncode != 0:
        return None
    pr1 = json.loads(probe.stdout)
    first = {
        "headRefName": pr1["head"]["ref"],
        "baseRefName": pr1["base"]["ref"],
        "title": pr1["title"],
        "body": pr1["body"],
    }
    if not first["headRefName"].startswith("pr-"):
        head = first["headRefName"]
        raise CorruptForkError(f"{full}: PR #1 head is {head!r}, not the benchmark branch; re-fork it")
    head_ref = first["headRefName"]
    if sibling_branch:
        # Leave every existing PR open; open the new PR from a sibling branch at the same commit, so each PR keeps one review.
        head_ref = f"{first['headRefName']}-{sibling_branch}"
        existing = subprocess.run(["gh", "api", f"repos/{full}/git/ref/heads/{head_ref}"], capture_output=True, text=True)
        if existing.returncode != 0:
            run_retrying("gh", "api", f"repos/{full}/git/refs", "-f", f"ref=refs/heads/{head_ref}", "-f", f"sha={pr1['head']['sha']}")
    else:
        for pr in prs:
            if pr["state"] == "OPEN":
                run_retrying("gh", "pr", "close", str(pr["number"]), "--repo", full)
    url = run_retrying("gh", "pr", "create", "--repo", full, "--head", head_ref, "--base", first["baseRefName"],
                       "--title", first["title"], "--body", first["body"] or "").strip().splitlines()[-1]
    match = re.search(r"/pull/(\d+)$", url)
    if not match:
        raise RuntimeError(f"could not parse PR number from gh pr create output: {url!r}")
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org", default="aether-bench")
    parser.add_argument("--tool", required=True, help="fork slug the repos were created with")
    parser.add_argument("--variant", required=True, help="short variant name, e.g. v2")
    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument("--prompt-file", type=Path, help="project review prompt text for this variant")
    prompt_group.add_argument("--default-prompt", action="store_true", help="restore the default project review prompt")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--agent-type")
    parser.add_argument("--model")
    parser.add_argument("--vm-size", choices=["small", "medium", "large"], help="project VM size for the reviews")
    parser.add_argument("--stagger-seconds", type=int, default=0, help="pause between repos so review posts spread out")
    parser.add_argument("--only", nargs="*", default=None, help="restrict to forks of these source PR numbers")
    parser.add_argument("--sibling-branch", default=None, help="open the variant PR from <head>-<suffix> at the same commit instead of closing the open PR")
    args = parser.parse_args()

    prompt = args.prompt_file.read_text().strip() if args.prompt_file else ("" if args.default_prompt else None)
    VARIANTS_DIR.mkdir(exist_ok=True)
    path = VARIANTS_DIR / f"{args.tool}-{args.variant}.json"
    variant = load_variant(path, args, prompt)

    repos = bench_repos(args.org, args.tool)
    if args.only:
        wanted = set(args.only)
        def wanted_repo(name: str) -> bool:
            number = re.search(r"__PR(\d+)__", name).group(1)
            return number in wanted or f"{name.split('__')[0]}:{number}" in wanted

        repos = [r for r in repos if wanted_repo(r)]
    if not repos:
        raise SystemExit(f"no repos in {args.org} match tool slug {args.tool!r}")
    by_repo = projects_by_repo()
    print(f"variant {variant['tool_name']}: {len(repos)} repos, {len(variant['repos'])} already done")

    corrupt: list[str] = []
    for repo in repos:
        if repo in variant["repos"]:
            continue
        project = by_repo.get(f"{args.org}/{repo}".lower())
        if project is None:
            print(f"  {repo}: no linked Aether project yet, skipped (run aether_link_and_trigger.py, then rerun)")
            continue
        try:
            pr_number = open_fresh_pr(args.org, repo, args.sibling_branch)
        except CorruptForkError as exc:
            print(f"  ERROR {exc}")
            corrupt.append(repo)
            continue
        if pr_number is None:
            print(f"  {repo}: no PR #1, skipped")
            continue
        configure_project(project["id"], prompt, args)
        run("gh", "pr", "comment", str(pr_number), "--repo", f"{args.org}/{repo}", "--body", TRIGGER_COMMENT)
        variant["repos"][repo] = {"pr_number": pr_number, "triggered_at": datetime.now(UTC).isoformat()}
        path.write_text(json.dumps(variant, indent=2) + "\n")
        print(f"  {repo}: PR #{pr_number} opened and triggered", flush=True)
        if args.stagger_seconds:
            time.sleep(args.stagger_seconds)

    numbers = sorted({r["pr_number"] for r in variant["repos"].values()})
    print(f"done: {len(variant['repos'])} repos, PR numbers {numbers}")
    print(f"next: step1_download_prs --org {args.org} --tool {args.tool} --variants-file {path}")
    if corrupt:
        raise SystemExit(f"{len(corrupt)} corrupt fork(s) must be deleted and re-forked: {corrupt}")


if __name__ == "__main__":
    main()
