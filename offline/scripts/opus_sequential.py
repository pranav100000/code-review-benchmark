#!/usr/bin/env python3
"""Run the remaining Opus benchmark reviews one at a time.

For every fork in variants/aether-final-final-opus.json without an aether-agent review:
trigger a review with an "aether review" comment, wait until the review posts or the task
errors; on a Claude session-limit error sleep until the reset time the error names and
retry the same PR. Any other error is recorded and the next PR starts. Exits non-zero when
any PR is left without a review.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

OFFLINE = Path("/Users/pranavsharan/Developer/code-review-benchmark/offline")
VARIANTS = OFFLINE / "variants/aether-final-final-opus.json"
LIMIT_RE = re.compile(r"resets (\d{1,2}):(\d{2})(am|pm) \(UTC\)")
POLL_SECONDS = 60
TASK_APPEAR_TIMEOUT = 15 * 60
REVIEW_TIMEOUT = 100 * 60
MAX_LIMIT_RETRIES = 12


def log(msg: str) -> None:
    print(f"{dt.datetime.now(dt.timezone.utc):%m-%d %H:%M:%SZ} {msg}", flush=True)


RETRY_ATTEMPTS = 20
RETRY_SLEEP = 30


def sh(args: list[str]) -> str:
    """Run a gh/aether command; retry transport failures (the laptop sleeps and drops its network)."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        err = r.stderr.strip()[:300]
        if attempt == RETRY_ATTEMPTS:
            raise RuntimeError(f"{' '.join(args[:4])} failed ({r.returncode}) after {RETRY_ATTEMPTS} attempts: {err}")
        log(f"retry {attempt}/{RETRY_ATTEMPTS} in {RETRY_SLEEP}s: {' '.join(args[:3])} -> {err[:120]}")
        time.sleep(RETRY_SLEEP)
    raise AssertionError("unreachable")


def recently_triggered(repo: str, pr: int, since: dt.datetime) -> bool:
    out = sh(["gh", "api", f"repos/aether-bench/{repo}/issues/{pr}/comments", "--jq",
              '.[-1] | "\\(.created_at) \\(.body)"']).strip()
    if not out:
        return False
    created, body = out.split(" ", 1)
    return body.strip() == "aether review" and parse_ts(created) >= since


def trigger(repo: str, pr: int, since: dt.datetime) -> None:
    """Post the trigger comment; a failed post is retried only after checking it did not land."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        r = subprocess.run(["gh", "pr", "comment", str(pr), "--repo", f"aether-bench/{repo}", "--body", "aether review"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return
        log(f"trigger attempt {attempt}/{RETRY_ATTEMPTS} failed: {r.stderr.strip()[:120]}")
        time.sleep(RETRY_SLEEP)
        if recently_triggered(repo, pr, since):
            log(f"{repo}#{pr}: trigger comment landed despite the error")
            return
    raise RuntimeError(f"could not post the trigger comment on {repo}#{pr}")


def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(re.sub(r"\.\d+", "", s).replace("Z", "+00:00"))


def review_count(repo: str, pr: int) -> int:
    out = sh(["gh", "api", f"repos/aether-bench/{repo}/pulls/{pr}/reviews", "--jq",
              '[.[] | select(.user.login=="aether-agent[bot]")] | length']).strip()
    return int(out)


def tasks_for(project_id: str) -> list[dict]:
    data = json.loads(sh(["aether", "task", "list", "--project", project_id, "--json"]))
    return sorted(data.get("tasks", []), key=lambda t: t["created_at"])


def task_get(task_id: str) -> dict:
    data = json.loads(sh(["aether", "task", "get", task_id, "--json"]))
    return data.get("task", data)


def reset_time(error: str, now: dt.datetime) -> dt.datetime:
    m = LIMIT_RE.search(error)
    if not m:
        raise RuntimeError(f"cannot parse reset time from limit error: {error!r}")
    hour, minute, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
    hour = hour % 12 + (12 if ampm == "pm" else 0)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += dt.timedelta(days=1)
    return candidate


def sleep_until(when: dt.datetime, why: str) -> None:
    # Short sleeps checked against the wall clock: one long sleep does not advance while the Mac sleeps.
    target = when + dt.timedelta(seconds=120)
    log(f"sleeping until {target:%H:%M}Z: {why}")
    while (remaining := (target - dt.datetime.now(dt.timezone.utc)).total_seconds()) > 0:
        time.sleep(min(60, remaining))
    log(f"awake at {dt.datetime.now(dt.timezone.utc):%H:%M}Z")


def wait_for_new_task(project_id: str, after: dt.datetime) -> dict:
    deadline = time.monotonic() + TASK_APPEAR_TIMEOUT
    while time.monotonic() < deadline:
        for t in reversed(tasks_for(project_id)):
            if parse_ts(t["created_at"]) >= after:
                return t
        time.sleep(20)
    raise RuntimeError(f"no task appeared in project {project_id} within {TASK_APPEAR_TIMEOUT//60} min of the trigger")


def run_one(repo: str, pr: int, project_id: str) -> str:
    """Returns 'reviewed' or an error description."""
    limit_retries = 0
    while True:
        if review_count(repo, pr) > 0:
            return "reviewed"
        trigger_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)
        trigger(repo, pr, trigger_at)
        task = wait_for_new_task(project_id, trigger_at)
        log(f"{repo}#{pr}: task {task['id']} created")
        started = time.monotonic()
        while True:
            time.sleep(POLL_SECONDS)
            if review_count(repo, pr) > 0:
                log(f"{repo}#{pr}: review posted after {(time.monotonic()-started)/60:.0f} min")
                return "reviewed"
            t = task_get(task["id"])
            if t.get("error"):
                break
            if t.get("display_status") in ("errored", "stopped", "completed"):
                break
            if time.monotonic() - started > REVIEW_TIMEOUT:
                return f"task {task['id']} still {t.get('display_status')} after {REVIEW_TIMEOUT//60} min"
        error = t.get("error") or f"display_status={t.get('display_status')} with no review"
        if "weekly limit" in error:
            # A weekly limit resets days later: stop the whole run instead of failing every remaining PR.
            raise RuntimeError(f"{repo}#{pr}: task {task['id']}: {error}")
        if "limit" in error and LIMIT_RE.search(error):
            limit_retries += 1
            if limit_retries > MAX_LIMIT_RETRIES:
                return f"gave up after {MAX_LIMIT_RETRIES} session-limit retries: {error}"
            sleep_until(reset_time(error, dt.datetime.now(dt.timezone.utc)), error)
            continue
        return f"task {task['id']} failed: {error[:200]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="only list what would run")
    args = ap.parse_args()
    repos = json.load(open(VARIANTS))["repos"]
    projects = json.loads(sh(["aether", "project", "list", "--json"]))
    by_repo = {p["repo_url"].lower().rsplit("/", 1)[-1].removesuffix(".git"): p["id"]
               for p in projects if p.get("repo_url")}
    todo = [(repo, info["pr_number"], by_repo[repo.lower()])
            for repo, info in sorted(repos.items()) if review_count(repo, info["pr_number"]) == 0]
    log(f"{len(todo)} Opus PRs without a review")
    if args.list:
        for repo, pr, _ in todo:
            print(f"  {repo}#{pr}")
        return 0
    failures = []
    for i, (repo, pr, project_id) in enumerate(todo, 1):
        log(f"[{i}/{len(todo)}] {repo}#{pr}: triggering")
        outcome = run_one(repo, pr, project_id)
        log(f"[{i}/{len(todo)}] {repo}#{pr}: {outcome}")
        if outcome != "reviewed":
            failures.append((repo, pr, outcome))
    log(f"OPUS SEQUENTIAL DONE: {len(todo)-len(failures)} reviewed, {len(failures)} failed")
    for repo, pr, outcome in failures:
        log(f"  FAILED {repo}#{pr}: {outcome}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
