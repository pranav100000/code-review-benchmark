#!/usr/bin/env python3
"""Link every benchmark fork for one tool slug to an Aether project and trigger its review.

For each repo in the org whose name matches {prefix}__{repo}__{tool}__PR{n}__{date}:
  1. find the Aether project linked to it, or create one and import the repo,
  2. enable the `aether review` comment trigger and pin the review agent,
  3. post `aether review` on PR #1 unless that comment already exists.

Idempotent: rerunning skips every step that is already done. Any failure aborts.

Usage:
  uv run python scripts/aether_link_and_trigger.py --tool aether-r1 --installation-id 168675679
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_NAME = re.compile(r"^(?P<prefix>.+?)__(?P<repo>.+?)__(?P<tool>.+?)__PR(?P<pr>\d+)__(?P<date>\d+)$")
TRIGGER_COMMENT = "aether review"


class CorruptForkError(RuntimeError):
    """A fork whose PR #1 is not the benchmark PR."""


def run(*cmd: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout


def run_json(*cmd: str):
    return json.loads(run(*cmd))


def normalize_repo(url: str) -> str:
    url = url.strip().lower()
    url = re.sub(r"^https://github\.com/", "", url)
    url = re.sub(r"^git@github\.com:", "", url)
    return url.removesuffix(".git").strip("/")


def bench_repos(org: str, tool: str) -> list[str]:
    repos = run_json("gh", "repo", "list", org, "--limit", "1000", "--json", "name")
    names = []
    for entry in repos:
        match = REPO_NAME.match(entry["name"])
        if match and match.group("tool") == tool:
            names.append(entry["name"])
    return sorted(names)


def projects_by_repo() -> dict[str, dict]:
    projects = run_json("aether", "project", "list", "--json")
    by_repo: dict[str, dict] = {}
    for project in projects:
        repo_url = project.get("repo_url")
        if not repo_url:
            continue
        key = normalize_repo(repo_url)
        if key in by_repo:
            raise RuntimeError(f"two projects link {key}: {by_repo[key]['id']} and {project['id']}")
        by_repo[key] = project
    return by_repo


def pr_exists(org: str, repo: str) -> bool:
    """PR #1 appears minutes after the repo while step0 is still pushing; such repos are skipped until it exists."""
    result = subprocess.run(["gh", "api", f"repos/{org}/{repo}/pulls/1"], capture_output=True, text=True)
    if result.returncode == 0:
        head = json.loads(result.stdout)["head"]["ref"]
        if not head.startswith("pr-"):
            # Dependabot can open PR #1 in a fork whose step0 run died before creating the real PR.
            raise CorruptForkError(f"{org}/{repo}: PR #1 head is {head!r}, not the benchmark branch; re-fork it")
        return True
    if "404" in result.stderr or "Not Found" in result.stderr:
        return False
    raise RuntimeError(f"gh api pulls/1 failed for {org}/{repo}:\n{result.stderr.strip()}")


def ensure_project(org: str, repo: str, by_repo: dict[str, dict], installation_id: int) -> tuple[str, str]:
    full = f"{org}/{repo}"
    existing = by_repo.get(full.lower())
    if existing:
        return existing["id"], "existing"
    # Project names allow only letters, numbers, dashes and underscores; the link itself is by repo URL.
    project_name = re.sub(r"[^A-Za-z0-9_-]", "-", repo)
    created = run_json("aether", "project", "create", "--name", project_name, "--json")
    project_id = created["id"]
    run(
        "aether", "github", "import", "--project", project_id, "--repo", full,
        "--installation-id", str(installation_id), "--json",
    )
    return project_id, "created"


def configure_review(
    project_id: str, agent_type: str, model: str, reasoning_effort: str | None, vm_size: str | None, prompt: str | None = None
) -> None:
    cmd = [
        "aether", "project", "update", project_id,
        "--pr-review-comment-trigger", "true",
        "--agent-type", agent_type,
        "--model", model,
        "--json",
    ]
    if prompt is not None:
        cmd += ["--pr-review-prompt", prompt]
    if reasoning_effort:
        cmd += ["--reasoning-effort", reasoning_effort]
    if vm_size:
        cmd += ["--default-size", vm_size]
    run(*cmd)


def ensure_trigger_comment(org: str, repo: str) -> str:
    bodies = run_json("gh", "api", f"repos/{org}/{repo}/issues/1/comments", "--jq", "[.[].body]")
    if any(body.strip().lower() == TRIGGER_COMMENT for body in bodies):
        return "already commented"
    run("gh", "pr", "comment", "1", "--repo", f"{org}/{repo}", "--body", TRIGGER_COMMENT)
    return "commented"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org", default="aether-bench")
    parser.add_argument("--tool", required=True, help="tool slug used with step0_fork_prs --name")
    parser.add_argument("--installation-id", type=int, required=True, help="GitHub App installation id on the org")
    parser.add_argument("--agent-type", default="claude-code")
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--vm-size", choices=["small", "medium", "large"], default=None)
    parser.add_argument("--no-trigger", action="store_true", help="link projects without posting the comment")
    parser.add_argument("--pr-review-prompt-file", type=Path, help="pin this review prompt on every project before triggering")
    parser.add_argument("--stagger-seconds", type=int, default=0, help="pause after each posted trigger comment")
    parser.add_argument("--dry-run", action="store_true", help="list what would happen, change nothing")
    args = parser.parse_args()
    prompt = args.pr_review_prompt_file.read_text().strip() if args.pr_review_prompt_file else None

    repos = bench_repos(args.org, args.tool)
    if not repos:
        sys.exit(f"no repos in {args.org} match tool slug {args.tool!r}")
    by_repo = projects_by_repo()
    print(f"{len(repos)} repos for tool {args.tool!r} in {args.org}")

    corrupt: list[str] = []
    for repo in repos:
        if args.dry_run:
            linked = by_repo.get(f"{args.org}/{repo}".lower())
            print(f"  {repo}: {'linked to ' + linked['id'] if linked else 'no project yet'}")
            continue
        try:
            if not pr_exists(args.org, repo):
                print(f"  {repo}: no PR #1 yet, skipped")
                continue
        except CorruptForkError as exc:
            print(f"  ERROR {exc}")
            corrupt.append(repo)
            continue
        project_id, project_state = ensure_project(args.org, repo, by_repo, args.installation_id)
        configure_review(project_id, args.agent_type, args.model, args.reasoning_effort, args.vm_size, prompt)
        comment_state = "not triggered" if args.no_trigger else ensure_trigger_comment(args.org, repo)
        if comment_state == "commented" and args.stagger_seconds:
            time.sleep(args.stagger_seconds)
        print(f"  {repo}: project {project_id} ({project_state}), {comment_state}")
    if corrupt:
        sys.exit(f"{len(corrupt)} corrupt fork(s) must be deleted and re-forked: {corrupt}")


if __name__ == "__main__":
    main()
